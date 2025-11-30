from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from apps.accounts.models import User
from apps.accounts.serializers import UserRegistrationSerializer
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
