from decimal import Decimal
from datetime import date, timedelta
import random
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import User, Transaction, Loan, Card, Notification, ContactMessage, CryptoWallet, BankAccount, TVNRequest, TaxVerificationNumber, Complaint
from .forms import (
    RegisterForm, LoginForm, TransferForm, DepositWithdrawForm,
    LoanApplicationForm, CardRequestForm, ProfileUpdateForm, ContactForm
)
from .utils import (
    send_registration_email, send_login_email, send_transaction_email,
    send_loan_email, send_card_email
)


# ──────────────────────────────────────
# HELPER: detect HTMX requests
# ──────────────────────────────────────
def is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


# ──────────────────────────────────────
# PUBLIC PAGES
# ──────────────────────────────────────
def home(request):
    return render(request, 'home.html')


def about(request):
    return render(request, 'about.html')


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return HttpResponse('<div class="bg-green-50 border border-green-200 text-green-700 p-4 rounded-lg text-center font-medium">Thank you! Your message has been sent successfully.</div>')
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})


def personal(request):
    return render(request, 'personal.html')


def business(request):
    return render(request, 'business.html')


def wealth(request):
    return render(request, 'wealth.html')


def careers(request):
    return render(request, 'careers.html')


def privacy(request):
    return render(request, 'privacy.html')


def terms(request):
    return render(request, 'terms.html')


def faq(request):
    return render(request, 'faq.html')


# ──────────────────────────────────────
# AUTHENTICATION
# ──────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_registration_email(user)
            Notification.objects.create(
                user=user,
                notification_type='system',
                title='Welcome to Citi Group!',
                message=f'Your account {user.account_number} has been created successfully.',
            )
            login(request, user)
            if is_htmx(request):
                return HttpResponse(status=204, headers={'HX-Redirect': '/dashboard/'})
            return redirect('dashboard')
        else:
            if is_htmx(request):
                return render(request, 'partials/register_form.html', {'form': form})
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            send_login_email(user)
            if is_htmx(request):
                return HttpResponse(status=204, headers={'HX-Redirect': '/dashboard/'})
            return redirect('dashboard')
        else:
            if is_htmx(request):
                return HttpResponse('<div class="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3 text-center">Invalid email or password. Please try again.</div>')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


# ──────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────
@login_required
def dashboard(request):
    user = request.user
    recent_transactions = Transaction.objects.filter(user=user)[:5]
    active_loans = Loan.objects.filter(user=user, status='active').count()
    active_cards = Card.objects.filter(user=user, status='active').count()

    # Monthly income/expense
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_income = Transaction.objects.filter(
        user=user, created_at__gte=month_start,
        transaction_type__in=['deposit', 'transfer_in']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    month_expense = Transaction.objects.filter(
        user=user, created_at__gte=month_start,
        transaction_type__in=['withdrawal', 'transfer_out']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # Unread notifications count
    unread_count = Notification.objects.filter(user=user, is_read=False).count()

    # Time-based greeting
    hour = now.hour
    if 5 <= hour < 12:
        greeting = 'Good morning'
    elif 12 <= hour < 17:
        greeting = 'Good afternoon'
    else:
        greeting = 'Good evening'

    context = {
        'greeting': greeting,
        'recent_transactions': recent_transactions,
        'active_loans': active_loans,
        'active_cards': active_cards,
        'month_income': month_income,
        'month_expense': month_expense,
        'unread_count': unread_count,
    }
    return render(request, 'dashboard.html', context)


# ──────────────────────────────────────
# DEPOSIT
# ──────────────────────────────────────
@login_required
def deposit(request):
    if request.method == 'POST':
        form = DepositWithdrawForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data.get('description', 'Cash Deposit')
            deposit_method = request.POST.get('deposit_method', 'bank')
            user = request.user
            # Create pending transaction — balance updated on admin approval
            method_label = 'Crypto Deposit' if deposit_method == 'crypto' else 'Bank Transfer Deposit'
            tx = Transaction.objects.create(
                user=user,
                transaction_type='deposit',
                amount=amount,
                description=description or method_label,
                deposit_method=deposit_method,
                status='pending',
                balance_after=user.balance,  # Snapshot current balance
            )
            Notification.objects.create(
                user=user, notification_type='transaction',
                title='Deposit Pending Approval',
                message=f'Your {method_label.lower()} of ${amount:,.2f} is pending admin approval.',
                link='/transactions/',
            )
            if is_htmx(request):
                return render(request, 'partials/deposit_success.html', {'tx': tx, 'user': user})
            messages.success(request, f'Deposit of ${amount:,.2f} submitted for approval!')
            return redirect('dashboard')
    else:
        form = DepositWithdrawForm()
    wallets = CryptoWallet.objects.filter(is_active=True)
    bank_accounts = BankAccount.objects.filter(is_active=True)
    return render(request, 'deposit.html', {'form': form, 'wallets': wallets, 'bank_accounts': bank_accounts})


# ──────────────────────────────────────
# WITHDRAW
# ──────────────────────────────────────
@login_required
def withdraw(request):
    if request.method == 'POST':
        form = DepositWithdrawForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data.get('description', 'Cash Withdrawal')
            withdrawal_method = request.POST.get('withdrawal_method', 'crypto')
            
            if withdrawal_method == 'crypto':
                recipient_account = request.POST.get('crypto_address', '')
                recipient_name = request.POST.get('crypto_network', '')
                method_label = 'Crypto Withdrawal'
            else:
                recipient_account = request.POST.get('bank_account', '')
                recipient_name = request.POST.get('bank_name', '')
                method_label = 'Bank Transfer Withdrawal'

            user = request.user
            if amount > user.balance:
                if is_htmx(request):
                    return HttpResponse('<div class="text-red-600 bg-red-50 border border-red-100 rounded-lg p-3 text-center text-sm font-medium">Insufficient funds for this withdrawal.</div>')
                messages.error(request, 'Insufficient funds.')
                return redirect('withdraw')
            # Create pending transaction — balance deducted on admin approval
            tx = Transaction.objects.create(
                user=user,
                transaction_type='withdrawal',
                amount=amount,
                description=description or method_label,
                deposit_method=withdrawal_method,
                recipient_account=recipient_account,
                recipient_name=recipient_name,
                status='pending',
                balance_after=user.balance,  # Snapshot current balance
            )
            Notification.objects.create(
                user=user, notification_type='transaction',
                title='Withdrawal Pending Approval',
                message=f'Your withdrawal of ${amount:,.2f} is pending admin approval.',
                link='/transactions/',
            )
            if is_htmx(request):
                return render(request, 'partials/withdraw_success.html', {'tx': tx, 'user': user})
            messages.success(request, f'Withdrawal of ${amount:,.2f} submitted for approval!')
            return redirect('dashboard')
    else:
        form = DepositWithdrawForm()
    return render(request, 'withdraw.html', {'form': form})


# ──────────────────────────────────────
# TRANSFER
# ──────────────────────────────────────
@login_required
def transfer(request):
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            description = form.cleaned_data.get('description', 'Transfer')
            transfer_type = form.cleaned_data['transfer_type']
            user = request.user

            if amount > user.balance:
                if is_htmx(request):
                    return HttpResponse('<div class="text-red-600 bg-red-50 border border-red-100 rounded-lg p-3 text-center text-sm font-medium">Insufficient funds for this transfer.</div>')
                messages.error(request, 'Insufficient funds.')
                return redirect('transfer')

            # ── LOCAL TRANSFER ──
            if transfer_type == 'local':
                local_account_number = form.cleaned_data['local_account_number']
                local_account_name = form.cleaned_data['local_account_name']
                local_bank_name = form.cleaned_data['local_bank_name']

                # Generate OTP
                pin = ''.join(random.choices(string.digits, k=6))
                
                # Store in session
                request.session['transfer_pin'] = pin
                request.session['transfer_data'] = {
                    'amount': str(amount),
                    'description': description or f'Local transfer to {local_account_name}',
                    'recipient_account': local_account_number,
                    'recipient_name': local_account_name,
                    'bank_name': local_bank_name,
                    'transfer_method': 'local'
                }

                # Send PIN
                from .utils import send_transfer_pin_email
                send_transfer_pin_email(user, pin)

                if is_htmx(request):
                    return render(request, 'partials/transfer_pin_verify.html', {'user': user, 'amount': amount})
                
                messages.info(request, 'Please check your email for the authorization PIN.')
                return redirect('transfer')

            # ── INTERNATIONAL WIRE TRANSFER ──
            else:
                intl_recipient_name = form.cleaned_data['intl_recipient_name']
                intl_bank_name = form.cleaned_data['intl_bank_name']
                intl_swift_code = form.cleaned_data['intl_swift_code']
                intl_iban = form.cleaned_data['intl_iban']
                intl_country = form.cleaned_data['intl_country']

                # Compliance check: block international wires > $1
                is_compliance_blocked = amount > Decimal('1')

                tx_out = Transaction.objects.create(
                    user=user, transaction_type='transfer_out',
                    amount=amount,
                    description=description or f'International wire to {intl_recipient_name}',
                    recipient_account=intl_iban,
                    recipient_name=intl_recipient_name,
                    transfer_method='international',
                    swift_code=intl_swift_code,
                    iban=intl_iban,
                    bank_name=intl_bank_name,
                    beneficiary_country=intl_country,
                    compliance_blocked=is_compliance_blocked,
                    status='pending', balance_after=user.balance,
                )

                if is_compliance_blocked:
                    Notification.objects.create(
                        user=user, notification_type='transaction',
                        title='⚠️ Transfer Under Compliance Review',
                        message=f'Your international wire of ${amount:,.2f} to {intl_recipient_name} exceeds $10,000 and is under compliance review.',
                        link='/transactions/',
                    )
                    # Redirect to the full compliance blocked page
                    from django.urls import reverse
                    redirect_url = reverse('compliance_blocked', args=[tx_out.id])
                    if is_htmx(request):
                        return HttpResponse(status=204, headers={'HX-Redirect': redirect_url})
                    return redirect('compliance_blocked', tx_id=tx_out.id)
                else:
                    Notification.objects.create(
                        user=user, notification_type='transaction',
                        title='International Wire Pending Approval',
                        message=f'Your international wire of ${amount:,.2f} to {intl_recipient_name} is pending admin approval.',
                        link='/transactions/',
                    )

                if is_htmx(request):
                    return render(request, 'partials/transfer_success.html', {'tx': tx_out, 'user': user, 'recipient_display': intl_recipient_name})
                messages.success(request, f'International wire of ${amount:,.2f} submitted for approval!')
                return redirect('dashboard')
    else:
        form = TransferForm()
    return render(request, 'transfer.html', {'form': form})


@login_required
@require_POST
def transfer_verify_pin(request):
    user = request.user
    pin_entered = request.POST.get('pin', '').strip()
    session_pin = request.session.get('transfer_pin')
    transfer_data = request.session.get('transfer_data')

    if not session_pin or not transfer_data:
        if is_htmx(request):
            return HttpResponse('<div class="text-red-600 bg-red-50 border border-red-100 rounded-lg p-3 text-center text-sm font-medium">Session expired. Please restart the transfer.</div>')
        messages.error(request, 'Transfer session expired.')
        return redirect('transfer')

    if pin_entered != session_pin:
        if is_htmx(request):
            return HttpResponse('<div class="text-red-600 bg-red-50 border border-red-100 rounded-lg p-3 text-center text-sm text-center mb-4">Invalid PIN entered. Please try again.</div>')
        messages.error(request, 'Invalid PIN.')
        return redirect('transfer')

    # Create the pending transaction
    amount = Decimal(transfer_data['amount'])
    tx_out = Transaction.objects.create(
        user=user, transaction_type='transfer_out',
        amount=amount, 
        description=transfer_data['description'],
        recipient_account=transfer_data['recipient_account'],
        recipient_name=transfer_data['recipient_name'],
        bank_name=transfer_data['bank_name'],
        transfer_method=transfer_data['transfer_method'],
        status='pending', balance_after=user.balance,
    )

    Notification.objects.create(
        user=user, notification_type='transaction',
        title='Local Transfer Pending Approval',
        message=f'Your local transfer of ${amount:,.2f} to {transfer_data["recipient_name"]} is pending admin approval.',
        link='/transactions/',
    )

    # Clear session
    del request.session['transfer_pin']
    del request.session['transfer_data']

    if is_htmx(request):
        return render(request, 'partials/transfer_success.html', {'tx': tx_out, 'user': user, 'recipient_display': transfer_data['recipient_name']})
        
    messages.success(request, f'Transfer of ${amount:,.2f} submitted for approval!')
    return redirect('dashboard')


# ──────────────────────────────────────
# TRANSACTION HISTORY
# ──────────────────────────────────────
@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user)

    # Filtering
    tx_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type)
    if status:
        transactions = transactions.filter(status=status)
    if search:
        transactions = transactions.filter(
            Q(description__icontains=search) | Q(reference__icontains=search)
        )
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)

    paginator = Paginator(transactions, 10)
    page = request.GET.get('page', 1)
    transactions_page = paginator.get_page(page)

    context = {
        'transactions': transactions_page,
        'tx_type': tx_type,
        'status': status,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
    }

    if is_htmx(request):
        return render(request, 'partials/transaction_table.html', context)

    return render(request, 'transaction_history.html', context)


@login_required
def transaction_receipt(request, tx_id):
    tx = get_object_or_404(Transaction, id=tx_id, user=request.user)
    return render(request, 'transaction_receipt.html', {'tx': tx})


# ──────────────────────────────────────
# LOANS
# ──────────────────────────────────────
@login_required
def loans(request):
    user_loans = Loan.objects.filter(user=request.user)
    active_loans = user_loans.filter(status='active')
    total_outstanding = active_loans.aggregate(total=Sum('outstanding_balance'))['total'] or Decimal('0')
    total_credit_limit = Decimal('25000') - total_outstanding

    context = {
        'loans': user_loans,
        'active_loans': active_loans,
        'total_outstanding': total_outstanding,
        'credit_limit': max(total_credit_limit, Decimal('0')),
    }
    return render(request, 'loans.html', context)


@login_required
def loan_apply(request):
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            purpose = form.cleaned_data['purpose']
            amount = form.cleaned_data['amount']
            term_months = int(form.cleaned_data['term_months'])

            loan = Loan.objects.create(
                user=request.user,
                purpose=purpose,
                amount=amount,
                term_months=term_months,
                interest_rate=Decimal('4.5'),
                status='pending',  # Requires admin approval
            )

            Notification.objects.create(
                user=request.user, notification_type='loan',
                title='Loan Application Submitted',
                message=f'Your {loan.get_purpose_display()} loan of ${amount:,.2f} is pending admin approval.',
                link='/loans/',
            )

            if is_htmx(request):
                return HttpResponse(status=204, headers={'HX-Redirect': '/loans/'})
            messages.success(request, 'Loan application submitted for approval!')
            return redirect('loans')
    else:
        form = LoanApplicationForm()
    return render(request, 'loan_apply.html', {'form': form})


@login_required
@require_POST
def loan_repay(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id, user=request.user)
    amount = min(loan.monthly_payment, loan.outstanding_balance)

    if amount > request.user.balance:
        if is_htmx(request):
            return HttpResponse('<div class="text-red-600 bg-red-50 p-3 rounded-lg text-center text-sm">Insufficient funds for loan payment.</div>')
        messages.error(request, 'Insufficient funds.')
        return redirect('loans')

    request.user.balance -= amount
    request.user.save()
    loan.total_paid += amount
    loan.outstanding_balance -= amount
    loan.next_payment_date = date.today() + timedelta(days=30)
    if loan.outstanding_balance <= 0:
        loan.status = 'paid'
        loan.outstanding_balance = Decimal('0')
    loan.save()

    tx = Transaction.objects.create(
        user=request.user, transaction_type='loan_repayment',
        amount=amount, description=f'Loan Repayment - {loan.get_purpose_display()}',
        status='completed', balance_after=request.user.balance,
    )
    send_transaction_email(request.user, tx)

    if is_htmx(request):
        return HttpResponse(status=204, headers={'HX-Redirect': '/loans/'})
    messages.success(request, f'Loan payment of ${amount:,.2f} successful!')
    return redirect('loans')


# ──────────────────────────────────────
# CARDS
# ──────────────────────────────────────
def cards(request):
    if request.user.is_authenticated:
        user_cards = Card.objects.filter(user=request.user)
    else:
        user_cards = []
    context = {'cards': user_cards}
    return render(request, 'cards.html', context)


@login_required
def card_request(request):
    if request.method == 'POST':
        form = CardRequestForm(request.POST)
        if form.is_valid():
            card_type = form.cleaned_data['card_type']
            tier = form.cleaned_data['tier']

            credit_limits = {'classic': 5000, 'gold': 15000, 'platinum': 25000}
            card = Card.objects.create(
                user=request.user,
                card_type=card_type,
                tier=tier,
                expiry_date=date.today() + timedelta(days=365 * 3),
                cvv=''.join(random.choices(string.digits, k=3)),
                pin=''.join(random.choices(string.digits, k=4)),
                credit_limit=credit_limits.get(tier, 5000) if card_type == 'credit' else 0,
                available_balance=credit_limits.get(tier, 5000) if card_type == 'credit' else 0,
                status='pending',  # Requires admin approval
            )
            Notification.objects.create(
                user=request.user, notification_type='card',
                title='Card Request Submitted',
                message=f'Your {card.get_tier_display()} {card.get_card_type_display()} card request is pending admin approval.',
                link='/cards/',
            )

            if is_htmx(request):
                return HttpResponse(status=204, headers={'HX-Redirect': '/cards/'})
            messages.success(request, 'Card request submitted for approval!')
            return redirect('cards')
    else:
        form = CardRequestForm()
    return render(request, 'card_request.html', {'form': form})


@login_required
@require_POST
def card_toggle_freeze(request, card_id):
    card = get_object_or_404(Card, id=card_id, user=request.user)
    if card.status == 'active':
        card.status = 'frozen'
        action = 'frozen'
    else:
        card.status = 'active'
        action = 'unfrozen'
    card.save()
    send_card_email(request.user, card, action)

    if is_htmx(request):
        return render(request, 'partials/card_status_badge.html', {'card': card})
    messages.success(request, f'Card has been {action}.')
    return redirect('cards')


# ──────────────────────────────────────
# PROFILE & SETTINGS
# ──────────────────────────────────────
@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return HttpResponse('<div class="text-green-600 bg-green-50 border border-green-100 rounded-lg p-3 text-center text-sm font-medium">Profile updated successfully!</div>')
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    password_form = PasswordChangeForm(request.user)
    context = {'form': form, 'password_form': password_form}
    return render(request, 'profile.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            Notification.objects.create(
                user=user, notification_type='security',
                title='Password Changed',
                message='Your password has been changed successfully.',
            )
            if is_htmx(request):
                return HttpResponse('<div class="text-green-600 bg-green-50 border border-green-100 rounded-lg p-3 text-center text-sm font-medium">Password changed successfully!</div>')
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
        else:
            if is_htmx(request):
                return HttpResponse('<div class="text-red-600 bg-red-50 border border-red-100 rounded-lg p-3 text-center text-sm font-medium">Please check your password entries and try again.</div>')
    return redirect('profile')


@login_required
@require_POST
def toggle_2fa(request):
    user = request.user
    user.two_factor_enabled = not user.two_factor_enabled
    user.save()
    status = 'enabled' if user.two_factor_enabled else 'disabled'
    Notification.objects.create(
        user=user, notification_type='security',
        title=f'2FA {status.title()}',
        message=f'Two-factor authentication has been {status}.',
    )
    if is_htmx(request):
        return render(request, 'partials/2fa_toggle.html', {'user': user})
    return redirect('profile')


# ──────────────────────────────────────
# NOTIFICATIONS
# ──────────────────────────────────────
@login_required
def notifications(request):
    notifs = Notification.objects.filter(user=request.user)
    unread_count = notifs.filter(is_read=False).count()

    if is_htmx(request):
        # Mark all as read
        notifs.filter(is_read=False).update(is_read=True)
        return render(request, 'partials/notification_list.html', {
            'notifications': notifs[:20],
            'unread_count': 0,
        })

    context = {
        'notifications': notifs[:50],
        'unread_count': unread_count,
    }
    return render(request, 'notifications.html', context)


@login_required
def notification_count(request):
    """HTMX endpoint to get unread notification count."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    if count > 0:
        return HttpResponse(f'<span class="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 border border-white dark:border-slate-900"></span>')
    return HttpResponse('')


# ──────────────────────────────────────
# HTMX: Verify recipient account
# ──────────────────────────────────────
@login_required
def check_recipient(request):
    account = request.GET.get('account', '').strip()
    if account:
        try:
            recipient = User.objects.get(account_number=account)
            if recipient != request.user:
                return HttpResponse(f'''
                    <div class="flex items-center gap-2 text-green-600 text-sm">
                        <span class="material-symbols-outlined text-sm">verified</span>
                        Verified: {recipient.get_full_name()}
                    </div>
                ''')
        except User.DoesNotExist:
            pass
    return HttpResponse('<div class="text-red-500 text-xs">Account not found</div>')


# ──────────────────────────────────────
# COMPLIANCE: Transaction Blocked Page
# ──────────────────────────────────────
@login_required
def compliance_status(request):
    """Page showing all compliance-blocked transactions and TVN requests."""
    blocked_transactions = Transaction.objects.filter(
        user=request.user, compliance_blocked=True
    ).order_by('-created_at')
    tvn_requests = TVNRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'compliance_status.html', {
        'blocked_transactions': blocked_transactions,
        'tvn_requests': tvn_requests,
    })


@login_required
def compliance_blocked_view(request, tx_id):
    tx = get_object_or_404(Transaction, id=tx_id, user=request.user, compliance_blocked=True)
    date_str = tx.created_at.strftime('%Y-%m-%d') if tx.created_at else 'PENDING'
    ref_number = f"MDL-{date_str}-{str(tx.id)[:4].upper()}"
    return render(request, 'compliance_blocked.html', {'tx': tx, 'ref_number': ref_number})


@login_required
@require_POST
def validate_tvn(request, tx_id):
    """Handle TVN code submission — validates against the database."""
    tx = get_object_or_404(Transaction, id=tx_id, user=request.user, compliance_blocked=True)
    tvn_code = request.POST.get('tvn_code', '').strip()
    if not tvn_code:
        messages.error(request, 'Please enter a valid TVN code.')
        return redirect('compliance_blocked', tx_id=tx.id)

    # Check if the TVN code exists and is active in the database
    tvn_record = TaxVerificationNumber.objects.filter(code=tvn_code, is_active=True).first()

    if not tvn_record:
        messages.error(request, 'Invalid Tax Verification Number. The TVN you entered does not match our records. Please check and try again, or apply for a new TVN.')
        return redirect('compliance_blocked', tx_id=tx.id)

    # Valid TVN found — store it on the transaction and submit for admin review
    tx.description = f"{tx.description} | TVN: {tvn_code}"
    tx.save()

    Notification.objects.create(
        user=request.user, notification_type='transaction',
        title='TVN Submitted for Verification',
        message=f'Your Tax Verification Number ({tvn_code}) has been submitted for transaction {tx.transaction_id}. Awaiting admin approval.',
        link='/transactions/',
    )
    messages.success(request, 'Your TVN has been verified and submitted. You will be notified once your transaction is processed.')
    return redirect('dashboard')


# ──────────────────────────────────────
# COMPLIANCE: TVN Request Application
# ──────────────────────────────────────
@login_required
def tvn_request(request, tx_id):
    tx = get_object_or_404(Transaction, id=tx_id, user=request.user, compliance_blocked=True)

    if request.method == 'POST':
        full_legal_name = request.POST.get('full_legal_name', '').strip()
        date_of_birth = request.POST.get('date_of_birth', '').strip()
        country_of_residence = request.POST.get('country_of_residence', '').strip()
        tax_id_last4 = request.POST.get('tax_id_last4', '').strip()
        residential_address = request.POST.get('residential_address', '').strip()

        if not all([full_legal_name, date_of_birth, country_of_residence, tax_id_last4, residential_address]):
            return render(request, 'tvn_request.html', {'tx': tx, 'error': 'All fields are required.'})

        tvn_req = TVNRequest.objects.create(
            user=request.user,
            transaction=tx,
            full_legal_name=full_legal_name,
            date_of_birth=date_of_birth,
            country_of_residence=country_of_residence,
            tax_id_last4=tax_id_last4,
            residential_address=residential_address,
            transfer_amount=tx.amount,
            receiving_bank=tx.bank_name,
            swift_code=tx.swift_code,
        )

        Notification.objects.create(
            user=request.user, notification_type='transaction',
            title='TVN Application Submitted',
            message=f'Your Tax Verification Number application (Ref: {tvn_req.reference_number}) has been submitted and is under review.',
            link='/transactions/',
        )
        messages.success(request, 'Your TVN application has been submitted successfully. You will be notified once processed.')
        return redirect('dashboard')

    return render(request, 'tvn_request.html', {'tx': tx})


# ──────────────────────────────────────
# GET IN TOUCH / LOG COMPLAINT
# ──────────────────────────────────────
@login_required
def support_contact(request):
    """Page for users to log complaints and view previous complaints."""
    if request.method == 'POST':
        category = request.POST.get('category', 'other').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()
        priority = request.POST.get('priority', 'medium').strip()

        if not subject or not message_text:
            messages.error(request, 'Subject and message are required.')
            return redirect('support_contact')

        complaint = Complaint.objects.create(
            user=request.user,
            category=category,
            subject=subject,
            message=message_text,
            priority=priority,
        )

        Notification.objects.create(
            user=request.user, notification_type='system',
            title='Complaint Submitted',
            message=f'Your complaint ({complaint.ticket_number}) has been submitted. Our team will review it shortly.',
            link='/support/',
        )
        messages.success(request, f'Your complaint ({complaint.ticket_number}) has been submitted successfully. We will get back to you soon.')
        return redirect('support_contact')

    complaints = Complaint.objects.filter(user=request.user)
    return render(request, 'support_contact.html', {'complaints': complaints})
