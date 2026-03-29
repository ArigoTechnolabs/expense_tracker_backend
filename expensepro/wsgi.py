"""
WSGI config for expensepro project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import warnings

# Suppress Python 3.8 EOL warning from Google Auth library
warnings.filterwarnings(
    "ignore", ".*Python version 3.8 past its end of life.*", category=FutureWarning
)

from django.core.wsgi import get_wsgi_application  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "expensepro.settings")

application = get_wsgi_application()
