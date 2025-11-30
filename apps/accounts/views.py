from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, UpdateAPIView
from django.utils import timezone
from datetime import timedelta
import random
from rest_framework_simplejwt.views import TokenObtainPairView


from apps.accounts.models import User
from apps.accounts.serializers import (
    MyTokenObtainPairSerializer,
    ResendOtpSerializer,
    UserOtpVerifySerializer,
    UserRegistrationSerializer,
)
from apps.accounts.utils import send_otp_email


class RegisterEmailView(CreateAPIView):
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send OTP email
        email_sent = send_otp_email(user.email, user.otp)
        if not email_sent:
            return Response(
                {"detail": "Failed to send OTP email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {
                "detail": "User registered successfully. Please check your email for the OTP."
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyOtpView(UpdateAPIView):
    serializer_class = UserOtpVerifySerializer
    queryset = User.objects.all()

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        # Check user exists
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"detail": "User not found."}, status=404)

        # If already verified
        if user.is_verified:
            return Response({"detail": "User already verified."}, status=400)

        # If OTP expired
        if not user.expires_at or user.expires_at < timezone.now():
            return Response(
                {"detail": "OTP expired. Please request a new OTP."}, status=400
            )

        # Check correct OTP
        if user.otp != otp:
            return Response({"detail": "Invalid OTP."}, status=400)

        # Mark as verified
        user.is_verified = True
        user.otp = None
        user.expires_at = None
        user.save()

        return Response(
            {"detail": "OTP verified successfully. You can now log in."},
            status=status.HTTP_200_OK,
        )


class ResendOtpView(CreateAPIView):
    serializer_class = ResendOtpSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        # Check user exists
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"detail": "User not found."}, status=404)

        # If already verified → no need to resend
        if user.is_verified:
            return Response(
                {"detail": "User already verified."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if OTP expired
        if user.expires_at and user.expires_at > timezone.now():
            return Response(
                {"detail": "OTP is still valid. Please wait until it expires."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate NEW OTP
        otp = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=5)

        user.otp = otp
        user.expires_at = expiry
        user.save()

        # Send OTP email again
        email_sent = send_otp_email(user.email, otp)
        if not email_sent:
            return Response(
                {"detail": "Failed to send OTP email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"detail": "New OTP sent successfully. Please check your email."},
            status=status.HTTP_200_OK,
        )


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
