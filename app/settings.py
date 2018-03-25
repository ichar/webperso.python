# -*- coding: utf-8 -*-

import re
from datetime import datetime

from flask import render_template, url_for, request, make_response, jsonify, flash
from flask.ext.login import login_required, current_user
from flask.ext.babel import gettext

from config import (
    IsDebug, IsDeepDebug, IsShowLoader, IsFuture, errorlog, print_to, print_exception, getCurrentDate
)

product_version = '1.80 (beta), 2018-03-25'

#########################################################################################

#   -------------
#   Default types
#   -------------

DEFAULT_LANGUAGE = 'ru'
DEFAULT_LOG_MODE = 1
DEFAULT_PER_PAGE = 10
DEFAULT_OPER_PER_PAGE = 50
DEFAULT_MANAGER_PER_PAGE = 20
DEFAULT_ADMIN_PER_PAGE = 50
DEFAULT_PAGE = 1
DEFAULT_UNDEFINED = '---'
DEFAULT_DATE_FORMAT = ('%d/%m/%Y', '%Y-%m-%d',)
DEFAULT_DATETIME_FORMAT = '<nobr>%Y-%m-%d</nobr><br><nobr>%H:%M:%S</nobr>'
DEFAULT_DATETIME_INLINE_FORMAT = '<nobr>%Y-%m-%d&nbsp;%H:%M:%S</nobr>'
DEFAULT_DATETIME_PERSOLOG_FORMAT = ('%Y%m%d', '%Y-%m-%d %H:%M:%S',)
DEFAULT_DATETIME_SDCLOG_FORMAT = ('%d.%m.%Y', '%d.%m.%Y %H:%M:%S,%f',)
DEFAULT_DATETIME_EXCHANGELOG_FORMAT = ('%d.%m.%Y', '%d.%m.%Y %H:%M:%S,%f',)
DEFAULT_DATETIME_READY_FORMAT = '%b %d %Y %I:%M%p'
DEFAULT_DATETIME_TODAY_FORMAT = '%d.%m.%Y'
DEFAULT_HTML_SPLITTER = ':'

USE_FULL_MENU = True

MAX_TITLE_WORD_LEN = 50
MAX_XML_BODY_LEN = 1024*10000
MAX_XML_TREE_NODES = 100
MAX_LOGS_LEN = 999
MAX_CARDHOLDER_ITEMS = 9999
EMPTY_VALUE = '...'

# action types
VALID_ACTION_TYPES = ('101','301',)

BATCH_TYPE_PERSO = 7

COMPLETE_STATUSES = (62, 64, 98, 197, 198, 201, 202, 203, 255,)

SETTINGS_PARSE_XML = True

_citi_tags = ( \
    'CompanyName:ClientName:BarcodeB:CONVB:',
    'AddressLine1:AddressLine2:AddressLine3:AddressLine4:AddressLine5:AddressLine6:AddressLine7:',
    'Client:PLASTIC:PlasticWH_ContainerList:Sort:AREP_NAME:DELIV_INC:CARD_TYPE:CDT_NAME:Urgency:CheckInfo:PROCESS_ERR_MSG:'
    'Envelope:Insert1:', #:Insert2:Insert3:Insert4:Insert5:Insert6:Insert7:Insert8:Insert9:Insert10:Insert11
    'PROCESS_ERR_MSG',
)

IMAGE_TAGS_DECODE_CYRILLIC = {
    'CITI_BANK' : (
        ('dostowin', {
            'default' : {
                        'AREP_Record' : _citi_tags[0] + _citi_tags[1],
                        'FileBody'    : _citi_tags[2],
                        },
            'record'  : {'.' : _citi_tags[0] + _citi_tags[1] + _citi_tags[2],},
            'image'   : {},
            }),
        ('iso', {'errors'  : {'.' : _citi_tags[3]},}),
    ),
}

PAN_TAGS = 'PAN:PANWIDE:PANCVC2:DLV_Record:DTC_Record:PIN_Record:OTK_Track1:OTK_Track2:TRACK1:TRACK2:PROCESS_ERR_MSG'

SEMAPHORE = {
    'count'    : 7,
    'timeout'  : 5000,
    'action'   : '901',
    'speed'    : '100:1000',
    'seen_at'  : (5,10,),
    'inc'      : (1,1,1,1,1,1,1,),
    'duration' : (9999, 5000, 0, 0, 0, 3000, -1,),
}

EXTRA_ = '__'

## ================================================== ##

_agent = None

def IsAndroid():
    return _agent.platform == 'android'
def IsiOS():
    return _agent.platform == 'ios'
def IsiPad():
    return _agent.platform == 'ipad'
def IsLinux():
    return _agent.platform == 'linux'

def IsChrome():
    return _agent.browser == 'chrome'
def IsFirefox():
    return _agent.browser == 'firefox'
def IsSafari():
    return _agent.browser == 'safari'
def IsOpera():
    return _agent.browser == 'opera' or 'OPR' in _agent.string

def IsIE(version=None):
    ie = _agent.browser.lower() in ('explorer', 'msie',)
    if not ie:
        return False
    elif version:
        return float(_agent.version) == version
    return float(_agent.version) < 10
def IsSeaMonkey():
    return _agent.browser == 'seamonkey'
def IsMSIE():
    return _agent.browser.lower() in ('explorer', 'ie', 'msie', 'seamonkey',)

def IsMobile():
    return IsAndroid() or IsiOS() or IsiPad()
def IsNotBootStrap():
    return IsIE(10) or IsAndroid()
def IsWebKit():
    return IsChrome() or IsFirefox() or IsOpera() or IsSafari()

def BrowserVersion():
    return _agent.version

## -------------------------------------------------- ##

def get_request_item(name):
    if request.method.upper() == 'POST':
        x = request.form.get(name)
    else:
        x = None
    if not x:
        x = request.args.get(name)
    if x:
        if x == DEFAULT_UNDEFINED or x.upper() == 'NONE':
            x = None
        elif x.startswith('{') and x.endswith('}'):
            return eval(re.sub('null', '""', x))
    return x or ''

def has_request_item(name):
    return name in request.form or name in request.args

def get_page_params(view=None):
    is_admin = current_user.is_administrator(private=True)
    is_manager = current_user.is_manager(private=True)
    is_operator = current_user.is_operator(private=True)

    page = 0

    default_per_page = (
        view in ('admin',) and DEFAULT_ADMIN_PER_PAGE or
        is_manager and DEFAULT_MANAGER_PER_PAGE or
        #is_operator and DEFAULT_OPER_PER_PAGE or
        view in ('cards',) and DEFAULT_PER_PAGE * 2 or
        DEFAULT_PER_PAGE
        )
    
    try:
        per_page = int(get_request_item('per_page')) or default_per_page
        page = int(get_request_item('page') or DEFAULT_PAGE)
    except:
        per_page = default_per_page
        page = DEFAULT_PAGE
    finally:
        if per_page <= 0 or per_page > 1000:
            per_page = default_per_page
        if page <= 0:
            page = DEFAULT_PAGE

    next = get_request_item('next') and True or False
    prev = get_request_item('prev') and True or False

    if next:
        page += 1
    if prev and page > 1:
        page -= 1
    
    return page, per_page

def make_platform(locale, debug=None):
    global _agent
    agent = request.user_agent
    browser = agent.browser
    os = agent.platform
    root = '%s/' % request.script_root

    _agent = agent

    is_owner = current_user.is_owner()
    is_manager = current_user.is_manager(private=True)
    is_operator = current_user.is_operator(private=True)

    referer = ''
    links = {}

    is_default = 1 or os in ('ipad', 'android',) and browser in ('safari', 'chrome',) and 1 or 0 
    is_frame = not IsMobile() and 1 or 0

    version = agent.version
    css = IsMSIE() and 'ie' or 'web'

    platform = '[os:%s, browser:%s (%s), css:%s, %s %s%s%s]' % (
        os, 
        browser, 
        version, 
        css, 
        locale, 
        is_default and ' default' or ' flex',
        is_frame and ' frame' or '', 
        debug and ' debug' or '',
    )

    kw = {
        'agent'          : agent.string,
        'browser'        : browser, 
        'os'             : os, 
        'root'           : root, 
        'referer'        : referer, 
        'links'          : links, 
        'version'        : version, 
        'css'            : css, 
        'is_frame'       : is_frame, 
        'is_demo'        : 0, 
        'is_show_loader' : IsShowLoader,
        'platform'       : platform,
        'style'          : {'default' : is_default},
        'screen'         : request.form.get('screen') or '',
        'scale'          : request.form.get('scale') or '',
        'usertype'       : is_manager and 'manager' or is_operator and 'operator' or 'default',
        'sidebar'        : {'state' : 1, 'title' : gettext('Click to close top menu')},
    }

    return kw

def make_keywords():
    return (
        # --------------
        # Error Messages
        # --------------
        "'Execution error':'%s'" % gettext('Execution error'),
        # -------
        # Buttons
        # -------
        "'Add':'%s'" % gettext('Add'),
        "'Back':'%s'" % gettext('Back'),
        "'Calculate':'%s'" % gettext('Calculate'),
        "'Cancel':'%s'" % gettext('Cancel'),
        "'Confirm':'%s'" % gettext('Confirm'),
        "'Execute':'%s'" % gettext('Execute'),
        "'Frozen link':'%s'" % gettext('Frozen link'),
        "'Link':'%s'" % gettext('Link'),
        "'OK':'%s'" % gettext('OK'),
        "'Reject':'%s'" % gettext('Decline'),
        "'Remove':'%s'" % gettext('Remove'),
        "'Run':'%s'" % gettext('Run'),
        "'Save':'%s'" % gettext('Save'),
        "'Search':'%s'" % gettext('Search'),
        "'Select':'%s'" % gettext('Select'),
        "'Update':'%s'" % gettext('Update'),
        # ----
        # Help
        # ----
        "'All':'%s'" % gettext('All'),
        "'Commands':'%s'" % gettext('Commands'),
        "'Help':'%s'" % gettext('Help'),
        "'Help information':'%s'" % gettext('Help information'),
        "'Helper keypress guide':'%s'" % gettext('Helper keypress guide'),
        "'System information':'%s'" % gettext('System information'),
        "'Total':'%s'" % gettext('Total'),
        # --------------------
        # Flags & Simple Items
        # --------------------
        "'error':'%s'" % gettext('error'),
        "'yes':'%s'" % gettext('Yes'),
        "'no':'%s'" % gettext('No'),
        "'none':'%s'" % gettext('None'),
        "'true':'%s'" % 'true',
        "'false':'%s'" % 'false',
        # ------------------------
        # Miscellaneous Dictionary
        # ------------------------
        "'batch':'%s'" % gettext('batch'),
        "'create selected file':'%s'" % gettext('create selected file'),
        "'delete selected file':'%s'" % gettext('delete selected file'),
        "'file':'%s'" % gettext('file'),
        "'No data':'%s'" % gettext('No data'),
        "'No data or access denied':'%s'" % gettext('No data or access denied'),
        "'of batch':'%s'" % gettext('of batch'),
        "'of file':'%s'" % gettext('of file'),
        "'order confirmation':'%s'" % gettext('Are you really going to'),
        "'select referenced item':'%s:'" % gettext('Choice the requested item from the given list'),
        "'shortcut version':'%s'" % '1.0',
        "'status confirmation':'%s'" % gettext('Are you really going to change the status'),
        "'status confirmation request':'%s:'" % gettext('Choice the requested status from the given list'),
        "'please confirm':'%s.'" % gettext('Please, confirm'),
        "'Recovery is impossible!':'%s'" % gettext('Recovery is impossible!'),
        "'top-close':'%s'" % gettext('Click to close top menu'),
        "'top-open':'%s'" % gettext('Click to open top menu'),
        # -------------
        # Notifications
        # -------------
        "'Command:Activate selected batch':'%s'" % gettext('Command: Activate selected batch?'),
        "'Command:Activate selected batches':'%s'" % gettext('Command: Activate selected batches?'),
        "'Command:Config item removing':'%s'" % gettext('Command: Do you really want to remove the config item?'),
        "'Command:Item was changed. Continue?':'%s'" % gettext('Command: Item was changed. Continue?'),
        "'Command:Reference item removing':'%s'" % gettext('Command: Do you really want to remove the reference item?'),
        "'Command:Reject activation':'%s'" % gettext('Command: Do you really want to reject selected batches?'),
        "'Command:Send request to the warehouse':'%s'" % gettext('Command: Send request to the warehouse?'),
        "'Exclamation:exists_inactive':'%s'" % gettext('Exclamation: Exist inactive batches'),
        "'Exclamation:exists_materials':'%s'" % gettext('Exclamation: Exist materials to send in order'),
        "'Message:Action was done successfully':'%s'" % gettext('Message: Action was done successfully.'),
        "'Message:Request sent successfully':'%s'" % gettext('Message: Request was sent successfully.'),
        "'OK:exists_inactive':'%s'" % gettext('OK: All batches done'),
        "'OK:exists_materials':'%s'" % gettext('OK: Materials OK'),
        "'Warning:No inactive batches':'%s'" % gettext('Warning: All batches for the given file are already activated.'),
        "'Warning:No report data':'%s'" % gettext('Warning: No report data.'),
        "'Warning:No selected items':'%s'" % gettext('Warning: Please, select items to execute before.'),
    )

def init_response(title):
    host = request.form.get('host') or request.host_url
    debug = request.args.get('debug') == '1' and True or False

    locale = 'rus'
    kw = make_platform(locale, debug)
    keywords = make_keywords()
    forms = ('index', 'admin',)

    now = datetime.today().strftime(DEFAULT_DATE_FORMAT[1])

    kw.update({
        'title'        : gettext(title),
        'host'         : host,
        'locale'       : locale, 
        'language'     : 'ru',
        'keywords'     : keywords, 
        'forms'        : forms,
        'now'          : now,
        'file_id'      : get_request_item('file_id') or '0',
        'batch_id'     : get_request_item('batch_id') or '0',
        'preload_id'   : get_request_item('preload_id') or '0',
        'order_id'     : get_request_item('order_id') or '0',
        'event_id'     : get_request_item('event_id') or '0',
        'pers_id'      : get_request_item('pers_id') or '0',
        'oper_id'      : get_request_item('oper_id') or '0',
    })

    return debug, kw

def get_navigation():
    is_superuser = current_user.is_superuser()
    is_admin = current_user.is_administrator()
    is_operator = current_user.is_operator()
    items = []
    if current_user.is_authenticated:
        if is_superuser:
            items.append({'link' : '%s/admin/index' % request.script_root, 
                          'title': 'Администратор', 
                          'class': '/admin' in request.url and 'selected' or ''})
        if USE_FULL_MENU or '/bankperso' not in request.url:
            items.append({'link' : '%s/bankperso' % request.script_root, 
                          'title': 'Журнал заказов', 
                          'class': '/bankperso' in request.url and 'selected' or ''})
        if is_operator and (USE_FULL_MENU or '/cards' not in request.url):
            #items.append({'link' : '%s/cards?date_from=%s' % (request.script_root, getCurrentDate()),
            items.append({'link' : '%s/cards' % request.script_root,
                          'title': 'Персонализация', 
                          'class': '/cards' in request.url and 'selected' or ''})
        """
        if USE_FULL_MENU or ('/preload' not in request.url and is_admin):
            items.append({'link' : '%s/preload' % request.script_root, 
                          'title': 'Предоработка', 
                          'class': '/preload' in request.url and 'selected' or ''})
        if is_superuser:
            items.append({'link' : '%s/orderstate' % request.script_root, 
                          'title': 'Менеджер заказов',
                          'class': '/orderstate' in request.url and 'selected' or ''})
        """
        if USE_FULL_MENU or ('/configurator' not in request.url and is_admin):
            items.append({'link' : '%s/configurator' % request.script_root, 
                          'title': 'Конфигуратор',
                          'class': '/configurator' in request.url and 'selected' or ''})
        if IsFuture:
            items.append({'link' : '%s/stock' % request.script_root,
                          'title': 'Склад',
                          'class': '/stock' in request.url and 'selected' or ''})

        items.append({'link' : '%s/auth/logout' % request.script_root, 'title': 'Выход', 'class':''})
    else:
        items.append({'link': '%s/auth/login' % request.script_root, 'title': 'Вход', 'class':''})
    return items

