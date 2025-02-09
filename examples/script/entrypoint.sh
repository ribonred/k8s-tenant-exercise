#!/bin/sh
echo "=======LOAD MODULE========"
echo $DJANGO_SETTINGS_MODULE
echo "=========================="
python manage.py migrate
touch /var/run/supervisor.sock && chmod 777 /var/run/supervisor.sock
supervisord -c /app/supervisor.conf -n