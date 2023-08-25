FROM python:3.10-slim-bullseye
# As of 2023-04-21: Python 3.10.11, Debian 11.0 (Bullseye)

LABEL org.opencontainers.image.source https://github.com/djaodjin/djaoapp

# Print version info for build log
RUN echo "Building with" `python --version` '('`which python`')' "on Debian" `cat /etc/debian_version` "(Bullseye Slim)..."

# ==== Installs required native packages
RUN set -eux; \
      apt-get update -y; \
      DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends\
        libcairo2 \
        libldap-2.4-2 libldap-common \
        libpangoft2-1.0-0 \
        libxmlsec1 \
        libxslt1.1; \
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
        libcairo2-dev \
        libldap2-dev \
        libsasl2-dev \
        libxmlsec1-dev \
        libxslt1-dev \
        pkg-config; \
      \
      /app/bin/pip install billiard==4.0.0 cairocffi==1.3.0 coverage==6.3.2 cryptography==36.0.2 psycopg2-binary==2.9.3 pycairo==1.21.0 python-ldap==3.4.0 setproctitle==1.2.3; \
      /app/bin/pip install boto3==1.28.3 Django==3.2.20 django-phonenumber-field==7.1.0 django-recaptcha==3.0.0 djangorestframework==3.12.4 djaodjin-deployutils==0.10.6 djaodjin-extended-templates==0.4.4 djaodjin-multitier==0.1.26 djaodjin-rules==0.4.2 djaodjin-saas==0.17.1 djaodjin-signup==0.8.4 docutils==0.15.2 jinja2==3.1.2 MarkupSafe==2.1.1 gunicorn==20.1.0 phonenumbers==8.13.13 PyJWT==2.6.0 pyotp==2.8.0 pytz==2023.3 social-auth-app-django==5.2.0 whitenoise==6.4.0 WeasyPrint==52.5; \
      /app/bin/pip install django-debug-toolbar==3.5.0 django-extensions==3.2.1 django-storages==1.13.2; \
      \
      apt-mark auto '.*'; \
      apt-mark manual $savedAptMark; \
      apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
      rm -rf /var/lib/apt/lists/*;

# Bundle app source
COPY . /app/reps/djaoapp
WORKDIR /app/reps/djaoapp

# Create local configuration files
RUN mkdir -p /etc/djaoapp
RUN sed -e "s,\%(SECRET_KEY)s,`/app/bin/python -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," etc/credentials > /etc/djaoapp/credentials
RUN sed -e "s,^DB_LOCATION *= *\".*\",DB_LOCATION = \"sqlite3:///app/reps/djaoapp/db.sqlite\"," etc/site.conf > /etc/djaoapp/site.conf
RUN sed -e 's,%(APP_NAME)s,djaoapp,g' -e 's,%(LOCALSTATEDIR)s,/var,g'\
  -e 's,%(PID_FILE)s,/var/run/djaoapp.pid,g'\
  -e 's,bind="127.0.0.1:%(APP_PORT)s",bind="0.0.0.0:80",'\
  etc/gunicorn.conf > /etc/djaoapp/gunicorn.conf

# Expose application http port
EXPOSE 80/tcp

# Run
ENTRYPOINT ["/app/bin/gunicorn", "-c", "/etc/djaoapp/gunicorn.conf", "djaoapp.wsgi"]
