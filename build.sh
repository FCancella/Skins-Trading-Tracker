#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Set DEBUG to false for production static file collection
export DJANGO_SETTINGS_MODULE=cs_trade_portfolio.settings
export DEBUG=False

python manage.py collectstatic --no-input

python manage.py migrate