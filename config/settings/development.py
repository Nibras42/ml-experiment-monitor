from datetime import timedelta

from .base import *  # noqa: F401, F403

DEBUG = True

# Longer token lifetime in dev so API testing doesn't expire mid-session
SIMPLE_JWT = {
    **globals().get('SIMPLE_JWT', {}),
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

INSTALLED_APPS += ['django_extensions']  # noqa: F405

LOGGING['root']['level'] = 'DEBUG'  # noqa: F405

# Use in-memory channel layer in dev so Redis is not required
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
