# -*- coding: utf-8 -*-

import os
import sys
import re
from math import ceil
from datetime import datetime
from collections import namedtuple
from operator import itemgetter
import requests, json
from requests.exceptions import ConnectionError

from . import db, login_manager

from flask.ext.babel import gettext
from flask_babel import lazy_gettext as _l
from flask import current_app, request, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask.ext.login import UserMixin, AnonymousUserMixin

from sqlalchemy import create_engine, MetaData
from sqlalchemy import func, asc, desc, and_, or_
#from sqlalchemy.ext.hybrid import hybrid_property
#from passlib.hash import sha256_crypt as spwd

from config import (
     IsDebug, IsDeepDebug, IsPrintExceptions, errorlog, default_unicode, default_encoding, default_print_encoding, 
     print_to, print_exception, isIterable)

from .settings import DEFAULT_PER_PAGE, DEFAULT_HTML_SPLITTER
from .utils import getDateOnly, getToday, out, cid, cdate, clean

roles_ids = ['USER', 'ADMIN', 'EDITOR', 'OPERATOR', 'VISITOR', 'X1', 'X2', 'X3', 'X4', 'ROOT']
roles_names = tuple([_l(x) for x in roles_ids])
ROLES = namedtuple('ROLES', ' '.join(roles_ids))
valid_user_roles = [n for n, x in enumerate(roles_ids)]
roles = ROLES._make(zip(valid_user_roles, roles_names))

app_roles_ids = ['EMPLOYEE', 'MANAGER', 'CHIEF', 'ADMIN', 'CTO', 'CAO', 'HEADOFFICE', 'ASSISTANT', 'CEO', 'HOLDER']
app_roles_names = tuple([_l(x) for x in app_roles_ids])
APP_ROLES = namedtuple('ROLES', ' '.join(app_roles_ids))
valid_user_app_roles = [n for n, x in enumerate(app_roles_ids)]
app_roles = APP_ROLES._make(zip(valid_user_app_roles, app_roles_names))

USER_DEFAULT_PHOTO = '/static/img/person-default.jpg'

password_mask = '*'*10

admin_config = {
    'users' : {
        'columns' : ('id', 'login', 'name', 'post', 'email', 'role', 'confirmed', 'enabled',),
        'headers' : {
            'id'          : (_l('ID'),               '',),
            'login'       : (_l('Login'),            '',),
            'name'        : (_l('Full person name'), '',),
            'post'        : (_l('Post'),             '',),
            'email'       : (_l('Email'),            '',),
            'role'        : (_l('Role'),             '',),
            'confirmed'   : (_l('Confirmed'),        '',),
            'enabled'     : (_l('Enabled'),          '',),
        },
        'fields' : ({
            'login'       : _l('Login'),
            'password'    : _l('Password'),
            'family_name' : _l('Family name'),
            'first_name'  : _l('First name'),
            'last_name'   : _l('Last name'),
            'nick'        : _l('Nick'),
            'post'        : _l('Post'),
            'email'       : _l('Email'),
            'role'        : _l('Role'),
            'confirmed'   : _l('Confirmed'),
            'enabled'     : _l('Enabled'),
        }),
    },
}

UserRecord = namedtuple('UserRecord', admin_config['users']['columns'] + ('selected',))


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
                    out.append(-1)
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


class Photo(db.Model, ExtClassMethods):
    """
        Пользовательский профайл (Фото)
    """
    __tablename__ = 'photo'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    data = db.Column(db.Text, nullable=True, default=None)

    user = db.relationship('User', backref=db.backref('photos', lazy='joined'), lazy='dynamic', uselist=True)

    def __init__(self, user, data):
        self.user_id = user.id
        self.data = data

    def __repr__(self):
        return '<Photo %s:[%s-%s]>' % (cid(self), str(self.user_id), self.data and 'Y' or 'N')


class Settings(db.Model, ExtClassMethods):
    """
        Пользовательский профайл (настройки интерфейса)
    """
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    pagesize_bankperso = db.Column(db.Integer, nullable=True)
    pagesize_cards = db.Column(db.Integer, nullable=True)
    pagesize_persostation = db.Column(db.Integer, nullable=True)
    pagesize_config = db.Column(db.Integer, nullable=True)
    pagesize_provision = db.Column(db.Integer, nullable=True)

    sidebar_collapse = db.Column(db.Boolean, default=True)
    use_extra_infopanel = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('settings', lazy='joined'), lazy='dynamic', uselist=True)

    def __init__(self, user):
        self.user_id = user.id

    def __repr__(self):
        return '<Settings %s:[%s-%s]>' % (cid(self), str(self.user_id), self.user_id and 'Y' or 'N')


class Subdivision(db.Model, ExtClassMethods):
    """
        Подразделения организации
    """
    __tablename__ = 'subdivisions'

    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(20), index=True)
    name = db.Column(db.Unicode(50), default='')
    manager = db.Column(db.Unicode(50), default='')
    fullname = db.Column(db.Unicode(200), default='')
    
    def __init__(self, code, name, manager=None, fullname=None):
        self.code = code
        self.name = name
        self.manager = manager
        self.fullname = fullname

    def __repr__(self):
        return '<Subdivision %s:[%s-%s]>' % (cid(self), str(self.code), self.name)

    @classmethod
    def get_by_code(cls, code):
        return cls.query.filter_by(code=code).first()

    @classmethod
    def get_manager(cls, id):
        return cls.query.filter_by(id=id).first().manager


class Privileges(db.Model, ExtClassMethods):
    """
        Привилегии пользователей
    """
    __tablename__ = 'privileges'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subdivision_id = db.Column(db.Integer, db.ForeignKey('subdivisions.id'))

    menu = db.Column(db.String(50), default='')
    base_url = db.Column(db.String(120), index=True)
    role = db.Column(db.SmallInteger, default=app_roles.EMPLOYEE[0])

    is_manager = db.Column(db.Boolean, default=False)
    is_author = db.Column(db.Boolean, default=False)
    is_consultant = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('privileges', lazy='joined'), lazy='dynamic', uselist=True)
    subdivision = db.relationship('Subdivision', backref=db.backref('privileges', lazy='joined'), lazy='dynamic', uselist=True)

    def __init__(self, user, subdivision):
        self.user_id = user.id
        self.subdivision_id = subdivision and subdivision.id or None

    def __repr__(self):
        return '<Privileges %s:[%s-%s] [%s] [%s] %s>' % (
            cid(self), 
            str(self.user_id), 
            str(self.subdivision_id), 
            self.app_role_name,
            '%s|%s' % (self.subdivision_name, self.subdivision_code),
            self.user[0].login
            )

    @property
    def app_role_name(self):
        return self.role in valid_user_app_roles and app_roles_names[self.role] or gettext('undefined')

    @property
    def subdivision_name(self):
        return self.subdivision and self.subdivision[0].name or ''

    @property
    def subdivision_fullname(self):
        return self.subdivision and self.subdivision[0].fullname or ''

    @property
    def subdivision_code(self):
        return self.subdivision and self.subdivision[0].code or ''


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

    post = db.Column(db.String(100), default='')

    def __init__(self, login, name=None, role=None, email=None, **kw):
        super(User, self).__init__(**kw)
        self.login = login
        self.set_name(name, **kw)
        self.role = role in valid_user_roles and role or roles.USER[0]
        self.post = kw.get('post') or ''
        self.email = not email and '' or email
        self.reg_date = datetime.now()

    def __repr__(self):
        return '<User %s:%s %s>' % (cid(self), str(self.login), self.full_name())

    @classmethod
    def get_by_login(cls, login):
        return cls.query.filter_by(login=login).first()

    @classmethod
    def get_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @property
    def role_name(self):
        return self.role in valid_user_roles and roles_names[self.role] or gettext('undefined')

    def has_privileges(self):
        return self.privileges is not None and len(self.privileges) > 0 and True or False

    @property
    def app_role(self):
        return self.has_privileges() and self.privileges[0].role

    @property
    def app_role_name(self):
        role = self.app_role
        return role in valid_user_app_roles and app_roles_names[role] or ''

    @property
    def subdivision(self):
        return self.has_privileges() and self.privileges[0].subdivision_id or 0

    @property
    def subdivision_id(self):
        return self.has_privileges() and self.privileges[0].subdivision_id or None

    @property
    def subdivision_name(self):
        return self.has_privileges() and self.privileges[0].subdivision_name or None

    @property
    def subdivision_fullname(self):
        return self.has_privileges() and self.privileges[0].subdivision_fullname or None

    @property
    def subdivision_code(self):
        return self.has_privileges() and self.privileges[0].subdivision_code or None

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def change_password(self, password):
        self.password = password
        self.confirmed = True
        self.last_pwd_changed = datetime.now()
        db.session.add(self)

    def unconfirmed(self):
        self.confirmed = False
        db.session.add(self)

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
        if private:
            return self.role == roles.EDITOR[0]
        return self.role in (roles.EDITOR[0], roles.ADMIN[0], roles.ROOT[0],)

    def is_operator(self, private=False):
        if private:
            return self.role == roles.OPERATOR[0]
        return self.role in (roles.OPERATOR[0], roles.ADMIN[0], roles.ROOT[0],)

    def is_owner(self):
        return self.login == 'admin'

    def is_any(self):
        return self.enabled and True or False

    def is_anybody(self):
        return self.is_any()

    def is_nobody(self):
        return False

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

    def get_avatar(self):
        return self.photos and '<img class="avatar" src="%s" title="" alt="">' % self.photos[0].data or ''

    def get_photo(self):
        return self.photos and self.photos[0].data or USER_DEFAULT_PHOTO

    def set_photo(self, data):
        is_changed = False
        for ob in self.photos:
            db.session.delete(ob)
            is_changed = True
        try:
            item = Photo(self, data)
            db.session.add(item)
            is_changed = True
        except ValueError:
            pass
        if is_changed:
            _commit(True)

    def delete_photo(self):
        is_changed = False
        for ob in self.photos:
            db.session.delete(ob)
            is_changed = True
        if is_changed:
            _commit(True)
        return self.get_photo()

    def get_pagesize(self, model):
        if not model or model == 'bankperso':
            return self.pagesize_bankperso
        elif model == 'cards':
            return self.pagesize_cards
        elif model == 'persostation':
            return self.pagesize_persostation
        elif model in 'config:configurator':
            return self.pagesize_config
        elif model == 'provision':
            return self.pagesize_provision
        return None

    def set_pagesize(self, model, value):
        is_changed = False
        if not self.has_settings():
            settings = self.add_settings()
            is_changed = True
        else:
            settings = self.settings[0]
        if not model or model == 'bankperso':
            settings.pagesize_bankperso = value
            is_changed = True
        elif model == 'cards':
            settings.pagesize_cards = value
            is_changed = True
        elif model == 'persostation':
            settings.pagesize_persostation = value
            is_changed = True
        elif model in 'config:configurator':
            settings.pagesize_config = value
            is_changed = True
        elif model == 'provision':
            settings.pagesize_provision = value
            is_changed = True
        if is_changed:
            _commit(True)

    def has_settings(self):
        return self.settings and len(self.settings) > 0

    @property
    def pagesize_bankperso(self):
        return self.has_settings() and self.settings[0].pagesize_bankperso or 10

    @property
    def pagesize_cards(self):
        return self.has_settings() and self.settings[0].pagesize_cards or 20

    @property
    def pagesize_persostation(self):
        return self.has_settings() and self.settings[0].pagesize_persostation or 10

    @property
    def pagesize_config(self):
        return self.has_settings() and self.settings[0].pagesize_config or 10

    @property
    def pagesize_provision(self):
        return self.has_settings() and self.settings[0].pagesize_provision or 10

    @property
    def sidebar_collapse(self):
        if self.has_settings():
            return self.settings[0].sidebar_collapse or False
        else:
            return False

    @sidebar_collapse.setter
    def sidebar_collapse(self, collapse):
        is_changed = False
        if not self.has_settings():
            settings = self.add_settings()
            is_changed = True
        else:
            settings = self.settings[0]
        if settings.sidebar_collapse != collapse:
            settings.sidebar_collapse = collapse
            is_changed = True
        if is_changed:
            _commit(True)

    @property
    def use_extra_infopanel(self):
        if self.has_settings():
            return self.has_settings() and self.settings[0].use_extra_infopanel or False
        else:
            return False

    def get_settings(self):
        return [self.pagesize_bankperso, 
                self.pagesize_cards, 
                self.pagesize_persostation, 
                self.pagesize_config, 
                self.pagesize_provision, 
                self.sidebar_collapse, 
                self.use_extra_infopanel
            ]

    def add_settings(self):
        settings = Settings(self)
        db.session.add(settings)
        return settings

    def set_settings(self, values):
        if not values:
            return
        check_session = True
        is_changed = False
        is_add = False
        try:
            if not self.settings:
                settings = Settings(self)
                is_add = True
            else:
                settings = self.settings[0]
            settings.pagesize_bankperso = int(values[0])
            settings.pagesize_cards = int(values[1])
            settings.pagesize_persostation = int(values[2])
            settings.pagesize_config = int(values[3])
            settings.pagesize_config = int(values[4])
            settings.sidebar_collapse = values[5] == '1' and True or False
            settings.use_extra_infopanel = values[6] == '1' and True or False
            if is_add:
                db.session.add(settings)
            else:
                self.settings[0] = settings
                check_session = False
            is_changed = True
        except ValueError:
            pass
        if is_changed:
            _commit(check_session)

    @property
    def app_role(self):
        return self.has_privileges() and self.privileges[0].role or 0

    @property
    def app_menu(self):
        return self.has_privileges() and self.privileges[0].menu or 'bankperso'

    @property
    def app_is_manager(self):
        # Роль: Менеджер
        return self.has_privileges() and self.privileges[0].is_manager or False

    @property
    def app_is_author(self):
        # Роль: Автор
        return self.has_privileges() and self.privileges[0].is_author or False

    @property
    def app_is_consultant(self):
        # Роль: Консультант
        return self.has_privileges() and self.privileges[0].is_consultant or False

    @property
    def app_is_office_direction(self):
        # Роль: Административное руководство
        return self.subdivision_code in ('0001','0002','0003','0004') and True or False

    @property
    def app_is_office_execution(self):
        # Роль: Исполнительное руководство
        return self.subdivision_code in ('0003','0004','0005','0007') and self.app_role >= app_roles.CHIEF[0] and True or False

    @property
    def app_role_ceo(self):
        # Роль: Генеральный директор
        return self.app_role == app_roles.CEO[0]

    @property
    def app_role_assistant(self):
        # Роль: Заместитель Генерального директора
        return self.app_role == app_roles.ASSISTANT[0]

    @property
    def app_role_chief(self):
        # Роль: Руководитель подразделения
        return self.app_role == app_roles.CHIEF[0]

    @property
    def app_role_headoffice(self):
        # Роль: Исполнительный директор
        return self.app_role == app_roles.HEADOFFICE[0]

    @property
    def app_role_cao(self):
        # Роль: Главный бухгалтер
        return self.app_role == app_roles.CAO[0]

    @property
    def app_role_cto(self):
        # Роль: Главный инженер
        return self.app_role == app_roles.CTO[0]

    @property
    def app_is_provision_manager(self):
        # Роль: Менеджеры снабжения
        return self.app_is_manager and (
                self.subdivision_code == '0008' and self.app_role > app_roles.EMPLOYEE[0]
                ) or self.is_owner()

    @staticmethod
    def has_subdivision_group(code):
        # Производственное подразделение (внутри цеха)
        return code and code[:3] > '000' and code[3] > '0' and True or False

    @staticmethod
    def get_subdivision_group(code):
        # Код цеха
        return code and '%s0' % code[0:3] or '0000'

    @property
    def get_manufacture_codes(self):
        # Производственные подразделения
        return ('0030','0040','0050','0060','0070')

    @property
    def app_is_manufacture(self):
        # Производственное подразделение (цех/филиал)
        code = self.get_subdivision_group(self.subdivision_code)
        return code in self.get_manufacture_codes and True or False

    @property
    def app_is_assistant_group(self):
        # Подразделение Заместителя Генерального директора
        s = self.subdivision_code
        return s and (
              (s[0:2] == '00' and s[2] > '0') or 
              (s[1] > '0')
            ) and True or False

    @property
    def base_url(self):
        return self.has_privileges() and self.privileges[0].base_url or ''

    def get_privileges(self):
        return [self.subdivision, 
                self.app_role, 
                self.app_menu, 
                self.base_url, 
                self.app_is_manager, 
                self.app_is_author,
                self.app_is_consultant,
            ]

    def set_privileges(self, values):
        if not values:
            return
        check_session = True
        is_changed = False
        is_add = False
        try:
            subdivision_id = int(values[0])
            subdivision = Subdivision.get_by_id(subdivision_id)
            if not self.privileges:
                privileges = Privileges(self, subdivision)
                is_add = True
            else:
                privileges = self.privileges[0]
                if privileges.subdivision_id != subdivision_id:
                    privileges.subdivision_id = subdivision_id
            privileges.role = int(values[1])
            privileges.menu = values[2]
            privileges.base_url = values[3]
            privileges.is_manager = values[4] == '1' and True or False
            privileges.is_author = values[5] == '1' and True or False
            privileges.is_consultant = values[6] == '1' and True or False
            if is_add:
                db.session.add(privileges)
            else:
                self.privileges[0] = privileges
                check_session = False
            is_changed = True
        except ValueError:
            pass
        if is_changed:
            _commit(check_session)

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
            data = { 
                'id'          : self.id,
                'login'       : self.login,
                'name'        : self.full_name(),
                'post'        : self.post,
                'email'       : self.email,
                'role'        : User.get_role(self.role)[1],
                'confirmed'   : self.confirmed and 'Да' or 'Нет',
                'enabled'     : self.enabled and 'Да' or 'Нет',
                'selected'    : kw.get('id') == self.id and 'selected' or '',
            }
        elif mode == 'register':
            data = { 
                'id'          : self.id,
                'login'       : self.login,
                'password'    : self.password_hash and password_mask or '',
                'family_name' : self.family_name,
                'first_name'  : self.first_name,
                'last_name'   : self.last_name,
                'post'        : self.post,
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

    @staticmethod
    def app_root(key=None, code=None):
        # Объект: Подразделение, по умолчанию - Администрация (ROOT)
        ob = Subdivision.query.filter_by(code=code or '0002').first()
        return ob and key and getattr(ob, key) or ob

    @staticmethod
    def get_managers(code):
        """
            Returns subdivision managers list: chief and manager roles.
        """
        items = []

        ob = Subdivision.query.filter_by(code=code).first()
        if ob is None:
            return items

        subdivision_id = ob.id
        roles = [app_roles.CHIEF[0], app_roles.MANAGER[0]]

        privileges = db.session.query(Privileges).filter_by(subdivision_id=subdivision_id).filter(Privileges.role.in_(roles)).all()

        for ob in privileges:
            user = User.query.filter_by(id=ob.user_id).first()
            items.append(user)

        return items

    def managers(self, id=None, key=None, with_headoffice=None, with_assistant=None, with_root=None):
        """
            Returns Managers of user's, or their `key` attribute, `email` as a rule.
            
            Arguments:
                id      -- subdivision id, if not present - user (instance) subdivision id
                key     -- type of data to return
        """
        items = []

        def _add(subdivision_id, role=app_roles.CHIEF[0]):
            if not subdivision_id:
                return
            for ob in Privileges.query.filter_by(subdivision_id=subdivision_id).filter_by(role=role).all():
                if ob is None:
                    continue
                user = User.query.filter_by(id=ob.user_id).first()
                items.append(user)
        #
        # Руководитель подразделения
        #
        try:
            _add(id or self.subdivision_id)
        except:
            pass
        #
        # Начальник цеха
        #
        subdivision_code = self.subdivision_code

        parent = None
        parent_code = self.get_subdivision_group(subdivision_code)

        if self.has_subdivision_group(subdivision_code):
            #parent = Subdivision.query.filter_by(code=parent_code).first()
            parent = self.app_root(code=parent_code)

        try:
            if parent is not None:
                _add(parent.id)
        except:
            pass
        #
        # Главный инженер
        #
        cto = self.app_root(code='0012')

        try:
            if self.app_is_manufacture:
                _add(cto.id, role=app_roles.CTO[0])
        except:
            pass
        #
        # Исполнительный директор
        #
        headoffice = None

        if parent_code in self.get_manufacture_codes:
            headoffice = self.app_root(code='0002')

        try:
            if with_headoffice and headoffice is not None:
                _add(headoffice.id, role=app_roles.HEADOFFICE[0])
        except:
            pass
        #
        # Заместитель Генерального директора (профильная компания/дирекция)
        #
        assistant = None

        if self.app_is_assistant_group:
            assistant = self.app_root(code=parent_code)

        try:
            if with_assistant and assistant is not None:
                _add(assistant.id, role=app_roles.ASSISTANT[0])
        except:
            pass
        #
        # Генеральный директор
        #
        root = self.app_root(code='0001')

        try:
            if with_root and root is not None:
                _add(root.id, role=app_roles.CEO[0])
        except:
            pass

        if key:
            items = [getattr(ob, key) for ob in items]

        return list(filter(None, items))


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser


class ExchangeRate(db.Model, ExtClassMethods):
    """
        Курсы валют
    """
    __tablename__ = 'rates'

    id = db.Column(db.Integer, primary_key=True)
    last_refreshed = db.Column(db.DateTime)

    rating = db.Column(db.String(50))
    currency = db.Column(db.String(10))
    cross = db.Column(db.Float, nullable=True)
    timezone = db.Column(db.String(10), nullable=True)

    def __init__(self, rating, currency, timezone=None):
        self.rating = rating
        self.currency = currency
        self.timezone = timezone

    def __repr__(self):
        return '<ExchangeRate %s:[%s] %s %s>' % (cid(self), self.currency, str(self.cross), str(self.last_refreshed))

    def update(self, cross):
        self.cross = cross
        self.last_refreshed = datetime.now()

    @staticmethod
    def currency_codes():
        return [x.split(':') for x in ('RUB:EUR', 'RUB:USD', 'USD:EUR', 'EUR:RUB', 'USD:RUB')]

    @staticmethod
    def is_uptodate():
        today = getDateOnly(getToday())
        return ExchangeRate.query.filter(ExchangeRate.last_refreshed > today).first() is not None

    @staticmethod
    def refresh(check, key=None):
        if check and ExchangeRate.is_uptodate():
            return
        
        rating = 'https://www.alphavantage.co'
        
        is_error = is_changed = is_add = False
        ob = None

        for source_code, code in ExchangeRate.currency_codes():
            currency = '%s:%s' % (source_code, code)

            url = '%s/query?function=CURRENCY_EXCHANGE_RATE&from_currency=%s&to_currency=%s&apikey=%s' % (
                rating, source_code, code, key or 'CRRAPQKU6BGLZG7Q')

            is_add = False

            try:
                ob = requests.get(url)
                if ob is not None:
                    data = ob.json().get('Realtime Currency Exchange Rate')
                    if data and isinstance(data, dict):
                        cross = float(data.get('5. Exchange Rate'))
                        timezone = data.get('7. Time Zone')

                        rate = ExchangeRate.query.filter_by(rating=rating).filter_by(currency=currency).first()
                        if rate is None:
                            rate = ExchangeRate(rating, currency, timezone)
                            is_add = True

                        rate.update(cross)

                        if is_add:
                            db.session.add(rate)

                        is_changed = True
            except ConnectionError:
                is_error = True
            except:
                if IsDebug:
                    print(url, repr(ob), ob and ob.json())
                    #raise
                if IsPrintExceptions:
                    print_exception()
                is_error = True
                break

        if is_changed and not is_error:
            _commit(1)

    @staticmethod
    def get_cross(currency):
        rate = ExchangeRate.query.filter_by(currency=currency).first()
        return rate and rate.cross or None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

## ============================================================ ##

def admin_view_users(id, page=1, per_page=DEFAULT_PER_PAGE, **kw):
    context = clean(kw.get('context') or '')
    
    query = db.session.query(User) #query = User.query

    where = kw.get('where')

    if where:
        is_joined = 0

        for k in where.keys():
            v = where[k]

            if v is None or v == -1:
                continue

            if not is_joined and k in ('subdivision_id', 'app_role_id', 'app_privilege'):
                query = query.join(Privileges)
                is_joined = 1

            if not k:
                pass
            elif k == 'subdivision_id':
                query = query.filter(Privileges.subdivision_id==v)
            elif k == 'app_role_id':
                query = query.filter(Privileges.role==v)
            elif k == 'app_privilege':
                if v == 1:
                    query = query.filter(Privileges.is_manager==1)
                if v == 2:
                    query = query.filter(Privileges.is_consultant==1)
                if v == 3:
                    query = query.filter(Privileges.is_author==1)
            elif k == 'role_id':
                query = query.filter(User.role==v)
            elif k == 'confirmed':
                query = query.filter(User.confirmed==v)
            elif k == 'enabled':
                query = query.filter(User.enabled==v)

    if context:
        c = '%' + context + '%'
        
        keys = ('login', 'first_name', 'family_name', 'last_name', 'email',)
        conditions = []

        for key in keys:
            conditions.append(getattr(User, key).ilike(c))
        query = query.filter(or_(*conditions))

    order = kw.get('order')

    if order:
        if order == 'fio':
            query = query.order_by(User.family_name).order_by(User.first_name).order_by(User.last_name)
        else:
            query = query.order_by(
                order == 'login' and User.login or 
                order == 'email' and User.email or 
                order == 'role' and User.role or 
                order == 'post' and User.post or
                ''
                )

    total = query.count()
    offset = per_page*(page-1)
    
    if offset > 0:
        query = query.offset(offset)
    query = query.limit(per_page)
    items = query.all()

    mode = kw.get('mode') or 0
    selected = ''

    users = []
    for ob in items:
        if mode:
            user = [ob.id, ob.login, ob.full_name(), ob.post, ob.email, roles[ob.role], ob.is_active and 'Y' or 'N', 
                ob.enabled and 'Y' or 'N', False]
            if mode == 2:
                users.append(UserRecord._make(user)) # yield UserRecord._make(user)
            else:
                users.append(user)
        else:
            users.append(ob.get_data('view', id=id))
            if not selected:
                selected = users[-1].get('selected')

    if not selected and len(users) > 0 and not mode:
        users[0]['selected'] = 'selected'

    if not mode:
        return Pagination(page, per_page, total, users, query)
    return users

def get_users(key=None):
    users = []
    for ob in User.all():
        if not (ob.is_active and ob.enabled and ob.email and ob.subdivision_id):
            continue
        users.append((
            ob.login,
            ob.full_name(),
            ob.post or '',
            ob.email,
            ob.subdivision_id,
            ob.subdivision_code,
            ob.subdivision_name,
            ob.id,
        ))
    return sorted(users, key=itemgetter(key is None and 1 or key or 0))

def get_users_dict(key=None, as_dict=None):
    if as_dict:
        return dict([(x[0], dict(zip(['full_name', 'post', 'email', 'subdivision_id', 'subdivision_code', 'subdivision_name', 'id'], x[1:]))) for x in get_users(key)])
    return [dict(zip(['login', 'full_name', 'post', 'email', 'subdivision_id', 'subdivision_code', 'subdivision_name', 'id'], x)) for x in get_users(key)]

def print_users(key=None):
    for x in get_users_dict(key):
        print(('%3d: %s %s %s %s %s %s' % (
            x['id'], 
            x['subdivision_code'], 
            x['subdivision_name'], 
            x['login'], 
            x['full_name'], 
            x['post'], 
            x['email'], 
            )).encode(default_print_encoding, 'ignore').decode(default_print_encoding))

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
        user.post = form.post.data
        user.email = form.email.data
        user.confirmed = form.confirmed.data
        user.enabled = form.enabled.data

        if user.login != form.login.data and form.login.data:
            user.login = form.login.data

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

def local_reflect_meta():
    meta = MetaData()
    meta.reflect(bind=db.engine)
    return meta

def drop_table(cls):
    cls.__table__.drop(db.engine)

def show_tables():
    return local_reflect_meta().tables.keys()

def print_tables():
    for x in db.get_tables_for_bind():
        print(x)

def show_all():
    return local_reflect_meta().sorted_tables

def get_app_roles():
    return [x for x in list(app_roles) if x[1]]

def get_roles():
    return [x for x in list(roles) if not x[1].startswith('X')]

def get_subdivisions(order=None):
    if order is None or order == 'name':
        order = Subdivision.name
    elif order == 'code':
        order = Subdivision.code
    query = Subdivision.query.order_by(order)
    return [(ob.id, ob.code, ob.name, ob.manager, ob.fullname) for ob in query.all()]

def print_subdivisions(order=None):
    for x in get_subdivisions(order):
        print(('%4d: %s %s %s %s' % x).encode(default_print_encoding, 'ignore').decode(default_print_encoding))

## ==================================================== ##

def gen_subdivisions():
    items = [
        ('0001', 'Администрация', 'Айбазов О.У.', ''),
        ('0002', 'Дирекция', 'Савельев А.С.', ''),
        ('0003', 'Финансовый отдел', '', ''),
        ('0004', 'Коммерческий отдел', '', ''),
        ('0005', 'Бухгалтерия', '', ''),
        ('0006', 'Отдел кадров', 'Куян Е.Н.', ''),
        ('0007', 'СТЗП', 'Боровин О.И.', ''),
        ('0008', 'Отдел снабжения', '', ''),
        ('0009', 'Отдел сертификации и проектов', 'Сосунов К.А.', ''),
        ('0010', 'Административный департамент', '', ''),
        ('0011', 'Группа системной поддержки', '', ''),
        ('0012', 'Сервисная служба', '', ''),
        ('0013', 'АХО', 'Азарова К.С.', ''),
        ('0014', 'Отдел продаж', 'Коблысь Н.А.', ''),
        ('0030', 'Производство', 'Сухоруков М.А.', ''),
        ('0031', 'ОМОК', '', 'Отдел механической обработки карт'),
        ('0032', 'ОДК', '', 'Отдел доукомплектования карт'),
        ('0033', 'ОП', '', 'Отдел печати'),
        ('0034', 'ОТК-1', '', 'ОТК производства'),
        ('0035', 'ОЦП и ДП', '', 'Отдел цифровой печати и допечатной подготовки'),
        ('0040', 'Цех персонализации', 'Каюмов Д.О.', ''),
        ('0041', 'ОТПП', '', 'Отдел технической поддержки персонализации'),
        ('0042', 'ОТК-2', '', 'ОТК цеха персонализации'),
        ('0100', 'Розан Даймонд', 'Казанцев К.', ''),
        ('0101', 'Ювелирное производство', 'Кондратьева А.А.', ''),
        ('0102', 'Дизайнерское бюро', 'Лазутина О.В.', ''),
        ('0060', 'Складское хозяйство', '', ''),
        ('0061', 'Транспорт', '', ''),
        ('0070', 'РозанСпб', '', ''),
    ]

    def find(code):
        return Subdivision.query.filter_by(code=code).first()

    for item in items:
        code, name, manager, fullname = item
        
        ob = find(code)
        
        if ob is None:
            ob = Subdivision(code, name, manager, fullname)
        else:
            ob.name = name
            ob.manager = manager
            ob.fullname = fullname

        db.session.add(ob)

    _commit()
