import datetime
import os
import json
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from apps.category.models import Emi, Transaction, Category

logger = logging.getLogger("emi_logger")

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError as e:
    firebase_admin = None
    logger.error(f"Firebase import error: {e}")


def get_due_date_for_month(year, month, day):
    while True:
        try:
            return datetime.date(year, month, day)
        except ValueError:
            day -= 1


class Command(BaseCommand):
    help = "Process EMIs"

    def handle(self, *args, **kwargs):

        # =========================
        # 🔥 FIREBASE INIT
        # =========================
        if firebase_admin and not firebase_admin._apps:
            cred = None

            if settings.FIREBASE_CREDENTIALS_JSON:
                try:
                    cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                    cred = credentials.Certificate(cred_dict)
                    logger.debug("Using Firebase JSON")
                except Exception as e:
                    logger.error(f"JSON error: {e}")

            firebase_path = settings.FIREBASE_CREDENTIALS_PATH
            logger.debug(f"Firebase path: {firebase_path}")

            if not cred and firebase_path:
                if os.path.exists(firebase_path):
                    try:
                        cred = credentials.Certificate(firebase_path)
                        logger.debug("Firebase file loaded")
                    except Exception as e:
                        logger.error(f"File error: {e}")
                else:
                    logger.error("Firebase file NOT found")

            if cred:
                try:
                    firebase_admin.initialize_app(cred)
                    logger.debug("Firebase initialized")
                except Exception as e:
                    logger.error(f"Init error: {e}")
            else:
                logger.error("No Firebase credentials")

        now = timezone.localtime()
        today = now.date()
        current_time = now.time()

        emis = Emi.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        )

        for emi in emis:

            if not emi.due_day:
                logger.debug(f"Skipping EMI (no due_day): {emi.name}")
                continue

            current_due_date = get_due_date_for_month(
                today.year, today.month, emi.due_day
            )

            days_until_due = (current_due_date - today).days

            logger.debug(f"EMI: {emi.name} | Days until due: {days_until_due}")

            # =========================
            # ✅ DUE TODAY OR PAST
            # =========================
            if current_due_date <= today:

                # 🔥 FIX: prevent 12 AM notification
                if emi.reminder_time and current_time < emi.reminder_time:
                    logger.debug("Skipping due notification before reminder_time")
                    continue

                last_processed = emi.last_processed_date

                if not last_processed or (
                    last_processed.year != today.year
                    or last_processed.month != today.month
                ):

                    # ✅ CREATE TRANSACTION
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
                        note=f"Auto EMI: {emi.name}",
                    )

                    logger.debug("Transaction created")

                    # ✅ SEND NOTIFICATION
                    self.send_notification(
                        emi.user,
                        "EMI Due",
                        f"{emi.name} of ₹{emi.amount} is due.",
                    )

                    emi.last_processed_date = today
                    emi.save()

            # =========================
            # 🔔 REMINDER
            # =========================
            elif days_until_due in [1, 2]:

                if not emi.last_notified_date or emi.last_notified_date < today:

                    if emi.reminder_time and current_time >= emi.reminder_time:

                        logger.debug("Sending reminder")

                        self.send_notification(
                            emi.user,
                            "EMI Reminder",
                            f"{emi.name} due in {days_until_due} day(s)",
                        )

                        emi.last_notified_date = today
                        emi.save()

        logger.debug("EMI processing completed")

    def send_notification(self, user, title, body):

        logger.debug(f"User: {user.id}, Token: {user.device_token}")

        if not firebase_admin or not firebase_admin._apps:
            logger.error("Firebase not initialized")
            return

        if not getattr(user, "device_token", None):
            logger.error(f"No token for user {user.id}")
            return

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                token=user.device_token,
            )

            response = messaging.send(message)
            logger.debug(f"Notification sent: {response}")

        except Exception as e:
            logger.error(f"Notification error: {e}")