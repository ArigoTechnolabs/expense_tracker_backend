"""
ASGI config for expensepro project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
import warnings

# Suppress Python 3.8 EOL warning from Google Auth library
warnings.filterwarnings(
    "ignore", ".*Python version 3.8 past its end of life.*", category=FutureWarning
)

from django.core.asgi import get_asgi_application  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "expensepro.settings")

application = get_asgi_application()
