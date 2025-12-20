from django.contrib import admin

from apps.accounts.models import TempUserRegistration, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "google_id",
        "is_verified",
        "terms_conditions_accepted",
    )


@admin.register(TempUserRegistration)
class TempUserRegistrationAdmin(admin.ModelAdmin):
    list_display = ("email", "expires_at")
