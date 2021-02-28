# Make a couple frequently used things available right here.
from webassets.bundle import Bundle
from django_assets.env import register


__all__ = ('Bundle', 'register')

__version__ = (2, 0)
__webassets_version__ = ('>=2.0',)


from django_assets import filter
