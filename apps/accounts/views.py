from datetime import timedelta
import random

from django.utils import timezone
from django.contrib.auth.hashers import make_password
from rest_framework.generics import CreateAPIView
from apps.common.utils import first_error_message, success_response, error_response
from apps.accounts.models import TempUserRegistration as PendingUser
from apps.accounts.serializers import (
    RegisterRequestOtpSerializer,
    RegisterCompleteSerializer,
)
from apps.accounts.utils import send_otp_email


class RegisterRequestOtpView(CreateAPIView):
    """
    - If email not yet registered:
        - If a PendingUser exists and its OTP not expired -> error (OTP still valid)
        - Else create/update PendingUser with new hashed OTP & expiry
        - Send OTP email
    """

    serializer_class = RegisterRequestOtpSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        email = serializer.validated_data["email"]

        pending = PendingUser.objects.filter(email=email).first()

        if pending and pending.expires_at > timezone.now():
            return error_response("OTP is still valid. Please wait until it expires.")

        otp = str(random.randint(100000, 999999))

        if not pending:
            pending = PendingUser(email=email)

        pending.otp_hash = make_password(otp)
        pending.expires_at = timezone.now() + timedelta(minutes=5)
        pending.save()

        email_sent = send_otp_email(email, otp)
        if not email_sent:
            return error_response("Failed to send OTP email.")

        return success_response("OTP sent successfully. Please check your email.")


class RegisterCompleteView(CreateAPIView):
    """
    Validates:
    - email not already registered
    - phone not already registered
    - OTP exists, is correct, and not expired (via TempUserRegistration)
    - T&C accepted

    On success:
    - Creates User
    - Deletes the TempUserRegistration record
    """

    serializer_class = RegisterCompleteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        user = serializer.save()

        user_data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": str(user.phone_number),
            "is_verified": user.is_verified,
        }

        return success_response("Registration successful.", data=user_data)
