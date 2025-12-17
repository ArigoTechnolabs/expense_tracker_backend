from rest_framework import serializers
from apps.accounts.models import User
from django.utils import timezone
from django.contrib.auth.hashers import check_password
from apps.accounts.models import TempUserRegistration as PendingUser


class RegisterRequestOtpSerializer(serializers.Serializer):
    """
    Serializer for requesting OTP during registration.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value


class RegisterCompleteSerializer(serializers.ModelSerializer):
    """
    Serializer for registering full serializer.
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
            raise serializers.ValidationError("You must accept terms and conditions.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already in use.")
        return value

    def validate(self, attrs):
        email = attrs.get("email")
        otp = attrs.get("otp")

        try:
            pending = PendingUser.objects.get(email=email)
        except PendingUser.DoesNotExist:
            raise serializers.ValidationError(
                {"email": "Pending registration not found for this email."}
            )

        if pending.expires_at < timezone.now():
            pending.delete()
            raise serializers.ValidationError(
                {"otp": "OTP expired. Please request a new one."}
            )

        if not check_password(otp, pending.otp_hash):
            raise serializers.ValidationError({"otp": "Invalid OTP."})

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
            raise serializers.ValidationError(
                "User already registered with this email."
            )

        user = User.objects.create_user(
            email=email,
            password=password,
            **validated_data,
            is_verified=True,
        )

        if hasattr(self, "_pending"):
            self._pending.delete()

        return user
