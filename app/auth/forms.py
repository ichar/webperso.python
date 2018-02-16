# -*- coding: utf-8 -*-

from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import Required, Length, Regexp, EqualTo
from wtforms import ValidationError

from ..models import User


class LoginForm(Form):
    login = StringField('Логин:', validators=[Required(), Length(1, 64)])
    password = PasswordField('Пароль:', validators=[Required()])
    remember_me = BooleanField('Сохранять подключение', default=True)
    submit = SubmitField('Войти')


class ChangePasswordForm(Form):
    old_password = PasswordField('Старый пароль:', validators=[Required()])
    password = PasswordField('Новый пароль:', validators=[Required(),
                                                          EqualTo('password2', message='Пароль должен совпадать')])
    password2 = PasswordField('Подтверждение пароля:', validators=[Required()])
    submit = SubmitField('Обновить')


class PasswordResetRequestForm(Form):
    login = StringField('Login', validators=[Required(), Length(1, 64)])
    submit = SubmitField('Reset Password')


class PasswordResetForm(Form):
    login = StringField('Login', validators=[Required(), Length(1, 64)])
    password = PasswordField('New Password', validators=[Required(),
                                                         EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm password', validators=[Required()])
    submit = SubmitField('Reset Password')

    def validate_login(self, field):
        if User.query.filter_by(login=field.data).first() is None:
            raise ValidationError('Unknown Login.')


class ChangeLoginForm(Form):
    login = StringField('Login', validators=[Required(), Length(1, 64)])
    password = PasswordField('Password', validators=[Required()])
    submit = SubmitField('Update Login')

    def validate_login(self, field):
        if User.query.filter_by(login=field.data).first():
            raise ValidationError('Login already registered.')
