from flask import abort
from flask_login import  current_user
from functools import wraps


def admin_only(f):
    """
    Decorator que comprueba que el usuario que está tratando de acceder a la página tiene permiso de Admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si no es admin arroja error 403
        if current_user.permisos != 'Admin':
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


def analista_only(f):
    """
    Decorator que comprueba que el usuario que está tratando de acceder a la página tiene permiso de Analista o Administrador
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si no es admin arroja error 403
        if current_user.permisos != 'Admin' and current_user.permisos != 'Analista':
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


