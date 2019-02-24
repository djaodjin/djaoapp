# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

import os

from django_assets import Bundle, register
from django.conf import settings

#pylint: disable=invalid-name

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
                 'js/djaodjin-dashboard.js',
                 'js/djaodjin-menubar.js',
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
    'vendor/nv.d3.css',
    'vendor/trip.css',
    'vendor/chardinjs.css', # XXX duplicated from snaplines.css
    filters='cssmin', output='cache/dashboard.css')
register('css_dashboard', css_dashboard)

js_vue = Bundle(
    'vendor/moment.js',
    'vendor/moment-timezone-with-data.js',
    'vendor/jquery-ui.js',
    'vendor/Sortable.js',
    'vendor/vue.js',
    'vendor/bootstrap-vue.min.js',
    'vendor/uiv.min.js', # XXX uiv is loaded from the vue.use in djaodjin-saas 
    'vendor/vue2-filters.js',
    filters='jsmin', output='cache/vue.js')
register('js_vue', js_vue)

js_djaodjin_vue = Bundle(
    'js/djaodjin-dashboard.js', # also in base.js
    'js/djaodjin-menubar.js',  # also in base.js
    'vendor/dropzone.js',                  # XXX also in js_pages
    'vendor/d3.js',
    'vendor/nv.d3.js',
    'vendor/trip.js',
    'vendor/chardinjs.js',
    'vendor/vue-croppa.min.js',
    'js/djaodjin-upload.js',
    'js/djaodjin-dashboard.js',
    'js/djaodjin-signup-vue.js',
    'js/djaodjin-saas-vue.js',
    'js/djaodjin-rules-vue.js',
    'js/djaodjin-metrics.js',
    filters='jsmin', output='cache/djaodjin-vue.js')
register('js_djaodjin_vue', js_djaodjin_vue)

# Used in docs/api.html
js_dashboard = Bundle(
    'js/djaodjin-dashboard.js',
    filters='jsmin', output='cache/djaodjin-dashboard.js')
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
