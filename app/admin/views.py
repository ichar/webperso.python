# -*- coding: utf-8 -*-

from config import (
     IsDebug, IsDeepDebug, IsTrace, errorlog, print_to, print_exception,
     default_unicode, default_encoding, default_iso
     )

from flask import render_template, make_response

from . import admin
from .. import db

from .forms import RegistrationForm, UserForm
from ..decorators import admin_required
from ..database import database_config, BankPersoEngine
from ..models import User, admin_config, admin_view_users, register_user, delete_user
from ..settings import *
from ..utils import getId

from ..semaphore.views import initDefaultSemaphore

##  =============
##  Admin Package
##  =============

default_page = 'admin'
default_action = '100'
engine = None

def before(f):
    def wrapper(**kw):
        global engine
        engine = BankPersoEngine()
        return f(**kw)
    return wrapper

@before
def refresh(**kw):
    return

@admin.route('/', methods = ['GET','POST'])
@admin.route('/index', methods = ['GET','POST'])
@login_required
@admin_required
def index():
    debug, kw = init_response('WebPerso Admin Page')
    command = get_request_item('command') or get_request_item('save') and 'save'

    if not current_user.is_superuser():
        flash('Sorry, it\'s restricted for your responsibilities!')
        return render_template('auth/unconfirmed.html')

    refresh()

    # --------------------------------------------
    # Позиционирование строки в журнале (position)
    # --------------------------------------------

    position = get_request_item('position').split(':')
    line = len(position) > 3 and int(position[3]) or 1

    try:
        user_id = int(getId(get_request_item('user_id')) or 0)
    except:
        user_id = None

    profile_clients = get_request_item('profile_clients') or ''

    if IsDebug:
        print('--> %s:%s [%s]' % (command, user_id, profile_clients))

    if IsTrace:
        print_to(errorlog, '!!! admin:%s [%s] %s %s %s' % ( \
            current_user.login, command or '', user_id, request.remote_addr, request.method), request=request)

    user_form = UserForm()

    errors = []
    args = {}

    if request.method == 'POST' and command in ('add', 'save'):
        user_form = UserForm(request.form)
        IsOk, errors = register_user(user_form, user_id)
    elif command == 'delete':
        delete_user(user_id)

    forms = dict([('user', user_form,),])

    page, per_page = get_page_params(default_page)

    if IsDebug:
        print('--> page %s:%s' % (page, per_page))

    search = get_request_item('search')

    users = admin_view_users(user_id, page, per_page, context=search)
    clients = engine.runQuery('clients', order='CName', as_dict=True, encode_columns=('CName',))

    if command != 'delete' and user_id:
        user = User.get_by_id(user_id)
        user.set_profile_clients(profile_clients)
        profile_clients = user.get_profile_clients()
    else:
        profile_clients = ''

    filter = ''

    root = '%s/' % request.script_root
    query_string = 'per_page=%s' % per_page
    base = 'index?%s' % query_string

    iter_pages = users.iter_pages(left_edge=5)

    pagination = { \
        'total'             : '%s ' % users.total,
        'per_page'          : per_page,
        'pages'             : users.pages,
        'current_page'      : page,
        'iter_pages'        : iter_pages,
        'has_next'          : users.has_next,
        'has_prev'          : users.has_prev,
        'per_page_options'  : (5,10,20,50,100),
        'link'              : '%s%s%s' % (base, filter, 
                                         (search and "&search=%s" % search) or ''
                                         ),
        'sort'              : {
            'modes'         : [],
            'sorted_by'     : '',
            'current_sort'  : 0,
        },
        'position'          : '%d:%d:%d:%d' % (page, users.pages, per_page, line),
    }

    kw.update({ \
        'base'              : base,
        'page_title'        : gettext('WebPerso Administrator View'),
        'header_subclass'   : 'left-header',
        'show_flash'        : True,
        'loader'            : '/admin/loader',
        'semaphore'         : initDefaultSemaphore(),
        'args'              : args,
        'user'              : (user_id,),
        'navigation'        : get_navigation(),
        'config'            : admin_config,
        'pagination'        : pagination,
        'forms'             : forms,
        'errors'            : errors,
        'OK'                : '',
        'users'             : users.value,
        'profile_clients'   : profile_clients,
        'clients'           : clients,
        'search'            : search or '',
    })

    sidebar = get_request_item('sidebar')
    if sidebar:
        kw['sidebar']['state'] = int(sidebar)

    return make_response(render_template('admin.html', debug=debug, **kw))

"""
@admin.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if register_user(request, form):
        flash('Thanks for registering')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)
"""

@admin.after_request
def make_response_no_cached(response):
    if engine is not None:
        engine.close()
    # response.cache_control.no_store = True
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response

@admin.route('/loader', methods = ['GET','POST'])
@login_required
@admin_required
def loader():
    exchange_error = '0'
    exchange_message = ''

    action = get_request_item('action') or default_action
    selected_menu_action = get_request_item('selected_menu_action') or action != default_action and action or '101'

    response = {}

    user_id = int(getId(get_request_item('user_id')) or '0')

    if IsDebug:
        print('--> action:%s file_id:%s' % (action, user_id))

    if IsTrace:
        print_to(errorlog, '--> loader:%s %s [%s:%s]' % (action, current_user.login, user_id, selected_menu_action))

    if not current_user.is_superuser():
        return jsonify(response)

    data = {}
    profile_name = ''
    profile_clients = ''

    try:
        if action == default_action:
            action = selected_menu_action

        if not action:
            pass

        elif action == '101':
            user = user_id and User.get_by_id(user_id) or None
        
            if IsDebug:
                print('--> %s:%s %s' % (action, user_id, user and user.login))

            if user is not None:
                data = user.get_data('register')
                profile_name = user.full_name()
                profile_clients = user.get_profile_clients()

    except:
        print_exception()

    response.update({ \
        'action'           : action,
        # --------------
        # Service Errors
        # --------------
        'exchange_error'   : exchange_error, 
        'exchange_message' : exchange_message,
        # -----------------------------
        # Results (Log page parameters)
        # -----------------------------
        'user_id'          : user_id,
        # ----------------------------
        # Results (Admin page content)
        # ----------------------------
        'total'            : 0,
        'data'             : data,
        'props'            : None,
        'columns'          : None,
        'profile_name'     : profile_name,
        'profile_clients'  : profile_clients,
    })

    return jsonify(response)
