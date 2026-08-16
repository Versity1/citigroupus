from django.urls import path
from . import views
from . import admin_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('personal/', views.personal, name='personal'),
    path('business/', views.business, name='business'),
    path('wealth/', views.wealth, name='wealth'),
    path('careers/', views.careers, name='careers'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('faq/', views.faq, name='faq'),

    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Transactions
    path('deposit/', views.deposit, name='deposit'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('transfer/', views.transfer, name='transfer'),
    path('transfer/verify-pin/', views.transfer_verify_pin, name='transfer_verify_pin'),
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('transactions/<uuid:tx_id>/receipt/', views.transaction_receipt, name='transaction_receipt'),

    # Loans
    path('loans/', views.loans, name='loans'),
    path('loans/apply/', views.loan_apply, name='loan_apply'),
    path('loans/<uuid:loan_id>/repay/', views.loan_repay, name='loan_repay'),

    # Cards
    path('cards/', views.cards, name='cards'),
    path('cards/request/', views.card_request, name='card_request'),
    path('cards/<uuid:card_id>/toggle-freeze/', views.card_toggle_freeze, name='card_toggle_freeze'),

    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/toggle-2fa/', views.toggle_2fa, name='toggle_2fa'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/count/', views.notification_count, name='notification_count'),

    # HTMX endpoints
    path('check-recipient/', views.check_recipient, name='check_recipient'),

    # Compliance & TVN
    path('compliance/', views.compliance_status, name='compliance_status'),
    path('compliance/<uuid:tx_id>/', views.compliance_blocked_view, name='compliance_blocked'),
    path('compliance/<uuid:tx_id>/validate-tvn/', views.validate_tvn, name='validate_tvn'),
    path('compliance/<uuid:tx_id>/tvn-request/', views.tvn_request, name='tvn_request'),

    # Support / Complaints
    path('support/', views.support_contact, name='support_contact'),

    # ──────────────────────────────────────
    # CUSTOM ADMIN PANEL
    # ──────────────────────────────────────
    path('management/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('management/users/', admin_views.admin_users, name='admin_users'),
    path('management/users/add/', admin_views.admin_user_form, name='admin_user_add'),
    path('management/users/<uuid:user_id>/edit/', admin_views.admin_user_form, name='admin_user_edit'),
    path('management/users/<uuid:user_id>/', admin_views.admin_user_detail, name='admin_user_detail'),
    path('management/transactions/', admin_views.admin_transactions, name='admin_transactions'),
    path('management/transactions/<uuid:tx_id>/edit/', admin_views.admin_transaction_edit, name='admin_transaction_edit'),
    path('management/transactions/<uuid:tx_id>/action/', admin_views.admin_transaction_action, name='admin_transaction_action'),
    path('management/loans/', admin_views.admin_loans, name='admin_loans'),
    path('management/loans/<uuid:loan_id>/action/', admin_views.admin_loan_action, name='admin_loan_action'),
    path('management/cards/', admin_views.admin_cards, name='admin_cards'),
    path('management/cards/<uuid:card_id>/action/', admin_views.admin_card_action, name='admin_card_action'),
    path('management/wallets/', admin_views.admin_wallets, name='admin_wallets'),
    path('management/wallets/add/', admin_views.admin_wallet_form, name='admin_wallet_add'),
    path('management/wallets/<int:wallet_id>/edit/', admin_views.admin_wallet_form, name='admin_wallet_edit'),
    path('management/wallets/<int:wallet_id>/delete/', admin_views.admin_wallet_delete, name='admin_wallet_delete'),
    path('management/bank-accounts/', admin_views.admin_bank_accounts, name='admin_bank_accounts'),
    path('management/bank-accounts/add/', admin_views.admin_bank_account_form, name='admin_bank_account_add'),
    path('management/bank-accounts/<int:account_id>/edit/', admin_views.admin_bank_account_form, name='admin_bank_account_edit'),
    path('management/bank-accounts/<int:account_id>/delete/', admin_views.admin_bank_account_delete, name='admin_bank_account_delete'),
    path('management/messages/', admin_views.admin_messages, name='admin_messages'),
    path('management/messages/<int:message_id>/toggle/', admin_views.admin_message_toggle, name='admin_message_toggle'),
    path('management/send-email/', admin_views.admin_send_email, name='admin_send_email'),
    path('management/compliance/', admin_views.admin_compliance, name='admin_compliance'),
    path('management/compliance/<uuid:tx_id>/action/', admin_views.admin_compliance_action, name='admin_compliance_action'),
    path('management/compliance/tvn/<uuid:tvn_id>/action/', admin_views.admin_tvn_action, name='admin_tvn_action'),
    path('management/complaints/', admin_views.admin_complaints, name='admin_complaints'),
    path('management/complaints/<uuid:complaint_id>/action/', admin_views.admin_complaint_action, name='admin_complaint_action'),
]
