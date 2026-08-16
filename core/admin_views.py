"""
Custom Admin Panel Views for Citi Group.
All views require staff access.
"""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta

from .models import (
    User, Transaction, Loan, Card, Notification,
    ContactMessage, CryptoWallet, BankAccount, TVNRequest, Complaint,
)
from .utils import send_transaction_email, send_loan_email, send_card_email, send_complaint_email


# ──────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────
@staff_member_required
def admin_dashboard(request):
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    total_users = User.objects.filter(is_staff=False).count()
    total_balance = User.objects.filter(is_staff=False).aggregate(s=Sum('balance'))['s'] or 0
    pending_txns = Transaction.objects.filter(status='pending').count()
    pending_loans = Loan.objects.filter(status='pending').count()
    pending_cards = Card.objects.filter(status='pending').count()
    total_pending = pending_txns + pending_loans + pending_cards

    # Monthly stats
    monthly_deposits = Transaction.objects.filter(
        transaction_type='deposit', status='completed',
        created_at__gte=thirty_days_ago,
    ).aggregate(s=Sum('amount'))['s'] or 0
    monthly_withdrawals = Transaction.objects.filter(
        transaction_type='withdrawal', status='completed',
        created_at__gte=thirty_days_ago,
    ).aggregate(s=Sum('amount'))['s'] or 0
    new_users_month = User.objects.filter(
        is_staff=False, date_joined__gte=thirty_days_ago,
    ).count()

    recent_txns = Transaction.objects.select_related('user').order_by('-created_at')[:10]
    recent_users = User.objects.filter(is_staff=False).order_by('-date_joined')[:5]

    context = {
        'total_users': total_users,
        'total_balance': total_balance,
        'pending_txns': pending_txns,
        'pending_loans': pending_loans,
        'pending_cards': pending_cards,
        'total_pending': total_pending,
        'monthly_deposits': monthly_deposits,
        'monthly_withdrawals': monthly_withdrawals,
        'new_users_month': new_users_month,
        'recent_txns': recent_txns,
        'recent_users': recent_users,
    }
    return render(request, 'management/dashboard.html', context)


# ──────────────────────────────────────
# USER MANAGEMENT
# ──────────────────────────────────────
@staff_member_required
def admin_users(request):
    q = request.GET.get('q', '')
    users = User.objects.filter(is_staff=False)
    if q:
        users = users.filter(
            Q(email__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(account_number__icontains=q)
        )
    users = users.order_by('-date_joined')
    paginator = Paginator(users, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'management/users.html', {'users': page, 'q': q})


@staff_member_required
def admin_user_form(request, user_id=None):
    user = get_object_or_404(User, id=user_id) if user_id else None
    if request.method == 'POST':
        data = request.POST
        if user is None:
            user = User()
            if User.objects.filter(email=data.get('email')).exists():
                messages.error(request, 'A user with this email already exists.')
                return redirect('admin_user_form')
        elif user.email != data.get('email') and User.objects.filter(email=data.get('email')).exists():
            messages.error(request, 'A user with this email already exists.')
            return redirect('admin_user_edit', user_id=user.id)
            
        user.first_name = data.get('first_name')
        user.last_name = data.get('last_name')
        user.email = data.get('email')
        user.phone = data.get('phone', '')
        user.address = data.get('address', '')
        user.city = data.get('city', '')
        user.state = data.get('state', '')
        user.zip_code = data.get('zip_code', '')
        user.country = data.get('country', 'United States')
        user.account_tier = data.get('account_tier', 'standard')
        
        user.is_active = data.get('is_active') == 'on'
        user.is_email_verified = data.get('is_email_verified') == 'on'
        
        if not user_id:
            password = data.get('password')
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
                
        user.save()
        messages.success(request, f'User {user.get_full_name()} {"updated" if user_id else "created"} successfully.')
        return redirect('admin_user_detail', user_id=user.id)
        
    return render(request, 'management/user_form.html', {'target_user': user})


@staff_member_required
def admin_user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'credit':
            try:
                amount = Decimal(request.POST.get('amount', '0'))
                if amount > 0:
                    user.balance += amount
                    user.save()
                    tx = Transaction.objects.create(
                        user=user, transaction_type='deposit',
                        amount=amount, description=request.POST.get('description', 'Admin Credit').strip() or 'Admin Credit',
                        status='completed', balance_after=user.balance
                    )
                    send_transaction_email(user, tx)
                    messages.success(request, f'Credited ${amount:,.2f} to {user.get_full_name()}')
            except Exception:
                messages.error(request, 'Invalid credit amount')
        elif action == 'debit':
            try:
                amount = Decimal(request.POST.get('amount', '0'))
                if amount > 0:
                    if amount > user.balance:
                        messages.error(request, 'Insufficient funds for debit')
                    else:
                        user.balance -= amount
                        user.save()
                        tx = Transaction.objects.create(
                            user=user, transaction_type='withdrawal',
                            amount=amount, description=request.POST.get('description', 'Admin Debit').strip() or 'Admin Debit',
                            status='completed', balance_after=user.balance
                        )
                        send_transaction_email(user, tx)
                        messages.success(request, f'Debited ${amount:,.2f} from {user.get_full_name()}')
            except Exception:
                messages.error(request, 'Invalid debit amount')
        elif action == 'update_tier':
            tier = request.POST.get('tier')
            if tier in ['standard', 'gold', 'platinum']:
                user.account_tier = tier
                user.save()
                messages.success(request, f'Tier updated to {tier}')
        elif action == 'toggle_active':
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User {status}')
        elif action == 'toggle_verified':
            user.is_email_verified = not user.is_email_verified
            user.save()
            status = 'verified' if user.is_email_verified else 'unverified'
            messages.success(request, f'Email set to {status}')
        return redirect('admin_user_detail', user_id=user.id)

    transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:10]
    loans = Loan.objects.filter(user=user)
    cards = Card.objects.filter(user=user)
    context = {
        'target_user': user,
        'transactions': transactions,
        'loans': loans,
        'cards': cards,
    }
    return render(request, 'management/user_detail.html', context)


# ──────────────────────────────────────
# TRANSACTION MANAGEMENT
# ──────────────────────────────────────
@staff_member_required
def admin_transactions(request):
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    q = request.GET.get('q', '')

    txns = Transaction.objects.select_related('user').all()
    if status_filter:
        txns = txns.filter(status=status_filter)
    if type_filter:
        txns = txns.filter(transaction_type=type_filter)
    if q:
        txns = txns.filter(
            Q(user__email__icontains=q) | Q(description__icontains=q) |
            Q(user__account_number__icontains=q)
        )
    txns = txns.order_by('-created_at')
    paginator = Paginator(txns, 25)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'management/transactions.html', {
        'transactions': page, 'status_filter': status_filter,
        'type_filter': type_filter, 'q': q,
    })
@staff_member_required
def admin_transaction_edit(request, tx_id):
    tx = get_object_or_404(Transaction, id=tx_id)
    if request.method == 'POST':
        date_str = request.POST.get('created_at')
        if date_str:
            from django.utils.dateparse import parse_datetime
            from django.utils import timezone
            parsed_date = parse_datetime(date_str)
            if parsed_date:
                if timezone.is_naive(parsed_date):
                    parsed_date = timezone.make_aware(parsed_date)
                Transaction.objects.filter(id=tx.id).update(created_at=parsed_date)
                
        amount_str = request.POST.get('amount')
        status = request.POST.get('status')
        description = request.POST.get('description')
        
        update_kwargs = {}
        if amount_str:
            try:
                from decimal import Decimal
                update_kwargs['amount'] = Decimal(amount_str)
            except Exception:
                pass
        if status in dict(Transaction.STATUS_CHOICES):
            update_kwargs['status'] = status
        if description is not None:
            update_kwargs['description'] = description
            
        if update_kwargs:
            Transaction.objects.filter(id=tx.id).update(**update_kwargs)
            
        messages.success(request, 'Transaction updated successfully.')
        return redirect('admin_transactions')
        
    return render(request, 'management/transaction_edit.html', {'tx': tx})


@staff_member_required
def admin_transaction_action(request, tx_id):
    if request.method == 'POST':
        tx = get_object_or_404(Transaction, id=tx_id)
        action = request.POST.get('action')
        user = tx.user

        if action == 'approve' and tx.status == 'pending':
            if tx.transaction_type == 'deposit':
                user.balance += tx.amount
                user.save()
                tx.status = 'completed'
                tx.balance_after = user.balance
                tx.save()
                Notification.objects.create(
                    user=user, notification_type='transaction',
                    title='Deposit Approved',
                    message=f'Your deposit of ${tx.amount:,.2f} has been approved.',
                    link='/transactions/',
                )
                send_transaction_email(user, tx)
                messages.success(request, f'Deposit of ${tx.amount:,.2f} approved')
            elif tx.transaction_type == 'withdrawal':
                if tx.amount > user.balance:
                    messages.error(request, f'Insufficient funds: user has ${user.balance:,.2f}')
                else:
                    user.balance -= tx.amount
                    user.save()
                    tx.status = 'completed'
                    tx.balance_after = user.balance
                    tx.save()
                    Notification.objects.create(
                        user=user, notification_type='transaction',
                        title='Withdrawal Approved',
                        message=f'Your withdrawal of ${tx.amount:,.2f} has been approved.',
                        link='/transactions/',
                    )
                    send_transaction_email(user, tx)
                    messages.success(request, f'Withdrawal of ${tx.amount:,.2f} approved')
            elif tx.transaction_type == 'transfer_out':
                if tx.amount > user.balance:
                    messages.error(request, f'Insufficient funds for transfer')
                else:
                    user.balance -= tx.amount
                    user.save()
                    tx.status = 'completed'
                    tx.balance_after = user.balance
                    tx.save()
                    if tx.recipient:
                        tx.recipient.balance += tx.amount
                        tx.recipient.save()
                        Transaction.objects.create(
                            user=tx.recipient,
                            transaction_type='transfer_in',
                            amount=tx.amount,
                            description=f'Transfer from {user.get_full_name()}',
                            status='completed',
                            balance_after=tx.recipient.balance,
                        )
                        Notification.objects.create(
                            user=tx.recipient, notification_type='transaction',
                            title='Transfer Received',
                            message=f'You received ${tx.amount:,.2f} from {user.get_full_name()}.',
                            link='/transactions/',
                        )
                    Notification.objects.create(
                        user=user, notification_type='transaction',
                        title='Transfer Approved',
                        message=f'Your transfer of ${tx.amount:,.2f} has been approved.',
                        link='/transactions/',
                    )
                    send_transaction_email(user, tx)
                    messages.success(request, f'Transfer of ${tx.amount:,.2f} approved')

        elif action == 'reject' and tx.status == 'pending':
            tx.status = 'rejected'
            tx.save()
            Notification.objects.create(
                user=user, notification_type='transaction',
                title='Transaction Rejected',
                message=f'Your {tx.get_transaction_type_display().lower()} of ${tx.amount:,.2f} has been rejected.',
                link='/transactions/',
            )
            messages.warning(request, f'Transaction rejected')

    return redirect('admin_transactions')


# ──────────────────────────────────────
# LOAN MANAGEMENT
# ──────────────────────────────────────
@staff_member_required
def admin_loans(request):
    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')
    loans_qs = Loan.objects.select_related('user').all()
    if status_filter:
        loans_qs = loans_qs.filter(status=status_filter)
    if q:
        loans_qs = loans_qs.filter(
            Q(user__email__icontains=q) | Q(user__first_name__icontains=q)
        )
    loans_qs = loans_qs.order_by('-created_at')
    paginator = Paginator(loans_qs, 25)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'management/loans.html', {
        'loans': page, 'status_filter': status_filter, 'q': q,
    })


@staff_member_required
def admin_loan_action(request, loan_id):
    if request.method == 'POST':
        loan = get_object_or_404(Loan, id=loan_id)
        action = request.POST.get('action')
        user = loan.user

        if action == 'approve' and loan.status == 'pending':
            user.balance += loan.amount
            user.save()
            loan.status = 'active'
            loan.save()
            Transaction.objects.create(
                user=user, transaction_type='loan_disbursement',
                amount=loan.amount,
                description=f'Loan disbursement - {loan.get_purpose_display()}',
                status='completed', balance_after=user.balance,
            )
            Notification.objects.create(
                user=user, notification_type='loan',
                title='Loan Approved',
                message=f'Your {loan.get_purpose_display()} loan of ${loan.amount:,.2f} has been approved.',
                link='/loans/',
            )
            send_loan_email(user, loan, 'approved')
            messages.success(request, f'Loan approved & ${loan.amount:,.2f} disbursed')

        elif action == 'reject' and loan.status == 'pending':
            loan.status = 'rejected'
            loan.save()
            Notification.objects.create(
                user=user, notification_type='loan',
                title='Loan Rejected',
                message=f'Your {loan.get_purpose_display()} loan of ${loan.amount:,.2f} has been rejected.',
                link='/loans/',
            )
            send_loan_email(user, loan, 'rejected')
            messages.warning(request, f'Loan rejected')

    return redirect('admin_loans')


# ──────────────────────────────────────
# CARD MANAGEMENT
# ──────────────────────────────────────
@staff_member_required
def admin_cards(request):
    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')
    cards_qs = Card.objects.select_related('user').all()
    if status_filter:
        cards_qs = cards_qs.filter(status=status_filter)
    if q:
        cards_qs = cards_qs.filter(
            Q(user__email__icontains=q) | Q(card_number__icontains=q)
        )
    cards_qs = cards_qs.order_by('-created_at')
    paginator = Paginator(cards_qs, 25)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'management/cards.html', {
        'cards': page, 'status_filter': status_filter, 'q': q,
    })


@staff_member_required
def admin_card_action(request, card_id):
    if request.method == 'POST':
        card = get_object_or_404(Card, id=card_id)
        action = request.POST.get('action')

        if action == 'approve' and card.status == 'pending':
            card.status = 'active'
            card.save()
            Notification.objects.create(
                user=card.user, notification_type='card',
                title='Card Approved',
                message=f'Your {card.get_tier_display()} {card.get_card_type_display()} card has been approved.',
                link='/cards/',
            )
            send_card_email(card.user, card, 'approved')
            messages.success(request, 'Card approved')

        elif action == 'reject' and card.status == 'pending':
            card.status = 'rejected'
            card.save()
            Notification.objects.create(
                user=card.user, notification_type='card',
                title='Card Rejected',
                message=f'Your {card.get_tier_display()} {card.get_card_type_display()} card request has been rejected.',
                link='/cards/',
            )
            send_card_email(card.user, card, 'rejected')
            messages.warning(request, 'Card rejected')

    return redirect('admin_cards')


# ──────────────────────────────────────
# CRYPTO WALLETS
# ──────────────────────────────────────
@staff_member_required
def admin_wallets(request):
    wallets = CryptoWallet.objects.all()
    return render(request, 'management/wallets.html', {'wallets': wallets})


@staff_member_required
def admin_wallet_form(request, wallet_id=None):
    wallet = get_object_or_404(CryptoWallet, id=wallet_id) if wallet_id else None
    if request.method == 'POST':
        data = request.POST
        files = request.FILES
        if wallet is None:
            wallet = CryptoWallet()
        wallet.name = data.get('name', '')
        wallet.symbol = data.get('symbol', '')
        wallet.network = data.get('network', '')
        wallet.address = data.get('address', '')
        wallet.icon_color = data.get('icon_color', 'bg-orange-500')
        wallet.icon_symbol = data.get('icon_symbol', '₿')
        wallet.is_active = data.get('is_active') == 'on'
        wallet.sort_order = int(data.get('sort_order', 0))
        if 'qr_code' in files:
            wallet.qr_code = files['qr_code']
        wallet.save()
        messages.success(request, f'Wallet {"updated" if wallet_id else "created"} successfully')
        return redirect('admin_wallets')
    return render(request, 'management/wallet_form.html', {'wallet': wallet})


@staff_member_required
def admin_wallet_delete(request, wallet_id):
    wallet = get_object_or_404(CryptoWallet, id=wallet_id)
    if request.method == 'POST':
        wallet.delete()
        messages.success(request, 'Wallet deleted')
    return redirect('admin_wallets')


# ──────────────────────────────────────
# BANK ACCOUNTS
# ──────────────────────────────────────
@staff_member_required
def admin_bank_accounts(request):
    accounts = BankAccount.objects.all()
    return render(request, 'management/bank_accounts.html', {'accounts': accounts})


@staff_member_required
def admin_bank_account_form(request, account_id=None):
    account = get_object_or_404(BankAccount, id=account_id) if account_id else None
    if request.method == 'POST':
        data = request.POST
        if account is None:
            account = BankAccount()
        account.bank_name = data.get('bank_name', '')
        account.account_name = data.get('account_name', '')
        account.account_number = data.get('account_number', '')
        account.routing_number = data.get('routing_number', '')
        account.swift_code = data.get('swift_code', '')
        account.iban = data.get('iban', '')
        account.additional_info = data.get('additional_info', '')
        account.is_active = data.get('is_active') == 'on'
        account.sort_order = int(data.get('sort_order', 0))
        account.save()
        messages.success(request, f'Bank account {"updated" if account_id else "created"} successfully')
        return redirect('admin_bank_accounts')
    return render(request, 'management/bank_account_form.html', {'account': account})


@staff_member_required
def admin_bank_account_delete(request, account_id):
    account = get_object_or_404(BankAccount, id=account_id)
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Bank account deleted')
    return redirect('admin_bank_accounts')


# ──────────────────────────────────────
# CONTACT MESSAGES
# ──────────────────────────────────────
@staff_member_required
def admin_messages(request):
    q = request.GET.get('q', '')
    read_filter = request.GET.get('read', '')
    msgs = ContactMessage.objects.all()
    if read_filter == 'unread':
        msgs = msgs.filter(is_read=False)
    elif read_filter == 'read':
        msgs = msgs.filter(is_read=True)
    if q:
        msgs = msgs.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(subject__icontains=q)
        )
    msgs = msgs.order_by('-created_at')
    paginator = Paginator(msgs, 25)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'management/messages.html', {'messages_list': page, 'q': q, 'read_filter': read_filter})


@staff_member_required
def admin_message_toggle(request, message_id):
    msg = get_object_or_404(ContactMessage, id=message_id)
    if request.method == 'POST':
        msg.is_read = not msg.is_read
        msg.save()
    return redirect('admin_messages')


# ──────────────────────────────────────
# EMAIL BROADCAST
# ──────────────────────────────────────
@staff_member_required
def admin_send_email(request):
    from django.core.mail import send_mail
    from django.conf import settings

    users = User.objects.filter(is_staff=False).order_by('first_name', 'last_name')

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        recipient_mode = request.POST.get('recipient_mode', 'all')

        if not subject or not body:
            messages.error(request, 'Subject and message body are required')
            return redirect('admin_send_email')

        # Build recipient list
        recipients = User.objects.filter(is_staff=False)

        if recipient_mode == 'selected':
            selected_ids = request.POST.getlist('selected_users')
            if not selected_ids:
                messages.error(request, 'Please select at least one user')
                return redirect('admin_send_email')
            recipients = recipients.filter(id__in=selected_ids)

        elif recipient_mode == 'filtered':
            tier_filter = request.POST.get('filter_tier', '')
            active_filter = request.POST.get('filter_active', '')
            verified_filter = request.POST.get('filter_verified', '')

            if tier_filter:
                recipients = recipients.filter(account_tier=tier_filter)
            if active_filter == 'yes':
                recipients = recipients.filter(is_active=True)
            elif active_filter == 'no':
                recipients = recipients.filter(is_active=False)
            if verified_filter == 'yes':
                recipients = recipients.filter(is_email_verified=True)
            elif verified_filter == 'no':
                recipients = recipients.filter(is_email_verified=False)

        recipient_emails = list(recipients.values_list('email', flat=True))

        if not recipient_emails:
            messages.error(request, 'No matching recipients found')
            return redirect('admin_send_email')

        # Send emails
        sent = 0
        failed = 0
        for email in recipient_emails:
            try:
                send_mail(
                    subject=f'Citi Group - {subject}',
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                sent += 1
            except Exception:
                failed += 1

        if sent:
            messages.success(request, f'Email sent successfully to {sent} recipient{"s" if sent != 1 else ""}')
        if failed:
            messages.warning(request, f'Failed to send to {failed} recipient{"s" if failed != 1 else ""}')

        return redirect('admin_send_email')

    return render(request, 'management/send_email.html', {'all_users': users})


# ──────────────────────────────────────
# COMPLIANCE MANAGEMENT
# ──────────────────────────────────────
@staff_member_required
def admin_compliance(request):
    tab = request.GET.get('tab', 'blocked')

    blocked_transactions = Transaction.objects.select_related('user').filter(
        compliance_blocked=True
    ).order_by('-created_at')

    tvn_requests = TVNRequest.objects.select_related('user', 'transaction').all().order_by('-created_at')

    blocked_count = blocked_transactions.filter(status='pending').count()
    tvn_pending_count = tvn_requests.filter(status='pending').count()
    tvn_approved_count = tvn_requests.filter(status='approved').count()
    total_held = blocked_transactions.filter(status='pending').aggregate(s=Sum('amount'))['s'] or 0

    return render(request, 'management/compliance.html', {
        'tab': tab,
        'blocked_transactions': blocked_transactions,
        'tvn_requests': tvn_requests,
        'blocked_count': blocked_count,
        'tvn_pending_count': tvn_pending_count,
        'tvn_approved_count': tvn_approved_count,
        'total_held': total_held,
    })


@staff_member_required
def admin_compliance_action(request, tx_id):
    if request.method == 'POST':
        tx = get_object_or_404(Transaction, id=tx_id, compliance_blocked=True)
        action = request.POST.get('action')
        user = tx.user

        if action == 'release' and tx.status == 'pending':
            # Release the compliance hold and process the transfer
            if tx.amount > user.balance:
                messages.error(request, f'Insufficient funds: user has ${user.balance:,.2f}')
            else:
                user.balance -= tx.amount
                user.save()
                tx.status = 'completed'
                tx.compliance_blocked = False
                tx.balance_after = user.balance
                tx.save()
                Notification.objects.create(
                    user=user, notification_type='transaction',
                    title='✅ Transfer Released',
                    message=f'Your international wire of ${tx.amount:,.2f} to {tx.recipient_name} has passed compliance review and been processed.',
                    link='/transactions/',
                )
                send_transaction_email(user, tx)
                messages.success(request, f'Transfer of ${tx.amount:,.2f} released and processed')

        elif action == 'reject' and tx.status == 'pending':
            tx.status = 'rejected'
            tx.save()
            Notification.objects.create(
                user=user, notification_type='transaction',
                title='❌ Transfer Rejected',
                message=f'Your international wire of ${tx.amount:,.2f} to {tx.recipient_name} has been rejected after compliance review.',
                link='/transactions/',
            )
            messages.warning(request, f'Transfer rejected')

    return redirect('admin_compliance')


@staff_member_required
def admin_tvn_action(request, tvn_id):
    if request.method == 'POST':
        tvn_req = get_object_or_404(TVNRequest, id=tvn_id)
        action = request.POST.get('action')

        if action == 'approve' and tvn_req.status == 'pending':
            tvn_req.status = 'approved'
            tvn_req.reviewed_at = timezone.now()
            tvn_req.save()
            Notification.objects.create(
                user=tvn_req.user, notification_type='transaction',
                title='✅ TVN Application Approved',
                message=f'Your Tax Verification Number application (Ref: {tvn_req.reference_number}) has been approved.',
                link='/compliance/',
            )
            messages.success(request, f'TVN request for {tvn_req.full_legal_name} approved')

        elif action == 'reject' and tvn_req.status == 'pending':
            tvn_req.status = 'rejected'
            tvn_req.reviewed_at = timezone.now()
            tvn_req.save()
            Notification.objects.create(
                user=tvn_req.user, notification_type='transaction',
                title='❌ TVN Application Rejected',
                message=f'Your Tax Verification Number application (Ref: {tvn_req.reference_number}) has been rejected.',
                link='/compliance/',
            )
            messages.warning(request, f'TVN request rejected')

    return redirect('admin_compliance')


# ──────────────────────────────────────
# COMPLAINT MANAGEMENT
# ──────────────────────────────────────
@staff_member_required
def admin_complaints(request):
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    q = request.GET.get('q', '')

    complaints = Complaint.objects.select_related('user').all()
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    if priority_filter:
        complaints = complaints.filter(priority=priority_filter)
    if q:
        complaints = complaints.filter(
            Q(subject__icontains=q) | Q(message__icontains=q) |
            Q(user__email__icontains=q) | Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q)
        )
    complaints = complaints.order_by('-created_at')

    # Stats
    open_count = Complaint.objects.filter(status='open').count()
    in_progress_count = Complaint.objects.filter(status='in_progress').count()
    resolved_count = Complaint.objects.filter(status='resolved').count()
    total_count = Complaint.objects.count()

    paginator = Paginator(complaints, 25)
    page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'management/complaints.html', {
        'complaints': page,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'q': q,
        'open_count': open_count,
        'in_progress_count': in_progress_count,
        'resolved_count': resolved_count,
        'total_count': total_count,
    })


@staff_member_required
def admin_complaint_action(request, complaint_id):
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, id=complaint_id)
        action = request.POST.get('action')
        user = complaint.user

        if action == 'update_status':
            new_status = request.POST.get('status', '')
            admin_response = request.POST.get('admin_response', '').strip()

            if new_status in ['open', 'in_progress', 'resolved', 'closed']:
                old_status = complaint.status
                complaint.status = new_status
                if admin_response:
                    complaint.admin_response = admin_response
                complaint.save()

                # Create notification for user
                status_display = complaint.get_status_display()
                Notification.objects.create(
                    user=user, notification_type='system',
                    title=f'Complaint {status_display}',
                    message=f'Your complaint ({complaint.ticket_number}) has been updated to: {status_display}.',
                    link='/support/',
                )

                # Send automatic email
                send_complaint_email(user, complaint)

                messages.success(request, f'Complaint {complaint.ticket_number} updated to "{status_display}" and email sent to {user.email}')
            else:
                messages.error(request, 'Invalid status')

    return redirect('admin_complaints')
