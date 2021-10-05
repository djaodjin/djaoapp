# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

# Django settings for Djaoapp project.
import os.path, sys

from django import VERSION as DJANGO_VERSION
from django.contrib.messages import constants as messages

from deployutils.configs import load_config, update_settings

from .compat import reverse_lazy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default values that can be overriden by `update_settings` later on.
APP_NAME = os.path.basename(BASE_DIR)

DEBUG = True

ALLOWED_HOSTS = ('*',)
BYPASS_VERIFICATION_KEY_EXPIRED_CHECK = False

DB_ENGINE = 'sqlite3'
DB_NAME = os.path.join(BASE_DIR, 'db.sqlite')
DB_HOST = ''
DB_PORT = 5432
DB_USER = None
DB_PASSWORD = None

SEND_EMAIL = True
RULES_APP_MODEL = 'djaoapp_extras.App'

#pylint: disable=undefined-variable
FEATURES_REVERT_TO_DJANGO = False   # 2016-03-31 temporary product switch
FEATURES_REVERT_STRIPE_V2 = False   # 2021-03-03 temporary reverts SCA

CONTACT_DYNAMIC_VALIDATOR = None

update_settings(sys.modules[__name__],
    load_config(APP_NAME, 'credentials', 'site.conf', verbose=True))

# Configuration settings that can be overriden on the command line.
if os.getenv('DEBUG'):
    DEBUG = bool(int(os.getenv('DEBUG')) > 0)

if not hasattr(sys.modules[__name__], 'FEATURES_DEBUG'):
    FEATURES_DEBUG = DEBUG

if os.getenv('BYPASS_VERIFICATION_KEY_EXPIRED_CHECK'):
    BYPASS_VERIFICATION_KEY_EXPIRED_CHECK = (int(os.getenv(
        'BYPASS_VERIFICATION_KEY_EXPIRED_CHECK', "0")) > 0)

API_DEBUG = True if int(os.getenv('API_DEBUG', "0")) > 0 else DEBUG

# Remove extra information used for documentation like examples, etc.
OPENAPI_SPEC_COMPLIANT = (int(os.getenv('OPENAPI_SPEC_COMPLIANT', "0")) > 0)


# Implementation Note: To simplify quick tests. The `SECRET_KEY` should
# be defined in the `credentials` otherwise all HTTP session will become
# invalid as the process is restarted.
if not hasattr(sys.modules[__name__], "SECRET_KEY"):
    from random import choice
    SECRET_KEY = "".join([choice(
        "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)])


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# py27/django-recaptcha workaround
for recaptcha_key in ['RECAPTCHA_PRIVATE_KEY', 'RECAPTCHA_PUBLIC_KEY']:
    recaptcha_key_value = getattr(sys.modules[__name__], recaptcha_key, None)
    if recaptcha_key_value and not isinstance(recaptcha_key_value, str):
        setattr(sys.modules[__name__], recaptcha_key,
            recaptcha_key_value.encode('utf-8'))

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']

if getattr(sys.modules[__name__], 'RULES_APP_MODEL', None):
    RULES_APPS = (RULES_APP_MODEL.split('.')[0],)
else:
    RULES_APPS = tuple([])

if DEBUG:
    if not FEATURES_REVERT_TO_DJANGO:
        # (Django2.2) We cannot include admin panels because a `check`
        # for DjangoTemplates will fail when we are using Jinja2 templates
        if DJANGO_VERSION[0] >= 2:
            # django-debug-toolbar==1.11 does not support Django2.2
            DEBUG_APPS = RULES_APPS + (
                'django_extensions',
            )
        else:
            DEBUG_APPS = RULES_APPS + (
                'debug_toolbar',
                'debug_panel',
                'django_extensions',
            )
    else:
        DEBUG_APPS = RULES_APPS + (
            'django.contrib.admin',
            'django.contrib.admindocs',
            'debug_toolbar',
            'debug_panel',
            'django_extensions',
        )
else:
    DEBUG_APPS = RULES_APPS

if API_DEBUG:
    ENV_INSTALLED_APPS = DEBUG_APPS + (
        'drf_yasg',
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
    'webpack_loader',
    'rest_framework',
    'captcha',
    'deployutils.apps.django',
#    'haystack', disabled until we actively use text searches on the site.
    'saas',  # Because we want `djaodjin-resources.js` picked up from here.
    'signup',
    'social_django',
    'pages',
    'multitier',
    'rules',
    'djaoapp'
)

if DEBUG and 'debug_toolbar' in INSTALLED_APPS:
    MIDDLEWARE = (
        'debug_panel.middleware.DebugPanelMiddleware',
    )
elif not DEBUG:
    MIDDLEWARE = (
        'whitenoise.middleware.WhiteNoiseMiddleware',
    )
else:
    MIDDLEWARE = tuple([])

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
    'deployutils.apps.django.middleware.RequestLoggingMiddleware',
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
LANGUAGE_CODE = 'en-us'

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

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = HTDOCS + '/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
APP_STATIC_ROOT = HTDOCS + '/static'
if DEBUG:
    STATIC_ROOT = ''
    # Additional locations of static files
    STATICFILES_DIRS = (APP_STATIC_ROOT, HTDOCS,)
else:
    STATIC_ROOT = APP_STATIC_ROOT

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'multitier.finders.MultitierFileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

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
            'vendor/djaodjin-pages/*.scss',
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

ASSETS_DEBUG = DEBUG
#XXX ASSETS_ROOT = os.path.join(BASE_DIR, 'assets')
ASSETS_ROOT = HTDOCS

if not hasattr(sys.modules[__name__], 'WEBPACK_LOADER_STATS_FILE'):
    WEBPACK_LOADER_STATS_FILE = os.path.join(ASSETS_ROOT, 'webpack-stats.json')

WEBPACK_LOADER = {
    'DEFAULT': {
        'CACHE': not ASSETS_DEBUG,
        'BUNDLE_DIR_NAME': 'cache/', # must end with slash
        'STATS_FILE': WEBPACK_LOADER_STATS_FILE,
        'POLL_INTERVAL': 0.1,
        'TIMEOUT': None,
        'IGNORE': [r'.+\.hot-update.js', r'.+\.map']
    }
}

# Sessions
# --------
# The default session serializer switched to JSONSerializer in Django 1.6
# but just to be sure:
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# Templates
# ---------
# Django 1.8+
FILE_CHARSET = 'utf-8'

if FEATURES_REVERT_TO_DJANGO:
    TEMPLATES_DIRS = (
        os.path.join(BASE_DIR, 'djaoapp', 'templates', 'django'),
        os.path.join(BASE_DIR, 'djaoapp', 'templates'),)
else:
    TEMPLATES_DIRS = (
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
    'django.contrib.auth.context_processors.auth', # because of admin/
    'django.template.context_processors.request',
    'django.template.context_processors.media',
    'multitier.context_processors.features_debug',
    'djaoapp.context_processors.features_flags',
            ],
            'loaders': TEMPLATES_LOADERS,
            'libraries': {},
            'builtins': [
                'django.templatetags.i18n',# XXX Format incompatible with Jinja2
                'multitier.templatetags.multitier_tags',
                'deployutils.apps.django.templatetags.deployutils_extratags',
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

EXTENDED_TEMPLATES = {
    'ASSETS_MAP': ASSETS_MAP,
    'ASSETS_DIRS_CALLABLE': 'djaoapp.thread_locals.get_current_assets_dirs',
    'BUILD_ABSOLUTE_URI_CALLABLE': 'multitier.mixins.build_absolute_uri',
}


MAX_UPLOAD_SIZE = 10240


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOG_HANDLER = {
    'level': 'DEBUG',
    'formatter': ('request_format' if (DEBUG or
        getattr(sys.modules[__name__], 'USE_FIXTURES', False)) else 'json'),
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
            '()': 'deployutils.apps.django.logging.RequestFilter',
        },
    },
    'formatters': {
        'simple': {
            'format': 'X X %(levelname)s [%(asctime)s] %(message)s',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z'
        },
        'json': {
            '()': 'deployutils.apps.django.logging.JSONFormatter',
            'format':
            'gunicorn.' + APP_NAME + '.app: [%(process)d] '\
                '%(log_level)s %(remote_addr)s %(http_host)s %(username)s'\
                ' [%(asctime)s] %(message)s',
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
            '%(levelname)s %(remote_addr)s %(username)s [%(asctime)s]'\
                ' %(message)s "%(http_user_agent)s"',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z'
        }
    },
    'handlers': {
        'db_log': {
            'level': 'DEBUG',
            'formatter': 'simple',
            'filters': ['require_debug_true'],
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
        'extended_templates': {
            'handlers': [],
            'level': 'INFO',
        },
        'multitier': {
            'handlers': [],
            'level': 'INFO',
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
        'pages': {
            'handlers': [],
            'level': 'INFO',
        },
        'djaoapp': {
            'handlers': [],
            'level': 'INFO',
        },
        'deployutils': {
            'handlers': ['db_log'],
            'level': 'INFO',
            'propagate': False
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
        'requests': {
            'handlers': [],
            'level': 'WARNING',
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


# Authentication
# --------------
SIGNUP = {
    'ACCOUNT_MODEL': 'saas.Organization',
    'ACCOUNT_ACTIVATION_DAYS': 30,
    'BYPASS_VERIFICATION_KEY_EXPIRED_CHECK':
        BYPASS_VERIFICATION_KEY_EXPIRED_CHECK,
    'DISABLED_AUTHENTICATION':
        'djaoapp.thread_locals.get_disabled_authentication',
    'DISABLED_REGISTRATION':
        'djaoapp.thread_locals.get_disabled_registration',
    'EMAIL_DYNAMIC_VALIDATOR': getattr(
        sys.modules[__name__], 'SIGNUP_EMAIL_DYNAMIC_VALIDATOR', None),
    'LOGIN_THROTTLE': getattr(
        sys.modules[__name__], 'SIGNUP_LOGIN_THROTTLE', None),
    'NOTIFICATION_TYPE': (
        ('card_updated', "Card updated"),
        ('charge_receipt', "Charge receipt"),
        ('claim_code_generated', "Claim code"),
        ('expires_soon', "Expires soon"),
        ('order_executed', "Order confirmation"),
        ('organization_updated', "Profile updated"),
        ('password_reset', "Password reset"),
        ('user_activated', "User activated"),
        ('user_contact', "User contact"),
        ('user_registered', "User registered"),
        ('user_welcome', "User welcome"),
        ('role_request_created', "Role requested"),
        ('verification', "Verification"),
        ('sales_report', "Weekly sales report"),
    ),
    'PASSWORD_RESET_THROTTLE': getattr(
        sys.modules[__name__], 'SIGNUP_PASSWORD_RESET_THROTTLE', None),
    'PICTURE_STORAGE_CALLABLE': 'djaoapp.thread_locals.get_default_storage',
    'RANDOM_SEQUENCE': getattr(
        sys.modules[__name__], 'SIGNUP_RANDOM_SEQUENCE', [])
}
for config_param in ('AWS_REGION', 'AWS_UPLOAD_ROLE', 'AWS_ACCOUNT_ID'):
    # This parameters are optional in site.conf.
    if hasattr(sys.modules[__name__], config_param):
        SIGNUP.update({config_param:
            getattr(sys.modules[__name__], config_param)})

ACCOUNT_ACTIVATION_DAYS = 2

LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = '/' # XXX otherwise logout on djaoapp might lead to 410.

SOCIAL_AUTH_RAISE_EXCEPTIONS = False
SOCIAL_AUTH_LOGIN_ERROR_URL = reverse_lazy('rules_page')
SOCIAL_AUTH_GITHUB_SCOPE = ['user:email']
SOCIAL_AUTH_USER_FIELDS = ['username', 'email', 'first_name', 'last_name']
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
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


NOCAPTCHA = True

AUTHENTICATION_BACKENDS = (
#    'social.backends.facebook.FacebookOAuth2',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.twitter.TwitterOAuth',
    'social_core.backends.github.GithubOAuth2',
    'signup.backends.auth.UsernameOrEmailModelBackend',
    'django.contrib.auth.backends.ModelBackend'
)

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'djaoapp.views.errors.drf_exception_handler',
    'PAGE_SIZE': 25,
    'DEFAULT_PAGINATION_CLASS':
        'djaoapp.pagination.PageNumberPagination',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'signup.authentication.JWTAuthentication',
        'signup.authentication.APIKeyAuthentication',
        # `rest_framework.authentication.SessionAuthentication` is the last
        # one in the list because it will raise a PermissionDenied if the CSRF
        # is absent.
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'djaoapp.views.docs.AutoSchema',
    'SEARCH_PARAM': 'q',
    'ORDERING_PARAM': 'o'
}
if not DEBUG:
    REST_FRAMEWORK.update({
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        )
    })

DEBUG_TOOLBAR_CONFIG = {
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
        'social_django', 'signup', 'saas', 'pages', 'rules'),
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


# imports made here so SECRET_KEY is defined when loading AUTH_USER.
import djaoapp.extras.saas, djaoapp.extras.rules, djaoapp.extras.pages

# Software-as-a-Service (provider)
SAAS = {
    'BROKER': {
        'GET_INSTANCE': 'djaoapp.thread_locals.get_current_broker',
        'IS_INSTANCE_CALLABLE': 'djaoapp.thread_locals.is_current_broker',
        'BUILD_ABSOLUTE_URI_CALLABLE':
            'djaoapp.thread_locals.provider_absolute_url',
    },
    'EXTRA_MIXIN': djaoapp.extras.saas.ExtraMixin,
    'PICTURE_STORAGE_CALLABLE': 'djaoapp.thread_locals.get_default_storage',
    'PROCESSOR_BACKEND_CALLABLE':
        'djaoapp.thread_locals.dynamic_processor_keys',

    'BYPASS_IMPLICIT_GRANT': getattr(
        sys.modules[__name__], 'BYPASS_IMPLICIT_GRANT', {}),
    'BYPASS_PROCESSOR_AUTH': getattr(
        sys.modules[__name__], 'USE_FIXTURES', False),
    'MAX_TYPEAHEAD_CANDIDATES': 5,
    'PROCESSOR': {
        'PUB_KEY': getattr(sys.modules[__name__], 'STRIPE_PUB_KEY', None),
        'PRIV_KEY': getattr(sys.modules[__name__], 'STRIPE_PRIV_KEY', None),
        'MODE': 1, # ``FORWARD``, i.e. defaults to mallspace.
        'USE_STRIPE_V3': not(getattr(sys.modules[__name__],
            'FEATURES_REVERT_STRIPE_V2', False)),
        'CLIENT_ID': getattr(sys.modules[__name__], 'STRIPE_CLIENT_ID', None),
        'CONNECT_STATE_CALLABLE':
            'djaoapp.thread_locals.get_authorize_processor_state',
        'REDIRECT_CALLABLE': 'djaoapp.thread_locals.processor_redirect',
        'FALLBACK':  getattr(sys.modules[__name__], 'PROCESSOR_FALLBACK', [])
    },
    'USER_SERIALIZER': 'signup.serializers.UserSerializer',
}

# Software-as-a-Service (forward requests with session data)
RULES = {
    'EXTRA_MIXIN': djaoapp.extras.rules.ExtraMixin,
    'ACCOUNT_MODEL': 'saas.Organization',
    'APP_SERIALIZER': 'djaoapp.api.serializers.AppSerializer',
    'DEFAULT_APP_CALLABLE': 'djaoapp.thread_locals.get_current_app',
    'DEFAULT_RULES': [('/app/', 1, False), ('/', 0, False)],
    'PATH_PREFIX_CALLABLE': 'multitier.thread_locals.get_path_prefix',
    'SESSION_SERIALIZER': 'djaoapp.api.serializers.SessionSerializer',
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
}

# Software-as-a-Service (pages editor)
def theme_dir(account):
    return os.path.join(MULTITIER['THEMES_DIRS'][0], str(account))

PAGES = {
    'ACCOUNT_MODEL': 'saas.Organization',
    'DEFAULT_ACCOUNT_CALLABLE': 'djaoapp.thread_locals.get_current_broker',
    'DEFAULT_STORAGE_CALLABLE': 'djaoapp.thread_locals.get_default_storage',
    'ACCOUNT_URL_KWARG' : 'app',
    'ACTIVE_THEME_CALLABLE': 'djaoapp.thread_locals.get_active_theme',
    'EXTRA_MIXIN': djaoapp.extras.pages.ExtraMixin,
    'PUBLIC_ROOT': HTDOCS,
    'TEMPLATES_BLACKLIST': [
        'jinja2/debug_toolbar/base.html',
        'jinja2/debug_toolbar/panels/cache.html',
        'jinja2/debug_toolbar/panels/headers.html',
        'jinja2/debug_toolbar/panels/logging.html',
        'jinja2/debug_toolbar/panels/profiling.html',
        'jinja2/debug_toolbar/panels/request.html',
        'jinja2/debug_toolbar/panels/settings.html',
        'jinja2/debug_toolbar/panels/signals.html',
        'jinja2/debug_toolbar/panels/sql.html',
        'jinja2/debug_toolbar/panels/sql_explain.html',
        'jinja2/debug_toolbar/panels/sql_profile.html',
        'jinja2/debug_toolbar/panels/sql_select.html',
        'jinja2/debug_toolbar/panels/staticfiles.html',
        'jinja2/debug_toolbar/panels/template_source.html',
        'jinja2/debug_toolbar/panels/templates.html',
        'jinja2/debug_toolbar/panels/timer.html',
        'jinja2/debug_toolbar/panels/versions.html',
        'jinja2/debug_toolbar/redirect.html',
        'notification/app_created.eml',
        'notification/app_updated.eml',
        'pages/_body_bottom.html',
        'pages/_body_bottom_edit_tools.html',
        'pages/_body_top_template.html',
        'pages/_edit_tools.html',
        'static/directory_index.html',
        'demo/frictionless.html',
        'demo/frictionless-iframe.html'
    ],
    'THEME_DIR_CALLABLE': theme_dir
}

# Demo mode ...
REUSABLE_PRODUCTS = ('livedemo',)
