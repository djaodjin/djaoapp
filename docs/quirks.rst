Installation Quirks
===================

cairo and pango
---------------

`djaodjin-extended-templates <https://github.com/djaodjin/djaodjin-extended-templates/>`_
requires `WeasyPrint <https://github.com/Kozea/WeasyPrint/>`_
to print PDF of charge receipts from an HTML template.

As a result both cairo and pango must be present on the Operating System.

Debian-based distributions:

    $ apt-get install libcairo2 libpangoft2-1.0-0

Note that the djaoapp Docker image is based on an official Python Docker image,
which in turn is based on a Debian Docker image. As a result, you can find
the exact commands to install on a Debian-based distribution in the
`Dockerfile <https://github.com/djaodjin/djaoapp/Dockerfile>`_.


RedHat-based distributions:

    $ yum install cairo pango
    $ pango-view --version
    pango-view (pango) 1.42.3

Amazon Linux 2 (as of 2023-08-21) comes with pango 1.42 while
`WeasyPrint 53 requires at least Pango 1.44 <https://github.com/Kozea/WeasyPrint/issues/1384>`_.
That is the main reason why weasyprint is pinned to version 52.5.

Mac OSX:

    $ brew install python3 cairo pango

You will want to use the python3 install from brew as `recommended on StackOverflow <https://stackoverflow.com/a/69295303/1491475>`_
to avoid going down a rabit hole.


xmlsec1 and openldap
--------------------

`djaodjin-signup <https://github.com/djaodjin/djaodjin-signup/>`_
requires transitively xmlsec1 and openldap native libraries to implement
SAML and LDAP identification respectively.

The SAML implementation depends on ``python-saml`` which transitively depends
on ``xmlsec1`` native libraries through ``xmlsec`` bindings. ``xmlsec1`` itself
depends on ``openssl``.

On some distributions (ex: AWS Linux 2), the ``xmlsec1`` rpm package is built
against OpenSSL 1.0 and thus depends on ``openssl``. Python3.11 is built
against OpenSSL 1.1 (minimum). ``openssl11`` is available on AWS Linux 2
but there is conflict when you try to install both ``openssl`` and
``openssl11``.

Installing xmlsec1 (here ``xmlsec1-1.3.0.tar.gz``) from source is a bit tricky.
Somehow it requires ``libgcrypt`` on the system we run tests with. That required
to install both ``libgpg-error`` and ``libgcrypt`` from source. Looking through
``libgcrypt`` rpm spec file we can find the following comment:

    # The original libgcrypt sources now contain potentially patented ECC

Installing ``python-xmlsec`` when ``xmlsec1`` was compiled from source
and installed in ``/usr/local``can be tricky. Typically it requires to
export ``PKG_CONFIG_PATH`` to the shell environment beforehand as in:

    export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig

The LDAP authentication backend requires ``python-ldap`` which transitively
depends on `openldap native libraries <https://www.python-ldap.org/en/python-ldap-3.4.3/installing.html#build-prerequisites>`_.


libxml2 libxslt1.1
------------------



There is a thorough analysis of native dependencies in `PR207 <https://github.com/djaodjin/djaoapp/pull/207>`_.

