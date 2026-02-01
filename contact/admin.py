from django.contrib import admin
from .models import ContactSubmission


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "email", "message")
    readonly_fields = ("created_at",)
