# Copyright (c) 2024, DjaoDjin inc.
# see LICENSE

-include $(buildTop)/share/dws/prefix.mk

APP_NAME      ?= $(notdir $(abspath $(srcDir)))
APP_PORT      ?= 8000
LIVEDEMO_ENTRY_POINT ?= http://djaopsp-demo

srcDir        ?= .
installTop    ?= $(if $(VIRTUAL_ENV),$(VIRTUAL_ENV),$(abspath $(srcDir))/.venv)
binDir        ?= $(installTop)/bin
libDir        ?= $(installTop)/lib
SYSCONFDIR    ?= $(installTop)/etc
LOCALSTATEDIR ?= $(installTop)/var
CONFIG_DIR    ?= $(SYSCONFDIR)/$(APP_NAME)
ASSETS_DIR    ?= $(srcDir)/htdocs/assets
# because we are not loading DB_NAME from site.conf
RUN_DIR       ?= $(abspath $(srcDir))

installDirs   ?= /usr/bin/install -d
installFiles  ?= /usr/bin/install -p -m 644
DOCKER        ?= docker
ESCHECK       ?= eslint
NPM           ?= npm
PIP           ?= pip
PYTHON        ?= python
SASSC         ?= sassc --style=compressed --source-map-urls absolute
# As of sqlite3 version  3.42.0 (2023-05-16) we need to pass `-unsafe-testing`
# to make adjustments in the demo database.
SQLITE_NO_UNSAFE_TESTING := $(shell echo '.schema' | sqlite3 -unsafe-testing > /dev/null 2>&1; echo $$?)
ifeq ($(SQLITE_NO_UNSAFE_TESTING),0)
SQLITE        ?= sqlite3
SQLITE_UNSAFE ?= sqlite3 -unsafe-testing
else
SQLITE        ?= sqlite3
SQLITE_UNSAFE ?= $(SQLITE)
endif
WEBPACK       ?= NODE_PATH=$(libDir)/node_modules:$(NODE_PATH) webpack --stats-error-details
#WEBPACK       ?= webpack --stats verbose
#WEBPACK       ?= webpack --profile --json > build.json

# Django 1.7,1.8 sync tables without migrations by default while Django 1.9
# requires a --run-syncdb argument.
# Implementation Note: We have to wait for the config files to be installed
# before running the manage.py command (else missing SECRECT_KEY).
MANAGE        := DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) manage.py
RUNSYNCDB     = $(if $(findstring --run-syncdb,$(shell cd $(srcDir) && $(MANAGE) migrate --help 2>/dev/null)),--run-syncdb,)


ifneq ($(wildcard $(CONFIG_DIR)/site.conf),)
# `make initdb` will install site.conf but only after `grep` is run
# and DB_FILENAME set to "". We use the default value in the template site.conf
# here to prevent that issue.
DB_FILENAME   ?= $(shell grep ^DB_NAME $(CONFIG_DIR)/site.conf | cut -f 2 -d '"')
else
DB_FILENAME   ?= $(RUN_DIR)/db.sqlite
endif
LIVEDEMO_DB_FILENAME := $(srcDir)/db.sqlite
MULTITIER_DB_FILENAME := $(dir $(DB_FILENAME))cowork.sqlite

MULTITIER_DB_NAME ?= $(if $(wildcard $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/site.conf),$(shell grep ^DB_NAME $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/site.conf | cut -f 2 -d '"'),$(dir $(DB_FILENAME))$(subst migratedb-,,$@).sqlite)
MULTITIER_DB_FIXTURES_TOP := $(abspath $(srcDir)/../../../workspace)

MY_EMAIL          ?= $(shell cd $(srcDir) && git config user.email)
EMAIL_FIXTURE_OPT := $(if $(MY_EMAIL),--email="$(MY_EMAIL)",)


.PHONY: build-assets doc generateschema initdb makemessages setup-livedemo vendor-assets-prerequisites

all:
	@echo "Nothing to be done for 'make'."


build-assets: $(ASSETS_DIR)/cache/base.css \
              $(ASSETS_DIR)/cache/djaodjin-menubar.css \
              $(ASSETS_DIR)/cache/email.css \
              $(ASSETS_DIR)/cache/dashboard.css \
              $(ASSETS_DIR)/cache/pages.css \
              $(ASSETS_DIR)/cache/saas.js
	cd $(srcDir) && $(MANAGE) compilemessages
	cd $(srcDir) && DEBUG=0 $(MANAGE) collectstatic --noinput
	cd $(srcDir) && $(ESCHECK) $(ASSETS_DIR)/cache/*.js $(ASSETS_DIR)/vendor/*.js


clean: clean-dbs clean-themes clean-assets
	[ ! -f $(srcDir)/package-lock.json ] || rm $(srcDir)/package-lock.json
	find $(srcDir) -name '__pycache__' -exec rm -rf {} +
	find $(srcDir) -name '*~' -exec rm -rf {} +


doc: schema.yml
	$(installDirs) build/docs
	cd $(srcDir) && sphinx-build -b html ./docs $(PWD)/build/docs


generateschema: schema.yml


# We add a `load_test_transactions` because the command will set the current
# site and thus need the rules.App table.
initdb: install-default-themes initdb-djaoapp initdb-cowork
	cd $(srcDir) && $(MANAGE) loadfixtures $(EMAIL_FIXTURE_OPT) \
        djaoapp/fixtures/livedemo-db.json \
        djaoapp/fixtures/20-broker-subscriptions.json \
        djaoapp/fixtures/40-provider-subscriptions.json \
        djaoapp/fixtures/50-saas-profiles.json \
        djaoapp/fixtures/55-saas-roles.json \
        djaoapp/fixtures/60-djaoapp-register.json \
        djaoapp/fixtures/100-balance-due.json \
        djaoapp/fixtures/120-subscriptions.json \
        djaoapp/fixtures/130-subscriptions.json \
        djaoapp/fixtures/150-subscriptions.json \
        djaoapp/fixtures/160-renewals.json \
        djaoapp/fixtures/160-subscriptions.json \
        djaoapp/fixtures/170-billing.json \
        djaoapp/fixtures/180-auth.json
	@echo "-- Set streetside processor deposit key."
	$(SQLITE) $(DB_FILENAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_PRIV_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where slug='djaoapp';"


install:: install-conf


makemessages:
	cd $(srcDir) && $(MANAGE) makemessages -l fr -l es -l pt --symlinks --no-wrap
	cd $(srcDir) && $(MANAGE) makemessages -d djangojs -l fr -l es -l pt --symlinks --no-wrap

ifeq ($(MY_EMAIL),)

.PHONY: package-docker

# We build a local sqlite3 database to be packaged with the Docker image
# such that the container can be started without prior configuration.
package-docker: build-assets initdb
	[[ -f $(srcDir)/db.sqlite ]] || cp $(DB_FILENAME) $(srcDir)/db.sqlite
	[[ -f $(srcDir)/cowork.sqlite ]] || cp $(MULTITIER_DB_FILENAME) $(srcDir)/cowork.sqlite
	cd $(srcDir) && $(DOCKER) build $(DOCKER_OPTS) .

endif

# download and install prerequisites then create the db.
require: require-pip require-resources initdb


# Once tests are completed, run 'coverage report'.
run-coverage: initdb
	cd $(srcDir) && coverage run --source='.,deployutils,extended-templates,rules,saas,signup,' \
		$(MANAGE) runserver $(APP_PORT) --noreload

# Implementation note:
# We need to install the user photos before running `load_test_transactions`
# because the command will read that directory.
# We use `$(LIVEDEMO_DB_FILENAME)` and `$(PYTHON) manage.py` in this target,
# so no matter the installed config files, we reliably create db.sqlite in
# the source directory and thus are able to transfer it onto the Docker
# container.
setup-livedemo:
	$(installDirs) $(srcDir)/themes/djaoapp/templates $(srcDir)/htdocs/media
	$(installFiles) $(srcDir)/livedemo/templates/index.html $(srcDir)/themes/djaoapp/templates
	mkdir -p $(srcDir)/htdocs/media/livedemo/profiles
	cd $(srcDir) $(if $(LIVEDEMO_ASSETS),&& cp -rf $(LIVEDEMO_ASSETS) htdocs/media,)
	cd $(srcDir) && rm -f $(LIVEDEMO_DB_FILENAME)
	cd $(srcDir) && $(PYTHON) manage.py migrate --run-syncdb
	cat $(srcDir)/djaoapp/migrations/adjustments1-sqlite3.sql | $(SQLITE_UNSAFE) $(LIVEDEMO_DB_FILENAME)
	cd $(srcDir) && APP_NAME=djaopsp $(PYTHON) manage.py loadfixtures djaoapp/fixtures/livedemo-db.json
	$(SQLITE) $(DB_FILENAME) "UPDATE rules_app set authentication=1, entry_point='$(LIVEDEMO_ENTRY_POINT)', enc_key='$(DJAODJIN_SECRET_KEY)';"
	cat $(srcDir)/djaoapp/migrations/adjustments2-sqlite3.sql | $(SQLITE) $(LIVEDEMO_DB_FILENAME)
	cd $(srcDir) && $(PYTHON) manage.py load_test_transactions --provider=djaopsp --profile-pictures htdocs/media/livedemo/profiles
	[ ! -f $(srcDir)/package-lock.json ] || rm $(srcDir)/package-lock.json
	find $(srcDir) -name '__pycache__' -exec rm -rf {} +
	find $(srcDir) -name '*~' -exec rm -rf {} +


# Download prerequisites specified in package.json and install relevant files
# in the directory assets are served from.
vendor-assets-prerequisites: $(installTop)/.npm/$(APP_NAME)-packages
	$(installDirs) $(ASSETS_DIR)/fonts $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/ace.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/ext-language_tools.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/ext-emmet.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/ext-modelist.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/theme-monokai.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/mode-html.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/mode-css.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/mode-javascript.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/worker-html.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/worker-css.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/ace-builds/src/worker-javascript.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/bootstrap/dist/js/bootstrap.min.js* $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/bootstrap-colorpicker/dist/css/bootstrap-colorpicker.css $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/bootstrap-colorpicker/dist/js/bootstrap-colorpicker.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/chart.js/dist/chart.js $(srcDir)/djaoapp/static/vendor
	$(installFiles) $(libDir)/node_modules/d3/d3.min.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/dropzone/dist/dropzone.css $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/dropzone/dist/dropzone.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/font-awesome/css/font-awesome.css $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/font-awesome/fonts/* $(ASSETS_DIR)/fonts
	$(installFiles) $(libDir)/node_modules/jquery/dist/jquery.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/jquery.selection/dist/jquery.selection.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/jquery-autosize/jquery.autosize.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/jquery.payment/lib/jquery.payment.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/lodash/lodash.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/moment/moment.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/moment-timezone/builds/moment-timezone-with-data.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/pagedown/Markdown.Converter.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/pagedown/Markdown.Sanitizer.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/@popperjs/core/dist/umd/popper.min.js* $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/qrcode/build/qrcode.js* $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/trip.js/dist/trip.css $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/trip.js/dist/trip.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/vue/dist/vue.js $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/vue-croppa/dist/vue-croppa.min.css $(ASSETS_DIR)/vendor
	$(installFiles) $(libDir)/node_modules/vue-croppa/dist/vue-croppa.min.js $(ASSETS_DIR)/vendor


# --------- intermediate targets

# We use rsync here so that make initdb can be run with user "nginx"
# after files were installed with user "fedora".
install-default-themes:: clean-themes
	$(installDirs) $(srcDir)/themes
	$(installDirs) $(srcDir)/htdocs/themes


initdb-cowork: clean-dbs
	$(if $(dir $(MULTITIER_DB_FILENAME)),[ -d $(DESTDIR)$(dir $(MULTITIER_DB_FILENAME)) ] || $(installDirs) $(DESTDIR)$(dir $(MULTITIER_DB_FILENAME)))
	cd $(srcDir) && MULTITIER_DB_NAME=$(MULTITIER_DB_FILENAME) \
		$(MANAGE) migrate $(RUNSYNCDB) --database cowork --noinput
	cat $(srcDir)/djaoapp/migrations/adjustments1-sqlite3.sql | $(SQLITE_UNSAFE) $(MULTITIER_DB_FILENAME)
	cd $(srcDir) && MULTITIER_DB_NAME=$(MULTITIER_DB_FILENAME) \
		$(MANAGE) loadfixtures $(EMAIL_FIXTURE_OPT) --database cowork djaoapp/fixtures/cowork-db.json
	cat $(srcDir)/djaoapp/migrations/adjustments2-sqlite3.sql | $(SQLITE) $(MULTITIER_DB_FILENAME)

clean-assets:
	rm -f $(srcDir)/webpack-conf-paths.json
	rm -f $(ASSETS_DIR)/js/*
	rm -f $(ASSETS_DIR)/cache/*

clean-dbs:
	[ ! -f $(DB_FILENAME) ] || rm $(DB_FILENAME)
	[ ! -f $(MULTITIER_DB_FILENAME) ] || rm $(MULTITIER_DB_FILENAME)
	[ ! -f $(srcDir)/db.sqlite ] || rm $(srcDir)/db.sqlite
	[ ! -f $(srcDir)/cowork.sqlite ] || rm $(srcDir)/cowork.sqlite

clean-themes:
	rm -rf $(srcDir)/themes/*
	rm -rf $(srcDir)/htdocs/themes/*
	rm -rf $(srcDir)/htdocs/djaoapp


initdb-djaoapp: clean-dbs
	$(if $(dir $(DB_FILENAME)),[ -d $(DESTDIR)$(dir $(DB_FILENAME)) ] || $(installDirs) $(DESTDIR)$(dir $(DB_FILENAME)))
	cd $(srcDir) && $(MANAGE) migrate $(RUNSYNCDB) --noinput --fake-initial
	cat $(srcDir)/djaoapp/migrations/adjustments1-sqlite3.sql | $(SQLITE_UNSAFE) $(DB_FILENAME)
	cat $(srcDir)/djaoapp/migrations/adjustments2-sqlite3.sql | $(SQLITE) $(DB_FILENAME)


migratedb-cowork: initdb-cowork
	@echo "-- Set streetside processor deposit key."
	$(SQLITE) $(call MULTITIER_DB_NAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_CONNECTED_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where is_provider=1;"


# Add necessary tables in an already existing database, then load information
migratedb-%:
	cd $(srcDir) && MULTITIER_DB_NAME=$(call MULTITIER_DB_NAME) \
		$(MANAGE) migrate $(RUNSYNCDB) --database $(basename $(notdir $(MULTITIER_DB_NAME)))
	cd $(srcDir) \
	&& DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) \
	MULTITIER_DB_NAME=$(call MULTITIER_DB_NAME) \
	$(MANAGE) loadfixtures --database $(basename $(notdir $(MULTITIER_DB_NAME))) $(EMAIL_FIXTURE_OPT) $(MULTITIER_DB_FIXTURES_TOP)/$(subst migratedb-,,$@)/reps/$(subst migratedb-,,$@)/$(subst migratedb-,,$@)/fixtures/$(basename $(notdir $(MULTITIER_DB_NAME)))-streetside.json
	@echo "-- Set streetside processor deposit key."
	$(SQLITE) $(call MULTITIER_DB_NAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_CONNECTED_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where is_provider=1;"
	cd $(srcDir) && $(MANAGE) loadfixtures $(EMAIL_FIXTURE_OPT) \
			$(MULTITIER_DB_FIXTURES_TOP)/$(subst migratedb-,,$@)/reps/$(subst migratedb-,,$@)/$(subst migratedb-,,$@)/fixtures/djaodjin.json
	@echo "-- Set passphrase to forward session."
	$(SQLITE) $(call MULTITIER_DB_NAME) "UPDATE rules_app set enc_key='$(shell grep ^DJAODJIN_SECRET_KEY $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/credentials | cut -f 2 -d \")';"

# npm --loglevel verbose
$(installTop)/.npm/$(APP_NAME)-packages: $(srcDir)/package.json
	$(installFiles) $^ $(libDir)
	$(NPM) install --cache $(installTop)/.npm --tmp $(installTop)/tmp --prefix $(libDir)
	[ -e $(binDir)/eslint ] || (cd $(binDir) && ln -s ../lib/node_modules/.bin/eslint eslint)
	[ -e $(binDir)/sassc ] || (cd $(binDir) && ln -s ../lib/node_modules/.bin/sass sassc)
	[ -e $(binDir)/webpack ] || (cd $(binDir) && ln -s ../lib/node_modules/.bin/webpack webpack)
	touch $@


schema.yml:
	cd $(srcDir) && DEBUG=0 API_DEBUG=1 OPENAPI_SPEC_COMPLIANT=1 \
		$(MANAGE) spectacular --color --file $@ --validate


$(ASSETS_DIR)/cache/saas.js: $(srcDir)/webpack.config.js \
                               $(wildcard $(srcDir)/djaoapp/static/js/*.js) \
                               webpack-conf-paths.json
	cd $(srcDir) && $(WEBPACK) -c $<


webpack-conf-paths.json: $(srcDir)/djaoapp/settings.py
	cd $(srcDir) && $(MANAGE) generate_webpack_paths -o $@


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


$(ASSETS_DIR)/cache/djaodjin-menubar.css: \
              $(srcDir)/djaoapp/static/scss/base/djaodjin-menubar.scss
	cd $(srcDir) && $(SASSC) $< $@


$(ASSETS_DIR)/cache/pages.css: \
       $(srcDir)/djaoapp/static/scss/pages/pages.scss \
       $(wildcard $(srcDir)/djaoapp/static/scss/vendor/djaodjin-extended-templates/*.scss) \
       $(srcDir)/djaoapp/static/scss/vendor/jquery-ui.scss \
       $(srcDir)/djaoapp/static/scss/vendor/bootstrap-colorpicker.scss
	cd $(srcDir) && $(SASSC) $< $@


$(srcDir)/djaoapp/locale/fr/LC_MESSAGES/django.mo: \
				$(wildcard $(srcDir)/djaoapp/locale/es/LC_MESSAGES/*.po) \
				$(wildcard $(srcDir)/djaoapp/locale/fr/LC_MESSAGES/*.po) \
				$(wildcard $(srcDir)/djaoapp/locale/pt/LC_MESSAGES/*.po)
	cd $(srcDir) && $(MANAGE) compilemessages


require-pip:
	$(PIP) install -r $(srcDir)/requirements.txt --upgrade

require-resources:
	cd $(srcDir) && $(MANAGE) download_resources


install-conf:: $(DESTDIR)$(CONFIG_DIR)/credentials \
				$(DESTDIR)$(CONFIG_DIR)/site.conf \
				$(DESTDIR)$(CONFIG_DIR)/gunicorn.conf \
				$(DESTDIR)$(SYSCONFDIR)/sysconfig/$(APP_NAME) \
				$(DESTDIR)$(SYSCONFDIR)/logrotate.d/$(APP_NAME) \
				$(DESTDIR)$(SYSCONFDIR)/monit.d/$(APP_NAME) \
				$(DESTDIR)$(SYSCONFDIR)/systemd/system/$(APP_NAME).service \
				$(DESTDIR)$(libDir)/tmpfiles.d/$(APP_NAME).conf
	[ -d $(DESTDIR)$(LOCALSTATEDIR)/log/gunicorn ] || $(installDirs) $(DESTDIR)$(LOCALSTATEDIR)/log/gunicorn
	[ -d $(DESTDIR)$(LOCALSTATEDIR)/run ] || $(installDirs) $(DESTDIR)$(LOCALSTATEDIR)/run


# Implementation Note:
# We use [ -f file ] before install here such that we do not blindly erase
# already present configuration files with template ones.
$(DESTDIR)$(CONFIG_DIR)/site.conf: $(srcDir)/etc/site.conf
	$(installDirs) $(dir $@)
	[ -f $@ ] || \
		sed -e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' \
			-e 's,%(SYSCONFDIR)s,$(SYSCONFDIR),' \
			-e 's,%(APP_NAME)s,$(APP_NAME),' \
			-e "s,%(ADMIN_EMAIL)s,$(MY_EMAIL)," \
			-e 's,%(installTop)s,$(installTop),' \
			-e "s,%(DB_NAME)s,$(APP_NAME)," \
			-e "s,%(DB_FILENAME)s,$(DB_FILENAME)," \
			-e "s,%(binDir)s,$(binDir)," $< > $@

$(DESTDIR)$(CONFIG_DIR)/credentials: $(srcDir)/etc/credentials
	$(installDirs) $(dir $@)
	[ -e $@ ] || sed \
		-e "s,\%(SECRET_KEY)s,`$(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," \
		-e "s,\%(FERNET_KEY)s,`$(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," \
		-e "s,STRIPE_PUB_KEY = \"\",STRIPE_PUB_KEY = \"$(STRIPE_PUB_KEY)\"," \
		-e "s,STRIPE_PRIV_KEY = \"\",STRIPE_PRIV_KEY = \"$(STRIPE_PRIV_KEY)\","\
			$< > $@

$(DESTDIR)$(CONFIG_DIR)/gunicorn.conf: $(srcDir)/etc/gunicorn.conf
	$(installDirs) $(dir $@)
	[ -e $@ ] || sed \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(APP_PORT)s,$(APP_PORT),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/systemd/system/%.service: \
			   $(srcDir)/etc/service.conf
	$(installDirs) $(dir $@)
	[ -e $@ ] || sed \
		-e 's,%(srcDir)s,$(srcDir),' \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(binDir)s,$(binDir),' \
		-e 's,%(SYSCONFDIR)s,$(SYSCONFDIR),' \
		-e 's,%(CONFIG_DIR)s,$(CONFIG_DIR),' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/logrotate.d/%: $(srcDir)/etc/logrotate.conf
	$(installDirs) $(dir $@)
	[ -e $@ ] || sed \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/monit.d/%: $(srcDir)/etc/monit.conf
	$(installDirs) $(dir $@)
	[ -e $@ ] || sed \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(APP_PORT)s,$(APP_NAME),g' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/sysconfig/%: $(srcDir)/etc/sysconfig.conf
	$(installDirs) $(dir $@)
	[ -e $@ ] || install -p -m 644 $< $@

$(DESTDIR)$(libDir)/tmpfiles.d/$(APP_NAME).conf: $(srcDir)/etc/tmpfiles.conf
	$(installDirs) $(dir $@)
	[ -e $@ ] || sed \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' $< > $@
