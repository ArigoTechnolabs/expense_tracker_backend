"""
This module previously hosted Celery tasks.

On shared hosting (no Celery/Redis), the periodic cleanup runs via the Django
management command: `python manage.py cleanup_expired_temp_users`.
"""


def cleanup_expired_temp_users():
    raise RuntimeError(
        "Celery is not configured. Run: python manage.py cleanup_expired_temp_users"
    )
