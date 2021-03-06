from functools import wraps
from flask import g, url_for, redirect, request, abort

from app.auth import constants as USER


def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

def requires_at_least_manager(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user.role < USER.MANAGER:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def requires_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user.role != USER.ADMIN:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def requires_at_least_owner(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user.role < USER.OWNER:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def requires_at_least_server(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user.role < USER.SERVER:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
