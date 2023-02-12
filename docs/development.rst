Working with the code base
===========================

CSS
---

The css files are built through saasc.

To rebuild the css files run the following make command:

.. code-block:: shell

    make build-assets

As it is inconvienient to edit/build/reload every time you make a change,
the ``AssetView`` class is used to detect changes and rebuild
``/static/cache/base.css`` as necessary on page load.
For that you need to make sure ``DEBUG`` is ``True`` and the ``--nostatic``
flag is passed to the runserver command line.

.. code-block:: shell

    DEBUG=1 python manage.py runserver --nostatic


So make your .sccs updates and reload the page!


HTML templates
--------------

The website is built as a Multi-Page Application (MPA). As much as possible
the template filenames follow the URL on which the template is used.
For example: you can find the template for ``/profile/{profile}/subscriptions/``
in ``djaoapp/templates/saas/profile/subscriptions.html``.
More details on the content of each page is available in the [default theme documentation](https://www.djaodjin.com/docs/guides/themes/).

Django reads and re-compiles the template on page load.

So make your .html template updates and reload the page!


Javascript
----------

Because the site is using a Multi-Page Application (MPA) architecture, there
are no complex business logic and/or dependency logic in the Javascript code.
The order of the ``<script>`` HTML elements in the templates is pretty
straightforward.

Most developers will work with a very recent browser with the latest
EcmaScript features available. So in DEBUG mode, all we really want to
do is to be able to inclde the .js files through ``<script>`` HTML
elements in one of the ``base.html`` template.

Because we want to be able to work when no Internet connection is available,
we serve local copies of 3rd party vendor scripts in development mode.
The static assets are served by Django so they must be found through
the ``STATICFILES_FINDERS`` settings. The following make target insures that.

.. code-block:: shell

    make vendor-assets-prerequisites


Then make your .js updates and reload the page!


To support production mode (i.e. ``DEBUG=False``), we would like:

1. 3rd party vendor scripts loaded through the official CDN whenever possible
   to take advantage of browser caching.
2. Transpile and optimize the Vue components native to the website so they
   work on target browsers.

That is why we use a Universal Module Definition (UMD)] format as a wrapper
and specific webpack plugins (Technically we only need to append to an
``exports`` variable it is exists).

Typically npm, webpack and other Javascript tools will install and expect
a node_modules directory in your source tree. That is just ugly, bloats
your backups and really cramp your style when you are working with command
line tools such as ``grep``. Furthermore we have .js files present in
static directories of Django app installed in the virtual env ``site-packages``
directory that must be imported.

The ``generate_webpack_paths`` Django command creates a
``webpack-conf-paths.json`` file that contains the same search path
as set in ``settings.STATICFILES_FINDERS`` (followed by
``VIRTUAL_ENV/lib/node_modules/`` for vendor modules). That
webpack-conf-paths.json file is then loaded in ``webpack.config.js``
to set the modules search path for webpack.

To compile .js production asset files run the following make command:

.. code-block:: shell

    make build-assets


Python/Django
-------------

Updating the Python code and debugging changes works as expected. You will
notice that the website code base itself contains very little Python code
itself - mostly to tie the major Django apps together.

- `djaodjin-signup`_ for authentication pages and APIs
- `djaodjin-saas`_ for subscription-based payment pages and APIs
- `djaodjin-rules`_ for role-based access control and HTTP request forwarding
- `djaodjin-deployutils`_ for encoding/decoding sessions
- `djaodjin-extended-templates`_ for live editing of theme templates

Translation
-----------

Whenever possible translated strings should be written in the HTML templates
within ``{% trans %}{% endtrans %}`` markers.

We initially `generated translation units for the Vue components <https://www.djaodjin.com/blog/integrating-django-i18-with-jinja2-and-vuejs.blog>`_
but it had many drawbacks:

1. It required to load a djaoapp-i18n.js file at runtime.

2. It required to re-bundle the assets to fix a typo.

3. Translation strings were in two separate ``.po`` files (one for the Python/HTML templates and one for the Javascript).

Since then we made it a policy that there should not be any translation
strings within the .js files. If it is necessary to pass translatable text
to a component, do so through a component configuration variable and
initialize that component with the default text value in the HTML template.

To add another language, generate a new translation unit with the following
command:

.. code-block:: shell

    python manage.py makemessages -l {locale_name}


Edit the generated djaoapp/locale/{locale_name}/LC_MESSAGES/django.po file with
appropriate translations. Then compile the messages into a ``.mo`` file.

.. code-block:: shell

    python manage.py compilemessages



Generating API Documentation
----------------------------

Run the the server using the following command, the browse
http://localhost:8000/docs/api/

.. code-block:: shell

    DEBUG=0 API_DEBUG=1 python manage.py runserver

The ``APIDocView`` view will spit out warning and error messages whenever
examples provided do not match the API definition.

When the API reference documentation looks reasonnably well, generate
an OpenAPI schema.

.. code-block:: shell

    make generateschema


Building the Docker container
-----------------------------

Run the following command

.. code-block:: shell

    make package-docker


.. _djaodjin-signup: https://github.com/djaodjin/djaodjin-signup/

.. _djaodjin-saas: https://github.com/djaodjin/djaodjin-saas/

.. _djaodjin-rules: https://github.com/djaodjin/djaodjin-rules/

.. _djaodjin-deployutils: https://github.com/djaodjin/djaodjin-deployutils/

.. _djaodjin-extended-templates: https://github.com/djaodjin/extended-templates/
