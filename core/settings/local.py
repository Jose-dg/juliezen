"""Local development settings."""
from .base import *  # noqa

DEBUG = True

INSTALLED_APPS += ["debug_toolbar", "silk"]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
] + MIDDLEWARE

INTERNAL_IPS = ["127.0.0.1", "0.0.0.0", "localhost"]

CORS_ALLOW_ALL_ORIGINS = True

# Database - Configuración para desarrollo local
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql', 
        'NAME': env('DB_NAME', default='daydreamshop'),
        'USER': env('DB_USER', default='daydreamshop'),
        'PASSWORD': env('DB_PASSWORD', default='daydreamshop123'),
        'HOST': env('DB_HOST', default='localhost'), 
        'PORT': env('DB_PORT', default='5433')
    }
}
