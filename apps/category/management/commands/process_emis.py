import datetime
import os
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from apps.category.models import Emi, Transaction, Category

try:
    import firebase_admin
    from firebase_admin import credentials
except ImportError:
    firebase_admin = None


def get_due_date_for_month(year, month, day):
    # Handle month rollover and days that don't exist in all months (like 31st)
    while True:
        try:
            return datetime.date(year, month, day)
        except ValueError:
            # If day 31 doesn't exist in that month, try 30, then 29...
            day -= 1


class Command(BaseCommand):
    help = "Process EMIs: send reminders and create expense transactions"

    def handle(self, *args, **kwargs):
        # Initialize Firebase if not already initialized
        if firebase_admin and not firebase_admin._apps:
            cred = None

            # 1. Try JSON string from ENV
            if settings.FIREBASE_CREDENTIALS_JSON:
                try:
                    cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                    cred = credentials.Certificate(cred_dict)
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Using Firebase credentials from JSON string."
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to load Firebase JSON string: {e}")
                    )

            # 2. Try file path from ENV if JSON string failed
            if not cred and settings.FIREBASE_CREDENTIALS_PATH:
                if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                    try:
                        cred = credentials.Certificate(
                            settings.FIREBASE_CREDENTIALS_PATH
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Using Firebase credentials from file: {settings.FIREBASE_CREDENTIALS_PATH}"
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Failed to load Firebase file: {e}")
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Firebase file not found at: {settings.FIREBASE_CREDENTIALS_PATH}"
                        )
                    )

            # 3. Fallback to default local path
            if not cred:
                default_path = os.path.join(
                    settings.BASE_DIR, "firebase-credentials.json"
                )
                if os.path.exists(default_path):
                    try:
                        cred = credentials.Certificate(default_path)
                        self.stdout.write(
                            self.style.SUCCESS(
                                "Using default firebase-credentials.json file."
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Failed to load default Firebase file: {e}"
                            )
                        )

            if cred:
                try:
                    firebase_admin.initialize_app(cred)
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to initialize Firebase app: {e}")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "No Firebase credentials provided. Notifications disabled."
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

        # Only process active EMIs where today is within the start and end range
        emis = Emi.objects.filter(
            is_active=True, start_date__lte=today, end_date__gte=today
        )

        for emi in emis:
            # Construct the due date for the CURRENT month
            current_due_date = get_due_date_for_month(
                today.year, today.month, emi.due_day
            )

            days_until_due = (current_due_date - today).days

            # 1. Check if DUE TODAY or PAST DUE for this month
            if current_due_date <= today:
                last_processed = emi.last_processed_date
                # If not processed this month yet
                if not last_processed or (
                    last_processed.year != today.year
                    or last_processed.month != today.month
                ):
                    # Create Expense Transaction
                    cat = emi.category
                    if not cat:
                        cat, _ = Category.objects.get_or_create(
                            name="EMI", type="expense"
                        )

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

                    # Update last_processed_date
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
