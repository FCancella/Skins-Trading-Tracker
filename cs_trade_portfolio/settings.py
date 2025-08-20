"""
Django settings for the Counter‑Strike skin trade management project.

Generated manually for this exercise, the settings defined here provide a
minimal yet functional configuration for running a small application. It
configures a SQLite database for persistence, sets the timezone to the
user's locale (America/Sao_Paulo), and enables the key Django apps and our
custom `trades` app.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/ and
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
from __future__ import annotations

import os
import dj_database_url 
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY: str = os.environ.get('SECRET_KEY', 'replace-this-with-a-secure-key-for-production')
print("\n"*10)
print(f"SECRET_KEY: {SECRET_KEY}")
print("\n"*10)
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG: bool = os.environ.get('DEBUG', 'False').lower() == 'true'

# ALLOWED_HOSTS deve ser configurado via variável de ambiente
ALLOWED_HOSTS_str: str = os.environ.get('DJANGO_ALLOWED_HOSTS', '*')
ALLOWED_HOSTS: list[str] = ALLOWED_HOSTS_str.split(',') if ALLOWED_HOSTS_str else []

print("\n"*10)
print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
print("\n"*10)

# CSRF_TRUSTED_ORIGINS = []

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "login"

# Application definition

INSTALLED_APPS: list[str] = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'trades',  # our custom app
]

MIDDLEWARE: list[str] = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF: str = 'cs_trade_portfolio.urls'

TEMPLATES: list[dict[str, object]] = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION: str = 'cs_trade_portfolio.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': dj_database_url.config(
        # Fallback para o SQLite se DATABASE_URL não estiver definida
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
        conn_health_checks=True,
    )
}
# DATABASES: dict[str, dict[str, str]] = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE: str = 'en-us'

TIME_ZONE: str = 'America/Sao_Paulo'

USE_I18N: bool = True

USE_L10N: bool = True

USE_TZ: bool = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL: str = '/static/'
STATICFILES_DIRS: list[Path] = [BASE_DIR / 'static']

#if not DEBUG:
# Tell Django to copy static assets into a path called `staticfiles` (this is specific to Render)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Enable the WhiteNoise storage backend, which compresses static files to reduce disk use
# and renames the files with unique names for each version to support long-term caching
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD: str = 'django.db.models.BigAutoField'