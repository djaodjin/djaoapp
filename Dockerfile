FROM python:3.10-slim-bullseye
# As of 2023-04-21: Python 3.10.11, Debian 11.0 (Bullseye)
# RUN which python3
# RUN python3 --version
# RUN cat /etc/debian_version
RUN /bin/mkdir -p /etc/djaoapp

# ==== Installs required native packages
RUN apt-get update -y
RUN DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get -y install python3-psycopg2 python3-cryptography python3-coverage python3-setproctitle python3-lxml python3-pil python3-cffi python3-billiard python3-ldap python3-cairo libpangoft2-1.0-0 libxmlsec1-openssl pkg-config gcc libxmlsec1-dev

# ==== Installs pip packages
# docutils==0.15.2 because botocore has a constraint: docutils<0.16
# WeasyPrint>=53 requires Pango1.44, AMZLinux2 has 1.42, but on Debian
# (Dockerfile), if we use version 52.5, it leads to
# `OSError: cannot load library 'pangocairo-1.0'`
RUN /usr/local/bin/python3 -m venv --upgrade-deps --system-site-packages /app
RUN /app/bin/pip install boto3==1.26.84 Django==3.2.19 django-phonenumber-field==6.3.0 django-recaptcha==3.0.0 djangorestframework==3.14.0 djaodjin-deployutils==0.10.6 djaodjin-extended-templates==0.4.3 djaodjin-multitier==0.1.25 djaodjin-rules==0.4.2 djaodjin-saas==0.17.0 djaodjin-signup==0.8.3 docutils==0.15.2 jinja2==3.1.2 MarkupSafe==2.1.1 gunicorn==20.1.0 phonenumbers==8.12.54 PyJWT==2.6.0 pytz==2022.7.1 social-auth-app-django==5.2.0 whitenoise==6.4.0 WeasyPrint==53.3 django-debug-toolbar==3.5.0 django-extensions==3.2.1 django-storages==1.13.2

# ==== Cleans up native package only necessary while installing pip packages
RUN DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get -y autoremove pkg-config gcc libxmlsec1-dev

# Bundle app source
COPY . /app/reps/djaoapp
WORKDIR /app/reps/djaoapp

# Create local configuration files
RUN /bin/sed -e "s,\%(SECRET_KEY)s,`/app/bin/python -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," etc/credentials > /etc/djaoapp/credentials
RUN /bin/sed -e "s,^DB_LOCATION *= *\".*\",DB_LOCATION = \"sqlite3:///app/reps/djaoapp/db.sqlite\"," etc/site.conf > /etc/djaoapp/site.conf
RUN /bin/sed -e 's,%(APP_NAME)s,djaoapp,g' -e 's,%(LOCALSTATEDIR)s,/var,g'\
  -e 's,%(PID_FILE)s,/var/run/djaoapp.pid,g'\
  -e 's,bind="127.0.0.1:%(APP_PORT)s",bind="0.0.0.0:80",'\
  etc/gunicorn.conf > /etc/djaoapp/gunicorn.conf

# Expose application http port
Expose 80

# Run
CMD ["/app/bin/gunicorn", "-c", "/etc/djaoapp/gunicorn.conf", "djaoapp.wsgi"]
