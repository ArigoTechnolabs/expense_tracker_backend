#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
import warnings

# Suppress Python 3.8 EOL warning from Google Auth library
warnings.filterwarnings(
    "ignore", ".*Python version 3.8 past its end of life.*", category=FutureWarning
)


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "expensepro.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
