import uuid
import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


def generate_account_number():
    """Generate a unique 10-digit account number."""
    return ''.join(random.choices(string.digits, k=10))


def generate_card_number():
    """Generate a 16-digit card number."""
    return ''.join(random.choices(string.digits, k=16))


class User(AbstractUser):
    """Custom user model for Citi Group."""
    ACCOUNT_TIER_CHOICES = [
        ('standard', 'Standard'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='United States')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    account_number = models.CharField(max_length=10, unique=True, default=generate_account_number)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    account_tier = models.CharField(max_length=20, choices=ACCOUNT_TIER_CHOICES, default='standard')
    is_email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.account_number})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_masked_account(self):
        return f"****-****-{self.account_number[-4:]}"


class Transaction(models.Model):
    """Model for all banking transactions."""
    TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer_out', 'Transfer Out'),
        ('transfer_in', 'Transfer In'),
        ('loan_disbursement', 'Loan Disbursement'),
        ('loan_repayment', 'Loan Repayment'),
    ]
    TRANSFER_METHOD_CHOICES = [
        ('local', 'Local Transfer'),
        ('international', 'International Wire'),
    ]
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transactions')
    recipient_account = models.CharField(max_length=255, blank=True)
    recipient_name = models.CharField(max_length=200, blank=True)
    deposit_method = models.CharField(max_length=10, choices=[('crypto', 'Cryptocurrency'), ('bank', 'Bank Transfer')], blank=True)
    transfer_method = models.CharField(max_length=15, choices=TRANSFER_METHOD_CHOICES, blank=True)
    swift_code = models.CharField(max_length=20, blank=True, help_text='SWIFT/BIC code for international wires')
    iban = models.CharField(max_length=50, blank=True, help_text='IBAN or account number for international wires')
    bank_name = models.CharField(max_length=200, blank=True, help_text='Beneficiary bank name')
    beneficiary_country = models.CharField(max_length=100, blank=True)
    compliance_blocked = models.BooleanField(default=False, help_text='Blocked for compliance verification')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    balance_after = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - ${self.amount} - {self.user}"

    @property
    def transaction_id(self):
        return f"#TXN-{str(self.id)[:8].upper()}"

    @property
    def is_credit(self):
        return self.transaction_type in ['deposit', 'transfer_in', 'loan_disbursement']


class Loan(models.Model):
    """Model for loan management."""
    PURPOSE_CHOICES = [
        ('home', 'Home Improvement'),
        ('auto', 'Auto Purchase'),
        ('personal', 'Personal'),
        ('business', 'Business'),
        ('debt', 'Debt Consolidation'),
        ('education', 'Education'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('paid', 'Fully Paid'),
        ('rejected', 'Rejected'),
    ]
    TERM_CHOICES = [
        (12, '12 Months'),
        (24, '24 Months'),
        (36, '36 Months'),
        (48, '48 Months'),
        (60, '60 Months'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=4.5)
    term_months = models.IntegerField(choices=TERM_CHOICES)
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    outstanding_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    next_payment_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_purpose_display()} Loan - ${self.amount} ({self.status})"

    @property
    def loan_number(self):
        return f"#{str(self.id)[:4].upper()}"

    @property
    def progress_percentage(self):
        if self.amount == 0:
            return 0
        return min(int((self.total_paid / self.amount) * 100), 100)

    @property
    def remaining_months(self):
        if self.monthly_payment <= 0:
            return 0
        if self.outstanding_balance <= 0:
            return 0
        return max(0, int(self.outstanding_balance / self.monthly_payment))

    def calculate_monthly_payment(self):
        """Calculate monthly payment using amortization formula."""
        r = float(self.interest_rate) / 100 / 12  # Monthly interest rate
        n = self.term_months
        p = float(self.amount)
        if r == 0:
            return round(p / n, 2)
        payment = p * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        return round(payment, 2)

    def save(self, *args, **kwargs):
        if not self.monthly_payment or self.monthly_payment == 0:
            self.monthly_payment = self.calculate_monthly_payment()
        if not self.outstanding_balance:
            self.outstanding_balance = self.amount
        super().save(*args, **kwargs)


class Card(models.Model):
    """Model for debit/credit card management."""
    CARD_TYPE_CHOICES = [
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ]
    TIER_CHOICES = [
        ('classic', 'Classic'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('expired', 'Expired'),
        ('pending', 'Pending Activation'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards')
    card_type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='classic')
    card_number = models.CharField(max_length=16, unique=True, default=generate_card_number)
    expiry_date = models.DateField()
    cvv = models.CharField(max_length=4)
    pin = models.CharField(max_length=4, blank=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    available_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_contactless = models.BooleanField(default=True)
    daily_limit = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_tier_display()} {self.get_card_type_display()} - ****{self.card_number[-4:]}"

    @property
    def masked_number(self):
        return f"**** **** **** {self.card_number[-4:]}"

    @property
    def holder_name(self):
        return self.user.get_full_name().upper()


class Notification(models.Model):
    """Model for in-app notifications."""
    TYPE_CHOICES = [
        ('transaction', 'Transaction'),
        ('loan', 'Loan'),
        ('card', 'Card'),
        ('security', 'Security'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user}"


class ContactMessage(models.Model):
    """Model for contact form submissions."""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=300)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} - {self.name}"


class CryptoWallet(models.Model):
    """Admin-managed crypto wallet addresses for deposits."""
    name = models.CharField(max_length=50, help_text="e.g. Bitcoin, Ethereum, USDT")
    symbol = models.CharField(max_length=10, help_text="e.g. BTC, ETH, USDT")
    network = models.CharField(max_length=50, blank=True, help_text="e.g. ERC20, TRC20, BEP20")
    address = models.CharField(max_length=255)
    qr_code = models.ImageField(upload_to='wallet_qr/', blank=True, null=True)
    icon_color = models.CharField(max_length=20, default='bg-orange-500', help_text="Tailwind bg color class")
    icon_symbol = models.CharField(max_length=5, default='₿', help_text="Symbol shown in the icon circle")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        label = f"{self.name} ({self.symbol})"
        if self.network:
            label += f" - {self.network}"
        return label


class BankAccount(models.Model):
    """Admin-managed bank account details for deposits."""
    bank_name = models.CharField(max_length=200)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50, blank=True)
    swift_code = models.CharField(max_length=20, blank=True, help_text="SWIFT/BIC code")
    iban = models.CharField(max_length=50, blank=True, help_text="IBAN (if applicable)")
    additional_info = models.TextField(blank=True, help_text="Any extra instructions for the user")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'bank_name']

    def __str__(self):
        return f"{self.bank_name} - {self.account_name}"


class TVNRequest(models.Model):
    """Model for Tax Verification Number (TVN) requests for compliance."""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tvn_requests')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='tvn_requests')

    # Applicant details
    full_legal_name = models.CharField(max_length=255, help_text='Full legal name as on passport')
    date_of_birth = models.DateField()
    country_of_residence = models.CharField(max_length=100)
    tax_id_last4 = models.CharField(max_length=4, help_text='Last 4 digits of Tax ID / SSN')
    residential_address = models.TextField()

    # Transaction details (snapshot)
    transfer_amount = models.DecimalField(max_digits=15, decimal_places=2)
    receiving_bank = models.CharField(max_length=200, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"TVN Request - {self.full_legal_name} ({self.status})"

    @property
    def reference_number(self):
        date_str = self.created_at.strftime('%Y-%m-%d') if self.created_at else 'PENDING'
        return f"MDL-{date_str}-{str(self.id)[:4].upper()}"


class TaxVerificationNumber(models.Model):
    """Admin-managed valid Tax Verification Numbers (TVN) for compliance validation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, help_text='The valid TVN code (e.g. TVN-USA-2026-XXXX)')
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tax_verification_numbers',
        help_text='Optionally assign this TVN to a specific user'
    )
    description = models.CharField(max_length=255, blank=True, help_text='Optional notes about this TVN')
    is_active = models.BooleanField(default=True, help_text='Only active TVNs can be validated')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Tax Verification Number'
        verbose_name_plural = 'Tax Verification Numbers'

    def __str__(self):
        label = self.code
        if self.assigned_to:
            label += f" ({self.assigned_to.get_full_name()})"
        return label


class Complaint(models.Model):
    """Model for user complaints and support requests."""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    CATEGORY_CHOICES = [
        ('transaction', 'Transaction Issue'),
        ('account', 'Account Issue'),
        ('card', 'Card Issue'),
        ('loan', 'Loan Issue'),
        ('security', 'Security Concern'),
        ('service', 'Service Quality'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    subject = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_response = models.TextField(blank=True, help_text='Admin reply to the complaint')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{str(self.id)[:6].upper()} - {self.subject} ({self.status})"

    @property
    def ticket_number(self):
        return f"TKT-{str(self.id)[:8].upper()}"
