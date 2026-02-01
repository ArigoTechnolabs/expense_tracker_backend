from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Delete unverified users where is_verified=False and updated_at exceeds one hour."

    def handle(self, *args, **options):
        now = timezone.now()
        one_hour_ago = now - timedelta(minutes=1)

        # Delete users where is_verified=False and updated_at is older than 1 hour
        deleted_count, _ = User.objects.filter(
            is_verified=False, updated_at__lt=one_hour_ago
        ).delete()

        msg = f"Deleted {deleted_count} unverified users older than 1 hour"
        self.stdout.write(self.style.SUCCESS(msg))
