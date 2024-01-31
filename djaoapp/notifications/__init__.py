# Copyright (c) 2024, DjaoDjin inc.
# see LICENSE
import sys
from collections import OrderedDict
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


def _load_backend(path):
    dot_pos = path.rfind('.')
    module, attr = path[:dot_pos], path[dot_pos + 1:]
    try:
        mod = import_module(module)
    except ImportError as err:
        raise ImproperlyConfigured(
            'Error importing notification backend %s: "%s"' % (path, err))
    except ValueError:
        raise ImproperlyConfigured('Error importing notification backend. '\
' Is NOTIFICATION_BACKENDS a list of paths to a callable?')
    try:
        cls = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a "%s" '\
' notification backend' % (module, attr))
    return cls


def send_notification(event_name, context=None, site=None, recipients=None):
    if not hasattr(sys.modules[__name__], '_NOTIFICATION_BACKENDS'):
        backends = OrderedDict()
        for backend_path in settings.NOTIFICATION_BACKENDS:
            backends.update({
                backend_path: _load_backend(backend_path)()})
        setattr(sys.modules[__name__], '_NOTIFICATION_BACKENDS', backends)
    for backend in _NOTIFICATION_BACKENDS.values():
        backend.send_notification(event_name, context, site, recipients)
