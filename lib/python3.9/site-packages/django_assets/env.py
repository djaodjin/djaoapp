import threading
from importlib import import_module
from importlib.util import find_spec as importlib_find

from django.apps import apps
from django.contrib.staticfiles import finders
from django.conf import settings
from webassets.env import (
    BaseEnvironment, ConfigStorage, Resolver, url_prefix_join)

from django_assets.glob import Globber, has_magic


__all__ = ('register',)


class DjangoConfigStorage(ConfigStorage):

    _mapping = {
        'debug': 'ASSETS_DEBUG',
        'cache': 'ASSETS_CACHE',
        'cache_file_mode': 'ASSETS_CACHE_FILE_MODE',
        'updater': 'ASSETS_UPDATER',
        'auto_build': 'ASSETS_AUTO_BUILD',
        'url_expire': 'ASSETS_URL_EXPIRE',
        'versions': 'ASSETS_VERSIONS',
        'manifest': 'ASSETS_MANIFEST',
        'load_path': 'ASSETS_LOAD_PATH',
        'url_mapping': 'ASSETS_URL_MAPPING',
    }

    def _transform_key(self, key):
        if key.lower() == 'directory':
            if hasattr(settings, 'ASSETS_ROOT'):
                return 'ASSETS_ROOT'
            if getattr(settings, 'STATIC_ROOT', None):
                # Is None by default
                return 'STATIC_ROOT'
            return 'MEDIA_ROOT'

        if key.lower() == 'url':
            if hasattr(settings, 'ASSETS_URL'):
                return 'ASSETS_URL'
            if getattr(settings, 'STATIC_URL', None):
                # Is '' by default
                return 'STATIC_URL'
            return 'MEDIA_URL'

        return self._mapping.get(key.lower(), key.upper())

    def __contains__(self, key):
        return hasattr(settings, self._transform_key(key))

    def __getitem__(self, key):
        if self.__contains__(key):
            value = self._get_deprecated(key)
            if value is not None:
                return value
            return getattr(settings, self._transform_key(key))
        else:
            raise KeyError("Django settings doesn't define %s" %
                           self._transform_key(key))

    def __setitem__(self, key, value):
        if not self._set_deprecated(key, value):
            setattr(settings, self._transform_key(key), value)

    def __delitem__(self, key):
        # This isn't possible to implement in Django without relying
        # on internals of the settings object, so just set to None.
        self.__setitem__(key, None)


class StorageGlobber(Globber):
    """Globber that works with a Django storage."""

    def __init__(self, storage):
        self.storage = storage

    def isdir(self, path):
        # No API for this, though we could a) check if this is a filesystem
        # storage, then do a shortcut, otherwise b) use listdir() and see
        # if we are in the directory set.
        # However, this is only used for the "sdf/" syntax, so by returning
        # False we disable this syntax and cause it no match nothing.
        return False

    def islink(self, path):
        # No API for this, just act like we don't know about links.
        return False

    def listdir(self, path):
        directories, files = self.storage.listdir(path)
        return directories + files

    def exists(self, path):
        try:
            return self.storage.exists(path)
        except NotImplementedError:
            return False


class DjangoResolver(Resolver):
    """Adds support for staticfiles resolving."""

    @property
    def use_staticfiles(self):
        return settings.ASSETS_DEBUG and \
            'django.contrib.staticfiles' in settings.INSTALLED_APPS

    def glob_staticfiles(self, item):
        # The staticfiles finder system can't do globs, but we can
        # access the storages behind the finders, and glob those.

        for finder in finders.get_finders():
            # Builtin finders use either one of those attributes,
            # though this does seem to be informal; custom finders
            # may well use neither. Nothing we can do about that.
            if hasattr(finder, 'storages'):
                storages = finder.storages.values()
            elif hasattr(finder, 'storage'):
                storages = [finder.storage]
            else:
                continue

            for storage in storages:
                globber = StorageGlobber(storage)
                for file in globber.glob(item):
                    yield storage.path(file)

    def search_for_source(self, ctx, item):
        if not self.use_staticfiles:
            return Resolver.search_for_source(self, ctx, item)

        if has_magic(item):
            return list(self.glob_staticfiles(item))
        else:
            f = finders.find(item)
            if f is not None:
                return f

        raise IOError(
            "'%s' not found (using staticfiles finders)" % item)

    def resolve_source_to_url(self, ctx, filepath, item):
        if not self.use_staticfiles:
            return Resolver.resolve_source_to_url(self, ctx, filepath, item)

        # With staticfiles enabled, searching the url mappings, as the
        # parent implementation does, will not help. Instead, we can
        # assume that the url is the root url + the original relative
        # item that was specified (and searched for using the finders).
        import os
        item = item.replace(os.sep, "/")
        return url_prefix_join(ctx.url, item)


class DjangoEnvironment(BaseEnvironment):
    """For Django, we need to redirect all the configuration values this
    object holds to Django's own settings object.
    """

    config_storage_class = DjangoConfigStorage
    resolver_class = DjangoResolver


# Django has a global state, a global configuration, and so we need a
# global instance of a asset environment.
env = None
env_lock = threading.RLock()

def get_env():
    # While the first request is within autoload(), a second thread can come
    # in and without the lock, would use a not-fully-loaded environment.
    with env_lock:
        global env
        if env is None:
            env = DjangoEnvironment()

            # Load application's ``assets``  modules. We need to do this in
            # a delayed fashion, since the main django_assets module imports
            # this, and the application ``assets`` modules we load will import
            # ``django_assets``, thus giving us a classic circular dependency
            # issue.
            autoload()
        return env

def reset():
    global env
    env = None

# The user needn't know about the env though, we can expose the
# relevant functionality directly. This is also for backwards-compatibility
# with times where ``django-assets`` was a standalone library.
def register(*a, **kw):
    return get_env().register(*a, **kw)


def module_has_submodule(package, module_name):
    """See if 'module' is in 'package'."""
    try:
        package_name = package.__name__
        package_path = package.__path__
    except AttributeError:
        # package isn't a package.
        return False

    full_module_name = package_name + '.' + module_name
    try:
        return importlib_find(full_module_name, package_path) is not None
    except (ModuleNotFoundError, AttributeError):
        # When module_name is an invalid dotted path, Python raises
        # ModuleNotFoundError. AttributeError is raised on PY36 (fixed in PY37)
        # if the penultimate part of the path is not a package.
        return False


_ASSETS_LOADED = False

def autoload():
    """Find assets by looking for an ``assets`` module within each
    installed application, similar to how, e.g., the admin autodiscover
    process works. This is were this code has been adapted from, too.

    Only runs once.
    """
    global _ASSETS_LOADED
    if _ASSETS_LOADED:
        return False

    # Import this locally, so that we don't have a global Django
    # dependency.
    from django.conf import settings

    for app in apps.get_app_configs():
        # For each app, we need to look for an assets.py inside that
        # app's package.

        try:
            import_module("{}.assets".format(app.name))
        except Exception:
            # Decide whether to bubble up this error. If the app just
            # doesn't have the module in question, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(app.module, 'assets'):
                raise

    # Load additional modules.
    for module in getattr(settings, 'ASSETS_MODULES', []):
        import_module("%s" % module)

    _ASSETS_LOADED = True
