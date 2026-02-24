from django.db import models
from apps.common.models import BaseModel
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifiers for authentication
    instead of usernames.
    """

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """
    User model with email as username
    """

    email = models.EmailField(unique=True)
    google_id = models.CharField(max_length=255, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    address = models.TextField(null=True, blank=True)
    phone_number = PhoneNumberField(unique=True)
    terms_conditions_accepted = models.BooleanField(default=False)
    device_token = models.CharField(max_length=255, null=True, blank=True)
    device_type = models.CharField(max_length=100, null=True, blank=True)
    device_version = models.CharField(max_length=100, null=True, blank=True)
    app_version = models.CharField(max_length=100, null=True, blank=True)
    device_model = models.CharField(max_length=100, null=True, blank=True)
    # security fields
    otp = models.CharField(max_length=6, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    jwt_key = models.CharField(max_length=255, null=True, blank=True)

    username = None  # Disable username if using email for login

    USERNAME_FIELD = "email"  # Use email for authentication
    REQUIRED_FIELDS = []  # Email & Password are required by default
    objects = UserManager()

    def __str__(self):
        return self.email


class TempUserRegistration(BaseModel):
    """
    Temporary model to store OTP and email during registration
    """

    email = models.EmailField(unique=True)
    otp_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()

    def __str__(self):
        return self.email
