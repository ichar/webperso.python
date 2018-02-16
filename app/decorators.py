from functools import wraps
from flask import abort
from flask.ext.login import current_user

from .models import roles


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            #print('current_user.is_administrator: %s' % current_user.is_administrator())
            if not current_user.is_superuser():
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return role_required(roles.ROOT)(f)
