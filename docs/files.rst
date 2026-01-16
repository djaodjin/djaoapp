Find your way around the code base
==================================

DjaoApp integrates a few Django applications into a coherent whole to
provide the Accounts, Billing and Access Control features every SaaS needs.

- `djaodjin-signup`_ for authentication pages and APIs
- `djaodjin-saas`_ for subscription-based payment pages and APIs
- `djaodjin-rules`_ for role-based access control and HTTP request forwarding
- `djaodjin-deployutils`_ for encoding/decoding sessions

Additionally, DjaoApp integrates `djaodjin-extended-templates`_ for live
editing of theme templates.

Apart from some glue code, you will find most of the functionality into
one of the preceding repository mentionned.

This repository contains primarily the `default theme`_ templates and styles
files.

SCSS files
----------

The default theme style is built on `Boostrap`_ with custom modifications.

You can find the ``.scss`` source files in the
`djaoapp/static/scss <https://github.com/djaodjin/djaoapp/djaoapp/static/scss>`_
directory. The files under the ``vendor`` subdirectory come from third-parties
(ex: Bootstrap) and are present in this repository purely for convienience, with
slight patches as necessary.

The default theme is using four CSS files
- `base.css <https://github.com/djaodjin/djaoapp/djaoapp/static/scss/base/base.scss>`_ is the primary stylesheet for the Website.
- `dashboard.css <https://github.com/djaodjin/djaoapp/djaoapp/static/scss/dashboard/dashboard.scss>`_ adds classes for charts and onboarding help tooltips that are present on dashboard pages. The public workflow pages do not have charts nor onboarding help tooltips.
- `email.css <https://github.com/djaodjin/djaoapp/djaoapp/static/scss/email/email.scss>`_ contains styles for e-mail notifications.
- `pages.css <https://github.com/djaodjin/djaoapp/djaoapp/static/scss/pages/pages.scss>`_ contains styles for the live editing tools.


Template files
--------------

Templates are written for the `Jinja2 template engine`_ rather than Django
template engine. We made that choice because Jinja2 templates can be served
by multiple backend technologies.

All templates are located in `djaoapp/templates <https://github.com/djaodjin/djaoapp/djaoapp/templates>`_.

Naming convention
^^^^^^^^^^^^^^^^^

Each template for a page URL is named such that it is either:
- the last part of the URL path suffixed by ``.html``
- ``index.html`` in a directory matching the last part of the URL path
- the name of the ``slug`` variable suffixed by ``.html`` for URL path ending
with a regex pattern.

Examples:

.. code::

    URL path /metrics/djaoapp/dashboard/ maps to saas/metrics/dashboard.html
    URL path /profile/djaoapp/plans/ maps to saas/profile/plans/index.html
    URL path /profile/djaoapp/roles/manager/ maps to saas/profile/roles/role.html


Templates that are intended for scaffolding have ``base`` in their name
(ex: ``base_dashboard.html``).

Templates that represent snipset of HTML code included (using ``{% include %}``)
in various places without fitting nicely in the template hierarchy starts with
an underscore character (ex: ``_pagination.html``).


Dashboard pages
^^^^^^^^^^^^^^^

`Dashboard pages <https://www.djaodjin.com/docs/guides/themes/#dashboards>`_
are used by subscribers to update their profile and billing information
as well as manage their subscriptions. Dashboard pages are also used by
providers to support subscribers and assess the performance of the business.

Dashboard pages extends one of the following base.html templates.

* base.html

  * saas/base.html

    * saas/base_dashboard.html

      * contacts/base.html

      * saas/metrics/base.html

      * users/base.html

Templates mapped to UI paths through the sidebar menus:

+----------------------------------------+-------------------------------------+
| UI Path                                | Template name                       |
+========================================+=====================================+
| Profile                                | saas/profile/index.html             |
+----------------------------------------+-------------------------------------+
| Profile > Change Password              | users/password.html                 |
+----------------------------------------+-------------------------------------+
| Profile > Rotate Keys                  | users/pubkey.html                   |
+----------------------------------------+-------------------------------------+
| Connected profiles                     | saas/users/roles.html               |
+----------------------------------------+-------------------------------------+
| Profile managers                       | saas/profile/roles/role.html        |
+----------------------------------------+-------------------------------------+
| **unaccessible**  (TODO: All roles)    | saas/profile/roles/index.html       |
+----------------------------------------+-------------------------------------+
| Notifications                          | users/notifications.html            |
+----------------------------------------+-------------------------------------+
| Subscriptions                          | saas/profile/subscriptions.html     |
+----------------------------------------+-------------------------------------+
| Billing                                | saas/billing/index.html             |
+----------------------------------------+-------------------------------------+
| Billing > Credit Card Update           | saas/billing/card.html              |
+----------------------------------------+-------------------------------------+
|                                        |                                     |
| Billing > Transaction Charge           | | saas/billing/receipt.html         |
|                                        | | saas/printable_charge_receipt.html|
|                                        |                                     |
+----------------------------------------+-------------------------------------+
| Dashboard                              | saas/metrics/dashboard.html         |
+----------------------------------------+-------------------------------------+
| Dashboard > Engagement details         | rules/engagement.html               |
+----------------------------------------+-------------------------------------+
| Dashboard                              | contacts/index.html                 |
| > Engagement details                   |                                     |
| > Contacts                             |                                     |
+----------------------------------------+-------------------------------------+
| Dashboard                              | contacts/contact.html               |
| > Engagement details                   |                                     |
| > Contacts                             |                                     |
| > Contact Details                      |                                     |
+----------------------------------------+-------------------------------------+
| Reports                                | saas/metrics/revenue.html           |
+----------------------------------------+-------------------------------------+
| Reports > Balances > Balance Sheet     | saas/metrics/balances.html          |
+----------------------------------------+-------------------------------------+
| Reports > Customers > Lifetime value   | saas/metrics/lifetimevalue.html     |
+----------------------------------------+-------------------------------------+
| Subscribers                            | saas/profile/subscribers.html       |
+----------------------------------------+-------------------------------------+
| Subscribers > Subscribers activity     | saas/metrics/activity.html          |
+----------------------------------------+-------------------------------------+
| Plans                                  | saas/profile/plans/index.html       |
+----------------------------------------+-------------------------------------+
| Plans > Plan Table                     | saas/profile/plans/plan.html        |
+----------------------------------------+-------------------------------------+
| Plans > Plan Table > Subscribers       | saas/profile/plans/subscribers.html |
+----------------------------------------+-------------------------------------+
| Coupons                                | saas/billing/coupons.html           |
+----------------------------------------+-------------------------------------+
| Coupons > Coupons Table                | saas/metrics/coupons.html           |
+----------------------------------------+-------------------------------------+
| Funds                                  | saas/billing/transfers.html         |
+----------------------------------------+-------------------------------------+
| Funds > Deposit Information            | saas/billing/bank.html              |
+----------------------------------------+-------------------------------------+
| Funds > Add Transaction                | saas/billing/import.html            |
+----------------------------------------+-------------------------------------+
| Funds > Raw Transactions Ledger        | saas/billing/transactions.html      |
+----------------------------------------+-------------------------------------+
| Funds > Charges                        | saas/billing/charges.html           |
+----------------------------------------+-------------------------------------+
| Theme                                  | extended_templates/theme.html       |
+----------------------------------------+-------------------------------------+
| Theme  > Notification Table            | notification/detail.html            |
+----------------------------------------+-------------------------------------+
| Rules                                  | rules/app_dashboard.html            |
+----------------------------------------+-------------------------------------+


Workflow pages
^^^^^^^^^^^^^^

The `workflow pages <https://www.djaodjin.com/docs/guides/themes/#workflows>`_
include all the classic pages you can expect to find browsing the website of
a Software-as-Service product as a visitor, or onboarding as a user.

Workflow pages extends one of the following base.html templates.

* base.html

  * login/base.html

  * saas/base.html

    * saas/legal/base.html

Templates mapped to click-through paths (Workflows) through the onboarding
pages:

+------------------------------------+----------------------------------------+
| UI Path                            | Template name                          |
+====================================+========================================+
| Homepage                           | index.html                             |
+------------------------------------+----------------------------------------+
| Contact us                         | contact.html                           |
+------------------------------------+----------------------------------------+
| Disabled login & register          | login/disabled.html                    |
+------------------------------------+----------------------------------------+
| Sign in & Sign up                  | | login/index.html                     |
|                                    | | login/verification_key.html          |
|                                    | | login/frictionless.html              |
|                                    | | login/personal.html                  |
+------------------------------------+----------------------------------------+
| Legal agreements                   | | saas/legal/index.html                |
|                                    | | saas/legal/agreement.html            |
+------------------------------------+----------------------------------------+
| Sign legal agreement               | saas/legal/sign.html                   |
+------------------------------------+----------------------------------------+
| Pricing                            | saas/pricing.html                      |
+------------------------------------+----------------------------------------+
| Redeem                             | saas/redeem.html                       |
+------------------------------------+----------------------------------------+
| Checkout                           | | saas/billing/cart.html               |
|                                    | | saas/billing/balance.html            |
|                                    | | saas/billing/cart-periods.html       |
|                                    | | saas/billing/cart-seats.html         |
+------------------------------------+----------------------------------------+
| Charge Receipt                     | saas/printable_charge_receipt.html     |
+------------------------------------+----------------------------------------+
| Select profile                     | | saas/organization_redirects.html     |
|                                    | | saas/profile/new.html                |
+------------------------------------+----------------------------------------+
| Default App                        | | app.html                             |
|                                    | | app_proxy_help.html                  |
|                                    | | rules/forward_error.html             |
|                                    | | rules/forward_error_manager_help.html|
+------------------------------------+----------------------------------------+
| Errors                             | | 400.html                             |
|                                    | | 403.html                             |
|                                    | | 404.html                             |
|                                    | | 500.html                             |
+------------------------------------+----------------------------------------+


Partial templates
^^^^^^^^^^^^^^^^^

The following partial templates are used to produce the top navbar:
* ``_generic_navbar.html`` contains the static menus / links shown in the top
navbar (ex: Blog, Pricing, Help).
* ``_menubar.html`` contains the dynamic menu dropdown for authenticated user.

The macros to display standard form input fields are defined
in ``jinja2/_form_fields.html``.

``saas/_filter.html`` contains the snipset to add a text match, start date,
and end date to filter lists. ``_pagination.html`` contains the code to show
pagination controls when there are more than one page of results.

``saas/_organization_card.html`` and ``saas/_user_card.html`` are used to embed
references to profiles and users, typically in roles and connected profiles
pages.

``users/_require_password.html`` contains the snipset to ask again
an authenticated user for her password before making a sensitive change
(ex: Update password, Rotate API keys).

``jinja2/saas/_card_use.html`` implements the input form fields to gather
credit card information. If you update this file, be carefull to not add
a ``name`` attribute to ``<input>`` elements, else values will hit the server
and you might break `PCI compliance <https://en.wikipedia.org/wiki/Payment_Card_Industry_Data_Security_Standard>`_ as a result.

``saas/_body_top_template.html`` is injected in the pages where payment
processor keys (ex: Stripe) are expected but none are present. If you see
the messages defined in ``saas/_body_top_template.html``, it is most likely
that the `payment processor backend <https://djaodjin-saas.readthedocs.io/en/latest/backends.html>`_
is not configured correctly.


.. _djaodjin-signup: https://github.com/djaodjin/djaodjin-signup/

.. _djaodjin-saas: https://github.com/djaodjin/djaodjin-saas/

.. _djaodjin-rules: https://github.com/djaodjin/djaodjin-rules/

.. _djaodjin-deployutils: https://github.com/djaodjin/djaodjin-deployutils/

.. _djaodjin-extended-templates: https://github.com/djaodjin/extended-templates/

.. _default theme: https://www.djaodjin.com/docs/guides/themes/

.. _Boostrap: https://getbootstrap.com/

.. _Jinja2 template engine: https://jinja.palletsprojects.com/
