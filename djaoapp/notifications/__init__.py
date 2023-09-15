from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

def get_notification_backend():
    WEBHOOK_BACKEND = 'djaoapp.notifications.backends.NotificationWebhookBackend'

    if settings.NOTIFICATION_BACKEND == WEBHOOK_BACKEND and \
        not getattr(settings, 'NOTIFICATION_WEBHOOK_URL', None):
        raise ImproperlyConfigured('You must set NOTIFICATION_WEBHOOK_URL if '\
            'you are using the webhook backend')

    return _load_backend(settings.NOTIFICATION_BACKEND)()


def _load_backend(path):
    dot_pos = path.rfind('.')
    module, attr = path[:dot_pos], path[dot_pos + 1:]
    try:
        mod = import_module(module)
    except ImportError as err:
        raise ImproperlyConfigured('Error importing notification backend %s: "%s"'
            % (path, err))
    except ValueError:
        raise ImproperlyConfigured('Error importing emailer backend. '\
' Is NOTIFICATION_BACKEND a path to a callable?')
    try:
        cls = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a "%s" '\
' notification backend' % (module, attr))
    return cls


def send_notification(event_name, context=None, site=None, recipients=None):
    backend = get_notification_backend()
    backend.send_notification(event_name, context, site, recipients)