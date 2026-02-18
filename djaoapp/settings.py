# Copyright (c) 2026, DjaoDjin inc.
# see LICENSE

# Django settings for Djaoapp project.
import datetime, os.path, sys

from django import VERSION as DJANGO_VERSION
from django.contrib.messages import constants as messages

from deployutils.configs import load_config, update_settings

from .compat import reverse_lazy, settings_lazy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default values that can be overriden by `update_settings` later on.
APP_NAME = os.path.basename(BASE_DIR)
APP_VERSION = "2026-02-23-dev"

# Feature flags
# -------------
DEBUG = True
USE_FIXTURES = True

ENABLE_DEBUG_TOOLBAR = True         # 2026-02-17 layout issue
FEATURES_REVERT_ASSETS_CDN = False  # 2025-09-19 temporary reverts cached js/css
FEATURES_REVERT_STRIPE_V2 = False   # 2021-03-03 temporary reverts SCA
FEATURES_REVERT_TO_DJANGO = False   # 2016-03-31 temporary product switch
FEATURES_REVERT_TO_VUE2 = True      # 2023-03-25 testing support for Vue3
OPENAPI_SPEC_COMPLIANT = False

# Defaults for database settings
# ------------------------------
DB_ENGINE = 'sqlite3'
DB_NAME = os.path.join(BASE_DIR, 'db.sqlite')
DB_HOST = ''
DB_PORT = 5432
DB_USER = None
DB_PASSWORD = None

# XXX djaodjin-saas==0.12.0 requires this
SAAS_ORGANIZATION_MODEL = 'saas.Organization'
MULTITIER_SITE_MODEL = None


# Defaults for responding to HTTP requests
# ----------------------------------------
ALLOWED_HOSTS = ('*',)

RULES_ENC_KEY_OVERRIDE = None
RULES_ENTRY_POINT_OVERRIDE = None
REQUESTS_TIMEOUT = 120

#: Root URL root when it cannot be infered from the HTTP request,
#: or there is no HTTP request in the context of `build_absolute_uri`.
BASE_URL = ""

#: Email address to use for various automated correspondence from
#: the site managers (also django-registration settings)
DEFAULT_FROM_EMAIL = settings_lazy(
    'multitier.thread_locals.get_default_from_email')


# Defaults for user and profile accounts settings
# -----------------------------------------------
DISABLED_USER_UPDATE = False

AUTHENTICATION_OVERRIDE = settings_lazy(
    'multitier.thread_locals.get_authentication_override', int)

REGISTRATION_STYLE = settings_lazy(
    'multitier.thread_locals.get_registration_type', int)

SKIP_VERIFICATION_CHECK = False
VERIFICATION_LIFETIME = datetime.timedelta(hours=1)

# Bots prevention
CONTACT_DYNAMIC_VALIDATOR = None
SIGNUP_EMAIL_DYNAMIC_VALIDATOR = None

DYNAMIC_MENUBAR_ITEM_CUT_OFF = 3

# Defaults for captcha workflows
REGISTRATION_REQUIRES_RECAPTCHA = settings_lazy(
    'multitier.thread_locals.get_registration_requires_recaptcha', bool)
CONTACT_REQUIRES_RECAPTCHA = settings_lazy(
    'multitier.thread_locals.get_contact_requires_recaptcha', bool)
# django-recaptcha will raise a `ImproperlyConfigured` exception
# if those two settings are not of type `str`.
RECAPTCHA_PUBLIC_KEY = 'multitier.thread_locals.get_recaptcha_pub_key'
RECAPTCHA_PRIVATE_KEY = 'multitier.thread_locals.get_recaptcha_priv_key'

# Defaults for social auth configuration
USE_X_FORWARDED_PORT = True
SOCIAL_AUTH_SAML_ENABLED_IDPS = {}

SOCIAL_AUTH_AZUREAD_OAUTH2_KEY = settings_lazy(
    'multitier.thread_locals.get_social_auth_azuread_oauth2_key')
SOCIAL_AUTH_AZUREAD_OAUTH2_SECRET = settings_lazy(
    'multitier.thread_locals.get_social_auth_azuread_oauth2_secret')

SOCIAL_AUTH_GITHUB_KEY = settings_lazy(
    'multitier.thread_locals.get_social_auth_github_key')
SOCIAL_AUTH_GITHUB_SECRET = settings_lazy(
    'multitier.thread_locals.get_social_auth_github_secret')

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = settings_lazy(
    'multitier.thread_locals.get_social_auth_google_oauth2_key')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = settings_lazy(
    'multitier.thread_locals.social_auth_google_priv_key')

# Defaults for street address auto-complete (Google Places)
GOOGLE_API_KEY = settings_lazy(
    'multitier.thread_locals.get_google_api_key')

# Defaults for payment processor settings
# ---------------------------------------

STRIPE_MODE = 1     # ``FORWARD``, i.e. defaults to storing customers and charges

STRIPE_USE_PLATFORM_KEYS = settings_lazy(
    'multitier.thread_locals.get_processor_use_platform_keys', bool)

#: Stripe public production key for the broker
STRIPE_PUB_KEY = settings_lazy(
    'multitier.thread_locals.get_processor_pub_key')
#: Stripe private production key for the broker
STRIPE_PRIV_KEY = settings_lazy(
    'multitier.thread_locals.get_processor_priv_key')
#: The StripeConnect platform/broker production key
STRIPE_CLIENT_ID = settings_lazy(
    'multitier.thread_locals.get_processor_client_id')
#: The StripeConnect redirect endpoint
STRIPE_CONNECT_CALLBACK_URL = settings_lazy(
    'multitier.thread_locals.get_processor_connect_callback_url')

ENABLES_PROCESSOR_TEST_KEYS = settings_lazy(
    'multitier.thread_locals.get_enables_processor_test_keys', bool)

#: The StripeConnect platform/broker test key
#: Stripe public test key for the broker
STRIPE_TEST_PUB_KEY = settings_lazy(
    'multitier.thread_locals.get_processor_test_pub_key')

#: Stripe private test key for the broker
STRIPE_TEST_PRIV_KEY = settings_lazy(
    'multitier.thread_locals.get_processor_test_priv_key')

STRIPE_TEST_CLIENT_ID = settings_lazy(
    'multitier.thread_locals.get_processor_test_client_id')

#: The StripeConnect test redirect endpoint
STRIPE_TEST_CONNECT_CALLBACK_URL = settings_lazy(
    'multitier.thread_locals.get_processor_test_connect_callback_url')

# Defaults for notification settings
# ----------------------------------

#: A URL, or callable function returning an URL, to which a notification event
#: will be posted.
NOTIFICATION_WEBHOOK_URL = settings_lazy(
    'multitier.thread_locals.get_notification_webhook_url')

#: Sometimes it is simpler to disable e-mail notifications through a settings
#: boolean, than removing the `NotificationEmailBackend`
#: from settings.NOTIFICATION_BACKENDS`.
NOTIFICATION_EMAIL_DISABLED = settings_lazy(
    'multitier.thread_locals.get_notification_email_disabled', bool)

LOG_FILE = None

# Overrides from config files
# ---------------------------
update_settings(sys.modules[__name__],
    load_config(APP_NAME, 'credentials', 'site.conf',
        verbose=True, debug=DEBUG))

if os.getenv('APP_NAME'):
    setattr(sys.modules[__name__], 'APP_NAME', os.getenv('APP_NAME'))

# Enable override on command line even when it is not defined in site.conf
for env_var in ['DEBUG', 'API_DEBUG', 'ASSETS_DEBUG', 'FEATURES_DEBUG']:
    if os.getenv(env_var):
        setattr(sys.modules[__name__], env_var, (int(os.getenv(env_var)) > 0))
    if not hasattr(sys.modules[__name__], env_var):
        setattr(sys.modules[__name__], env_var, DEBUG)
if sys.version_info[0] < 3:
    # Requires Python3+ to create API docs
    API_DEBUG = False

# OPENAPI_SPEC_COMPLIANT
# Remove extra information used for documentation like examples, etc.
for env_var in ['OPENAPI_SPEC_COMPLIANT']:
    if os.getenv(env_var):
        setattr(sys.modules[__name__], env_var, (int(os.getenv(env_var)) > 0))

for env_var in ['SKIP_VERIFICATION_CHECK']:
    if os.getenv(env_var):
        setattr(sys.modules[__name__], env_var, int(os.getenv(env_var)))


# Implementation Note: To simplify quick tests. The `SECRET_KEY` should
# be defined in the `credentials` otherwise all HTTP session will become
# invalid as the process is restarted.
if not hasattr(sys.modules[__name__], "SECRET_KEY"):
    from random import choice
    SECRET_KEY = "".join([choice(
        "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)])


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

BUILD_ABSOLUTE_URI_CALLABLE = 'multitier.mixins.build_absolute_uri'
EMAIL_CONNECTION_CALLABLE = 'multitier.thread_locals.get_email_connection'
NOTIFIED_ON_ERRORS_CALLABLE = 'multitier.thread_locals.get_notified_on_errors'

SILENCED_SYSTEM_CHECKS = ['django_recaptcha.recaptcha_test_key_error']

if getattr(sys.modules[__name__], 'MULTITIER_SITE_MODEL', None):
    MULTITIER_APPS = (MULTITIER_SITE_MODEL.split('.', maxsplit=1)[0],)
else:
    MULTITIER_APPS = tuple([])

if DEBUG:
    if not FEATURES_REVERT_TO_DJANGO:
        # (Django2.2) We cannot include admin panels because a `check`
        # for DjangoTemplates will fail when we are using Jinja2 templates
        if DJANGO_VERSION[0] >= 2:
            # django-debug-toolbar==1.11 does not support Django2.2
            DEBUG_APPS = MULTITIER_APPS + (
                'debug_toolbar',
                'django_extensions',
            )
        else:
            DEBUG_APPS = MULTITIER_APPS + (
                'debug_toolbar',
                'django_extensions',
            )
    else:
        DEBUG_APPS = MULTITIER_APPS + (
            'django.contrib.admin',
            'django.contrib.admindocs',
            'debug_toolbar',
            'django_extensions',
        )
else:
    DEBUG_APPS = MULTITIER_APPS

if API_DEBUG:
    ENV_INSTALLED_APPS = DEBUG_APPS + (
        'drf_spectacular',
    )
else:
    ENV_INSTALLED_APPS = DEBUG_APPS

INSTALLED_APPS = ENV_INSTALLED_APPS + (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_recaptcha',
    'deployutils.apps.django_deployutils',
    'signup',  # Because we want `djaodjin-resources.js` picked up from here.
    'saas',
    'social_django',
    'multitier',            # need to be included if we don't change fixtures
    'extended_templates',
    'rules',
    'djaoapp'
)

MIDDLEWARE = tuple([])
if DEBUG:
    if ENABLE_DEBUG_TOOLBAR and 'debug_toolbar' in INSTALLED_APPS:
        MIDDLEWARE += (
            'debug_toolbar.middleware.DebugToolbarMiddleware',
        )
elif not DEBUG:
    MIDDLEWARE += (
        'whitenoise.middleware.WhiteNoiseMiddleware',
    )

MIDDLEWARE += (
    'django.middleware.common.CommonMiddleware',
    'multitier.middleware.SiteMiddleware',
    'multitier.middleware.SetRemoteAddrFromForwardedFor',
    'rules.middleware.RulesMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    # The locale middleware seems to use `request.session` but not
    # `request.user` so it is strategically placed in-between here.
    'signup.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'deployutils.apps.django_deployutils.middleware.RequestLoggingMiddleware',
)

ROOT_URLCONF = 'djaoapp.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'djaoapp.wsgi.application'

EMAIL_SUBJECT_PREFIX = '[%s] ' % APP_NAME
EMAILER_BACKEND = 'extended_templates.backends.TemplateEmailBackend'

if not hasattr(sys.modules[__name__], 'DB_BACKEND'):
    DB_BACKEND = (DB_ENGINE if DB_ENGINE.startswith('django.db.backends.') else
        'django.db.backends.%s' % DB_ENGINE)
DATABASES = {
    'default': {
        'ENGINE':DB_BACKEND,
        'NAME': DB_NAME,
        'USER': DB_USER,                 # Not used with sqlite3.
        'PASSWORD': DB_PASSWORD,         # Not used with sqlite3.
        'HOST': DB_HOST,                 # Not used with sqlite3.
        'PORT': DB_PORT,                 # Not used with sqlite3.
        'TEST': {
            'NAME': None,
        }
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

DATABASE_ROUTERS = ('multitier.routers.SiteRouter',)

if os.getenv('MULTITIER_DB_NAME'):
    MULTITIER_DB_NAME = os.getenv('MULTITIER_DB_NAME')
    MULTITIER_NAME = os.path.splitext(os.path.basename(MULTITIER_DB_NAME))[0]
    if not MULTITIER_NAME in DATABASES:
        DATABASES.update({MULTITIER_NAME: {
                'ENGINE':DB_BACKEND,
                'NAME': MULTITIER_DB_NAME,
                'USER': DB_USER,                 # Not used with sqlite3.
                'PASSWORD': DB_PASSWORD,         # Not used with sqlite3.
                'HOST': DB_HOST,                 # Not used with sqlite3.
                'PORT': DB_PORT,                 # Not used with sqlite3.
                }})

MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

# Language settings
# -----------------
# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

LOCALE_PATHS = (os.path.join(BASE_DIR, APP_NAME, 'locale'),)

# Date/time settings
# ------------------
# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Local time zone for this installation. Choices can be found here:
#   http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
#
# We must use UTC here otherwise the date of request in gunicorn access
# and error logs will be off compared to the dates shown in nginx logs.
# (see https://github.com/benoitc/gunicorn/issues/963)
TIME_ZONE = 'UTC'

# static assets
# -------------
HTDOCS = os.path.join(BASE_DIR, 'htdocs')
PUBLIC_ROOT = os.path.join(HTDOCS, 'themes')

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
if not hasattr(sys.modules[__name__], 'MEDIA_ROOT'):
    MEDIA_ROOT = os.path.join(HTDOCS, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
APP_STATIC_ROOT = HTDOCS + '/assets'
STATIC_URL = '/assets/'
STATIC_ROOT = APP_STATIC_ROOT
if DEBUG:
    STATIC_ROOT = ''
    # Additional locations of static files
    STATICFILES_DIRS = (PUBLIC_ROOT, APP_STATIC_ROOT, HTDOCS,)

ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'multitier.finders.MultitierFileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder'
)

if FEATURES_REVERT_ASSETS_CDN:
    ASSETS_CDN = {}
else:
    ASSETS_CDN = {
        '/assets/cache/auth.js': '/assets/cache/auth-%s.js' % APP_VERSION,
        '/assets/cache/base.js': '/assets/cache/base-%s.js' % APP_VERSION,
        '/assets/cache/pages.js': '/assets/cache/pages-%s.js' % APP_VERSION,
        '/assets/cache/saas.js': '/assets/cache/saas-%s.js' % APP_VERSION,
        '/assets/cache/djaodjin-vue.js':
            '/assets/cache/djaodjin-vue-%s.js' % APP_VERSION,
        '/assets/cache/theme-editors.js':
            '/assets/cache/theme-editors-%s.js' % APP_VERSION,
        '/assets/cache/base.css': '/assets/cache/base-%s.css' % APP_VERSION,
        '/assets/cache/email.css': '/assets/cache/email-%s.css' % APP_VERSION,
        '/assets/cache/pages.css': '/assets/cache/pages-%s.css' % APP_VERSION,
        '/assets/cache/dashboard.css':
            '/assets/cache/dashboard-%s.css' % APP_VERSION,
        '/assets/cache/djaodjin-menubar.css':
            '/assets/cache/djaodjin-menubar-%s.css' % APP_VERSION,
    }

ASSETS_MAP = {
    'cache/base.css': (
        'base/base.scss', (
            'base/*.scss',
            'vendor/bootstrap/*.scss',
            'vendor/bootstrap/mixins/*.scss',
            'vendor/bootstrap/utilities/*.scss',
            'vendor/djaodjin/*.scss',
            'vendor/toastr/*.scss'
        )
    ),
    'cache/pages.css': (
        'pages/pages.scss', (
            'pages/*.scss',
            'vendor/jquery-ui.scss',
            'vendor/bootstrap-colorpicker.scss',
            'vendor/djaodjin-extended-templates/*.scss',
        )
    ),
    'cache/dashboard.css': (
        'dashboard/dashboard.scss', (
            'dashboard/*.scss',
            'vendor/nv.d3.scss',
            'vendor/trip.scss',
        )
    ),
    'cache/email.css': (
        'email/email.scss', (
            'email/*.scss',
        )
    ),
}

#XXX ASSETS_ROOT = os.path.join(BASE_DIR, 'assets')
ASSETS_ROOT = HTDOCS

# Templates
# ---------
# Django 1.8+
FILE_CHARSET = 'utf-8'

if FEATURES_REVERT_TO_DJANGO:
    TEMPLATES_DIRS = (
        os.path.join(BASE_DIR, 'themes', 'djaoapp', 'templates'),
        os.path.join(BASE_DIR, 'djaoapp', 'templates', 'django'),
        os.path.join(BASE_DIR, 'djaoapp', 'templates'),)
else:
    TEMPLATES_DIRS = (
        os.path.join(BASE_DIR, 'themes', 'djaoapp', 'templates'),
        os.path.join(BASE_DIR, 'djaoapp', 'templates', 'jinja2'),
        os.path.join(BASE_DIR, 'djaoapp', 'templates'),)

TEMPLATES_LOADERS = (
    'multitier.loaders.django.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATES = [
    {
        'NAME': 'eml',
        'BACKEND': 'extended_templates.backends.eml.EmlEngine',
        'DIRS': TEMPLATES_DIRS,
        'OPTIONS': {
            'engine': 'html',
        }
    },
    {
        'NAME': 'pdf',
        'BACKEND': 'extended_templates.backends.pdf.PdfEngine',
        'DIRS': TEMPLATES_DIRS,
        'OPTIONS': {
            'loaders': TEMPLATES_LOADERS,
        }
    }]

if FEATURES_REVERT_TO_DJANGO:
    sys.stderr.write("Use Django templates engine.\n")
    TEMPLATES += [
    {
        'NAME': 'html',
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATES_DIRS,
        'OPTIONS': {
            'context_processors': [
    'django.contrib.auth.context_processors.auth',         # because of admin/
    'django.contrib.messages.context_processors.messages', # because of admin/
    'django.template.context_processors.request',
    'django.template.context_processors.media',
    'multitier.context_processors.features_debug',
    'djaoapp.context_processors.features_flags',
            ],
            'loaders': TEMPLATES_LOADERS,
            'libraries': {},
            'builtins': [
                'django.templatetags.i18n',# XXX Format incompatible with Jinja2
    'deployutils.apps.django_deployutils.templatetags.deployutils_extratags',
                    # for |host
                'saas.templatetags.saas_tags',
                'djaoapp.templatetags.djaoapp_tags']
        }
    }
    ]
else:
    sys.stderr.write("Use Jinja2 templates engine.\n")
    TEMPLATES += [
    {
        'NAME': 'html',
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': TEMPLATES_DIRS,
        'OPTIONS': {
            'loader': 'multitier.loaders.jinja2.Loader',
            'environment': 'djaoapp.jinja2.environment'
        }
    }]


MAX_UPLOAD_SIZE = 10240


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOG_HANDLER = {
    'level': 'DEBUG',
    'formatter': 'request_format',
    'filters': ['request'],
    'class':'logging.StreamHandler',
}
if not DEBUG and hasattr(sys.modules[__name__], 'LOG_FILE') and LOG_FILE:
    LOG_HANDLER.update({
        'class':'logging.handlers.WatchedFileHandler',
        'filename': LOG_FILE
    })

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        # Add an unbound RequestFilter.
        'request': {
            '()': 'deployutils.apps.django_deployutils.logging.RequestFilter',
        },
    },
    'formatters': {
        'simple': {
            'format': '- - - [%(asctime)s] %(levelname)s %(message)s',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z'
        },
        'json': {
            '()': 'deployutils.apps.django_deployutils.logging.JSONFormatter',
            'format':
                '%(remote_addr)s %(http_host)s %(username)s [%(asctime)s]'\
                ' %(levelname)s %(message)s',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z',
            'replace': False,
            'whitelists': {
                'record': [
                    'nb_queries', 'queries_duration',
                    'charge', 'amount', 'unit', 'modified',
                    'customer', 'organization', 'provider'],
            }
        },
        'request_format': {
            'format':
                '%(remote_addr)s %(http_host)s %(username)s [%(asctime)s]'\
                ' %(levelname)s %(message)s',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z'
        }
    },
    'handlers': {
        'db_log': {
            'level': 'DEBUG',
            'formatter': 'request_format',
            'filters': ['require_debug_true', 'request'],
            'class':'logging.StreamHandler',
        },
        'log': LOG_HANDLER,
        # Add `mail_admins` in top-level handler when there are no other
        # mechanism to be notified of server errors.
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
    },
    'loggers': {
        'boto': {
            # AWSAuthConnection.get_object() will log 2 errors and raise
            # an exception. That's a little too much.
            'handlers': ['log'],
            'level': 'ERROR',
            'propagate': False
        },
        'deployutils': {
            'handlers': ['db_log'],
            'level': 'INFO',
            'propagate': False
        },
        'djaoapp': {
            'handlers': [],
            'level': 'INFO',
        },
        'extended_templates': {
            'handlers': [],
            'level': 'INFO',
        },
        'multitier': {
            'handlers': [],
            'level': 'INFO',
        },
        'requests': {
            'handlers': [],
            'level': 'WARNING',
        },
        'rules': {
            'handlers': [],
            'level': 'INFO',
        },
        'saas': {
            'handlers': [],
            'level': 'INFO',
        },
        'signup': {
            'handlers': [],
            'level': 'INFO',
        },
        'weasyprint': {
            'handlers': [],
            'level': 'INFO',
        },
#        'django.db.backends': {
#           'handlers': ['db_log'],
#           'level': 'DEBUG',
#           'propagate': False
#        },
        'django.request': {
            'handlers': [],
            'level': 'ERROR',
        },
        # If we don't disable 'django' handlers here, we will get an extra
        # copy on stderr.
        'django': {
            'handlers': [],
        },
        # This is the root logger.
        # The level will only be taken into account if the record is not
        # propagated from a child logger.
        #https://docs.python.org/2/library/logging.html#logging.Logger.propagate
        '': {
            'handlers': ['log'],
            'level': 'INFO'
        },
    },
}


# API settings
# ------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'signup.authentication.JWTAuthentication',
        'signup.authentication.APIKeyAuthentication',
        # `rest_framework.authentication.SessionAuthentication` is the last
        # one in the list because it will raise a PermissionDenied if the CSRF
        # is absent.
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS':
        'djaoapp.pagination.PageNumberPagination',
    'DEFAULT_SCHEMA_CLASS': 'djaoapp.api_docs.schemas.AutoSchema',
    'EXCEPTION_HANDLER': 'djaoapp.views.errors.drf_exception_handler',
    'NON_FIELD_ERRORS_KEY': 'detail',
    'ORDERING_PARAM': 'o',
    'PAGE_SIZE': 25,
    'SEARCH_PARAM': 'q',
}

SPECTACULAR_SETTINGS = {
    'ENUM_GENERATE_CHOICE_DESCRIPTION': False,
    'AUTHENTICATION_WHITELIST': []
}

if not DEBUG:
    # We are using Jinja2 templates so there are no templates
    # for `rest_framework.renderers.BrowsableAPIRenderer`.
    REST_FRAMEWORK.update({
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        )
    })

# Session settings
# ----------------
# The default session serializer switched to JSONSerializer in Django 1.6
# but just to be sure:
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

DEBUG_TOOLBAR_PATCH_SETTINGS = False
DEBUG_TOOLBAR_CONFIG = {
    'JQUERY_URL': '',
    'SHOW_COLLAPSED': True,
    'SHOW_TEMPLATE_CONTEXT': True,
}

INTERNAL_IPS = ('127.0.0.1', '::1')

# Software-as-a-Service  (multi-tenant)
# We add all the rules_* tables because we don't want to add the App
# and end up with multitier in the tenant db.
MULTITIER = {
    'ACCOUNT_MODEL': 'saas.Organization',
    'ACCOUNT_URL_KWARG': 'organization',
#    'DEFAULT_URLS': ['login'], # XXX can't do reverse in multitier middleware.
    'ROUTER_APPS': (
        'social_django', 'signup', 'saas', 'extended_templates', 'rules'),
    'ROUTER_TABLES': ('rules_app', 'rules_rules', 'rules_engagement',
        'django_admin_log', 'django_session', 'auth_user'),
    'THEMES_DIRS': [
        os.path.join(BASE_DIR, 'themes'),
    ],
}
for config_param in ['DEFAULT_DOMAIN', 'DEFAULT_SITE']:
    # This parameters are optional in site.conf.
    multitier_config_param = 'MULTITIER_%s' % config_param
    if hasattr(sys.modules[__name__], multitier_config_param):
        MULTITIER.update({config_param:
            getattr(sys.modules[__name__], multitier_config_param)})


# Software-as-a-Service (pages editor)
def theme_dir(account):
    return os.path.join(MULTITIER['THEMES_DIRS'][0], str(account))

import djaoapp.extras.extended_templates

EXTENDED_TEMPLATES = {
    'ACCOUNT_MODEL': 'saas.Organization',
    'ACCOUNT_URL_KWARG' : 'app',
    'ACTIVE_THEME_CALLABLE': 'djaoapp.thread_locals.get_current_theme',
    'ASSETS_MAP': ASSETS_MAP,
    'ASSETS_DIRS_CALLABLE': 'djaoapp.thread_locals.get_current_assets_dirs',
    'BUILD_ABSOLUTE_URI_CALLABLE': 'djaoapp.thread_locals.build_absolute_uri',
    'DEFAULT_ACCOUNT_CALLABLE': 'saas.models.get_broker',
    'DEFAULT_STORAGE_CALLABLE': 'djaoapp.thread_locals.get_default_storage',
    'EXTRA_MIXIN': djaoapp.extras.extended_templates.ExtraMixin,
    'PUBLIC_ROOT': PUBLIC_ROOT,
    'TEMPLATES_BLACKLIST': [
        r'django/.*',
        r'jinja2/debug_toolbar/.*\.html',
        'api_docs/index.html',
        'api_docs/notifications.html',
        'extended_templates/_body_bottom.html',
        'extended_templates/_body_bottom_edit_tools.html',
        'extended_templates/_body_top_template.html',
        'extended_templates/_edit_tools.html',
        'static/directory_index.html'
    ],
    'THEME_DIR_CALLABLE': theme_dir
}


# imports made here so SECRET_KEY is defined when loading AUTH_USER.
import djaoapp.extras.saas, djaoapp.extras.rules

# Software-as-a-Service (provider)
SAAS = {
    'BROKER': {
        'GET_INSTANCE': 'djaoapp.thread_locals.get_current_broker',
        'BUILD_ABSOLUTE_URI_CALLABLE':
            'djaoapp.thread_locals.build_absolute_uri',
    },
    'BYPASS_IMPLICIT_GRANT': getattr(
        sys.modules[__name__], 'BYPASS_IMPLICIT_GRANT', {}),
    'BYPASS_PROCESSOR_AUTH': getattr(
        sys.modules[__name__], 'USE_FIXTURES', False),
    'EXTRA_MIXIN': djaoapp.extras.saas.ExtraMixin,
    'FORCE_PERSONAL_PROFILE': 'djaoapp.utils.get_force_personal_profile',
    'MAX_TYPEAHEAD_CANDIDATES': 5,
    'PHONE_VERIFICATION_BACKEND': getattr(
        sys.modules[__name__], 'SIGNUP_PHONE_VERIFICATION_BACKEND', None),
    'PICTURE_STORAGE_CALLABLE': 'djaoapp.thread_locals.get_picture_storage',
    'PRODUCT_URL_CALLABLE': 'djaoapp.utils.product_url',
    'PROCESSOR_BACKEND_CALLABLE':
        'djaoapp.thread_locals.dynamic_processor_keys',
    'PROCESSOR': {
        'BACKEND': 'saas.backends.stripe_processor.StripeBackend',
        'PUB_KEY': STRIPE_PUB_KEY,
        'PRIV_KEY': STRIPE_PRIV_KEY,
        'MODE': STRIPE_MODE,
        'CLIENT_ID': STRIPE_CLIENT_ID,
        'CONNECT_CALLBACK_URL': STRIPE_CONNECT_CALLBACK_URL,
        'CONNECT_STATE_CALLABLE':
            'djaoapp.thread_locals.get_authorize_processor_state',
        'REDIRECT_CALLABLE': 'djaoapp.thread_locals.processor_redirect',
        'FALLBACK':  getattr(sys.modules[__name__], 'PROCESSOR_FALLBACK', []),
        'USE_PLATFORM_KEYS': STRIPE_USE_PLATFORM_KEYS,
        'USE_STRIPE_V2': FEATURES_REVERT_STRIPE_V2,
    },
    'USER_SERIALIZER': 'signup.serializers_overrides.UserSerializer',
    'USER_DETAIL_SERIALIZER':
        'signup.serializers_overrides.UserDetailSerializer',
}

# Software-as-a-Service (forward requests with session data)
RULES = {
    'ACCOUNT_MODEL': 'saas.Organization',
    'AUTHENTICATION_OVERRIDE': AUTHENTICATION_OVERRIDE,
    'DEFAULT_APP_CALLABLE': 'djaoapp.thread_locals.djaoapp_get_current_app',
    'DEFAULT_PREFIXES': [
        '/api/accounts', '/api/activities', '/api/agreements', '/api/billing',
        # '/api/contacts', '/api/legal',
        '/api/metrics', # '/api/notifications',
        '/api/profile', # '/api/proxy',
        '/api/themes', '/api/users',
        '/activities/', '/billing/', # '/legal',
        '/metrics/', '/profile/', # '/proxy/', '/themes/',
        '/users/'],
    'DEFAULT_RULES': [('/app/', 1, False), ('/', 0, False)],
    'ENC_KEY_OVERRIDE': RULES_ENC_KEY_OVERRIDE,
    'ENTRY_POINT_OVERRIDE': RULES_ENTRY_POINT_OVERRIDE,
    'EXTRA_MIXIN': djaoapp.extras.rules.ExtraMixin,
    'RULE_OPERATORS': (
        '',                                            # 0
        'saas.decorators.fail_authenticated',          # 1
        'saas.decorators.fail_agreement',              # 2
        'saas.decorators.fail_direct',                 # 3
        'saas.decorators.fail_direct_weak',            # 4
        'saas.decorators.fail_direct_strong',          # 5
        'saas.decorators.fail_provider',               # 6
        'saas.decorators.fail_provider_weak',          # 7
        'saas.decorators.fail_provider_strong',        # 8
        'saas.decorators.fail_provider_only',          # 9
        'saas.decorators.fail_provider_only_weak',     # 10
        'saas.decorators.fail_provider_only_strong',   # 11
        'saas.decorators.fail_self_provider',          # 12
        'saas.decorators.fail_self_provider_weak',     # 13
        'saas.decorators.fail_self_provider_strong',   # 14
        'saas.decorators.fail_paid_subscription',      # 15
        'saas.decorators.fail_subscription',           # 16
        'signup.decorators.fail_active',               # 17
        'saas.decorators.fail_provider_readable'       # 18
    ),
    'PATH_PREFIX_CALLABLE': 'multitier.thread_locals.get_path_prefix',
    'SESSION_SERIALIZER': 'djaoapp.api.serializers.SessionSerializer',
    'TIMEOUT': REQUESTS_TIMEOUT,
}

# Authentication
# --------------
PASSWORD_MIN_LENGTH = 10
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": PASSWORD_MIN_LENGTH,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    }
]

# Implementation note: this import must be after multitier and rules
# have been loaded otherwise multitier.settings.ROUTER_TABLES is [].
import djaoapp.extras.signup

SIGNUP = {
    'ACCOUNT_MODEL': 'saas.Organization',
    'ACCOUNT_SERIALIZER': 'saas.api.serializers.OrganizationSerializer',
    'SKIP_VERIFICATION_CHECK': SKIP_VERIFICATION_CHECK,
    'DISABLED_AUTHENTICATION': 'djaoapp.utils.get_disabled_authentication',
    'DISABLED_REGISTRATION': 'djaoapp.utils.get_disabled_registration',
    'DISABLED_USER_UPDATE': DISABLED_USER_UPDATE,
    'EMAIL_DYNAMIC_VALIDATOR': getattr(
        sys.modules[__name__], 'SIGNUP_EMAIL_DYNAMIC_VALIDATOR', None),
    'EMAIL_VERIFICATION_BACKEND':
        'djaoapp.notifications.backends.email.EmailVerificationBackend',
    'EXTRA_MIXIN': djaoapp.extras.signup.ExtraMixin,
    'LDAP': {
        'SERVER_URI': getattr(sys.modules[__name__], 'LDAP_SERVER_URI', ""),
        'USER_SEARCH_DN': getattr(sys.modules[__name__], 'LDAP_USER_SEARCH_DN', ""),
    },
    'LOGIN_THROTTLE': getattr(
        sys.modules[__name__], 'LOGIN_THROTTLE', None),
    'NOTIFICATION_TYPE': (
        ('card_updated', "Card updated"),
        ('charge_updated', "Charge receipt"),
        ('claim_code_generated', "Claim code"),
        ('expires_soon', "Expires soon"),
        ('order_executed', "Order confirmation"),
        ('period_sales_report_created', "Weekly sales report"),
        ('profile_updated', "Profile updated"),
        ('role_request_created', "Role requested"),
        ('user_activated', "User activated"),
        ('user_contact', "User contact"),
        ('user_registered', "User registered"),
        ('user_welcome', "User welcome"),
    ),
    'PASSWORD_MIN_LENGTH': PASSWORD_MIN_LENGTH,
    'PASSWORD_RESET_THROTTLE': getattr(
        sys.modules[__name__], 'SIGNUP_PASSWORD_RESET_THROTTLE', None),
    'PHONE_VERIFICATION_BACKEND': getattr(
        sys.modules[__name__], 'SIGNUP_PHONE_VERIFICATION_BACKEND', None),
    'PICTURE_STORAGE_CALLABLE': 'djaoapp.thread_locals.get_picture_storage',
    'RANDOM_SEQUENCE': getattr(
        sys.modules[__name__], 'SIGNUP_RANDOM_SEQUENCE', []),
    'SSO_PROVIDERS': {
        'azuread-oauth2': {'name': 'Microsoft', 'icon': 'microsoft'},
        'github': {'name': 'GitHub', 'icon': 'github'},
        'google-oauth2': {'name': 'Google', 'icon': 'google'},
    },
    'USE_VERIFICATION_LINKS': False,
    'USER_API_KEY_LIFETIME': 'djaoapp.utils.get_user_api_key_lifetime',
    'USER_OTP_REQUIRED': 'djaoapp.utils.get_user_otp_required',
    'VERIFICATION_LIFETIME': VERIFICATION_LIFETIME,
    'VERIFIED_LIFETIME': datetime.timedelta(days=365)
}
for config_param in ('AWS_REGION', 'AWS_UPLOAD_ROLE', 'AWS_ACCOUNT_ID'):
    # This parameters are optional in site.conf.
    if hasattr(sys.modules[__name__], config_param):
        SIGNUP.update({config_param:
            getattr(sys.modules[__name__], config_param)})

SOCIAL_AUTH_RAISE_EXCEPTIONS = False
SOCIAL_AUTH_LOGIN_ERROR_URL = reverse_lazy('rules_page')
SOCIAL_AUTH_GITHUB_SCOPE = ['user:email']
SOCIAL_AUTH_USER_FIELDS = ['username', 'email', 'first_name', 'last_name']
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'signup.utils.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    # adds the following to the default pipeline because sites offer
    # login by e-mail, which be definition then is unique in `auth_user`.
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# Use of reCAPTCHA workflow
NOCAPTCHA = True


# User settings
# -------------
LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = reverse_lazy('product_default_start')

AUTHENTICATION_BACKENDS = (
    'social_core.backends.azuread.AzureADOAuth2',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.github.GithubOAuth2',
# disables SAML so it is simpler to configure on a developer machine.
#    'social_core.backends.saml.SAMLAuth',
# disables LDAP so a few dependencies do not need to be installed either.
#    'signup.backends.auth_ldap.LDAPBackend',
    'signup.backends.auth.UsernameOrEmailPhoneModelBackend',
    'django.contrib.auth.backends.ModelBackend'
)

# Notification settings
# ---------------------
#: The backend to send notifications to users and/or profile managers.
#: The two backend bundled with the project are
#: `djaoapp.notifications.backends.NotificationEmailBackend` to notify users
#: by e-mail and `djaoapp.notifications.backends.NotificationWebhookBackend` to
#: `POST` and event to an URL.
NOTIFICATION_BACKENDS = (
    'djaoapp.notifications.backends.NotificationWebhookBackend',
    'djaoapp.notifications.backends.NotificationEmailBackend',
)


# Demo mode ...
REUSABLE_PRODUCTS = ('livedemo',)
