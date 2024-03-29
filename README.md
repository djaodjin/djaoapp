DjaoDjin subscriber session proxy
=================================

[![Documentation Status](https://readthedocs.org/projects/djaoapp/badge/?version=latest)](https://djaoapp.readthedocs.io/en/latest/?badge=latest)

DjaoApp brings fully-featured profile, billing and role-based access control
pages so you can start building your SaaS product faster.
To learn more visit [DjaoDjin's Website](https://www.djaodjin.com/) or browse
the project documentation on [Read-the-Docs](https://djaoapp.readthedocs.org/).

DjaoApp is built on
[Django](https://www.djangoproject.com/),
[Vue.js](https://vuejs.org/), [Bootstrap](https://getbootstrap.com/)
frameworks and many more Open Source projects. Thank you for the support!

<p align="center">
<img src="https://static.djangoproject.com/img/logos/django-logo-positive.png" height="75">
<img src="https://vuejs.org/images/logo.png" height="75">
<img src="https://getbootstrap.com/docs/4.3/assets/brand/bootstrap-solid.svg" height="75">
</p>

If you are looking to update the client front-end, you can browse through
the [API documentation](https://www.djaodjin.com/docs/reference/djaoapp/latest/api/)
and [theme templates documentation](https://www.djaodjin.com/docs/guides/themes/).

If you are looking to add features, this project integrates
- [djaodjin-signup](https://github.com/djaodjin/djaodjin-signup/) for authentication pages and APIs
- [djaodjin-saas](https://github.com/djaodjin/djaodjin-saas/) for subscription-based payment pages and APIs
- [djaodjin-rules](https://github.com/djaodjin/djaodjin-rules/) for role-based access control and HTTP request forwarding
- [djaodjin-deployutils](https://github.com/djaodjin/djaodjin-deployutils/) for encoding/decoding sessions
- [djaodjin-extended-templates](https://github.com/djaodjin/djaodjin-extended-templates/) for live editing of theme templates

Tested with

- **Python:** 3.10, **Django:** 3.2 ([LTS](https://www.djangoproject.com/download/))

Install
-------

First you will need to create a workspace environment, download the 3rd party
vendor prerequisite packages and build the static assets.

DjaoApp transitively depends on multiple native libraries that could or could
not be straightforward to install on your Operating System. If you have trouble
with the `pip install -r requirements-native.txt` command, take a look at
[installation quirks](https://djaoapp.readthedocs.io/en/latest/quirks.html)
in the documentation.

<pre><code>
    $ python -m venv <em>installTop</em>
    $ source <em>installTop</em>/bin/activate
    $ pip install -r requirements-native.txt
    $ pip install -r requirements.txt
    $ make vendor-assets-prerequisites
    $ make install-conf
    $ make build-assets
</code></pre>

At this point, all the 3rd party vendor prerequisite packages (Python and
Javascript) have been downloaded and installed in the environment. You now
need to add your STRIPE keys to the configuration file (i.e.
*installTop*/etc/djaoapp/credentials).

<pre><code>
    $ diff -u <em>installTop</em>/etc/djaoapp/credentials
    # Authentication with payment provider
    -STRIPE_CLIENT_ID = ""
    -STRIPE_PUB_KEY = ""
    -STRIPE_PRIV_KEY = ""
    +STRIPE_CLIENT_ID = "<em>your-stripe-client-id</em>"
    +STRIPE_PUB_KEY = "<em>your-stripe-production-public-key</em>"
    +STRIPE_PRIV_KEY = "<em>your-stripe-production-private-key</em>"

    # Authentication with payment provider (test keys)
    -STRIPE_TEST_CLIENT_ID = ""
    -STRIPE_TEST_PUB_KEY = ""
    -STRIPE_TEST_PRIV_KEY = ""
    +STRIPE_TEST_CLIENT_ID = "<em>your-stripe-client-id</em>"
    +STRIPE_TEST_PUB_KEY = "<em>your-stripe-test-public-key</em>"
    +STRIPE_TEST_PRIV_KEY = "<em>your-stripe-test-private-key</em>"
</code></pre>


Then create the database, and start the built-in webserver

    $ python manage.py migrate --run-syncdb
    $ python manage.py createsuperuser
    $ python manage.py runserver


Development
-----------

You will want to toggle `DEBUG` on in the site.conf file.

<pre><code>
    $ diff -u <em>installTop</em>/etc/djaoapp/site.conf
    -DEBUG = False
    +DEBUG = True

    # Create the tests databases and load test datasets.
    $ make initdb

    # To generate some sample data, disable emailing of receipts and run:
    $ python manage.py load_test_transactions

    # Spins up a dev server that re-compiles the `.css` files
    # on page reload whenever necessary.
    $ python manage.py runserver --nostatic
</code></pre>


Templates Search Path
---------------------

When a ``rules.App`` exists, templates will be first searched for in
templates/*project_name*, then in templates/*project_repo*, then
the default will be used.

All CSS present in the default templates must be declared which ever
base.html is included.


Release Notes
=============

- Sep 6th 2023
  Support on Python2 was officially ended on Jan 1st 2020. As of Sep 6th 2023,
  we no longer test this project for compatibillity with Py2.7.

See [release notes](https://www.djaodjin.com/docs/reference/djaoapp/releases/) and [roadmap](https://www.djaodjin.com/docs/reference/roadmap/).
