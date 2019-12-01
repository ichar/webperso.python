# -*- coding: utf-8 -*-

from functools import wraps
from flask import abort, request, redirect, render_template, current_app, make_response
from flask.ext import login
from flask.ext.login import current_user

from config import DEFAULT_ROOT

LIMITED_PAGES = ('/', 'bankperso', 'cards', 'configurator')

ROOT_URL = '/'


def forbidden(e):
    from .settings import make_platform
    kw = make_platform()
    kw.update({
        'root'       : ROOT_URL,
        'title'      : 'Forbidden Error Page',
        'module'     : 'auth',
        'width'      : 1080,
        'message'    : 'Доступ закрыт',
        'pagination' : None,
    })
    return render_template('auth/403.html', **kw), 403


def is_limited(key):
    host = request.host
    public = DEFAULT_ROOT['public']
    return public and host in public and key in LIMITED_PAGES and True or False


def _login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_app.login_manager._login_disabled:
            return func(*args, **kwargs)
        elif not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        elif request.path == '/auth/change_password':
            return func(*args, **kwargs)

        host = request.host
        link = request.path
        items = link.split('/')
        root = len(items) > 1 and items[1] or ROOT_URL
        public = DEFAULT_ROOT['public']

        base_url = current_user.base_url
        app_menu = current_user.app_menu

        if is_limited(root):
            return redirect('/auth/default')
        elif root in ('semaphore',) or 'loader' in items:
            pass
        elif root == ROOT_URL and base_url and base_url != ROOT_URL:
            return redirect(base_url)
        """
        if current_user.is_anonymous:
            return redirect('/auth/login')
        elif not LIMITED_PAGES:
            pass
        elif app_menu in ('demo', 'headoffice', 'default') and root in LIMITED_PAGES:
            pass
        elif app_menu == 'bankperso' and root in LIMITED_PAGES:
            pass
        elif app_menu == root:
            pass
        elif current_user.is_superuser() and root in ('admin',):
            pass
        elif root not in ('auth',):
            abort(403)
        """
        return func(*args, **kwargs)

    return decorated_view

login.login_required = _login_required
