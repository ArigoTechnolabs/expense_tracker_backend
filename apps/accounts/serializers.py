from rest_framework import serializers
from apps.accounts.models import User
from django.utils import timezone
from django.contrib.auth.hashers import check_password
from apps.accounts.models import TempUserRegistration as PendingUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.common import messages
from apps.common.constants import UserType


class UserResponseSerializer(serializers.ModelSerializer):
    """
    Serializer used for returning user details in API responses.
    """

    phone_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_verified",
        )

    def get_phone_number(self, obj):
        return str(obj.phone_number) if obj.phone_number else None


class RegisterRequestOtpSerializer(serializers.Serializer):
    """
    Serializer for requesting an OTP during registration or login.
    """

    email = serializers.EmailField()
    type = serializers.ChoiceField(choices=UserType.UserTypeChoices)

    def validate(self, attrs):
        email = attrs["email"]
        req_type = attrs["type"]

        user_exists = User.objects.filter(email=email).exists()

        if req_type == "register" and user_exists:
            raise serializers.ValidationError(
                {"email": messages.EMAIL_ALREADY_REGISTERED}
            )

        if req_type == "login" and not user_exists:
            raise serializers.ValidationError(
                {"email": messages.EMAIL_DOESNOT_REGISTERED_PLEASE_REGISTER}
            )

        return attrs


class RegisterCompleteSerializer(serializers.ModelSerializer):
    """
    Serializer responsible for completing user registration.
    """

    otp = serializers.CharField(max_length=6, write_only=True)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "phone_number",
            "address",
            "terms_conditions_accepted",
            "otp",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate_terms_conditions_accepted(self, value):
        if not value:
            raise serializers.ValidationError(messages.ACCEPT_TERMS_CONDITIONS)
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(messages.EMAIL_ALREADY_REGISTERED)
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(messages.PHONE_NUMBER_ALREADY_IN_USE)
        return value

    def validate(self, attrs):
        email = attrs.get("email")
        otp = attrs.get("otp")

        try:
            pending = PendingUser.objects.get(email=email)
        except PendingUser.DoesNotExist:
            raise serializers.ValidationError({"email": messages.OTP_NOT_SENT})

        if pending.expires_at < timezone.now():
            pending.delete()
            raise serializers.ValidationError({"otp": messages.OTP_EXPIRED})

        if not check_password(otp, pending.otp_hash):
            raise serializers.ValidationError({"otp": messages.INVALID_OTP})

        self._pending = pending
        return attrs

    def create(self, validated_data):
        """
        Create the actual user and delete the pending temp record.
        """
        email = validated_data.pop("email")
        password = validated_data.pop("password")

        if User.objects.filter(email=email).exists():
            if hasattr(self, "_pending"):
                self._pending.delete()
            raise serializers.ValidationError(messages.USER_ALREADY_REGISTERED)

        user = User.objects.create_user(
            email=email,
            password=password,
            **validated_data,
            is_verified=True,
        )

        if hasattr(self, "_pending"):
            self._pending.delete()

        return user


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        if not user.is_verified:
            raise serializers.ValidationError(messages.VERIFY_YOUR_EMAIL_ADDRESS)
        data["user"] = user
        return data


class ForgotPasswordRequestOtpSerializer(serializers.Serializer):
    """
    Serializer for initiating the forgot password flow.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(messages.EMAIL_DOESNOT_EXIST)
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for resetting a user's password using OTP.
    """

    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)

    def validate(self, attrs):
        email = attrs["email"]
        otp = attrs["otp"]

        try:
            pending = PendingUser.objects.get(email=email)
        except PendingUser.DoesNotExist:
            raise serializers.ValidationError({"email": messages.OTP_NOT_SENT})

        if pending.expires_at < timezone.now():
            pending.delete()
            raise serializers.ValidationError({"otp": messages.OTP_EXPIRED})

        if not check_password(otp, pending.otp_hash):
            raise serializers.ValidationError({"otp": messages.INVALID_OTP})
        self._pending = pending
        return attrs
