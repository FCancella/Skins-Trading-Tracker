#!/usr/bin/env python3
"""
Django's command-line utility for administrative tasks.

This file can be used to run development servers, perform database migrations,
and interact with your application. It is intentionally minimal and relies
on Django's internal management machinery. When executed, it looks for the
`DJANGO_SETTINGS_MODULE` environment variable and uses it to configure
settings before delegating to Django's `execute_from_command_line` function.

Usage:
    python manage.py runserver
    python manage.py makemigrations
    python manage.py migrate
"""
import os
import sys


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cs_trade_portfolio.settings')
    try:
        from django.core.management import execute_from_command_line  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()