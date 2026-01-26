from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import TempUserRegistration


class Command(BaseCommand):
    help = "Delete expired temp user registrations."

    def handle(self, *args, **options):
        now = timezone.now()
        deleted_count, _ = TempUserRegistration.objects.filter(
            expires_at__lt=now
        ).delete()
        msg = f"Deleted {deleted_count} expired temp users"
        self.stdout.write(self.style.SUCCESS(msg))
