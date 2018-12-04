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
DB_FILENAME   := $(shell grep ^DB_NAME $(CONFIG_DIR)/site.conf | cut -f 2 -d '"')
DB_TEST_FILENAME := $(shell grep ^TEST_DB_NAME $(CONFIG_DIR)/site.conf | cut -f 2 -d '"')
ifeq ($(dir $(DB_FILENAME)),./)
MULTITIER_DB_FILENAME := cowork
else
MULTITIER_DB_FILENAME := $(dir $(DB_FILENAME))cowork.sqlite
endif

MULTITIER_DB_NAME = $(if $(wildcard $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/site.conf),$(shell grep ^DB_NAME $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/site.conf | cut -f 2 -d '"'),$(dir $(DB_FILENAME))$(subst migratedb-,,$@).sqlite)

MY_EMAIL          := $(shell cd $(srcDir) && git config user.email)
EMAIL_FIXTURE_OPT := $(if $(MY_EMAIL),--email="$(MY_EMAIL)",)

all:
	@echo "Nothing to be done for 'make'."

# Remove cache directories (htdocs/media/ are uploaded files, cannot be rebuilt)
clean: clean-themes
	-rm -rf $(srcDir)/htdocs/static/.webassets-cache \
		$(srcDir)/htdocs/static/cache

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
	rsync -av $(srcDir)/htdocs/static/fonts $(srcDir)/htdocs/media


# download and install prerequisites then create the db.
require: require-pip require-resources initdb


# We add a `load_test_transactions` because the command will set the current
# site and thus need the rules.App table.
initdb: install-default-themes initdb-testing initdb-cowork
	-[ -f $(DB_FILENAME) ] && rm -f $(DB_FILENAME)
	-[ -f $(dir $(DB_FILENAME))my-streetside.sqlite ] && rm -f $(dir $(DB_FILENAME))my-streetside.sqlite
	cd $(srcDir) && \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py migrate $(RUNSYNCDB) --noinput --fake-initial
	echo "CREATE UNIQUE INDEX uniq_email ON auth_user(email);" | $(SQLITE) $(DB_FILENAME)
	cd $(srcDir) && \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) djaoapp/fixtures/default-db.json
	@echo "-- Set streetside processor deposit key."
	sqlite3 $(DB_FILENAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_PRIV_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where slug='djaoapp';"


initdb-testing: install-conf
	-[ -f $(DB_TEST_FILENAME) ] && rm -f $(DB_TEST_FILENAME)
	cd $(srcDir) && DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py migrate $(RUNSYNCDB) --database testing --noinput
	echo "CREATE UNIQUE INDEX uniq_email ON auth_user(email);" | $(SQLITE) $(DB_TEST_FILENAME)
	cd $(srcDir) && \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) --database testing djaoapp/fixtures/testing-db.json


initdb-cowork: install-conf
	-[ -f $(MULTITIER_DB_FILENAME) ] && rm -f $(MULTITIER_DB_FILENAME)
	cd $(srcDir) && MULTITIER_DB_NAME=$(MULTITIER_DB_FILENAME) \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py migrate \
		$(RUNSYNCDB) --database cowork --noinput
	echo "CREATE UNIQUE INDEX uniq_email ON auth_user(email);" | $(SQLITE) $(MULTITIER_DB_FILENAME)
	cd $(srcDir) && MULTITIER_DB_NAME=$(MULTITIER_DB_FILENAME) \
		DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) --database cowork djaoapp/fixtures/cowork-db.json


migratedb-cowork: initdb-cowork
	@echo "-- Set streetside processor deposit key."
	sqlite3 $(call MULTITIER_DB_NAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_CONNECTED_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where is_provider=1;"


# Add necessary tables in an already existing database, then load information
migratedb-%:
	cd $(srcDir) && MULTITIER_DB_NAME=$(call MULTITIER_DB_NAME) \
		$(PYTHON) ./manage.py migrate $(RUNSYNCDB) --database $(subst migratedb-,,$@)
	cd $(srcDir) \
	&& DJAOAPP_SETTINGS_LOCATION=$(CONFIG_DIR) \
	MULTITIER_DB_NAME=$(call MULTITIER_DB_NAME) \
	$(PYTHON) ./manage.py loadfixtures --database $(subst migratedb-,,$@) $(EMAIL_FIXTURE_OPT) $(abspath $(srcDir)/../../..)/$(subst migratedb-,,$@)/reps/$(subst migratedb-,,$@)/$(subst migratedb-,,$@)/fixtures/$(subst migratedb-,,$@)-streetside.json
	@echo "-- Set streetside processor deposit key."
	sqlite3 $(call MULTITIER_DB_NAME) "UPDATE saas_organization set processor_deposit_key='$(shell grep ^STRIPE_TEST_CONNECTED_KEY $(CONFIG_DIR)/credentials | cut -f 2 -d \")' where is_provider=1;"
	cd $(srcDir) && $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) \
			$(abspath $(srcDir)/../../..)/$(subst migratedb-,,$@)/reps/$(subst migratedb-,,$@)/$(subst migratedb-,,$@)/fixtures/djaodjin.json
	@echo "-- Set passphrase to forward session."
	sqlite3 $(call MULTITIER_DB_NAME) "UPDATE rules_app set enc_key='$(shell grep ^DJAODJIN_SECRET_KEY $(dir $(installTop))$(subst migratedb-,,$@)/etc/$(subst migratedb-,,$@)/credentials | cut -f 2 -d \")';"

# Download prerequisites specified in package.json and install relevant files
# in directory assets are served from.
# The less files (under source control) to build djaoapp base.css will be
# also be installed into the directory assets are served from to support
# style editing.
vendor-assets-prerequisites: $(srcDir)/package.json
	$(installFiles) $^ $(installTop)
	$(NPM) install --loglevel verbose --cache $(installTop)/.npm --tmp $(installTop)/tmp --prefix $(installTop)
	$(installDirs) $(ASSETS_DIR)/fonts $(ASSETS_DIR)/base $(ASSETS_DIR)/vendor/bootstrap $(ASSETS_DIR)/vendor/config $(ASSETS_DIR)/vendor/extensions $(ASSETS_DIR)/vendor/jax/output/CommonHTML/fonts/TeX $(ASSETS_DIR)/vendor/fonts/HTML-CSS/TeX/woff $(ASSETS_DIR)/vendor/fonts/HTML-CSS/TeX/otf $(ASSETS_DIR)/img/bootstrap-colorpicker
	$(installFiles) $(srcDir)/assets/less/base/*.less $(ASSETS_DIR)/base
	$(installFiles) $(srcDir)/assets/less/vendor/bootstrap/*.less $(ASSETS_DIR)/vendor/bootstrap
	$(installFiles) $(installTop)/node_modules/ace-builds/src/ace.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/ext-language_tools.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/ext-modelist.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/ext-emmet.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/theme-monokai.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/mode-html.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/mode-css.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/mode-javascript.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/worker-html.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/worker-css.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/ace-builds/src/worker-javascript.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/animate.css/animate.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/angular-animate/angular-animate.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/angular-ui-bootstrap/dist/ui-bootstrap-tpls.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/angular-dragdrop/src/angular-dragdrop.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/angular-resource/angular-resource.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/angular-route/angular-route.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/angular-sanitize/angular-sanitize.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/angular-touch/angular-touch.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootbox/bootbox.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootstrap/dist/js/bootstrap.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootstrap-colorpicker/dist/img/bootstrap-colorpicker/*.png $(ASSETS_DIR)/img/bootstrap-colorpicker
	$(installFiles) $(installTop)/node_modules/bootstrap-colorpicker/dist/css/bootstrap-colorpicker.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/bootstrap-colorpicker/dist/js/bootstrap-colorpicker.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/chardin.js/chardinjs.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/chardin.js/chardinjs.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/d3/d3.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/dropzone/dist/dropzone.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/dropzone/dist/dropzone.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/font-awesome/css/font-awesome.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/font-awesome/fonts/* $(ASSETS_DIR)/fonts
	$(installFiles) $(installTop)/node_modules/highlightjs/styles/monokai_sublime.css $(installTop)/node_modules/highlightjs/styles/github.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/highlightjs/highlight.pack.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery/dist/jquery.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery-autosize/jquery.autosize.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery.cookie/jquery.cookie.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery.payment/lib/jquery.payment.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery.selection/dist/jquery.selection.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/jquery-ui-touch-punch/jquery.ui.touch-punch.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/moment/moment.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/moment-timezone/builds/moment-timezone-with-data.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/mathjax/MathJax.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/mathjax/config/*.js $(ASSETS_DIR)/vendor/config
	$(installFiles) $(installTop)/node_modules/mathjax/extensions/*.js $(ASSETS_DIR)/vendor/extensions
	$(installFiles) $(installTop)/node_modules/mathjax/jax/output/CommonHTML/*.js $(ASSETS_DIR)/vendor/jax/output/CommonHTML
	$(installFiles) $(installTop)/node_modules/mathjax/jax/output/CommonHTML/fonts/TeX/*.js $(ASSETS_DIR)/vendor/jax/output/CommonHTML/fonts/TeX
	$(installFiles) $(installTop)/node_modules/mathjax/fonts/HTML-CSS/TeX/woff/* $(ASSETS_DIR)/vendor/fonts/HTML-CSS/TeX/woff
	$(installFiles) $(installTop)/node_modules/mathjax/fonts/HTML-CSS/TeX/otf/* $(ASSETS_DIR)/vendor/fonts/HTML-CSS/TeX/otf
	$(installFiles) $(installTop)/node_modules/nvd3/build/nv.d3.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/nvd3/build/nv.d3.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/pagedown/Markdown.Converter.js $(installTop)/node_modules/pagedown/Markdown.Sanitizer.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/skrollr/src/skrollr.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/toastr/toastr.js $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/trip.js/dist/trip.css $(ASSETS_DIR)/vendor
	$(installFiles) $(installTop)/node_modules/trip.js/dist/trip.js $(ASSETS_DIR)/vendor
	[ -f $(binDir)/lessc ] || (cd $(binDir) && ln -s ../node_modules/less/bin/lessc)

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
	install -d $(DESTDIR)$(LOCALSTATEDIR)/run
	install -d $(DESTDIR)$(LOCALSTATEDIR)/log/gunicorn


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
		-e 's,%(APP_NAME)s,$(APP_NAME),' $< > $@

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
