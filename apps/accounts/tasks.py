from django.utils import timezone
from apps.accounts.models import TempUserRegistration
from celery import shared_task


@shared_task
def cleanup_expired_temp_users():
    """
    Delete expired temp user registrations
    """
    now = timezone.now()
    deleted_count, _ = TempUserRegistration.objects.filter(expires_at__lt=now).delete()

    return f"Deleted {deleted_count} expired temp users"
