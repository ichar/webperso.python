# -*- coding: utf-8 -*-

from flask import abort, render_template, redirect, request, url_for, flash
from flask.ext.login import login_user, logout_user, login_required, current_user
from flask.ext.babel import gettext

from flask import session
#from passlib.hash import pbkdf2_sha256 as hasher

from config import (
     IsDebug, IsDeepDebug, IsTrace, IsPrintExceptions, errorlog, print_to, print_exception,
     default_unicode, default_encoding, default_iso
     )

from . import auth
from ..import db, babel

from ..utils import monthdelta
from ..models import User
from ..settings import *

from .forms import LoginForm, ChangePasswordForm, PasswordResetRequestForm, PasswordResetForm

IsResponseNoCached = 0

##  ===========================
##  User Authentication Package
##  ===========================

@babel.localeselector
def get_locale():
    return get_request_item('locale') or DEFAULT_LANGUAGE

def is_valid_pwd(x):
    v = len(x) > 5 and \
        len(re.sub(r'[\D]+', '', x)) > 0 and \
        len(re.sub(r'[\d]+', '', x)) > 0 and \
        len(re.sub(r'[\w]+', '', x)) > 0 and \
        True or False
    return v

def is_pwd_changed():
    return True #current_user.last_pwd_changed and monthdelta(current_user.last_pwd_changed, 1) > current_user.last_seen and True or False

@auth.before_app_request
def before_request():
    if IsDeepDebug:
        print('--> before_request:is_authenticated:%s is_active:%s' % (current_user.is_authenticated, current_user.is_active))
    
    if not request.endpoint:
        return

    if current_user.is_authenticated and request.endpoint[:5] != 'auth.' and request.endpoint != 'static':
        current_user.ping()
        if not current_user.confirmed:
            return redirect(url_for('auth.unconfirmed'))
        if not is_pwd_changed():
            current_user.unconfirmed()
            return redirect(url_for('auth.change_password'))

def get_default_url(user):
    next = request.args.get('next')
    url = next not in ('', '/') and next or user.base_url or None
    if url and IsResponseNoCached:
        return '%s%svsc=%s' % (url, '?' in url and '&' or '?', vsc()[1:])
    return url or 'default'

def menu(force=None):
    kw = make_platform()
    if kw.get('is_mobile') or force:
        kw.update({
            'navigation' : get_navigation(),
            'module'     : 'auth',
            'width'      : 1080,
            'message'    : gettext('Main menu').upper(),
            'vsc'        : vsc(),
        })
        return render_template("default.html", **kw)
    return redirect(url_for('bankperso.start'))


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if IsDeepDebug:
        print('--> current_user.is_active:%s' % current_user.is_active)

    form = LoginForm()
    login = form.login.data

    if login and form.validate_on_submit():
        user = User.query.filter_by(login=login).first()
    else:
        user = None

    if user is not None:
        accessed_link = get_default_url(user)

        is_valid_password = user.verify_password(form.password.data)
        is_admin = user.is_administrator()
        is_confirmed = user.confirmed
        is_enabled = user.enabled

        if IsDeepDebug:
            print('--> user:%s valid:%s enabled:%s is_admin:%s' % (user and user.login, 
                is_valid_password, is_enabled, is_admin))

        IsEnabled = False

        if not is_enabled:
            flash('Access to the service is denied!')
        elif not is_valid_password:
            flash('Password is incorrect!')
        elif not is_confirmed:
            flash('You should change you password!')
            accessed_link = url_for('auth.change_password')
            IsEnabled = True
        elif 'admin' in accessed_link and not is_admin:
            flash('You cannot access this page!')
        else:
            IsEnabled = True

        if IsDeepDebug:
            print('--> link:%s enabled:%s' % (accessed_link, IsEnabled))

        if IsTrace:
            print_to(errorlog, '\n==> login:%s %s enabled:%s' % (user.login, request.remote_addr, is_valid_password), request=request)

        if IsEnabled:
            try:
                login_user(user, remember=form.remember_me.data)
            except Exception as ex:
                print_to(errorlog, '!!! auth.login error: %s %s' % (login, str(ex)))
                if IsPrintExceptions:
                    print_exception()

            if accessed_link in ('default', '/'):
                return menu()
            return redirect(accessed_link)

    elif login:
        if IsTrace:
            print_to(errorlog, '\n==> login:%s is invalid!!! %s' % (login, request.remote_addr,))

        flash('Invalid username or password.')

    kw = make_platform(mode='auth')

    kw.update({
        'title'        : gettext('WebPerso Login'),
        'page_title'   : gettext('WebPerso Auth'),
        'header_class' : 'middle-header',
        'show_flash'   : True,
        'semaphore'    : {'state' : ''},
        'sidebar'      : {'state' : 0, 'title' : ''},
    })

    kw['vsc'] = vsc()

    link = 'auth/login%s.html' % (IsEdge() and '_default' or '')

    return render_template(link, form=form, **kw)


@auth.route('/default', methods=['GET', 'POST'])
def default():
    return menu(1)


@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if IsDeepDebug:
        print('--> change password:is_active:%s' % current_user.is_active)

    form = ChangePasswordForm()

    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            if not is_valid_pwd(form.password.data):
                flash('Invalid password syntax.')
            else:
                current_user.change_password(form.password.data)
                flash('Your password has been updated.')
                return default()
        else:
            flash('Invalid password.')
    elif not form.old_password.data:
        pass
    else:
        flash('ChangePasswordForm data is invalid.')

    if IsDeepDebug:
        print('--> password invalid: [%s-%s-%s]' % (form.old_password.data, form.password.data, form.password2.data))

    kw = make_platform(mode='auth')

    kw.update({
        'title'        : gettext('WebPerso Change Password'),
        'page_title'   : gettext('WebPerso Reset Password'),
        'header_class' : 'middle-header',
        'show_flash'   : True,
        'semaphore'    : {'state' : ''},
        'sidebar'      : {'state' : 0, 'title' : ''},
        'module'       : 'auth',
    })

    kw['vsc'] = vsc()

    link = 'auth/change_password%s.html' % (IsEdge() and '_default' or '')

    return render_template(link, form=form, **kw)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))


@auth.route('/operator')
@login_required
def operator():
    logout_user()
    return redirect(url_for('persostation.register'))


@auth.route('/provision')
@login_required
def provision():
    logout_user()
    return redirect(url_for('provision.start')+'?sidebar=0&short=1')


@auth.route('/forbidden')
def forbidden():
    abort(403)


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous:
        return redirect(url_for('auth.login'))

    kw = make_platform(mode='auth')

    kw.update({
        'title'        : gettext('WebPerso Unconfirmed'),
        'page_title'   : gettext('WebPerso Reset Password'),
        'header_class' : 'middle-header',
        'show_flash'   : True,
        'semaphore'    : {'state' : ''},
        'sidebar'      : {'state' : 0, 'title' : ''},
        'module'       : 'auth',
    })

    kw['vsc'] = vsc()

    return render_template('auth/unconfirmed.html', **kw)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('auth.default'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('auth.default'))
