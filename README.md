DjaoDjin subscriber session proxy
=================================

This Django project contains the code for DjaoDjin subscription-based session
manager. To learn more visit [DjaoDjin's Website](https://djaodjin.com/).

It integrates
- [djaodjin-signup](https://github.com/djaodjin/djaodjin-signup/) for authentication pages and APIs
- [djaodjin-saas](https://github.com/djaodjin/djaodjin-saas/) for subscription-based payment pages and APIs
- [djaodjin-rules](https://github.com/djaodjin/djaodjin-rules/) for role-based access control and HTTP request forwarding
- [djaodjin-pages](https://github.com/djaodjin/djaodjin-pages/) for live editingof self-hosted HTML pages

Tested with

- **Python:** 2.7, **Django:** 1.11.20 ([LTS](https://www.djangoproject.com/download/)), **Django Rest Framework:** 3.8.2
- **Python:** 3.6, **Django:** 1.11.20 ([LTS](https://www.djangoproject.com/download/)), **Django Rest Framework:** 3.8.2
- **Python:** 3.6, **Django:** 2.1.7 (latest),       **Django Rest Framework:** 3.8.2

Install
-------

First you will need to create a workspace environment, downlaod the 3rd party
vendor prerequisite packages and build the static assets.

    $ virtualenv *`installTop`*
    $ source *`installTop`*/bin/activate

    $ mkdir -p  *`installTop`*/reps
    $ cd *`installTop`*/reps
    $ git clone https://github.com/djaodjin/djaoapp.git
    $ cd djaoapp
    $ make install-conf
    $ pip install -r requirements.txt
    $ make build-assets

At this point, all the 3rd party vendor prerequisite packages (Python and
Javascript) have been downloaded and installed in the environment. You now
need to add your STRIPE keys to the configuration file (i.e.
*installTop*/etc/djaoapp/credentials).

    $ diff -u *installTop*/etc/djaoapp/credentials
    # Authentication with payment provider
    -STRIPE_CLIENT_ID = ""
    -STRIPE_PUB_KEY = ""
    -STRIPE_PRIV_KEY = ""
    +STRIPE_CLIENT_ID = "*`your-stripe-client-id`*"
    +STRIPE_PUB_KEY = "*`your-stripe-production-public-key`*"
    +STRIPE_PRIV_KEY = "*`your-stripe-production-private-key`*"

    # Authentication with payment provider (test keys)
    -STRIPE_TEST_CLIENT_ID = ""
    -STRIPE_TEST_PUB_KEY = ""
    -STRIPE_TEST_PRIV_KEY = ""
    +STRIPE_TEST_CLIENT_ID = "*`your-stripe-client-id`*"
    +STRIPE_TEST_PUB_KEY = "*`your-stripe-test-public-key`*"
    +STRIPE_TEST_PRIV_KEY = "*`your-stripe-test-private-key`*"

Then create the database, and start the built-in webserver

    $ python manage.py migrate --run-syncdb
    $ python manage.py createsuperuser
    $ python manage.py runserver


Development
-----------

    You will want to toggle `DEBUG` on in the site.conf file.

    $ diff -u *`installTop`*/etc/djaoapp/site.conf
    -DEBUG = False
    +DEBUG = True

    # Create the tests databases and load test datasets.
    $ make initdb

    # To generate some sample data, disable emailing of receipts and run:
    $ python manage.py load_test_transactions


Templates Search Path
---------------------

When a ``rules.App`` exists, templates will be first searched for in
templates/*project_name*, then in templates/*project_repo*, then
the default will be used.

All CSS present in the default templates must be declared which ever
base.html is included.
