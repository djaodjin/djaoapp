FROM python:3.9-slim-bullseye
# As of 2021-10-04: Python 3.9.7, Debian 11.0 (Bullseye)
# RUN which python3
# RUN python3 --version
# RUN cat /etc/debian_version

#     Loads the list of native packages
RUN apt-get update -y
#     Installs required native packages
RUN DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get -y install python3-psycopg2 python3-cryptography python3-coverage python3-setproctitle python3-lxml python3-pillow python3-cffi python3-billiard python3-ldap python3-cairo libpangoft2-1.0-0

RUN /usr/local/bin/python3 -m venv /app --system-site-packages
RUN /app/bin/pip install pip setuptools --upgrade

# Bundle app source
COPY . /app/reps/djaoapp
WORKDIR /app/reps/djaoapp
RUN /app/bin/pip install -r requirements.txt

# Create local configuration files
RUN /bin/mkdir -p /etc/djaoapp
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
