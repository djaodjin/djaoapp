FROM centos:7

RUN /usr/bin/yum -y install epel-release
RUN /usr/bin/yum -y install python36 python36-psycopg2 python36-cryptography python36-coverage python36-setproctitle python36-lxml python36-pillow python36-cffi cairo pango 
RUN /usr/bin/python3.6 -m venv /app --system-site-packages
RUN /app/bin/pip install pip setuptools --upgrade

# Bundle app source
COPY . /app/reps/djaoapp

WORKDIR /app/reps/djaoapp
RUN /app/bin/pip install -r requirements.txt billiard
# XXX Upgrading to Django 2.2 requires to install a recent version of sqlite3
# from source.
RUN /app/bin/pip install Django==1.11.29 django-localflavor==2.2
RUN /usr/bin/mkdir -p /etc/djaoapp
RUN /usr/bin/sed -e "s,\%(SECRET_KEY)s,`/app/bin/python -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," \
  etc/credentials > /etc/djaoapp/credentials
# XXX force running in production mode without bringing in a site.conf
RUN /usr/bin/echo "DEBUG=0" >> /etc/djaoapp/credentials
RUN /usr/bin/sed -e 's,%(APP_NAME)s,djaoapp,g' -e 's,%(LOCALSTATEDIR)s,/var,g'\
  -e 's,%(PID_FILE)s,/var/run/djaoapp.pid,g'\
  -e 's,bind="127.0.0.1:%(APP_PORT)s",bind="0.0.0.0:80",'\
  etc/gunicorn.conf > /etc/djaoapp/gunicorn.conf

# Expose application http port
Expose 80

# Run
CMD ["/app/bin/gunicorn", "-c", "/etc/djaoapp/gunicorn.conf", "djaoapp.wsgi"]
