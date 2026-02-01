from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import ContactSubmissionSerializer


@api_view(["POST"])
def contact_submit(request):
    """
    API endpoint to handle contact form submissions.
    Sends email to arigo.technolabs@gmail.com and saves submission to database.
    """
    serializer = ContactSubmissionSerializer(data=request.data)

    if serializer.is_valid():
        # Save to database
        contact = serializer.save()

        # Prepare email content
        subject = f"New Contact Form Submission from {contact.name}"
        message = f"""
You have received a new contact form submission:

Name: {contact.name}
Email: {contact.email}

Message:
{contact.message}

---
This message was sent from your website contact form.
        """

        recipient_email = "arigo.technolabs@gmail.com"

        try:
            # Send email using SMTP
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )

            return Response(
                {
                    "success": True,
                    "message": "Your message has been sent successfully!",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            # Even if email fails, the submission is saved
            return Response(
                {
                    "success": True,
                    "message": "Your message has been received, but there was an issue sending the email notification.",
                    "error": str(e),
                },
                status=status.HTTP_201_CREATED,
            )

    return Response(
        {"success": False, "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )
