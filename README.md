DjaoDjin subscriber session proxy
=================================

This repository contains the code for DjaoDjin subscriber session proxy.
It is a core part of the infrastructure that makes it possible to bring
fully-featured SaaS products to production faster. To learn more visit
[DjaoDjin's Website](https://djaodjin.com/).

The session proxy is built on [Django](https://www.djangoproject.com/),
[Vue.js](https://vuejs.org/), [Bootstrap 4](https://getbootstrap.com/)
frameworks and many more Open Source projects. Thank you for the support!

<p align="center">
<img src="https://static.djangoproject.com/img/logos/django-logo-positive.png" height="75">
<img src="https://vuejs.org/images/logo.png" height="75">
<img src="https://getbootstrap.com/docs/4.3/assets/brand/bootstrap-solid.svg" height="75">
</p>

If you are looking to update the client front-end, you can browse through
the [API documentation](https://djaodjin.com/docs/djaoapp-api/) and
[theme templates documentation](https://djaodjin.com/docs/themes/#default-theme).

If you are looking to add features, this project integrates
- [djaodjin-signup](https://github.com/djaodjin/djaodjin-signup/) for authentication pages and APIs
- [djaodjin-saas](https://github.com/djaodjin/djaodjin-saas/) for subscription-based payment pages and APIs
- [djaodjin-rules](https://github.com/djaodjin/djaodjin-rules/) for role-based access control and HTTP request forwarding
- [djaodjin-pages](https://github.com/djaodjin/djaodjin-pages/) for live editingof self-hosted HTML pages

Tested with

- **Python:** 3.6, **Django:** 1.11.23 ([LTS](https://www.djangoproject.com/download/)), **Django Rest Framework:** 3.10
- **Python:** 3.6, **Django:** 2.2.4 (latest),       **Django Rest Framework:** 3.10
- **Python:** 2.7, **Django:** 1.11.23 ([LTS](https://www.djangoproject.com/download/)), **Django Rest Framework:** 3.9.4
(*Note Python2 end of life is scheduled for Jan 1st 2020. All production
features are still supported until then. Development features are partially
supported, notably the API docs generator is not, due to newer versions
of prerequisites having deprecated Python2 support earlier than 2020. Please
use `requirements-legacy.txt` instead of `requirements.txt` to install
Python2 prerequisites.*)

Install
-------

First you will need to create a workspace environment, download the 3rd party
vendor prerequisite packages and build the static assets.

<pre><code>
    $ virtualenv <em>installTop</em>
    $ source <em>installTop</em>/bin/activate
    $ pip install -r requirements.txt
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
</code></pre>


Templates Search Path
---------------------

When a ``rules.App`` exists, templates will be first searched for in
templates/*project_name*, then in templates/*project_repo*, then
the default will be used.

All CSS present in the default templates must be declared which ever
base.html is included.
