from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta
from corsheaders.defaults import default_headers

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ==================================================
# CORE SETTINGS
# ==================================================

SECRET_KEY = "django-insecure-*4#@bd@imsilz&=y(u5i5%-ylraqaj@3cktb7=ccsggzr0^n#6"

DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "arigotechnolabs.com",
    "www.arigotechnolabs.com",
    "api.arigotechnolabs.com",
]

# ==================================================
# APPLICATIONS
# ==================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "corsheaders",
    "phonenumber_field",
    # Local apps
    "apps.common",
    "apps.accounts",
    "apps.category",
    "contact",
]

# ==================================================
# MIDDLEWARE
# ==================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # MUST be first
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==================================================
# TEMPLATES
# ==================================================

ROOT_URLCONF = "expensepro.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "expensepro.wsgi.application"

# ==================================================
# DATABASE
# ==================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "charset": "utf8mb4",
        },
    }
}

# ==================================================
# AUTH / JWT
# ==================================================

AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ==================================================
# CORS & CSRF (FIXED)
# ==================================================

CORS_URLS_REGEX = r"^/api/.*$"
CORS_ALLOW_HEADERS = list(default_headers) + ["authorization"]
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = [
    "https://arigotechnolabs.com",
    "https://www.arigotechnolabs.com",
]

# 🔥 IMPORTANT: Local vs Prod cookie settings
if DEBUG:
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
else:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SAMESITE = "None"

# ==================================================
# EMAIL (GMAIL SMTP)
# ==================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ==================================================
# STATIC FILES
# ==================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==================================================
# DRF SPECTACULAR (Swagger)
# ==================================================

if DEBUG:
    SPECTACULAR_SETTINGS = {
        "TITLE": "Accounts API",
        "DESCRIPTION": "Local Development API",
        "VERSION": "1.0.0",
        "SCHEMA_PATH_PREFIX": "/api",
        "SERVE_INCLUDE_SCHEMA": False,
        "SERVERS": [
            {
                "url": "http://127.0.0.1:8000/",
                "description": "Local server",
            }
        ],
        "SECURITY": [{"bearerAuth": []}],
        "COMPONENTS": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        },
    }
else:
    SPECTACULAR_SETTINGS = {
        "TITLE": "Accounts API",
        "DESCRIPTION": "Production API",
        "VERSION": "1.0.0",
        "SCHEMA_PATH_PREFIX": "/api",
        "SERVE_INCLUDE_SCHEMA": False,
        "SERVERS": [
            {
                "url": "https://arigotechnolabs.com/api",
                "description": "Production server",
            }
        ],
        "SECURITY": [{"bearerAuth": []}],
    }

# ==================================================
# INTERNATIONALIZATION
# ==================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
