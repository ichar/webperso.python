# -*- coding: utf-8 -*-

from flask import render_template, redirect, request, url_for, flash
from flask.ext.login import login_user, logout_user, login_required, current_user
from flask.ext.babel import gettext

from config import (
     IsDebug, IsDeepDebug, IsTrace, errorlog, print_to, print_exception,
     default_unicode, default_encoding, default_iso
     )

from . import auth
from .. import db, babel

from ..models import User
from ..settings import DEFAULT_LANGUAGE
from .forms import LoginForm, ChangePasswordForm, PasswordResetRequestForm, PasswordResetForm

##  ===========================
##  User Authentication Package
##  ===========================

@babel.localeselector
def get_locale():
    return DEFAULT_LANGUAGE

@auth.before_app_request
def before_request():
    if IsDeepDebug:
        print('--> before_request:is_authenticated:%s is_active:%s' % (current_user.is_authenticated, current_user.is_active))
    
    if not request.endpoint:
        return

    if current_user.is_authenticated \
            and request.endpoint[:5] != 'auth.' \
            and request.endpoint != 'static':
        current_user.ping()
        if not current_user.confirmed:
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if IsDeepDebug:
        print('--> current_user.is_active:%s' % current_user.is_active)

    default_link = 'auth/login.html'

    form = LoginForm()
    login = form.login.data

    if login and form.validate_on_submit():
        user = User.query.filter_by(login=login).first()
    else:
        user = None

    link = default_link

    if user is not None:
        accessed_link = request.args.get('next') or url_for('bankperso.index')
        is_valid_password = user.verify_password(form.password.data)
        is_admin = user.is_administrator()
        is_confirmed = user.confirmed
        is_enabled = user.enabled

        if IsDeepDebug:
            print('--> user:%s valid:%s enabled:%s is_admin:%s' % (user and user.login, \
                is_valid_password, is_enabled, is_admin))

        if not is_enabled:
            flash('Access to the service is denied!')
            IsEnabled = False
        elif not is_valid_password:
            flash('Password is incorrect!')
            IsEnabled = False
        elif not is_confirmed:
            flash('You should change you password!')
            accessed_link = url_for('auth.change_password')
            IsEnabled = True
        elif 'admin' in accessed_link and not is_admin:
            flash('You cannot access this page!')
            IsEnabled = False
        else:
            IsEnabled = True

        if IsDeepDebug:
            print('--> link:%s enabled:%s' % (accessed_link, IsEnabled))

        if IsTrace:
            print_to(errorlog, '\n==> login:%s %s enabled:%s' % (user.login, request.remote_addr, is_valid_password), request=request)

        if IsEnabled:
            login_user(user, form.remember_me.data)
            return redirect(accessed_link)

    elif login:
        if IsTrace:
            print_to(errorlog, '\n==> login:%s is invalid!!! %s' % (login, request.remote_addr,))

        flash('Invalid username or password.')

    kw = {
        'title'        : gettext('WebPerso Login'),
        'page_title'   : gettext('WebPerso Auth'),
        'header_class' : 'middle-header',
        'show_flash'   : True,
        'semaphore'    : {'state' : ''},
        'sidebar'      : {'state' : 0, 'title' : ''},
    }

    return render_template(link, form=form, **kw)


@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if IsDeepDebug:
        print('--> change password:is_active:%s' % current_user.is_active)

    form = ChangePasswordForm()

    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.change_password(form.password.data)
            flash('Your password has been updated.')
            return redirect(url_for('bankperso.index'))
        else:
            flash('Invalid password.')

    if IsDeepDebug:
        print('--> password invalid')

    kw = {
        'title'        : gettext('WebPerso Change Password'),
        'page_title'   : gettext('WebPerso Reset Password'),
        'header_class' : 'middle-header',
        'show_flash'   : True,
        'semaphore'    : {'state' : ''},
        'sidebar'      : {'state' : 0, 'title' : ''},
    }

    return render_template("auth/change_password.html", form=form, **kw)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))

"""
@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('admin.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('admin.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('admin.index'))
"""
