from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-ly6551f6_ak0rbs3@c+e^g(sda-b*^44mpldpjosh01qb*o%3^'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'store.apps.StoreConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'tailwind',
    'theme',
    'fontawesomefree',
    'django_filters',
    'django_fastdev',
    'import_export',
    'redisboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # "django.middleware.cache.UpdateCacheMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    "django.middleware.common.CommonMiddleware",
    "django.middleware.cache.FetchFromCacheMiddleware",
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.redis.RedisCache",
#         "LOCATION": "redis://127.0.0.1:6379",
#     }
# }


# # # Cache settings
# CACHE_MIDDLEWARE_SECONDS = 60 * 15  # 15 minutes default cache
# CACHE_MIDDLEWARE_KEY_PREFIX = "pharm"
# CACHE_MIDDLEWARE_ALIAS = "default"

ROOT_URLCONF = 'pharm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'pharm.wsgi.application'

TAILWIND_APP_NAME='theme'
INTERNAL_IPS=['127.0.0.1']
NPM_BIN_PATH = "/usr/bin/npm"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': 'pharmdb',
#         #'NAME': 'pharm_db',
#         'USER': 'padmin',
#         'PASSWORD': 'pharm2024',
#         'HOST': 'localhost',
#         'PORT': '',
#     }
# }


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


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Lagos'

USE_I18N = False

USE_L10N=True

USE_THOUSAND_SEPARATOR=True

USE_TZ = True

DATE_INPUT_FORMATS = ['%d-%m-%Y'] 
DATETIME_INPUT_FORMAT=['%d-%m-%Y']

LOGIN_REDIRECT_URL = '/'
LOGIN_URL="/login/"


STATIC_URL = 'static/'
STATIC_ROOT=os.path.join(BASE_DIR,'static/')

# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = "default"

SESSION_COOKIE_AGE = 3600  
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Log out when browser closes
SESSION_SAVE_EVERY_REQUEST = True  # Reset session timeout on activity
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS



# # Redis cache configuration

# # views.py
# @method_decorator(never_cache, name='dispatch')
# class StoreWorthView(LoginRequiredMixin, StoreGroupRequiredMixin, TemplateView):
#     # ... rest of your view stays the same

# # Function-based views
# @never_cache
# def current_stock_level(request, drug_id):
#     # Real-time stock check