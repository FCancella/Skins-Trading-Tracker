"""
Application configuration for the `trades` app.

This class defines metadata about the application used by Django to
initialize it properly. It primarily sets the name of the app.
"""
from __future__ import annotations

from django.apps import AppConfig


class TradesConfig(AppConfig):
    """AppConfig for the trades app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trades'