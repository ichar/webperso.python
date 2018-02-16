# -*- coding: utf-8 -*-

import os
import sys
import re
from math import ceil
from datetime import datetime
from collections import namedtuple

from . import db, login_manager

from flask.ext.babel import gettext
from flask import current_app, request, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask.ext.login import UserMixin, AnonymousUserMixin

#from sqlalchemy import create_engine
from sqlalchemy import func, asc, desc, and_, or_
#from passlib.hash import sha256_crypt as spwd

from config import (
     IsDebug, IsDeepDebug, errorlog, default_unicode, default_encoding, default_print_encoding, 
     print_to, print_exception, isIterable
     )

from .database import database_config
from .settings import DEFAULT_PER_PAGE, DEFAULT_HTML_SPLITTER
from .utils import out, cid, cdate, clean

roles_names = ('Пользователь', 'Администратор', 'Менеджер', 'Оператор', 'Гость', 'Суперпользователь',)
ROLES = namedtuple('ROLES', 'USER ADMIN EDITOR OPERATOR VISITOR ROOT')
valid_user_roles = [0,1,2,3,4,9]
roles = ROLES._make(zip(valid_user_roles, roles_names))

types_names = ('Строка', 'Целое число', 'Дробное число', 'Флаг', 'ДатаВремя',)
TYPES = namedtuple('TYPES', 'STRING INT FLOAT BOOLEAN DATETIME')
valid_setting_types = [0,1,2,3,4]
types = TYPES._make(zip(valid_setting_types, types_names))

password_mask = '*'*10

admin_config = { \
    'users' : { \
        'columns' : ('id', 'login', 'name', 'email', 'role', 'confirmed', 'enabled',),
        'headers' : { \
            'id'          : ('ID',       '',),
            'login'       : ('Логин',    '',),
            'name'        : ('ФИО',      '',),
            'email'       : ('Email',    '',),
            'role'        : ('Роль',     '',),
            'confirmed'   : ('Активен',  '',),
            'enabled'     : ('Доступен', '',),
        },
        'fields' : ({ \
            'login'       : 'Логин',
            'password'    : 'Пароль',
            'email'       : 'Email',
            'family_name' : 'Фамилия',
            'first_name'  : 'Имя',
            'last_name'   : 'Отчество',
            'nick'        : 'Псевдоним',
            'role'        : 'Роль',
            'confirmed'   : 'Активен',
            'enabled'     : 'Доступ разрешен',
        }),
    },
}

UserRecord = namedtuple('UserRecord', admin_config['users']['columns'] + ('selected',))


def _add(ob):
    if IsDebug:
        print('>>> Add %s' % ob)
    db.session.add(ob)

def _delete(ob):
    if IsDebug:
        print('>>> Delete %s' % ob)
    db.session.delete(ob)

def _commit(check_session=True):
    if check_session:
        if not (db.session.new or db.session.dirty or db.session.deleted):
            if IsDebug:
                print('>>> No data to commit: new[%s], dirty[%s], deleted[%s]' % ( \
                    len(db.session.new),
                    len(db.session.dirty),
                    len(db.session.deleted))
                )
            return
    try:
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        if IsDebug:
            print('>>> Commit Error: %s' % error)
        print_to(errorlog, str(error))
    if IsDebug:
        print('>>> OK')

##  ------------
##  Help Classes
##  ------------

class Pagination(object):
    #
    # Simple Pagination
    #
    def __init__(self, page, per_page, total, value, sql):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.value = value
        self.sql = sql

    @property
    def query(self):
        return self.sql

    @property
    def items(self):
        return self.value

    @property
    def current_page(self):
        return self.page

    @property
    def pages(self):
        return int(ceil(self.total / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def get_page_params(self):
        return (self.current_page, self.pages, self.per_page, self.has_prev, self.has_next, self.total,)

    def iter_pages(self, left_edge=1, left_current=0, right_current=3, right_edge=1):
        last = 0
        out = []
        for num in range(1, self.pages + 1):
            if num <= left_edge or (
                num > self.page - left_current - 1 and num < self.page + right_current) or \
                num > self.pages - right_edge:
                if last + 1 != num:
                    out.append(None)
                out.append(num)
                last = num
        return out

##  ==========================
##  Objects Class Construction
##  ==========================

class ExtClassMethods(object):
    """
        Abstract class methods
    """
    @classmethod
    def all(cls):
        return cls.query.all()

    @classmethod
    def count(cls):
        return cls.query.count()

    @classmethod
    def get_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def print_all(cls):
        for x in cls.all():
            print(x)


class ClientProfile(db.Model, ExtClassMethods):
    """
        Пользовательский профайл (Клиенты-Банки, Клиентский сегмент)
    """
    __tablename__ = 'client_profile'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    ClientID = db.Column(db.Integer, index=True, nullable=False, default=0)

    user = db.relationship('User', backref=db.backref('clients', lazy='joined'), lazy='dynamic', uselist=True)

    def __init__(self, user, client_id):
        self.user_id = user.id
        self.ClientID = client_id

    def __repr__(self):
        return '<ClientProfile %s:[%s-%s]>' % (cid(self), str(self.user_id), str(self.ClientID))


class User(UserMixin, db.Model, ExtClassMethods):
    """
        Пользователи
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    reg_date = db.Column(db.DateTime, index=True)

    login = db.Column(db.Unicode(20), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    nick = db.Column(db.Unicode(40), default='')
    first_name = db.Column(db.Unicode(50), default='')
    family_name = db.Column(db.Unicode(50), default='')
    last_name = db.Column(db.Unicode(50), default='')
    role = db.Column(db.SmallInteger, default=roles.USER[0])
    email = db.Column(db.String(120), index=True)

    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    last_visit = db.Column(db.DateTime)
    last_pwd_changed = db.Column(db.DateTime)

    confirmed = db.Column(db.Boolean, default=False)
    enabled = db.Column(db.Boolean(), default=True)

    def __init__(self, login, name=None, role=None, email=None, **kw):
        super(User, self).__init__(**kw)
        self.login = login
        self.set_name(name, **kw)
        self.role = role in valid_user_roles and role or roles.USER[0]
        self.email = not email and '' or email
        self.reg_date = datetime.now()

    def __repr__(self):
        return '<User %s:%s %s>' % (cid(self), str(self.login), self.full_name())

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def is_superuser(self, private=False):
        return self.role in (roles.ROOT[0],)

    def is_administrator(self, private=False):
        if private:
            return self.role == roles.ADMIN[0]
        return self.role in (roles.ADMIN[0], roles.ROOT[0],)

    def is_manager(self, private=False):
        return self.role == roles.EDITOR[0]

    def is_operator(self, private=False):
        if private:
            return self.role == roles.OPERATOR[0]
        return self.role in (roles.OPERATOR[0], roles.ADMIN[0], roles.ROOT[0],)

    def is_owner(self):
        return self.login == 'admin'

    def is_any(self):
        return self.enabled and True or False

    def is_nobody(self):
        return False

    def change_password(self, password):
        self.password = password
        self.confirmed = True
        self.last_pwd_changed = datetime.now()
        db.session.add(self)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    def get_profile_clients(self, by_list=None):
        items = []
        for ob in self.clients:
            items.append(str(ob.ClientID))
        if by_list:
            return items
        return DEFAULT_HTML_SPLITTER.join(items)

    def set_profile_clients(self, data):
        is_changed = False
        for ob in self.clients:
            db.session.delete(ob)
            is_changed = True
        for id in data.split(':'):
            if not id:
                continue
            try:
                item = ClientProfile(self, int(id))
                db.session.add(item)
                is_changed = True
            except ValueError:
                pass
        if is_changed:
            _commit(True)

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def full_name(self):
        return ('%s %s %s' % (self.family_name, self.first_name, self.last_name)).strip()

    def set_name(self, name=None, **kw):
        if name and isIterable(name):
            self.first_name = name[0] or ''
            self.last_name = len(name) > 1 and name[1] or ''
            self.family_name = len(name) > 2 and name[2] or ''
        self.nick = kw.get('nick') or ''

    def get_data(self, mode=None, **kw):
        if not mode or mode == 'view':
            data = { \
                'id'          : self.id,
                'login'       : self.login,
                'name'        : self.full_name(),
                'email'       : self.email,
                'role'        : User.get_role(self.role)[1],
                'confirmed'   : self.confirmed and 'Да' or 'Нет',
                'enabled'     : self.enabled and 'Да' or 'Нет',
                'selected'    : kw.get('id') == self.id and 'selected' or '',
            }
        elif mode == 'register':
            data = { \
                'id'          : self.id,
                'login'       : self.login,
                'password'    : self.password_hash and password_mask or '',
                'family_name' : self.family_name,
                'first_name'  : self.first_name,
                'last_name'   : self.last_name,
                'email'       : self.email,
                'role'        : self.role,
                'confirmed'   : self.confirmed,
                'enabled'     : self.enabled,
            }
        else:
            data = {}
        
        return data

    @staticmethod
    def get_role(role):
        for x in roles:
            if x[0] == role:
                return x
        return None

    @staticmethod
    def get_roles(ids=None):
        return [getattr(roles, x) for x in vars(roles) if not ids or x in ids]

    @staticmethod
    def get_user_by_login(login):
        return User.query.filter_by(login=login).first()


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Setting(db.Model, ExtClassMethods):
    """
        Справочник настроек интерфейса
    """
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(100), default='')
    value_type = db.Column(db.SmallInteger, default=types.INT[0])

    profile = db.relationship('UserProfile', backref=db.backref('setting', lazy='joined'), cascade="all, delete, delete-orphan", lazy='dynamic')

    def __init__(self, name, value_type=None, **kw):
        super(Setting, self).__init__(**kw)
        self.name = name
        if value_type in valid_setting_types:
            self.value_type = value_type

    def __repr__(self):
        return '<Setting %s:%s [%s]>' % (cid(self), str(self.name), self.value_type)


class Page(db.Model, ExtClassMethods):
    """
        Справочник страниц интерфейса
    """
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(100))
    model = db.Column(db.String(20), default='global')

    profile = db.relationship('UserProfile', backref=db.backref('page', lazy='joined'), cascade="all, delete, delete-orphan", lazy='dynamic')

    def __init__(self, name, model, **kw):
        super(Page, self).__init__(**kw)
        self.name = gettext(name)
        self.model = model

    def __repr__(self):
        return '<Page %s:%s [%s]>' % (cid(self), str(self.model), str(self.name))


class StringSettingValue(db.Model, ExtClassMethods):
    """
        Значение параметра: строка
    """
    __tablename__ = 'values_string'

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(100))

    def __init__(self, value=None):
        super(StringSettingValue, self).__init__(**kw)
        self.value = value or ''

    def __repr__(self):
        return '<StringSettingValue %s: [%s]>' % (cid(self), str(self.value))


class IntSettingValue(db.Model, ExtClassMethods):
    """
        Значение параметра: Целое число
    """
    __tablename__ = 'values_int'

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer)

    def __init__(self, value=None):
        super(IntSettingValue, self).__init__(**kw)
        self.value = value or 0

    def __repr__(self):
        return '<IntSettingValue %s: [%s]>' % (cid(self), str(self.value))


class FloatSettingValue(db.Model, ExtClassMethods):
    """
        Значение параметра: Дробное число
    """
    __tablename__ = 'values_float'

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Float)

    def __init__(self, value=None):
        super(FloatSettingValue, self).__init__(**kw)
        self.value = value or 0.0

    def __repr__(self):
        return '<FloatSettingValue %s: [%s]>' % (cid(self), str(self.value))


class BooleanSettingValue(db.Model, ExtClassMethods):
    """
        Значение параметра: Флаг
    """
    __tablename__ = 'values_boolean'

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Boolean)

    def __init__(self, value=None):
        super(BooleanSettingValue, self).__init__(**kw)
        self.value = value and True or False

    def __repr__(self):
        return '<BooleanSettingValue %s: [%s]>' % (cid(self), str(self.value))


class DateTimeSettingValue(db.Model, ExtClassMethods):
    """
        Значение параметра: ДатаВремя
    """
    __tablename__ = 'values_datetime'

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.DateTime)

    def __init__(self, value=None):
        super(DateTimeSettingValue, self).__init__(**kw)
        self.value = value

    def __repr__(self):
        return '<DateTimeSettingValue %s: [%s]>' % (cid(self), cdate(self.value))


class UserProfile(db.Model, ExtClassMethods):
    """
        Профайл пользователя
    """
    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    setting_id = db.Column(db.Integer, db.ForeignKey('settings.id'))
    value_id = db.Column(db.Integer)
    """
    value_string = db.Column(db.String(100))
    value_int = db.Column(db.Integer, nullable=False, default=0)
    value_float = db.Column(db.Float, nullable=False, default=0.0)
    value_boolean = db.Column(db.Boolean, default=False)
    value_timestamp = db.Column(db.DateTime)
    """
    user = db.relationship('User', backref=db.backref('profile', lazy='joined'), lazy='dynamic', uselist=True)

    def __init__(self, page, setting, value=None, **kw):
        super(UserProfile, self).__init__(**kw)
        self.page = page
        self.setting = setting
        self.set_value(value)

    def __repr__(self):
        return '<UserProfile %s:[%s-%s]>' % (cid(self), str(self.user_id), str(self.setting_id))

    def set_value(self, value):
        if value is None:
            return
        value_type = self.setting.value_type


## ============================================================ ##

def admin_view_users(id, page=1, per_page=DEFAULT_PER_PAGE, **kw):
    context = clean(kw.get('context') or '')
    
    query = User.query

    if context:
        c = '%' + context + '%'
        
        keys = ('login', 'first_name', 'family_name', 'last_name', 'email',)
        conditions = []

        for key in keys:
            conditions.append(getattr(User, key).ilike(c))
        query = query.filter(or_(*conditions))

    total = query.count()
    offset = per_page*(page-1)
    
    if offset > 0:
        query = query.offset(offset)
    query = query.limit(per_page)
    items = query.all()
    
    users = []
    for ob in items:
        #user = [ob.id, ob.login, ob.full_name(), roles[ob.role][1], ob.is_active and 'Y' or 'N', ob.enabled and 'Y' or 'N', False]
        #yield UserRecord._make(user)
        #users.append(UserRecord._make(user))
        users.append(ob.get_data('view', id=id))

    return Pagination(page, per_page, total, users, query)

def register_user(form, id=None):
    IsOk = False
    errors = []

    if form is not None and form.validate():
        if id:
            user = User.get_by_id(id)
        else:
            user = User(form.login.data)

        if not id and form.login.data and User.get_user_by_login(form.login.data):
            errors.append( \
                'User with given login exists!')
            IsOk = False
        else:
            IsOk = True

    if IsOk:
        user.set_name((form.first_name.data, form.last_name.data, form.family_name.data,))
        user.role = form.role.data
        user.email = form.email.data
        user.confirmed = form.confirmed.data
        user.enabled = form.enabled.data

        if form.password.data and form.password.data != password_mask:
            user.password = form.password.data

        if not id:
            db.session.add(user)

        db.session.commit()

    if IsDeepDebug:
        print('--> OK:%s %s' % (IsOk, form.errors))

    return IsOk, errors

def delete_user(id):
    user = User.get_by_id(id)

    if user:
        db.session.delete(user)
        db.session.commit()

def setup():
    #engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=True)
    #Base.metadata.create_all(engine)
    db.create_all()

def updateSettings():
    """
        Словарь настроек профайла пользователя:
        
        Структура settings:
            <name>       -- String, наименование
            <page>       -- String, имя страницы, default: 'global'
            <value_type> -- Int, тип значения
            <values>     -- List, возможные значения: ('значение:наименование', ...)
            <default>    -- значение по умолчанию
    """
    pages = {
        'bankperso'    : ('WebPerso Order Registry View', 'orders'),
        'cards'        : ('WebPerso Cards Batch View', 'cards.batches'),
        'configurator' : ('WebPerso Configurator View', 'configurator-files'),
    }
    
    _DEFAULT_COLUMN_VALUES = ['1:+', '0:-']
    
    settings = ( \
        ('Состояние всплывающей командной панели', 'global', types.BOOLEAN[0], ['True:On', 'False:Off'], True,),
        ('Размер страницы', None, types.INT[0], [], 10,),
        ('Сортировка страницы', None, types.INT[0],),
        ('Список полей', None, types.INT[0], _DEFAULT_COLUMN_VALUES, 1,),
    )

    for model, value in pages.items():
        name, view = value
        config = database_config[view]

        page = Page(name, model)

        _add(page)

        title = gettext(name)

        _commit()
