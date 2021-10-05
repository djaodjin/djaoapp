# Copyright (c) 2018, DjaoDjin inc.
# see LICENSE

-include $(buildTop)/share/dws/prefix.mk

srcDir        ?= .
installTop    ?= $(VIRTUAL_ENV)
binDir        ?= $(installTop)/bin
SYSCONFDIR    := $(installTop)/etc
LOCALSTATEDIR := $(installTop)/var
CONFIG_DIR    := $(SYSCONFDIR)/djaoapp
ASSETS_DIR    := $(srcDir)/htdocs/static

installDirs   ?= /usr/bin/install -d
installFiles  ?= /usr/bin/install -p -m 644
NPM           ?= npm
PIP           := $(binDir)/pip
PYTHON        := $(binDir)/python
SASSC         := $(binDir)/sassc
SQLITE        ?= sqlite3
WEBPACK       ?= $(installTop)/node_modules/.bin/webpack

# Django 1.7,1.8 sync tables without migrations by default while Django 1.9
# requires a --run-syncdb argument.
# Implementation Note: We have to wait for the config files to be installed
# before running the manage.py command (else missing SECRECT_KEY).
RUNSYNCDB     = $(if $(findstring --run-syncdb,$(shell cd $(srcDir) && DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) manage.py migrate --help 2>/dev/null)),--run-syncdb,)

APP_NAME      ?= djaoapp
APP_PORT      ?= 8000

WEBPACK_MODE  ?= production
ifneq ($(WEBPACK_MODE),production)
WEBPACK := $(installTop)/node_modules/.bin/webpack-dev-server
endif

ifneq ($(wildcard $(CONFIG_DIR)/site.conf),)
# `make initdb` will install site.conf but only after `grep` is run
# and DB_FILNAME set to "". We use the default value in the template site.conf
# here to prevent that issue.
DB_FILENAME   := $(shell grep ^DB_NAME $(CONFIG_DIR)/site.conf | cut -f 2 -d '"')
else
DB_FILENAME   := $(srcDir)/db.sqlite
endif
MULTITIER_DB_FILENAME := $(dir $(DB_FILENAME))cowork.sqlite

MULTITIER_DB_NAME ?= $(if $(wildcard $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/site.conf),$(shell grep ^DB_NAME $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/site.conf | cut -f 2 -d '"'),$(dir $(DB_FILENAME))$(subst migratedb-,,$@).sqlite)

MY_EMAIL          ?= $(shell cd $(srcDir) && git config user.email)
EMAIL_FIXTURE_OPT := $(if $(MY_EMAIL),--email="$(MY_EMAIL)",)

all:
	@echo "Nothing to be done for 'make'."

clean: clean-dbs clean-themes
	[ ! -f $(srcDir)/package-lock.json ] || rm $(srcDir)/package-lock.json
	find $(srcDir) -name '__pycache__' -exec rm -rf {} +
	find $(srcDir) -name '*~' -exec rm -rf {} +

clean-dbs:
	[ ! -f $(DB_FILENAME) ] || rm $(DB_FILENAME)
	[ ! -f $(MULTITIER_DB_FILENAME) ] || rm $(MULTITIER_DB_FILENAME)

clean-themes:
	rm -rf $(srcDir)/themes/* $(srcDir)/htdocs/themes/*

install:: install-conf

doc:
	$(installDirs) build/docs
	cd $(srcDir) && sphinx-build -b html ./docs $(PWD)/build/docs

# We use rsync here so that make initdb can be run with user "nginx"
# after files were installed with user "fedora".
install-default-themes:: clean-themes


# download and install prerequisites then create the db.
require: require-pip require-resources initdb


# We add a `load_test_transactions` because the command will set the current
# site and thus need the rules.App table.
initdb: install-default-themes initdb-djaoapp initdb-cowork
	-[ -f $(dir $(DB_FILENAME))my-streetside.sqlite ] && rm -f $(dir $(DB_FILENAME))my-streetside.sqlite
	cd $(srcDir) && \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) djaoapp/fixtures/default-db.json djaoapp/fixtures/djaoapp-roles-card1.json djaoapp/fixtures/100-balance-due.json djaoapp/fixtures/110-balance-checkout.json
	@echo "-- Set streetside processor deposit key."
	$(SQLITE) $(DB_FILENAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_PRIV_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where slug='djaoapp';"
	$(SQLITE) $(DB_FILENAME) "UPDATE rules_app set show_edit_tools=1;"

initdb-cowork:
	-[ -f $(MULTITIER_DB_FILENAME) ] && rm -f $(MULTITIER_DB_FILENAME)
	cd $(srcDir) && MULTITIER_DB_NAME=$(MULTITIER_DB_FILENAME) \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py migrate \
		$(RUNSYNCDB) --database cowork --noinput
	cat $(srcDir)/djaoapp/migrations/adjustments1-sqlite3.sql | $(SQLITE) $(MULTITIER_DB_FILENAME)
	cd $(srcDir) && MULTITIER_DB_NAME=$(MULTITIER_DB_FILENAME) \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) --database cowork djaoapp/fixtures/cowork-db.json
	cat $(srcDir)/djaoapp/migrations/adjustments2-sqlite3.sql | $(SQLITE) $(MULTITIER_DB_FILENAME)


initdb-djaoapp:
	-[ -f $(DB_FILENAME) ] && rm -f $(DB_FILENAME)
	cd $(srcDir) && \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py migrate $(RUNSYNCDB) --noinput --fake-initial
	cat $(srcDir)/djaoapp/migrations/adjustments1-sqlite3.sql | $(SQLITE) $(DB_FILENAME)
	cat $(srcDir)/djaoapp/migrations/adjustments2-sqlite3.sql | $(SQLITE) $(DB_FILENAME)


makemessages:
	cd $(srcDir) && $(PYTHON) manage.py makemessages -l fr -l es -l pt --symlinks --no-wrap
	cd $(srcDir) && $(PYTHON) manage.py makemessages -d djangojs -l fr -l es -l pt --symlinks --no-wrap


generateschema:
	cd $(srcDir) && $(PYTHON) manage.py generateschema --url http://cowork.djaoapp.com > schema.yml
	cd $(srcDir) && swagger-cli validate schema.yml


migratedb-cowork: initdb-cowork
	@echo "-- Set streetside processor deposit key."
	$(SQLITE) $(call MULTITIER_DB_NAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_CONNECTED_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where is_provider=1;"


# Add necessary tables in an already existing database, then load information
migratedb-%:
	cd $(srcDir) && MULTITIER_DB_NAME=$(call MULTITIER_DB_NAME) \
		$(PYTHON) ./manage.py migrate $(RUNSYNCDB) --database $(basename $(notdir $(MULTITIER_DB_NAME)))
	cd $(srcDir) \
	&& DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) \
	MULTITIER_DB_NAME=$(call MULTITIER_DB_NAME) \
	$(PYTHON) ./manage.py loadfixtures --database $(basename $(notdir $(MULTITIER_DB_NAME))) $(EMAIL_FIXTURE_OPT) $(abspath $(srcDir)/../../..)/$(subst migratedb-,,$@)/reps/$(subst migratedb-,,$@)/$(subst migratedb-,,$@)/fixtures/$(basename $(notdir $(MULTITIER_DB_NAME)))-streetside.json
	@echo "-- Set streetside processor deposit key."
	$(SQLITE) $(call MULTITIER_DB_NAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_CONNECTED_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where is_provider=1;"
	cd $(srcDir) && $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) \
			$(abspath $(srcDir)/../../..)/$(subst migratedb-,,$@)/reps/$(subst migratedb-,,$@)/$(subst migratedb-,,$@)/fixtures/djaodjin.json
	@echo "-- Set passphrase to forward session."
	$(SQLITE) $(call MULTITIER_DB_NAME) "UPDATE rules_app set enc_key='$(shell grep ^DJAODJIN_SECRET_KEY $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/credentials | cut -f 2 -d \")';"

# Download prerequisites specified in package.json and install relevant files
# in directory assets are served from.
# The less files (under source control) to build djaoapp base.css will be
# also be installed into the directory assets are served from to support
# style editing.
vendor-assets-prerequisites: $(installTop)/.npm/djaoapp-packages

$(installTop)/.npm/djaoapp-packages: $(srcDir)/package.json
	$(installFiles) $^ $(installTop)
	$(NPM) install --loglevel verbose --cache $(installTop)/.npm --tmp $(installTop)/tmp --prefix $(installTop)
	$(installDirs) -d $(ASSETS_DIR)/fonts $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery/dist/jquery.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/moment/moment.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootstrap-colorpicker/dist/css/bootstrap-colorpicker.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/nvd3/build/nv.d3.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/trip.js/dist/trip.css $(ASSETS_DIR)/vendor
	[ -f $(SASSC) ] || (cd $(binDir) && ln -s ../node_modules/.bin/sass sassc)
	touch $@

# webpack will remove all files in the cache folder so we build the Javascript
# bundle before the css files.
build-assets: $(ASSETS_DIR)/cache/djaodjin-vue.js \
                $(ASSETS_DIR)/cache/base.css \
                $(ASSETS_DIR)/cache/email.css \
                $(ASSETS_DIR)/cache/dashboard.css \
                $(ASSETS_DIR)/cache/pages.css

$(ASSETS_DIR)/cache/djaodjin-vue.js: $(installTop)/.npm/djaoapp-packages
	cd $(srcDir) && $(PYTHON) manage.py generate_assets_paths --venv=$(installTop) $(installTop)/djaodjin-webpack.json
	$(installFiles) $(srcDir)/webpack.common.js $(installTop)
	$(installFiles) $(srcDir)/webpack.development.js $(installTop)
	$(installFiles) $(srcDir)/webpack.production.js $(installTop)
	cd $(installTop) && $(WEBPACK) --config $(installTop)/webpack.$(WEBPACK_MODE).js

$(ASSETS_DIR)/cache/base.css: $(srcDir)/djaoapp/static/scss/base/base.scss \
  $(wildcard $(srcDir)/djaoapp/static/scss/base/*.scss) \
  $(wildcard $(srcDir)/djaoapp/static/scss/vendor/bootstrap/*.scss) \
  $(wildcard $(srcDir)/djaoapp/static/scss/vendor/bootstrap/mixins/*.scss) \
  $(wildcard $(srcDir)/djaoapp/static/scss/vendor/bootstrap/utilities/*.scss) \
  $(wildcard $(srcDir)/djaoapp/static/scss/vendor/djaodjin/*.scss) \
  $(wildcard $(srcDir)/djaoapp/static/scss/vendor/toastr/*.scss)
	cd $(srcDir) && $(SASSC) $< $@


$(ASSETS_DIR)/cache/email.css: $(srcDir)/djaoapp/static/scss/email/email.scss \
              $(wildcard $(srcDir)/djaoapp/static/scss/email/*.scss) \
              $(wildcard $(srcDir)/djaoapp/static/scss/vendor/bootstrap/*.scss)
	cd $(srcDir) && $(SASSC) $< $@


$(ASSETS_DIR)/cache/dashboard.css: \
              $(srcDir)/djaoapp/static/scss/dashboard/dashboard.scss \
              $(wildcard $(srcDir)/djaoapp/static/scss/dashboard/*.scss) \
              $(srcDir)/djaoapp/static/scss/vendor/nv.d3.scss \
              $(srcDir)/djaoapp/static/scss/vendor/trip.scss
	cd $(srcDir) && $(SASSC) $< $@


$(ASSETS_DIR)/cache/pages.css: \
       $(srcDir)/djaoapp/static/scss/pages/pages.scss \
       $(wildcard $(srcDir)/djaoapp/static/scss/pages/*.scss) \
       $(wildcard $(srcDir)/djaoapp/static/scss/vendor/djaodjin-pages/*.scss) \
       $(srcDir)/djaoapp/static/scss/vendor/jquery-ui.scss \
       $(srcDir)/djaoapp/static/scss/vendor/bootstrap-colorpicker.scss
	cd $(srcDir) && $(SASSC) $< $@


setup-livedemo:
	$(installDirs) $(srcDir)/themes/djaoapp/templates
	$(installFiles) $(srcDir)/livedemo/templates/index.html $(srcDir)/themes/djaoapp/templates
	cd $(srcDir) $(if $(LIVEDEMO_ASSETS),&& cp -rf $(LIVEDEMO_ASSETS) htdocs/media,)
	cd $(srcDir) && rm -f $(DB_FILENAME)
	cd $(srcDir) && $(PYTHON) manage.py migrate --run-syncdb
	cat $(srcDir)/djaoapp/migrations/adjustments1-sqlite3.sql | $(SQLITE) $(DB_FILENAME)
	cd $(srcDir) && $(PYTHON) manage.py loadfixtures djaoapp/fixtures/livedemo-db.json
	cat $(srcDir)/djaoapp/migrations/adjustments2-sqlite3.sql | $(SQLITE) $(DB_FILENAME)
	cd $(srcDir) && $(PYTHON) manage.py load_test_transactions --profile-pictures htdocs/media/livedemo/profiles
	[ ! -f $(srcDir)/package-lock.json ] || rm $(srcDir)/package-lock.json
	find $(srcDir) -name '__pycache__' -exec rm -rf {} +
	find $(srcDir) -name '*~' -exec rm -rf {} +


$(srcDir)/djaoapp/locale/fr/LC_MESSAGES/django.mo: \
				$(wildcard $(srcDir)/djaoapp/locale/es/LC_MESSAGES/*.po) \
				$(wildcard $(srcDir)/djaoapp/locale/fr/LC_MESSAGES/*.po) \
				$(wildcard $(srcDir)/djaoapp/locale/pt/LC_MESSAGES/*.po)
	cd $(srcDir) && \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) manage.py compilemessages


# Once tests are completed, run 'coverage report'.
run-coverage: initdb
	cd $(srcDir) && coverage run --source='.,saas,signup' \
		manage.py runserver 8020 --noreload

run-agent-coverage:
	cd $(srcDir) && DJANGO_SETTINGS_MODULE=agent.settings coverage run \
		--source='agent' manage.py runserver 8010 --noreload

require-pip:
	$(PIP) install -r $(srcDir)/requirements.txt --upgrade

require-resources:
	cd $(srcDir) && $(PYTHON) ./manage.py download_resources


install-conf:: $(DESTDIR)$(CONFIG_DIR)/credentials \
				$(DESTDIR)$(CONFIG_DIR)/site.conf \
				$(DESTDIR)$(CONFIG_DIR)/gunicorn.conf \
				$(DESTDIR)$(SYSCONFDIR)/sysconfig/$(APP_NAME) \
				$(DESTDIR)$(SYSCONFDIR)/logrotate.d/$(APP_NAME) \
				$(DESTDIR)$(SYSCONFDIR)/monit.d/$(APP_NAME) \
				$(DESTDIR)$(SYSCONFDIR)/systemd/system/$(APP_NAME).service
	install -d $(DESTDIR)$(LOCALSTATEDIR)/db
	install -d $(DESTDIR)$(LOCALSTATEDIR)/log/gunicorn
	[ -d $(DESTDIR)$(LOCALSTATEDIR)/run ] || install -d $(DESTDIR)$(LOCALSTATEDIR)/run


# Implementation Note:
# We use [ -f file ] before install here such that we do not blindly erase
# already present configuration files with template ones.
$(DESTDIR)$(SYSCONFDIR)/%/site.conf: $(srcDir)/etc/site.conf
	install -d $(dir $@)
	[ -f $@ ] || \
		sed -e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' \
			-e 's,%(SYSCONFDIR)s,$(SYSCONFDIR),' \
			-e 's,%(APP_NAME)s,$(APP_NAME),' \
			-e "s,%(ADMIN_EMAIL)s,$(MY_EMAIL)," \
			-e 's,%(installTop)s,$(installTop),' \
			-e "s,%(DB_NAME)s,djaodjin," \
			-e "s,%(binDir)s,$(binDir)," $< > $@

$(DESTDIR)$(SYSCONFDIR)/%/credentials: $(srcDir)/etc/credentials
	install -d $(dir $@)
	[ -e $@ ] || sed \
		-e "s,\%(SECRET_KEY)s,`$(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," \
		-e "s,STRIPE_PUB_KEY = \"\",STRIPE_PUB_KEY = \"$(STRIPE_PUB_KEY)\"," \
		-e "s,STRIPE_PRIV_KEY = \"\",STRIPE_PRIV_KEY = \"$(STRIPE_PRIV_KEY)\","\
			$< > $@

$(DESTDIR)$(SYSCONFDIR)/%/gunicorn.conf: $(srcDir)/etc/gunicorn.conf
	install -d $(dir $@)
	[ -e $@ ] || sed \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' \
		-e 's,%(APP_NAME)s,$(APP_NAME),' \
		-e 's,%(APP_PORT)s,$(APP_PORT),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/systemd/system/%.service: \
			   $(srcDir)/etc/service.conf
	install -d $(dir $@)
	[ -e $@ ] || sed \
		-e 's,%(srcDir)s,$(srcDir),' \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(binDir)s,$(binDir),' \
		-e 's,%(SYSCONFDIR)s,$(SYSCONFDIR),' \
		-e 's,%(CONFIG_DIR)s,$(CONFIG_DIR),' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/logrotate.d/%: $(srcDir)/etc/logrotate.conf
	install -d $(dir $@)
	[ -e $@ ] || sed \
		-e 's,%(APP_NAME)s,$(APP_NAME),' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/monit.d/%: $(srcDir)/etc/monit.conf
	install -d $(dir $@)
	[ -e $@ ] || sed \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/sysconfig/%: $(srcDir)/etc/sysconfig.conf
	install -d $(dir $@)
	[ -e $@ ] || install -p -m 644 $< $@
