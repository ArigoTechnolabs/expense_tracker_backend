from datetime import timedelta
import random
from rest_framework_simplejwt.tokens import RefreshToken

from django.utils import timezone
from django.contrib.auth.hashers import make_password
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.common.utils import first_error_message, success_response, error_response
from apps.accounts.models import TempUserRegistration as PendingUser, User
from apps.accounts.serializers import (
    ForgotPasswordRequestOtpSerializer,
    MyTokenObtainPairSerializer,
    RegisterRequestOtpSerializer,
    RegisterCompleteSerializer,
    ResetPasswordSerializer,
    UserResponseSerializer,
)
from apps.accounts.utils import send_otp_email
from apps.common import messages


class RegisterRequestOtpView(CreateAPIView):
    """
    Request an OTP for registration or login.
    """

    serializer_class = RegisterRequestOtpSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        email = serializer.validated_data["email"]
        req_type = serializer.validated_data["type"]

        # If login type and user is already registered, don't send OTP
        # User should login with email and password directly
        if req_type == "login":
            user_exists = User.objects.filter(email=email).exists()
            if user_exists:
                return error_response(messages.USER_ALREADY_REGISTERED)

        pending = PendingUser.objects.filter(email=email).first()

        if pending and pending.expires_at > timezone.now():
            return error_response(messages.OTP_STILL_VALID)

        otp = str(random.randint(100000, 999999))

        if not pending:
            pending = PendingUser(email=email)

        pending.otp_hash = make_password(otp)
        pending.expires_at = timezone.now() + timedelta(minutes=5)
        pending.save()

        email_sent = send_otp_email(email, otp)
        if not email_sent:
            return error_response(messages.FAILED_TO_SEND_OTP_EMAIL)

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
        refresh = RefreshToken.for_user(user)

        response_data = {
            "user": UserResponseSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        # user_data = UserResponseSerializer(user).data

        return success_response(messages.REGISTRATION_SUCCESSFUL, data=response_data)


class MyTokenObtainPairView(CreateAPIView):
    """
    Login view to obtain JWT tokens.
    """

    serializer_class = MyTokenObtainPairSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        user = serializer.validated_data["user"]

        # Rotate JWT Key for single-device login
        from apps.accounts.authentication import rotate_jwt_key

        rotate_jwt_key(user)

        refresh = RefreshToken.for_user(user)
        # Manually add jwt_key to token claims
        refresh["jwt_key"] = user.jwt_key

        response_data = {
            "user": UserResponseSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        return success_response(
            message=messages.TOKEN_OBTAINED_SUCCESSFULLY,
            data=response_data,
        )


class UserProfileView(APIView):
    """
    Get or update user profile details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserResponseSerializer(request.user)
        return success_response(data=serializer.data)

    def patch(self, request):
        from apps.accounts.serializers import UserUpdateSerializer

        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(first_error_message(serializer.errors))

        user = serializer.save()
        return success_response(
            message="Profile updated successfully",
            data=UserResponseSerializer(user).data,
        )


class ForgotPasswordRequestOtpView(CreateAPIView):
    """
    Forgot password - request OTP view.
    """

    serializer_class = ForgotPasswordRequestOtpSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return error_response(first_error_message(serializer.errors))

        email = serializer.validated_data["email"]

        pending = PendingUser.objects.filter(email=email).first()
        if pending and pending.expires_at > timezone.now():
            return error_response(messages.OTP_STILL_VALID)

        otp = str(random.randint(100000, 999999))

        if not pending:
            pending = PendingUser(email=email)

        pending.otp_hash = make_password(otp)
        pending.expires_at = timezone.now() + timedelta(minutes=5)
        pending.save()

        if not send_otp_email(email, otp):
            return error_response(messages.FAILED_TO_SEND_OTP_EMAIL)

        return success_response(messages.OTP_SENT_SUCCESSFULLY)


class ResetPasswordView(CreateAPIView):
    """
    Reset Password view.
    """

    serializer_class = ResetPasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return error_response(first_error_message(serializer.errors))

        email = serializer.validated_data["email"]
        new_password = serializer.validated_data["new_password"]

        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        if hasattr(serializer, "_pending"):
            serializer._pending.delete()

        return success_response(messages.PASSWORD_RESET_SUCCESSFUL)
