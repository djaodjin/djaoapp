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
SQLITE        ?= sqlite3

# Django 1.7,1.8 sync tables without migrations by default while Django 1.9
# requires a --run-syncdb argument.
# Implementation Note: We have to wait for the config files to be installed
# before running the manage.py command (else missing SECRECT_KEY).
RUNSYNCDB     = $(if $(findstring --run-syncdb,$(shell cd $(srcDir) && DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) manage.py migrate --help 2>/dev/null)),--run-syncdb,)

APP_NAME      ?= djaoapp
APP_PORT      ?= 8000
ifneq ($(wildcard $(CONFIG_DIR)/site.conf),)
# `make initdb` will install site.conf but only after `grep` is run
# and DB_FILNAME set to "". We use the default value in the template site.conf
# here to prevent that issue.
DB_FILENAME   := $(shell grep ^DB_NAME $(CONFIG_DIR)/site.conf | cut -f 2 -d '"')
mode          ?= $(if $(findstring True,$(shell grep ^DEBUG $(CONFIG_DIR)/site.conf | cut -f 2 -d '=')),,production)
else
DB_FILENAME   := $(LOCALSTATEDIR)/db/djaodjin.sqlite
endif

ifeq ($(dir $(DB_FILENAME)),./)
MULTITIER_DB_FILENAME := cowork
else
MULTITIER_DB_FILENAME := $(dir $(DB_FILENAME))cowork.sqlite
endif

MULTITIER_DB_NAME ?= $(if $(wildcard $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/site.conf),$(shell grep ^DB_NAME $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/site.conf | cut -f 2 -d '"'),$(dir $(DB_FILENAME))$(subst migratedb-,,$@).sqlite)

MY_EMAIL		  := $(shell cd $(srcDir) && git config user.email)
EMAIL_FIXTURE_OPT := $(if $(MY_EMAIL),--email="$(MY_EMAIL)",)

all:
	@echo "Nothing to be done for 'make'."

clean: clean-themes

clean-themes:
	-rm -rf $(srcDir)/themes/djaoapp/templates/index.html \
		$(srcDir)/themes/brevent-eb84bac8559b825b545a8299c3888c52f3f172b7 \
		$(srcDir)/htdocs/brevent-eb84bac8559b825b545a8299c3888c52f3f172b7 \
		$(srcDir)/htdocs/balme
	cd $(srcDir) && find . -type d -name "brevent-*" -exec rm -rf {} +

install:: install-conf

# We use rsync here so that make initdb can be run with user "nginx"
# after files were installed with user "fedora".
install-default-themes:: clean-themes


# download and install prerequisites then create the db.
require: require-pip require-resources initdb


# We add a `load_test_transactions` because the command will set the current
# site and thus need the rules.App table.
initdb: install-default-themes initdb-cowork
	-[ -f $(DB_FILENAME) ] && rm -f $(DB_FILENAME)
	-[ -f $(dir $(DB_FILENAME))my-streetside.sqlite ] && rm -f $(dir $(DB_FILENAME))my-streetside.sqlite
	cd $(srcDir) && \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py migrate $(RUNSYNCDB) --noinput --fake-initial
	echo "CREATE UNIQUE INDEX uniq_email ON auth_user(email);" | $(SQLITE) $(DB_FILENAME)
	cd $(srcDir) && \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) djaoapp/fixtures/default-db.json djaoapp/fixtures/djaoapp-roles-card1.json
	@echo "-- Set streetside processor deposit key."
	$(SQLITE) $(DB_FILENAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_PRIV_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where slug='djaoapp';"
	$(SQLITE) $(DB_FILENAME) "UPDATE rules_app set show_edit_tools=1;"


initdb-cowork: install-conf
	-[ -f $(MULTITIER_DB_FILENAME) ] && rm -f $(MULTITIER_DB_FILENAME)
	cd $(srcDir) && MULTITIER_DB_NAME=$(MULTITIER_DB_FILENAME) \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py migrate \
		$(RUNSYNCDB) --database cowork --noinput
	echo "CREATE UNIQUE INDEX uniq_email ON auth_user(email);" | $(SQLITE) $(MULTITIER_DB_FILENAME)
	cd $(srcDir) && MULTITIER_DB_NAME=$(MULTITIER_DB_FILENAME) \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) --database cowork djaoapp/fixtures/cowork-db.json
	$(SQLITE) $(dir $(DB_FILENAME))/cowork.sqlite "UPDATE rules_app set show_edit_tools=1;"


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
	touch $@

ifeq ($(mode),production)
ifeq ($(watch),true)
webpack_watch = '-w'
endif
webpack = $(installTop)/node_modules/.bin/webpack --config $(installTop)/webpack.production.js $(webpack_watch)
else
webpack = $(installTop)/node_modules/.bin/webpack-dev-server --config $(installTop)/webpack.development.js
endif

build-assets: $(installTop)/.npm/djaoapp-packages $(ASSETS_DIR)/js/djaoapp-i18n.js
	cd $(srcDir) && $(PYTHON) manage.py generate_assets_paths --venv=$(installTop) $(installTop)/djaodjin-webpack.json
	$(installFiles) $(srcDir)/webpack.common.js $(installTop)
	$(installFiles) $(srcDir)/webpack.development.js $(installTop)
	$(installFiles) $(srcDir)/webpack.production.js $(installTop)
	cd $(installTop) && $(webpack)


$(ASSETS_DIR)/js/djaoapp-i18n.js: \
				$(srcDir)/djaoapp/locale/fr/LC_MESSAGES/django.mo
	$(installDirs) $(dir $@)
	cd $(srcDir) && $(PYTHON) manage.py generate_i18n_js $@

$(srcDir)/djaoapp/locale/fr/LC_MESSAGES/django.mo: \
				$(wildcard $(srcDir)/djaoapp/locale/es/LC_MESSAGES/*.po) \
				$(wildcard $(srcDir)/djaoapp/locale/fr/LC_MESSAGES/*.po) \
				$(wildcard $(srcDir)/djaoapp/locale/pt/LC_MESSAGES/*.po)
	cd $(srcDir) && $(PYTHON) manage.py compilemessages


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
	[ -f $@ ] || \
		SECRET_KEY=`$(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'` && sed \
		-e "s,\%(SECRET_KEY)s,$${SECRET_KEY}," \
		-e "s,STRIPE_PUB_KEY = \"\",STRIPE_PUB_KEY = \"$(STRIPE_PUB_KEY)\"," \
		-e "s,STRIPE_PRIV_KEY = \"\",STRIPE_PRIV_KEY = \"$(STRIPE_PRIV_KEY)\","\
			$< > $@

$(DESTDIR)$(SYSCONFDIR)/%/gunicorn.conf: $(srcDir)/etc/gunicorn.conf
	install -d $(dir $@)
	[ -f $@ ] || sed \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' \
		-e 's,%(APP_NAME)s,$(APP_NAME),' \
		-e 's,%(APP_PORT)s,$(APP_PORT),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/systemd/system/%.service: \
			   $(srcDir)/etc/service.conf
	install -d $(dir $@)
	[ -f $@ ] || sed \
		-e 's,%(srcDir)s,$(srcDir),' \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(binDir)s,$(binDir),' \
		-e 's,%(SYSCONFDIR)s,$(SYSCONFDIR),' \
		-e 's,%(CONFIG_DIR)s,$(CONFIG_DIR),' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/logrotate.d/%: $(srcDir)/etc/logrotate.conf
	install -d $(dir $@)
	[ -f $@ ] || sed \
		-e 's,%(APP_NAME)s,$(APP_NAME),' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/monit.d/%: $(srcDir)/etc/monit.conf
	install -d $(dir $@)
	[ -f $@ ] || sed \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/sysconfig/%: $(srcDir)/etc/sysconfig.conf
	install -d $(dir $@)
	[ -f $@ ] || install -p -m 644 $< $@
