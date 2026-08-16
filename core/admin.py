from datetime import date, timedelta
from decimal import Decimal
from django.contrib import admin, messages
from django.utils import timezone
from .models import User, Transaction, Loan, Card, Notification, ContactMessage, CryptoWallet, BankAccount, TaxVerificationNumber, Complaint
from .utils import send_transaction_email, send_loan_email, send_card_email


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'account_number', 'balance', 'account_tier', 'is_active']
    list_filter = ['account_tier', 'is_active', 'is_email_verified']
    search_fields = ['email', 'first_name', 'last_name', 'account_number']
    readonly_fields = ['account_number', 'created_at', 'updated_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'user', 'transaction_type', 'amount', 'deposit_method', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'deposit_method', 'created_at']
    search_fields = ['user__email', 'description', 'reference']
    readonly_fields = ['id', 'created_at']
    actions = ['approve_transactions', 'reject_transactions']

    @admin.action(description='✅ Approve selected transactions')
    def approve_transactions(self, request, queryset):
        pending = queryset.filter(status='pending')
        approved_count = 0
        for tx in pending:
            user = tx.user
            if tx.transaction_type == 'deposit':
                user.balance += tx.amount
                user.save()
                tx.status = 'completed'
                tx.balance_after = user.balance
                tx.save()
                Notification.objects.create(
                    user=user, notification_type='transaction',
                    title='Deposit Approved',
                    message=f'Your deposit of ${tx.amount:,.2f} has been approved. New balance: ${user.balance:,.2f}',
                    link='/transactions/',
                )
                send_transaction_email(user, tx)
                approved_count += 1

            elif tx.transaction_type == 'withdrawal':
                if tx.amount > user.balance:
                    self.message_user(
                        request,
                        f'Skipped withdrawal {tx.transaction_id}: insufficient funds (needs ${tx.amount:,.2f}, has ${user.balance:,.2f})',
                        messages.WARNING,
                    )
                    continue
                user.balance -= tx.amount
                user.save()
                tx.status = 'completed'
                tx.balance_after = user.balance
                tx.save()
                Notification.objects.create(
                    user=user, notification_type='transaction',
                    title='Withdrawal Approved',
                    message=f'Your withdrawal of ${tx.amount:,.2f} has been approved. New balance: ${user.balance:,.2f}',
                    link='/transactions/',
                )
                send_transaction_email(user, tx)
                approved_count += 1

            elif tx.transaction_type == 'transfer_out':
                if tx.amount > user.balance:
                    self.message_user(
                        request,
                        f'Skipped transfer {tx.transaction_id}: insufficient funds (needs ${tx.amount:,.2f}, has ${user.balance:,.2f})',
                        messages.WARNING,
                    )
                    continue
                recipient = tx.recipient
                if not recipient:
                    self.message_user(request, f'Skipped transfer {tx.transaction_id}: no recipient found.', messages.WARNING)
                    continue

                # Deduct from sender
                user.balance -= tx.amount
                user.save()
                tx.status = 'completed'
                tx.balance_after = user.balance
                tx.save()

                # Credit recipient
                recipient.balance += tx.amount
                recipient.save()
                Transaction.objects.create(
                    user=recipient, transaction_type='transfer_in',
                    amount=tx.amount,
                    description=f'Transfer from {user.get_full_name()}',
                    status='completed',
                    balance_after=recipient.balance,
                )

                Notification.objects.create(
                    user=user, notification_type='transaction',
                    title='Transfer Approved',
                    message=f'Your transfer of ${tx.amount:,.2f} to {recipient.get_full_name()} has been approved.',
                    link='/transactions/',
                )
                Notification.objects.create(
                    user=recipient, notification_type='transaction',
                    title='Transfer Received',
                    message=f'${tx.amount:,.2f} received from {user.get_full_name()}.',
                    link='/transactions/',
                )
                send_transaction_email(user, tx)
                approved_count += 1

        self.message_user(request, f'{approved_count} transaction(s) approved successfully.', messages.SUCCESS)

    @admin.action(description='❌ Reject selected transactions')
    def reject_transactions(self, request, queryset):
        pending = queryset.filter(status='pending')
        count = pending.count()
        for tx in pending:
            tx.status = 'rejected'
            tx.save()
            Notification.objects.create(
                user=tx.user, notification_type='transaction',
                title='Transaction Rejected',
                message=f'Your {tx.get_transaction_type_display().lower()} of ${tx.amount:,.2f} has been rejected by admin.',
                link='/transactions/',
            )
        self.message_user(request, f'{count} transaction(s) rejected.', messages.WARNING)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['loan_number', 'user', 'purpose', 'amount', 'outstanding_balance', 'status', 'created_at']
    list_filter = ['status', 'purpose']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at']
    actions = ['approve_loans', 'reject_loans']

    @admin.action(description='✅ Approve selected loans')
    def approve_loans(self, request, queryset):
        pending = queryset.filter(status='pending')
        approved_count = 0
        for loan in pending:
            user = loan.user
            loan.status = 'active'
            loan.approved_at = timezone.now()
            loan.next_payment_date = date.today() + timedelta(days=30)
            loan.save()

            # Disburse loan amount to user balance
            user.balance += loan.amount
            user.save()

            # Create disbursement transaction
            Transaction.objects.create(
                user=user, transaction_type='loan_disbursement',
                amount=loan.amount,
                description=f'{loan.get_purpose_display()} Loan Disbursement',
                status='completed',
                balance_after=user.balance,
            )

            Notification.objects.create(
                user=user, notification_type='loan',
                title='Loan Approved!',
                message=f'Your {loan.get_purpose_display()} loan of ${loan.amount:,.2f} has been approved and disbursed to your account.',
                link='/loans/',
            )
            send_loan_email(user, loan, 'approved and disbursed')
            approved_count += 1

        self.message_user(request, f'{approved_count} loan(s) approved and disbursed.', messages.SUCCESS)

    @admin.action(description='❌ Reject selected loans')
    def reject_loans(self, request, queryset):
        pending = queryset.filter(status='pending')
        count = pending.count()
        for loan in pending:
            loan.status = 'rejected'
            loan.save()
            Notification.objects.create(
                user=loan.user, notification_type='loan',
                title='Loan Rejected',
                message=f'Your {loan.get_purpose_display()} loan of ${loan.amount:,.2f} has been rejected.',
                link='/loans/',
            )
            send_loan_email(loan.user, loan, 'rejected')
        self.message_user(request, f'{count} loan(s) rejected.', messages.WARNING)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['masked_number', 'user', 'card_type', 'tier', 'status', 'created_at']
    list_filter = ['card_type', 'tier', 'status']
    search_fields = ['user__email', 'card_number']
    readonly_fields = ['id', 'card_number', 'cvv', 'created_at']
    actions = ['approve_cards', 'reject_cards']

    @admin.action(description='✅ Approve selected cards')
    def approve_cards(self, request, queryset):
        pending = queryset.filter(status='pending')
        approved_count = 0
        for card in pending:
            card.status = 'active'
            card.save()
            Notification.objects.create(
                user=card.user, notification_type='card',
                title='Card Activated!',
                message=f'Your {card.get_tier_display()} {card.get_card_type_display()} card ending in {card.card_number[-4:]} is now active.',
                link='/cards/',
            )
            send_card_email(card.user, card, 'activated')
            approved_count += 1
        self.message_user(request, f'{approved_count} card(s) approved and activated.', messages.SUCCESS)

    @admin.action(description='❌ Reject selected cards')
    def reject_cards(self, request, queryset):
        pending = queryset.filter(status='pending')
        count = pending.count()
        for card in pending:
            card.status = 'rejected'
            card.save()
            Notification.objects.create(
                user=card.user, notification_type='card',
                title='Card Request Rejected',
                message=f'Your {card.get_tier_display()} {card.get_card_type_display()} card request has been rejected.',
                link='/cards/',
            )
            send_card_email(card.user, card, 'rejected')
        self.message_user(request, f'{count} card(s) rejected.', messages.WARNING)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['title', 'user__email']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'name', 'email', 'is_read', 'created_at']
    list_filter = ['is_read']
    search_fields = ['name', 'email', 'subject']


@admin.register(CryptoWallet)
class CryptoWalletAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbol', 'network', 'address', 'is_active', 'sort_order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['name', 'symbol', 'address']
    fieldsets = (
        (None, {'fields': ('name', 'symbol', 'network', 'address')}),
        ('Appearance', {'fields': ('icon_color', 'icon_symbol', 'qr_code')}),
        ('Settings', {'fields': ('is_active', 'sort_order')}),
    )


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'account_name', 'account_number', 'is_active', 'sort_order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['bank_name', 'account_name', 'account_number']
    fieldsets = (
        (None, {'fields': ('bank_name', 'account_name', 'account_number')}),
        ('Wire Details', {'fields': ('routing_number', 'swift_code', 'iban')}),
        ('Extra', {'fields': ('additional_info', 'is_active', 'sort_order')}),
    )


@admin.register(TaxVerificationNumber)
class TaxVerificationNumberAdmin(admin.ModelAdmin):
    list_display = ['code', 'assigned_to', 'is_active', 'description', 'created_at']
    list_filter = ['is_active']
    list_editable = ['is_active']
    search_fields = ['code', 'description', 'assigned_to__email', 'assigned_to__first_name', 'assigned_to__last_name']
    raw_id_fields = ['assigned_to']


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'user', 'category', 'subject', 'priority', 'status', 'created_at']
    list_filter = ['status', 'priority', 'category']
    search_fields = ['subject', 'message', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_editable = ['status']
