from django.db import models
from apps.common.models import BaseModel
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import AbstractUser


class User(AbstractUser, BaseModel):
    email = models.EmailField(unique=True)
    google_id = models.CharField(max_length=255, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    address = models.TextField(null=True, blank=True)
    phone_number = PhoneNumberField(unique=True)
    terms_conditions_accepted = models.BooleanField(default=False)

    # otp fields
    otp = models.CharField(max_length=6, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    username = None  # Disable username if using email for login

    USERNAME_FIELD = "email"  # Use email for authentication
    REQUIRED_FIELDS = []  # Email & Password are required by default

    def __str__(self):
        return self.email
