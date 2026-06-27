import logging

from .models import User

logger = logging.getLogger(__name__)


def register_user(email, password, first_name='', last_name=''):
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    logger.info('New user registered: %s', user.email)
    return user


def get_user_by_id(user_id):
    return User.objects.get(id=user_id)
