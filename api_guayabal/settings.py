from datetime import timedelta
import os
import sys

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-+^r^8axypcaff45vn7y9v#i=#oab1#18tn0%n(%nika5knpbqv'


DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "192.168.1.3",
    "127.0.0.1",
    "10.0.2.2",
    "0.0.0.0",
]



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'corsheaders',
    'app',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'api_guayabal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}





WSGI_APPLICATION = 'api_guayabal.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'app_TechNova',
        'USER': 'guayabal_user',
        'PASSWORD': 'admin1234',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Evita requerir CREATEDB en PostgreSQL al correr tests locales.
IS_TESTING = any(arg.startswith('test') for arg in sys.argv)
USE_SQLITE_FOR_TESTS = os.getenv('USE_SQLITE_FOR_TESTS', '1').strip().lower() in {'1', 'true', 'yes'}
if IS_TESTING and USE_SQLITE_FOR_TESTS:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
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


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

#LANGUAGE_CODE = 'en-us'
LANGUAGE_CODE = 'es-mx'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Google Maps/Places server key (use backend-only key restricted by IP).
GOOGLE_MAPS_SERVER_API_KEY = os.getenv('GOOGLE_MAPS_SERVER_API_KEY', '')
GOOGLE_MAPS_LANGUAGE = os.getenv('GOOGLE_MAPS_LANGUAGE', 'es')
GOOGLE_MAPS_REGION = os.getenv('GOOGLE_MAPS_REGION', 'ec')

# Geo provider:
# - "osm": OpenStreetMap stack (Nominatim + OSRM) [default]
# - "google": Google stack (Places/Geocoding/Routes/Address Validation)
GEO_PROVIDER = os.getenv('GEO_PROVIDER', 'osm').strip().lower()

# OpenStreetMap / OSRM settings
GEOCODER_USER_AGENT = os.getenv('GEOCODER_USER_AGENT', 'api-guayabal/1.0 (mobile-app)')
OSM_NOMINATIM_BASE_URL = os.getenv('OSM_NOMINATIM_BASE_URL', 'https://nominatim.openstreetmap.org')
OSM_ROUTER_BASE_URL = os.getenv('OSM_ROUTER_BASE_URL', 'https://router.project-osrm.org')
