from datetime import timedelta
import random
from rest_framework_simplejwt.tokens import RefreshToken

from django.utils import timezone
from django.contrib.auth.hashers import make_password
from rest_framework.generics import CreateAPIView
from apps.common.utils import first_error_message, success_response, error_response
from apps.accounts.models import TempUserRegistration as PendingUser
from apps.accounts.serializers import (
    MyTokenObtainPairSerializer,
    RegisterRequestOtpSerializer,
    RegisterCompleteSerializer,
    UserResponseSerializer,
)
from apps.accounts.utils import send_otp_email


class RegisterRequestOtpView(CreateAPIView):
    serializer_class = RegisterRequestOtpSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        email = serializer.validated_data["email"]
        req_type = serializer.validated_data["type"]

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

        return success_response(
            f"OTP sent successfully for {req_type}. Please check your email."
        )


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
        user_data = UserResponseSerializer(user).data

        return success_response("Registration successful.", data=user_data)


class MyTokenObtainPairView(CreateAPIView):
    serializer_class = MyTokenObtainPairSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        response_data = {
            "user": UserResponseSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        return success_response(
            message="Token obtained successfully.",
            data=response_data,
        )
