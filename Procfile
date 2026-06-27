web: python manage.py migrate --noinput && python -m daphne -b 0.0.0.0 -p $PORT config.asgi:application
worker: celery -A config worker --loglevel=info --pool=solo
beat: celery -A config beat --loglevel=info
