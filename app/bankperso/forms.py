# -*- coding: utf-8 -*-

from flask.ext.wtf import Form
from wtforms import StringField, BooleanField, PasswordField, SelectField, validators
from wtforms.validators import DataRequired

from ..models import admin_config, User

class LoginForm(Form):
    openid = StringField('openid', validators=[DataRequired()])
    remember_me = BooleanField('remember_me', default=False)
