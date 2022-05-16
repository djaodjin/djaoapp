# syntax=docker/dockerfile:1
FROM python:3.9-slim-bullseye

# Install required external libraries for wheels: lxml, python-ldap,
# pycairo, WeasyPrint.
RUN set -eux; \
      apt-get update; \
      apt-get -y install --no-install-recommends \
        libxslt1.1 \
        libldap-2.4-2 libldap-common \
        libcairo2 \
        libpangoft2-1.0-0; \
      rm -rf /var/lib/apt/lists/*;

# Set up virtual environment
ENV VIRTUAL_ENV="/app"
RUN python -m venv --upgrade-deps $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin${PATH:+:}$PATH"

# Bundle app source
COPY . $VIRTUAL_ENV/reps/djaoapp
WORKDIR $VIRTUAL_ENV/reps/djaoapp

# Install source-wheel build-time dependencies, build and/or install all
# wheels, then uninstall source-wheel build-time dependencies.
RUN set -eux; \
      \
      savedAptMark="$(apt-mark showmanual)"; \
      \
      apt-get update; \
      apt-get -y install --no-install-recommends \
        libxslt1-dev \
        libldap2-dev libsasl2-dev build-essential\
        libcairo2-dev pkg-config; \
      \
      pip install -r requirements.txt; \
      \
      apt-mark auto '.*'; \
      apt-mark manual $savedAptMark; \
      apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
      rm -rf /var/lib/apt/lists/*;

# Create local configuration files
RUN mkdir -p /etc/djaoapp
RUN sed -e "s,\%(SECRET_KEY)s,`python -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," etc/credentials > /etc/djaoapp/credentials
RUN sed -e "s,^DB_LOCATION *= *\".*\",DB_LOCATION = \"sqlite3:///app/reps/djaoapp/db.sqlite\"," etc/site.conf > /etc/djaoapp/site.conf
RUN sed -e 's,%(APP_NAME)s,djaoapp,g' -e 's,%(LOCALSTATEDIR)s,/var,g'\
  -e 's,%(PID_FILE)s,/var/run/djaoapp.pid,g'\
  -e 's,bind="127.0.0.1:%(APP_PORT)s",bind="0.0.0.0:80",'\
  etc/gunicorn.conf > /etc/djaoapp/gunicorn.conf

# Print version info for build log
RUN echo "Built with" `python --version` '('`which python`')' "on Debian" `cat /etc/debian_version` '(Bullseye Slim).';

# Expose application http port
EXPOSE 80/tcp

# Run
ENTRYPOINT ["/app/bin/gunicorn", "-c", "/etc/djaoapp/gunicorn.conf", "djaoapp.wsgi"]
