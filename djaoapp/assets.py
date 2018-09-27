# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

import os

from django_assets import Bundle, register
from django.conf import settings

#pylint: disable=invalid-name

# All the CSS we need for the entire site. This tradeoff between
# bandwidth and latency is good as long as we have a high and consistent
# utilization of all the CSS tags for all pages on the site.
css_base = Bundle(
    os.path.join(settings.BASE_DIR, 'assets/less/base/base.less'),
    filters=['less', 'cssmin'],
    output='cache/base.css', debug=False)
register('css_base', css_base)

css_email = Bundle(
    os.path.join(settings.BASE_DIR, 'assets/less/email/email.less'),
    filters=['less', 'cssmin'],
    output='cache/email.css', debug=False)
register('css_email', css_email)

# Minimal: jquery and bootstrap always active on the site
js_base = Bundle('vendor/jquery.js',
                 'vendor/jquery.cookie.js',
                 'vendor/bootstrap.js',
                 'vendor/bootbox.js',
                 'vendor/toastr.js',
                 'js/djaodjin-general.js',
            filters='yui_js', output='cache/base.js')
register('js_base', js_base)


# User cart and payment processing (also includes ``showErrorMessages``).
js_saas = Bundle(
    'vendor/jquery.payment.js',
    'js/djaodjin-saas.js',
    'js/djaodjin-stripe.js',
    'js/djaodjin-postal.js',
    'js/djaodjin-password-strength.js',
    'js/djaodjin-resources.js', # At the end to avoid errors in browser
                                # after all files are concatenated together
    filters='jsmin', output='cache/saas.js') # XXX yuv_js produces errors.
register('js_saas', js_saas)


js_auth = Bundle(
    'js/djaodjin-postal.js',
    'js/djaodjin-password-strength.js',
    filters='yui_js', output='cache/auth.js')
register('js_auth', js_auth)

# Related to djaodjin-saas manager dasboard
# -----------------------------------------

# must be present:
#  - css_base
css_dashboard = Bundle(
    Bundle(
        os.path.join(settings.BASE_DIR,
            'assets/less/base/djaodjin-dashboard.less'),
        filters='less', output='cache/djaodjin-dashboard.css', debug=False),
    'vendor/nv.d3.css',
    'vendor/trip.css',
    'vendor/chardinjs.css', # XXX duplicated from snaplines.css
    filters='cssmin', output='cache/dashboard.css')
register('css_dashboard', css_dashboard)


js_angular = Bundle(
    'vendor/moment.js',
    'vendor/moment-timezone-with-data.js',
    'vendor/angular.min.js',
    'vendor/angular-touch.min.js',
    'vendor/angular-animate.min.js',
    'vendor/angular-dragdrop.js',
    'vendor/angular-resource.js', # modified to prevent / encode
    'vendor/angular-route.min.js',
    'vendor/angular-sanitize.js',
    'vendor/ui-bootstrap-tpls.js',
    'vendor/jquery-ui.js',
    'vendor/vue.js',
    'vendor/uiv.min.js',
    'vendor/vue2-filters.js',
    'js/djaodjin-vue.js',
    filters='jsmin', output='cache/angular.js')
register('js_angular', js_angular)


# must be present:
#  - ???
js_dashboard = Bundle(
    'vendor/dropzone.js',                  # XXX also in js_pages
    'vendor/d3.js',
    'vendor/nv.d3.js',
    'vendor/trip.js',
    'vendor/chardinjs.js',
    'js/djaodjin-upload.js',
    'js/djaodjin-dashboard.js',
    'js/djaodjin-signup-angular.js',
    'js/djaodjin-saas-angular.js',
    'js/djaodjin-proxy-angular.js',
    'js/djaodjin-metrics.js',
    'js/uploadapp.js',
    filters='jsmin', output='cache/dashboard.js')
register('js_dashboard', js_dashboard)


# Related to djaodjin-pages edition tools
# ---------------------------------------

# must be present:
#  - css_base
css_pages = Bundle(
    "vendor/jquery-ui.css",                 # pages
    "vendor/chardinjs.css", # XXX duplicated from snaplines.css
    "vendor/bootstrap-colorpicker.css",
    'css/djaodjin-editor.css',
    'css/djaodjin-sidebar-gallery.css',
    filters='cssmin', output='cache/pages.css')
register('css_pages', css_pages)

# must be previously included:
#   - vendor/js/jquery.js (js_base)
js_pages = Bundle(
    "vendor/dropzone.js",                  # pages
    "vendor/jquery-ui.js",                 # pages
    "vendor/jquery.selection.js",          # pages
    "vendor/jquery.autosize.js",           # pages
    "vendor/Markdown.Converter.js",        # pages
    "vendor/Markdown.Sanitizer.js",        # pages
    "vendor/rangy-core.js",
    "vendor/hallo.js",
    "vendor/jquery.textarea_autosize.js",
    "vendor/jquery.ui.touch-punch.js",     # pages
    "vendor/chardinjs.js", # XXX duplicated from js_dashboard
    "vendor/less.js",
    "js/djaodjin-resources.js",
    "js/djaodjin-editor.js",           # pages
    "js/djaodjin-upload.js",           # pages
    "js/djaodjin-sidebar-gallery.js",  # pages
    "js/djaodjin-plan-edition.js",
    "js/wizard.js",
    filters='jsmin', output='cache/pages.js')
register('js_pages', js_pages)


js_theme_editors = Bundle(
    #XXX Cannot find a bower install:
    # https://raw.githubusercontent.com/cowboy/jquery-throttle-debounce/master/jquery.ba-throttle-debounce.js
    "vendor/jquery.ba-throttle-debounce.js",
    "vendor/bootstrap-colorpicker.js",
    "js/djaodjin-code-editor.js",      # pages
    "js/djaodjin-style-editor.js",     # pages
    filters='jsmin', output='cache/theme-editors.js')
register('js_theme_editors', js_theme_editors)
