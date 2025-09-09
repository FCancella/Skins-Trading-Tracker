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
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Credenciais do Mercado Pago
MERCADOPAGO_PUBLIC_KEY = os.environ.get('MERCADOPAGO_PUBLIC_KEY')
MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN')
MERCADOPAGO_WEBHOOK_SECRET = os.environ.get('MERCADOPAGO_WEBHOOK_SECRET')

# Carregue a chave secreta de uma variável de ambiente.
SECRET_KEY: str = os.environ.get('SECRET_KEY')

# Chave de API para o Scanner
SCANNER_API_KEY = os.environ.get('SCANNER_API_KEY')

# ATENÇÃO: DEBUG deve ser False em produção!
DEBUG: bool = os.environ.get('DEBUG', 'False').lower() == 'true'

# Carregue os hosts permitidos de uma variável de ambiente.
ALLOWED_HOSTS_str: str = os.environ.get('DJANGO_ALLOWED_HOSTS')
ALLOWED_HOSTS: list[str] = ALLOWED_HOSTS_str.split(',') if ALLOWED_HOSTS_str else []

# Carregue as origens confiáveis para CSRF (essencial para proxy reverso com Nginx)
CSRF_TRUSTED_ORIGINS_str = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS: list[str] = CSRF_TRUSTED_ORIGINS_str.split(',') if CSRF_TRUSTED_ORIGINS_str else []


LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "home"

# Application definition

INSTALLED_APPS: list[str] = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'trades',
    'scanner',
    'subscriptions'
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
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    # {
    #     'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    # },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    # },
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
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# O Nginx servirá os arquivos estáticos, mas o WhiteNoise ainda é útil para compressão
# e pode servir como fallback.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD: str = 'django.db.models.BigAutoField'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'cache-location',
        'TIMEOUT': 60 * 60 * 2,
    }
}

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)

EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')