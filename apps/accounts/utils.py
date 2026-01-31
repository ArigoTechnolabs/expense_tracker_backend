from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_otp_email(to_email, otp):
    """
    Send OTP email using SMTP.
    """
    try:
        subject = "OTP Verification - ExpensePro"

        # Render HTML email template
        html_message = render_to_string("emails/otp_email.html", {"otp": otp})

        # Plain text fallback
        plain_message = f"Your OTP for verification is: {otp}\n\nThis OTP is valid for a limited time. Please do not share this code with anyone."

        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"OTP email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"SMTP Exception: {e}")
        return False
