DjaoDjin website
================

This Django project contains the code for the reverse proxy serving
sites on djaoapp.com.

Templates Search Path
---------------------

When a ``rules.App`` exists, templates will be first searched for in
templates/*project_name*, then in templates/*project_repo*, then
the default will be used.

All CSS present in the default templates must be declared which ever
base.html is included.

Install
-------

    $ virtualenv _installTop_
    $ source _installTop_/bin/activate

    $ mkdir -p  _installTop_/reps
    $ cd _installTop_/reps
    $ git clone https://github.com/djaodjin/djaoapp.git
    $ cd djaoapp
    $ pip install -r requirements.txt
    $ make install-conf
    $ make vendor-assets-prerequisites
    $ DEBUG=1 python manage.py assets build

    $ make initdb

Testing
-------

    # To generate some sample data, disable emailing of receipts and run:
    $ python manage.py load_test_transactions

    $ python manage.py runserver
    # Browse to http://localhost:8000/

Information about specific tests is in the fixtures/DESCRIPTION file.


Running in DEBUG mode
---------------------

    $ diff -u `_installTop_/etc/djaoapp/site.conf`
    -DEBUG = False
    +DEBUG = True
