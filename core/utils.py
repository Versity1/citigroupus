from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


def send_notification_email(subject, message, recipient_email):
    """Send a simple notification email."""
    try:
        send_mail(
            subject=f"Citi Group - {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=True,
        )
    except Exception:
        pass


def send_registration_email(user):
    send_notification_email(
        "Welcome to Citi Group!",
        f"Hello {user.first_name},\n\nWelcome to Citi Group! Your account has been created successfully.\n\nAccount Number: {user.account_number}\n\nThank you for choosing Citi Group!",
        user.email,
    )


def send_login_email(user):
    send_notification_email(
        "New Login Detected",
        f"Hello {user.first_name},\n\nA new login was detected on your Citi Group account.\n\nIf this wasn't you, please contact support immediately.",
        user.email,
    )


def send_transaction_email(user, transaction):
    tx_type = transaction.get_transaction_type_display()
    send_notification_email(
        f"Transaction Alert: {tx_type}",
        f"Hello {user.first_name},\n\nA {tx_type.lower()} of ${transaction.amount:,.2f} has been processed.\n\nDescription: {transaction.description}\nNew Balance: ${transaction.balance_after:,.2f}\n\nTransaction ID: {transaction.transaction_id}",
        user.email,
    )


def send_loan_email(user, loan, action="requested"):
    send_notification_email(
        f"Loan {action.title()}",
        f"Hello {user.first_name},\n\nYour {loan.get_purpose_display()} loan for ${loan.amount:,.2f} has been {action}.\n\nMonthly Payment: ${loan.monthly_payment:,.2f}\nTerm: {loan.term_months} months\nInterest Rate: {loan.interest_rate}%",
        user.email,
    )


def send_card_email(user, card, action="requested"):
    send_notification_email(
        f"Card {action.title()}",
        f"Hello {user.first_name},\n\nYour {card.get_tier_display()} {card.get_card_type_display()} card has been {action}.\n\nCard Number: {card.masked_number}",
        user.email,
    )


def send_complaint_email(user, complaint):
    """Send email when a complaint status is updated."""
    status_display = complaint.get_status_display()
    body = (
        f"Hello {user.first_name},\n\n"
        f"Your complaint ticket {complaint.ticket_number} has been updated.\n\n"
        f"Subject: {complaint.subject}\n"
        f"Category: {complaint.get_category_display()}\n"
        f"Status: {status_display}\n"
    )
    if complaint.admin_response:
        body += f"\nAdmin Response:\n{complaint.admin_response}\n"
    body += "\nThank you for contacting Citi Group Support."
    send_notification_email(
        f"Complaint Update - {complaint.ticket_number}",
        body,
        user.email,
    )


def send_transfer_pin_email(user, pin):
    """Send an authorization PIN to the user for a local transfer."""
    send_notification_email(
        "Transfer Authorization PIN",
        f"Hello {user.first_name},\n\nYou have initiated a local transfer.\n\nYour Authorization PIN is: {pin}\n\nPlease enter this PIN on the transfer page to complete your transaction.\nIf you did not initiate this transfer, please contact support immediately.",
        user.email,
    )
