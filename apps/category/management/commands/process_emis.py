import datetime
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from apps.category.models import Emi, Transaction, Category

try:
    import firebase_admin
    from firebase_admin import credentials
except ImportError:
    firebase_admin = None


def get_next_month_date(current_date):
    month = current_date.month
    year = current_date.year
    if month == 12:
        month = 1
        year += 1
    else:
        month += 1

    day = current_date.day
    while True:
        try:
            return datetime.date(year, month, day)
        except ValueError:
            day -= 1


class Command(BaseCommand):
    help = "Process EMIs: send reminders and create expense transactions"

    def handle(self, *args, **kwargs):
        # Initialize Firebase if not already initialized
        if firebase_admin and not firebase_admin._apps:
            cred_path = os.path.join(settings.BASE_DIR, "firebase-credentials.json")
            if os.path.exists(cred_path):
                try:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to initialize Firebase: {e}")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Firebase credentials not found at root. Notifications disabled."
                    )
                )
        elif not firebase_admin:
            self.stdout.write(
                self.style.WARNING(
                    "firebase-admin package not installed. Notifications disabled."
                )
            )

        today = timezone.now().date()
        current_time = timezone.now().time()

        emis = Emi.objects.filter(is_active=True)

        for emi in emis:
            days_until_due = (emi.next_due_date - today).days

            # 1. Check if DUE TODAY or PAST DUE
            if days_until_due <= 0 and emi.last_processed_date != today:
                # Create Expense Transaction
                cat = emi.category
                if not cat:
                    cat, _ = Category.objects.get_or_create(name="EMI", type="expense")

                Transaction.objects.create(
                    user=emi.user,
                    type="expense",
                    category=cat,
                    amount=emi.amount,
                    date=today,
                    note=f"Auto-generated EMI expense for {emi.name}",
                )

                # Send Notification
                self.send_notification(
                    emi.user,
                    "EMI Due Today",
                    f"Your EMI '{emi.name}' of amount {emi.amount} is due today and has been recorded as an expense.",
                )

                # Update EMI next_due_date to next month
                emi.next_due_date = get_next_month_date(emi.next_due_date)
                emi.last_processed_date = today
                emi.save()

            # 2. Check if Reminder is needed (1 or 2 days prior)
            elif days_until_due in [1, 2]:
                if emi.last_notified_date != today:
                    # Check if reminder time has passed or arrived
                    if current_time >= emi.reminder_time:
                        self.send_notification(
                            emi.user,
                            "Upcoming EMI Reminder",
                            f"Your EMI '{emi.name}' of amount {emi.amount} is due in {days_until_due} day(s).",
                        )
                        emi.last_notified_date = today
                        emi.save()

        self.stdout.write(self.style.SUCCESS("Successfully processed all EMIs"))

    def send_notification(self, user, title, body):
        if not firebase_admin or not firebase_admin._apps:
            return  # Firebase not configured

        if getattr(user, "device_token", None):
            try:
                from firebase_admin import messaging

                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    token=user.device_token,
                )
                response = messaging.send(message)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully sent message to {user.email}: {response}"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error sending message to {user.email}: {e}")
                )
