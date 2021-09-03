# Copyright (c) 2021, DjaoDjin inc.
# see LICENSE

from extended_templates.views.static import AssetView as BaseAssetView
from rules.views.app import AppMixin, SessionProxyMixin

class AssetView(SessionProxyMixin, AppMixin, BaseAssetView):
    pass
