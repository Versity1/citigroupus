from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Loan, Card, ContactMessage


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'First Name',
            'class': 'form-input w-full pl-10 pr-4 py-3 rounded-lg border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-primary focus:ring-0 transition-colors',
        })
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last Name',
            'class': 'form-input w-full pl-10 pr-4 py-3 rounded-lg border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-primary focus:ring-0 transition-colors',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'name@example.com',
            'class': 'form-input w-full pl-10 pr-10 py-3 rounded-lg border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-primary focus:ring-0 transition-colors',
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '+1 (555) 000-0000',
            'class': 'form-input w-full pl-10 pr-4 py-3 rounded-lg border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-primary focus:ring-0 transition-colors',
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Create a strong password',
            'class': 'form-input w-full pl-10 pr-10 py-3 rounded-lg border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-primary focus:ring-0 transition-colors',
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your password',
            'class': 'form-input w-full pl-10 pr-4 py-3 rounded-lg border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-primary focus:ring-0 transition-colors',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email  # Use email as username
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email or ID',
            'class': 'form-input flex w-full rounded-lg text-slate-900 border border-slate-200 bg-slate-50 focus:bg-white focus:border-primary focus:ring-4 focus:ring-primary/10 h-12 pl-10 pr-4 placeholder:text-slate-400 text-base transition-all duration-200',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'form-input flex w-full rounded-lg text-slate-900 border border-slate-200 bg-slate-50 focus:bg-white focus:border-primary focus:ring-4 focus:ring-primary/10 h-12 pl-10 pr-10 placeholder:text-slate-400 text-base transition-all duration-200',
        })
    )


class TransferForm(forms.Form):
    TRANSFER_TYPE_CHOICES = [
        ('local', 'Local Transfer'),
        ('international', 'International Wire'),
    ]

    transfer_type = forms.ChoiceField(
        choices=TRANSFER_TYPE_CHOICES,
        initial='local',
        widget=forms.HiddenInput(),
    )

    # ── Common fields ──
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0.01',
            'class': 'bg-transparent border-none p-0 text-4xl font-bold text-slate-900 dark:text-white focus:ring-0 placeholder-gray-300 w-full',
        })
    )
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'e.g. Rent for November',
            'rows': 2,
            'class': 'w-full rounded-lg border-slate-200 dark:border-slate-700 focus:border-primary focus:ring-primary p-3 text-slate-900 dark:text-white dark:bg-slate-900 placeholder-gray-400 font-medium resize-none',
        })
    )

    # ── Local transfer fields ──
    local_account_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Account Number',
            'class': 'w-full h-12 rounded-lg border-slate-200 dark:border-slate-700 focus:border-primary focus:ring-primary pl-4 pr-10 text-slate-900 dark:text-white dark:bg-slate-900 placeholder-gray-400 font-medium transition-shadow',
        })
    )
    local_account_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Account Name',
            'class': 'w-full h-12 rounded-lg border-slate-200 dark:border-slate-700 focus:border-primary focus:ring-primary pl-4 pr-4 text-slate-900 dark:text-white dark:bg-slate-900 placeholder-gray-400 font-medium',
        })
    )
    local_bank_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Bank Name',
            'class': 'w-full h-12 rounded-lg border-slate-200 dark:border-slate-700 focus:border-primary focus:ring-primary pl-4 pr-4 text-slate-900 dark:text-white dark:bg-slate-900 placeholder-gray-400 font-medium',
        })
    )

    # ── International wire fields ──
    intl_recipient_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Full name of beneficiary',
            'class': 'w-full h-12 rounded-lg border-slate-200 dark:border-slate-700 focus:border-primary focus:ring-primary pl-4 pr-4 text-slate-900 dark:text-white dark:bg-slate-900 placeholder-gray-400 font-medium',
        })
    )
    intl_bank_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Deutsche Bank',
            'class': 'w-full h-12 rounded-lg border-slate-200 dark:border-slate-700 focus:border-primary focus:ring-primary pl-4 pr-4 text-slate-900 dark:text-white dark:bg-slate-900 placeholder-gray-400 font-medium',
        })
    )
    intl_swift_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. DEUTDEFF',
            'class': 'w-full h-12 rounded-lg border-slate-200 dark:border-slate-700 focus:border-primary focus:ring-primary pl-4 pr-4 text-slate-900 dark:text-white dark:bg-slate-900 placeholder-gray-400 font-medium uppercase',
        })
    )
    intl_iban = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. DE89 3704 0044 0532 0130 00',
            'class': 'w-full h-12 rounded-lg border-slate-200 dark:border-slate-700 focus:border-primary focus:ring-primary pl-4 pr-4 text-slate-900 dark:text-white dark:bg-slate-900 placeholder-gray-400 font-medium',
        })
    )
    intl_country = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Germany',
            'class': 'w-full h-12 rounded-lg border-slate-200 dark:border-slate-700 focus:border-primary focus:ring-primary pl-4 pr-4 text-slate-900 dark:text-white dark:bg-slate-900 placeholder-gray-400 font-medium',
        })
    )

    def clean(self):
        cleaned = super().clean()
        transfer_type = cleaned.get('transfer_type')

        if transfer_type == 'local':
            required_local = {
                'local_account_number': 'Account Number',
                'local_account_name': 'Account Name',
                'local_bank_name': 'Bank Name',
            }
            for field, label in required_local.items():
                if not cleaned.get(field):
                    self.add_error(field, f'{label} is required for local transfers.')
        elif transfer_type == 'international':
            required_intl = {
                'intl_recipient_name': 'Beneficiary name',
                'intl_bank_name': 'Bank name',
                'intl_swift_code': 'SWIFT/BIC code',
                'intl_iban': 'IBAN / Account number',
                'intl_country': 'Country',
            }
            for field, label in required_intl.items():
                if not cleaned.get(field):
                    self.add_error(field, f'{label} is required for international wire transfers.')

        return cleaned


class DepositWithdrawForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0.01',
            'class': 'bg-transparent border-none p-0 text-3xl font-bold text-slate-900 focus:ring-0 placeholder-gray-300 w-full',
        })
    )
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Description (optional)',
            'class': 'w-full rounded-lg border-slate-200 focus:border-primary focus:ring-primary p-3 text-slate-900 placeholder-gray-400 font-medium',
        })
    )


class LoanApplicationForm(forms.Form):
    PURPOSE_CHOICES = [
        ('home', 'Home Improvement'),
        ('auto', 'Auto Purchase'),
        ('personal', 'Personal'),
        ('business', 'Business'),
        ('debt', 'Debt Consolidation'),
        ('education', 'Education'),
    ]
    TERM_CHOICES = [
        (12, '12 Months'),
        (24, '24 Months'),
        (36, '36 Months'),
        (48, '48 Months'),
        (60, '60 Months'),
    ]

    purpose = forms.ChoiceField(
        choices=PURPOSE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full appearance-none bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white rounded-lg py-3 px-4 focus:ring-2 focus:ring-primary focus:border-transparent cursor-pointer',
        })
    )
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=1000,
        max_value=50000,
        widget=forms.NumberInput(attrs={
            'step': '500',
            'min': '1000',
            'max': '50000',
            'class': 'w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer dark:bg-slate-700',
        })
    )
    term_months = forms.ChoiceField(
        choices=TERM_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'peer sr-only',
        })
    )


class CardRequestForm(forms.Form):
    CARD_TYPE_CHOICES = [
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ]
    TIER_CHOICES = [
        ('classic', 'Classic'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]

    card_type = forms.ChoiceField(choices=CARD_TYPE_CHOICES)
    tier = forms.ChoiceField(choices=TIER_CHOICES)


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'address', 'city', 'state', 'zip_code', 'country']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'block w-full rounded-md border-0 py-1.5 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6'}),
            'last_name': forms.TextInput(attrs={'class': 'block w-full rounded-md border-0 py-1.5 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6'}),
            'phone': forms.TextInput(attrs={'class': 'block w-full rounded-md border-0 py-1.5 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'block w-full rounded-md border-0 py-1.5 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6'}),
            'city': forms.TextInput(attrs={'class': 'block w-full rounded-md border-0 py-1.5 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6'}),
            'state': forms.TextInput(attrs={'class': 'block w-full rounded-md border-0 py-1.5 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6'}),
            'zip_code': forms.TextInput(attrs={'class': 'block w-full rounded-md border-0 py-1.5 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6'}),
            'country': forms.TextInput(attrs={'class': 'block w-full rounded-md border-0 py-1.5 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6'}),
        }


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your full name', 'class': 'w-full h-12 rounded-lg border-slate-200 focus:border-primary focus:ring-primary pl-4 text-slate-900 placeholder-gray-400'}),
            'email': forms.EmailInput(attrs={'placeholder': 'name@example.com', 'class': 'w-full h-12 rounded-lg border-slate-200 focus:border-primary focus:ring-primary pl-4 text-slate-900 placeholder-gray-400'}),
            'subject': forms.TextInput(attrs={'placeholder': 'How can we help?', 'class': 'w-full h-12 rounded-lg border-slate-200 focus:border-primary focus:ring-primary pl-4 text-slate-900 placeholder-gray-400'}),
            'message': forms.Textarea(attrs={'placeholder': 'Tell us more...', 'rows': 5, 'class': 'w-full rounded-lg border-slate-200 focus:border-primary focus:ring-primary p-4 text-slate-900 placeholder-gray-400 resize-none'}),
        }
