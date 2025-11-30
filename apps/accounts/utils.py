from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from expensepro.settings import (
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL,
    SENDGRID_TEMPLATE_ID_OTP,
)


def send_otp_email(to_email, otp):
    message = Mail(
        from_email=SENDGRID_FROM_EMAIL,
        to_emails=to_email,
    )

    message.template_id = SENDGRID_TEMPLATE_ID_OTP
    print(message.template_id, "Template ID")
    message.dynamic_template_data = {"otp": otp}

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print("SendGrid status code:", response.status_code)
        print("SendGrid body:", response.body)
        return True
    except Exception as e:
        print("SendGrid Exception:", e)
        return False
