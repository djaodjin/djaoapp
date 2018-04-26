# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

# Django settings for Djaoapp project.
import logging, os.path, sys

from django.contrib.messages import constants as messages

from deployutils.configs import load_config, update_settings

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

#pylint: disable=undefined-variable
FEATURES_REVERT_TO_DJANGO = False # XXX 2016-03-31 temporary product switch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_NAME = os.path.basename(BASE_DIR)

DB_HOST = ''
DB_PORT = 5432

update_settings(sys.modules[__name__],
    load_config(APP_NAME, 'credentials', 'site.conf', verbose=True,
        location=os.getenv("SETTINGS_LOCATION", None),
        passphrase=os.getenv("SETTINGS_CRYPT_KEY", None)))

if os.getenv('DEBUG'):
    # Enable override on command line.
    DEBUG = True if int(os.getenv('DEBUG')) > 0 else False

if getattr(sys.modules[__name__], 'RULES_APP_MODEL', None):
    RULES_APPS = (RULES_APP_MODEL.split('.')[0],)
else:
    RULES_APPS = tuple([])

if DEBUG:
    ENV_INSTALLED_APPS = RULES_APPS + (
        'django.contrib.admin',
        'django.contrib.admindocs',
        'debug_toolbar',
        'debug_panel',
        'django_extensions',
        )
else:
    ENV_INSTALLED_APPS = RULES_APPS

INSTALLED_APPS = ENV_INSTALLED_APPS + (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_assets',
    'rest_framework',
    'captcha',
    'deployutils.apps.django',
#    'haystack', disabled until we actively use text searches on the site.
#XXX deprecated?    'tagging',
    'signup',
    'social_django',
    'saas',
    'pages',
    'multitier',
    'rules',
    'survey',     # For contact page
    # project should be the last entry.
    'djaoapp'
)

if DEBUG:
    MIDDLEWARE_CLASSES = tuple([
        'debug_panel.middleware.DebugPanelMiddleware',
    ])
else:
    MIDDLEWARE_CLASSES = ()

MIDDLEWARE_CLASSES += (
    'django.middleware.common.CommonMiddleware',
    'multitier.middleware.SiteMiddleware',
    'multitier.middleware.SetRemoteAddrFromForwardedFor',
    'rules.middleware.RulesMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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

DB_TEST = 'testing'

DATABASES = {
    'default': {
        'ENGINE':DB_ENGINE,
        'NAME': DB_NAME,
        'USER': DB_USER,                 # Not used with sqlite3.
        'PASSWORD': DB_PASSWORD,         # Not used with sqlite3.
        'HOST': DB_HOST,                 # Not used with sqlite3.
        'PORT': DB_PORT,                 # Not used with sqlite3.
        'TEST': {
            'NAME': None,
        }
    },
    DB_TEST: {
        'ENGINE':DB_ENGINE,
        'NAME': TEST_DB_NAME,
        'USER': DB_USER,                 # Not used with sqlite3.
        'PASSWORD': DB_PASSWORD,         # Not used with sqlite3.
        'HOST': DB_HOST,                 # Not used with sqlite3.
        'PORT': DB_PORT,                 # Not used with sqlite3.
        'TEST': {
            'NAME': None,
        }
    }
}

MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

DATABASE_ROUTERS = ('multitier.routers.SiteRouter',)

if os.getenv('MULTITIER_DB_NAME'):
    MULTITIER_DB_NAME = os.getenv('MULTITIER_DB_NAME')
    MULTITIER_NAME = os.path.splitext(os.path.basename(MULTITIER_DB_NAME))[0]
    if not MULTITIER_NAME in DATABASES:
        DATABASES.update({MULTITIER_NAME: {
                'ENGINE':DB_ENGINE,
                'NAME': MULTITIER_DB_NAME,
                'USER': DB_USER,                 # Not used with sqlite3.
                'PASSWORD': DB_PASSWORD,         # Not used with sqlite3.
                'HOST': DB_HOST,                 # Not used with sqlite3.
                'PORT': DB_PORT,                 # Not used with sqlite3.
                }})

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
    'django_assets.finders.AssetsFinder',
)

ASSETS_DEBUG = DEBUG
ASSETS_AUTO_BUILD = DEBUG
ASSETS_ROOT = HTDOCS + '/static'
ASSETS_URL = STATIC_URL

# Sessions
# --------
# The default session serializer switched to JSONSerializer in Django 1.6
# but just to be sure:
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# Templates
# ---------
# Django 1.8+

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
        'BACKEND': 'extended_templates.backends.eml.EmlEngine',
        'DIRS': TEMPLATES_DIRS,
        'OPTIONS': {
            'engine': 'html',
        }
    },
    {
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
            ],
            'loaders': TEMPLATES_LOADERS,
            'libraries': {},
            'builtins': [
                'django_assets.templatetags.assets',
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

CRISPY_TEMPLATE_PACK = 'bootstrap3'
CRISPY_CLASS_CONVERTERS = {'textinput':"form-control"}

EXTENDED_TEMPLATES = {
    'ASSETS_DIRS_CALLABLE': 'djaoapp.locals.get_current_assets_dirs',
    'BUILD_ABSOLUTE_URI_CALLABLE': 'multitier.mixins.build_absolute_uri',
}


MAX_UPLOAD_SIZE = 10240

# Searches
# --------

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(SEARCH_INDEXES_ROOT, APP_NAME + '.idx')
    },
}


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOG_HANDLER = {
    'level': 'DEBUG',
    'formatter': 'request_format' if DEBUG else 'json',
    'filters': ['request'],
    'class':'logging.StreamHandler',
}
if logging.getLogger('gunicorn.error').handlers:
    #pylint:disable=invalid-name
    _handler = logging.getLogger('gunicorn.error').handlers[0]
    if isinstance(_handler, logging.FileHandler):
        LOG_HANDLER.update({
            'class':'logging.handlers.WatchedFileHandler',
            'filename': LOG_FILE
        })
    else:
        # stderr or logging.handlers.SysLogHandler
        LOG_HANDLER.update({'class': "%s.%s" % (
            _handler.__class__.__module__, _handler.__class__.__name__)})

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
            'handlers': ['log', 'mail_admins'],
            'level': 'INFO'
        },
    },
}


# Authentication
# --------------
SIGNUP = {
    'ACCOUNT_MODEL': 'saas.Organization',
}
for config_param in ('AWS_REGION', 'AWS_UPLOAD_ROLE', 'AWS_ACCOUNT_ID'):
    # This parameters are optional in site.conf.
    if hasattr(sys.modules[__name__], config_param):
        SIGNUP.update({config_param:
            getattr(sys.modules[__name__], config_param)})

ACCOUNT_ACTIVATION_DAYS = 2

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/' # XXX otherwise logout on djaoapp might lead to 410.

SOCIAL_AUTH_GITHUB_SCOPE = ['user:email']
SOCIAL_AUTH_USER_FIELDS = ['username', 'email', 'first_name', 'last_name']

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
    'PAGE_SIZE': 25,
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    )
}
if not DEBUG:
    REST_FRAMEWORK.update({
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        )
    })

DEBUG_TOOLBAR_PATCH_SETTINGS = False
DEBUG_TOOLBAR_CONFIG = {
    'JQUERY_URL': '/static/vendor/jquery.js',
    'SHOW_COLLAPSED': True,
    'SHOW_TEMPLATE_CONTEXT': True,
}

INTERNAL_IPS = ('127.0.0.1', '::1')

# Software-as-a-Service  (multi-tenant)
MULTITIER = {
    'ACCOUNT_MODEL': 'saas.Organization',
    'ACCOUNT_URL_KWARG': 'organization',
#    'DEFAULT_URLS': ['login'], # XXX can't do reverse in multitier middleware.
    'ROUTER_APPS': RULES_APPS + ('signup', 'saas', 'pages', 'rules', 'survey'),
    'ROUTER_TABLES': ('django_session', 'auth_user'),
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
    'BYPASS_PROCESSOR_AUTH': getattr(
        sys.modules[__name__], 'USE_FIXTURES', False),
    'EXTRA_MIXIN': djaoapp.extras.saas.ExtraMixin,
    'BROKER': {
        'GET_INSTANCE': 'djaoapp.locals.get_current_broker',
        'IS_INSTANCE_CALLABLE': 'djaoapp.locals.is_current_broker',
        'BUILD_ABSOLUTE_URI_CALLABLE': 'multitier.mixins.build_absolute_uri',
    },
    'PROCESSOR': {
        'PUB_KEY': STRIPE_PUB_KEY,
        'PRIV_KEY': STRIPE_PRIV_KEY,
        'MODE': 1, # Default: Mallspace, i.e. ``FORWARD``.
        'CLIENT_ID': STRIPE_CLIENT_ID,
        'REDIRECT_CALLABLE': 'djaoapp.locals.processor_redirect',
        'FALLBACK':  getattr(sys.modules[__name__], 'PROCESSOR_FALLBACK', [])
    },
    'PROCESSOR_BACKEND_CALLABLE': 'djaoapp.locals.dynamic_processor_keys',
}

# Software-as-a-Service (forward requests with session data)
RULES = {
    'EXTRA_MIXIN': djaoapp.extras.rules.ExtraMixin,
    'ACCOUNT_MODEL': 'saas.Organization',
    'DEFAULT_APP_CALLABLE': 'djaoapp.locals.get_current_app',
    'DEFAULT_RULES': [('/app/', 1, False), ('/', 0, False)],
    'PATH_PREFIX_CALLABLE': 'multitier.thread_locals.get_path_prefix',
    'SESSION_SERIALIZER': 'djaoapp.api.serializers.SessionSerializer',
    'RULE_OPERATORS': (
        '',                                             # 0
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
    ),
}

# Software-as-a-Service (pages editor)
def theme_dir(account):
    return os.path.join(MULTITIER['THEMES_DIRS'][0], str(account))

PAGES = {
    'ACCOUNT_MODEL': getattr(sys.modules[__name__], 'RULES_APP_MODEL',
        'rules.App'),
    'ACCOUNT_URL_KWARG' : 'app',
    'ACTIVE_THEME_CALLABLE': 'djaoapp.locals.get_active_theme',
    'DEFAULT_ACCOUNT_CALLABLE': 'djaoapp.locals.get_current_app',
    'EXTRA_MIXIN': djaoapp.extras.pages.ExtraMixin,
    'PUBLIC_ROOT': HTDOCS,
    'TEMPLATES_BLACKLIST': [
        '403.html',
        '404.html',
        '500.html',
        '_field.html',
        '_form.html',
        'accounts/_recover_form.html',
        'accounts/_register_form.html',
        'accounts/activate.html',
        'accounts/base.html',
        'accounts/login.html',
        'accounts/logout.html',
        'accounts/recover.html',
#        'accounts/register.html',
        'accounts/reset.html',
#        'app.html',
        'app_proxy_help.html',
        'base.html',
        'contact.html',
        'generic_navbar.html',
#        'index.html',
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
        'notification/base.eml',
        'notification/card_updated.eml',
        'notification/charge_receipt.eml',
        'notification/claim_code_generated.eml',
        'notification/new_task_added.eml',
        'notification/order_executed.eml',
        'notification/password_reset.eml',
        'notification/user_activated.eml',
        'notification/user_contact.eml',
        'notification/user_registered.eml',
        'notification/role_added.eml',
        'notification/verification.eml',
        'pages/_body_bottom.html',
        'pages/_body_top.html',
        'pages/_body_top_connect_processor.html',
        'pages/_body_top_toggle_production.html',
        'pages/create_package.html',
        'pages/file_edition.html',
        'pages/pages_editor_modes.html',
        'pages/theme.html',
        'rules/app_dashboard.html',
        'saas/_bank_use.html',
        'saas/_card_use.html',
        'saas/_invoiceables.html',
        'saas/_plan_form.html',
#        'saas/_plan_short.html',
        'saas/_provider_sidebar.html',
        'saas/_subscriber_sidebar.html',
        'saas/_transactions.html',
        'saas/agreements/security.md'
        'saas/agreements/terms-of-use.md'
        'saas/app/new.html',
        'saas/base-2col.html',
        'saas/base.html',
        'saas/base_dashboard.html',
        'saas/billing/balance.html',
        'saas/billing/bank.html',
        'saas/billing/card.html',
        'saas/billing/cart-periods.html',
        'saas/billing/cart-seats.html',
        'saas/billing/cart.html',
        'saas/billing/coupons.html',
        'saas/billing/import.html',
        'saas/billing/index.html',
        'saas/billing/receipt.html',
        'saas/billing/transactions.html',
        'saas/billing/transfers.html',
        'saas/billing/withdraw.html',
        'saas/legal/agreement.html',
        'saas/legal/base.html',
        'saas/legal/index.html',
        'saas/legal/sign.html',
        'saas/users/roles.html',
        'saas/metrics/balances.html',
        'saas/metrics/base.html',
        'saas/metrics/coupons.html',
        'saas/metrics/dashboard.html',
        'saas/metrics/plans.html',
        'saas/organization_redirects.html',
#        'saas/pricing.html',
        'saas/printable_charge_receipt.html',
        'saas/profile/index.html',
        'saas/profile/plans.html',
        'saas/profile/roles/index.html',
        'saas/profile/roles/role.html',
        'saas/profile/subscribers.html',
        'saas/profile/subscriptions.html',
        'saas/redeem.html',
        'static/directory_index.html',
        'users/base.html',
        'users/password_change_form.html',
        'users/user_form.html',
    ],
    'THEME_DIR_CALLABLE': theme_dir
}

# Surveys (contact page)
SURVEY = {
    'BELONGS_MODEL': 'saas.Organization'
}

# Demo mode ...
REUSABLE_PRODUCTS = ('demo',)
