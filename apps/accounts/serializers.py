from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
import random

from apps.accounts.models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
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
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        email = validated_data["email"]
        raw_password = validated_data.pop("password")

        # Generate OTP ONCE
        otp = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=5)

        user = User.objects.filter(email=email).first()

        # If user exists AND verified → block
        if user and user.is_verified:
            raise serializers.ValidationError("User already registered and verified.")

        # If user exists but unverified → update only user info + KEEP OTP flow
        if user:
            for key, value in validated_data.items():
                setattr(user, key, value)

            user.set_password(raw_password)
            user.otp = otp
            user.expires_at = expiry
            user.save()
            return user

        # NEW USER
        validated_data["otp"] = otp
        validated_data["expires_at"] = expiry

        user = User(**validated_data)
        user.set_password(raw_password)
        user.save()
        return user


class UserOtpVerifySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "otp"]
