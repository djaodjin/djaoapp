FROM python:3.10-slim-bookworm
#2025-04-15: python:3.10-slim-bookworm - Python 3.10.17, Debian 12.10 (Bookworm)
#2023-04-21: python:3.10-slim-bullseye - Python 3.10.11, Debian 11.0 (Bullseye)

LABEL org.opencontainers.image.source https://github.com/djaodjin/djaoapp

# Print version info for build log
RUN echo "Building with" `python --version` '('`which python`')' "on Debian" `cat /etc/debian_version` "..."

# ==== Installs required native packages
RUN set -eux; \
      apt-get update -y; \
      DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends\
        libcairo2 \
        libldap-2.5-0 libldap-common \
        libpangoft2-1.0-0 \
        libxmlsec1 \
        libxslt1.1 \
        sqlite3; \
      rm -rf /var/lib/apt/lists/*;

# ==== Installs pip packages
# docutils==0.15.2 because botocore has a constraint: docutils<0.16
# WeasyPrint>=53 requires Pango1.44, AMZLinux2 has 1.42, but on Debian
# (Dockerfile), if we use version 52.5, it leads to
# `OSError: cannot load library 'pangocairo-1.0'`
RUN /usr/local/bin/python3 -m venv --upgrade-deps /app

# Install source-wheel build-time dependencies, build and/or install all
# wheels, then uninstall source-wheel build-time dependencies.
RUN set -eux; \
      \
      savedAptMark="$(apt-mark showmanual)"; \
      apt-get update; \
      apt-get -y install --no-install-recommends \
        build-essential \
        git-core \
        libcairo2-dev \
        libldap2-dev \
        libsasl2-dev \
        libxmlsec1-dev \
        libxslt1-dev \
        pkg-config; \
      \
      /app/bin/pip install billiard==4.0.0 cairocffi==1.3.0 coverage==7.2.7 cryptography==44.0.1 psycopg2-binary==2.9.3 pycairo==1.21.0 python-ldap==3.4.0 setproctitle==1.2.3; \
      /app/bin/pip install xmlsec==1.3.14; \
      /app/bin/pip install django-fernet-fields@git+https://github.com/djaodjin/django-fernet-fields.git@6f261ed465a7fbafa1c41b635f7acd9fd6f3ccca; \
      /app/bin/pip install boto3==1.33.13 Django==4.2.28 django-phonenumber-field==7.1.0 django-recaptcha==4.0.0 djangorestframework==3.15.2 djaodjin-deployutils==0.14.2 djaodjin-extended-templates==0.4.12 djaodjin-multitier==0.3.1 djaodjin-rules==0.4.11 djaodjin-saas==1.2.0 djaodjin-signup==0.11.1 docutils==0.15.2 drf-spectacular==0.27.0 googlemaps==4.10.0 gunicorn==23.0.0 jinja2==3.1.6 phonenumbers==8.13.17 pydyf==0.1.2 PyJWT==2.10.1 pyotp==2.8.0 pytz==2025.1 social-auth-app-django==5.4.3 stripe==12.5.1 whitenoise==6.4.0 WeasyPrint==53.4 django-storages==1.14.2; \
      /app/bin/pip install django-debug-toolbar==3.5.0 django-extensions==3.2.3; \
      \
      apt-mark auto '.*'; \
      apt-mark manual $savedAptMark; \
      apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
      rm -rf /var/lib/apt/lists/*;

# Bundle app source
COPY . /app/reps/djaoapp
WORKDIR /app/reps/djaoapp

# Create local configuration files
# We remove the `pidfile` settings from the gunicorn.conf conf file
# such that we are able to run the container as a non-root user.
RUN mkdir -p /etc/djaoapp /var/run/djaoapp
RUN sed -e "s,\%(SECRET_KEY)s,`/app/bin/python -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," etc/credentials > /etc/djaoapp/credentials
RUN sed -e "s,^DB_SECRET_LOCATION *= *\".*\",DB_SECRET_LOCATION = \"sqlite3:///app/reps/djaoapp/db.sqlite\"," -e 's,%(DB_FILENAME)s,/app/reps/djaoapp/db.sqlite,g' etc/site.conf > /etc/djaoapp/site.conf
RUN sed -e 's,%(APP_NAME)s,djaoapp,g' -e 's,%(LOCALSTATEDIR)s,/var,g'\
  -e '/pidfile=/d' -e 's,bind="127.0.0.1:%(APP_PORT)s",bind="0.0.0.0:80",'\
  etc/gunicorn.conf > /etc/djaoapp/gunicorn.conf

# Expose application http port
EXPOSE 80/tcp

# Run
ENTRYPOINT ["/app/bin/gunicorn", "-c", "/etc/djaoapp/gunicorn.conf", "djaoapp.wsgi"]
