# -*- coding: utf-8 -*-

import os
import locale
import random
import string
from operator import itemgetter
from copy import deepcopy

from config import (
     CONNECTION,
     IsDebug, IsDeepDebug, IsTrace, IsForceRefresh, IsPrintExceptions, IsNoEmail, LocalDebug,
     errorlog, print_to, print_exception,
     default_unicode, default_encoding, default_iso,
     LOCAL_EASY_DATESTAMP, LOCAL_EXCEL_TIMESTAMP, LOCAL_EXPORT_TIMESTAMP,
     UTC_FULL_TIMESTAMP, UTC_EASY_TIMESTAMP, DATE_STAMP, DEFAULT_ROOT,
     )

from . import provision

from ..settings import *
from ..database import database_config, BankPersoEngine, Connection, DBEngine
from ..models import User, ExchangeRate, get_users, get_users_dict
from ..decoders import FileDecoder
from ..mails import send_simple_mail
from ..utils import (
     getToday, getDate, getDateOnly, getUID, checkDate, cdate, minutedelta, normpath,
     Capitalize, unCapitalize, makeCSVContent, makeXLSContent,
     checkPaginationRange, reprSortedDict, unquoted_url, is_unique_strings
     )

from ..semaphore.views import initDefaultSemaphore

from .sellers import Seller

##  ========================
##  Provision Orders Package
##  ========================

default_page = 'provision'
default_locator = 'provision'
default_action = '830'
default_log_action = '831'
default_print_action = '850'
default_template = 'provision-orders'

engine = None
instance = None

is_no_price = 0

# Локальный отладчик
IsLocalDebug = LocalDebug[default_page]
# Принудительная загрузка данных генератора
IsLoaderExplicit = 0
# Включить согласование руководителями компании
IsReviewHeadOffice = 1
# Выборка данных для назначенных рецензентов
IsWithReviewersTemplate = 1
# Выборка данных без ограничений размера страницы
IsMaxPerPage = 0
# Использовать OFFSET в SQL запросах
IsApplyOffset = 1
# Использовать UNION в SQL запросах
IsApplyUnion = 1

_views = {
    'orders'          : 'provision-orders',
    'reviews'         : 'provision-reviews',
    'subdivisions'    : 'provision-subdivisions',
    'categories'      : 'provision-categories',
    'sellers'         : 'provision-sellers',
    'equipments'      : 'provision-equipments',
    'conditions'      : 'provision-conditions',
    'params'          : 'provision-params',
    'payments'        : 'provision-payments',
    'comments'        : 'provision-comments',
    'authors'         : 'provision-order-authors',
    'order-params'    : 'provision-order-params',
    'order-items'     : 'provision-order-items',
    'order-payments'  : 'provision-order-payments',
    'order-comments'  : 'provision-order-comments',
    'order-reviewers' : 'provision-order-reviewers',
    'order-documents' : 'provision-order-documents',
    'order-unreads'   : 'provision-order-unreads',
    'order-changes'   : 'provision-order-changes',
    'dates'           : 'provision-order-dates',
    'download'        : 'provision-download-image',
}

_default_encode_columns = ('Article', 'Purpose', 'Subdivision', 'Condition', 'Equipment', 'Seller', 'Account',)

_default_statuses = dict(zip([0,1,2,3,4,5,6,7,9], ['work', 'review', 'accepted', 'rejected', 'confirm', 'execute', 'finish', 'archive', 'removed']))

_extra_action = (default_print_action,)

_rlink = re.compile(r'((http|https)://[^\s\n\t]+)')

requested_object = {}

locale.setlocale(locale.LC_ALL, '')

_PROVISION_STATUSES = {
    'work'     : (0, 'on-work', 'в работе', '', ''),
    'review'   : (1, 'on-review', 'на согласовании', '', ''),
    'accepted' : (2, 'on-accepted', 'согласовано', '2.2', 'на согласовании = согласовано'),
    'rejected' : (3, 'on-rejected', 'отказано', '3.3', 'на согласовании = отказано'),
    'confirm'  : (4, 'on-confirm', 'требуется обоснование', '4.4', 'на согласовании = требуется обоснование'),
    'execute'  : (5, 'on-execute', 'на исполнении', '5.2', 'на исполнении = согласовано'),
    'paid'     : (5, 'on-paid', 'на исполнении', '5.6', 'на исполнении = оплачено'),
    'finish'   : (6, 'on-finish', 'исполнено', '6.6', 'исполнено'),
    'archive'  : (7, 'on-archive', 'в архиве', '', ''),
    'x1'       : (8, None, '', '', ''),
    'removed'  : (9, 'on-removed', 'корзина', '', ''),
}

_PROVISION_SUB_STATUSES = dict([(x[1][3], x[0]) for x in _PROVISION_STATUSES.items() if x[1][3]])

_PROVISION_REVIEW_STATUSES = {
    2 : ('accept', 'согласовано'),
    3 : ('reject', 'отказано'),
    4 : ('confirm', 'требуется обоснование'),
    5 : ('confirmation', 'информация'),
    6 : ('paid', 'оплачено'),
}

valid_status = 7

_SQL = {
    'Orders' : {
        'delete'     : 'DELETE FROM [ProvisionDB].[dbo].[Orders_tb] {where}',
        'set-status' : 'UPDATE [ProvisionDB].[dbo].[Orders_tb] SET Status=%d {where}'
    },
    'OrderDates' : {
        'delete'     : 'DELETE FROM [ProvisionDB].[dbo].[OrderDates_tb] WHERE OrderID in (select TID from [ProvisionDB].[dbo].[Orders_tb] {where})',
    },
    'Reviews' : {
        'delete'     : 'DELETE FROM [ProvisionDB].[dbo].[Reviews_tb] WHERE OrderID in (select TID from [ProvisionDB].[dbo].[Orders_tb] {where})',
    },
    'Params' : {
        'delete'     : 'DELETE FROM [ProvisionDB].[dbo].[Params_tb] WHERE OrderID in (select TID from [ProvisionDB].[dbo].[Orders_tb] {where})',
    },
    'Items' : {
        'delete'     : 'DELETE FROM [ProvisionDB].[dbo].[Items_tb] WHERE OrderID in (select TID from [ProvisionDB].[dbo].[Orders_tb] {where})',
    },
    'Payments' : {
        'delete'     : 'DELETE FROM [ProvisionDB].[dbo].[Payments_tb] WHERE OrderID in (select TID from [ProvisionDB].[dbo].[Orders_tb] {where})',
    },
    'Comments' : {
        'delete'     : 'DELETE FROM [ProvisionDB].[dbo].[Comments_tb] WHERE OrderID in (select TID from [ProvisionDB].[dbo].[Orders_tb] {where})',
    },
    #'OrderDocuments' : {
    #    'set'        : 'INSERT INTO [ProvisionDB].[dbo].[OrderDocuments_tb]([UID], OrderID, [Login], [FileName], FileSize, ContentType, Note, [Image]) '
    #                   'VALUES(%s, %d, %s, %s, %d, %s, %s, %s)',
    #    'get'        : 'SELECT [FileName], FileSize, ContentType, Image FROM [ProvisionDB].[dbo].[OrderDocuments_tb] WHERE UID=%s',
    #},
}

#
# Warning!!! ValueError: unsupported format character ';' (0x3b) at index 981 -> use `100%%` double semicolon!
#

_DEFAULT_EMAILS = {
    'approval' : ('snab1c@rosan.ru',),
    'create'   : ('snab1c@rosan.ru', 'import@rosan.ru',),
    'remove'   : ('snab1c@rosan.ru', 'import@rosan.ru',),
    'review'   : ('snab1c@rosan.ru', 'import@rosan.ru',),
    'execute'  : ('snab1c@rosan.ru', 'import@rosan.ru', 'kotova@rosan.ru',),
    'common'   : ('webdev@rosan.ru',),
    'public'   : ('olegaybazov@rosan.ru',)
}

_APPROVAL_ALARM_HTML = '''
<html>
<head>
  <style type="text/css">
    h1 { font-size:18px; padding:0; margin:0 0 10px 0; }
    div.box { font:normal 12px Verdana; }
    div.box * { display:block; }
    dd { font-size:16px; font-weight:bold; line-height:24px; padding:0; color:#468; margin-left:10px; white-space:nowrap; }
    span { color:#000; padding-top:3px; font-size:12px; white-space:nowrap; }
    a { cursor:pointer; }
    .seller {}
    .order * { display:inline-block !important; }
    .caption { padding-top:10px; padding-bottom:10px; }
    .info { margin:10px 0 10px 0; }
    div.title { margin-top:10px; font-weight:bold; color:rgba(120, 100, 80, 0.6); }
    div.message { margin-top:10px; font-size:11px; }
    div.line { border-top:1px dotted #888; width:100%%; height:1px; margin:10px 0 10px 0; }
    div.line hr { display:none; }
  </style>
</head>
<body>
  <div class="box">
  <h1 class="center">Запрос на согласование</h1>
  <table>
  <tr><td class="info">Просим в течение 2-х рабочих дней согласовать исполнение заказа.</td></tr>
  <tr><td class="caption">Заказ:</td></tr>
  <tr><td><dd class="order"><a target="_blank" href="webperso&_id=%(id)s">[%(id)05d]</a>&nbsp;%(Article)s</dd></td></tr>
  <tr><td><span class="info">%(Date)s</span></td></tr>
  <tr><td>
    <div class="title">%(Title)s. %(Reviewer)s</div>
    <div class="message">%(Message)s</div>
  </td></tr>
  <tr><td><div class="line"><hr></div></td></tr>
  </table>
  </div>
</body>
</html>
'''

_CREATE_ALARM_HTML = '''
<html>
<head>
  <style type="text/css">
    h1 { font-size:18px; padding:0; margin:0 0 10px 0; }
    div.box { font:normal 12px Verdana; }
    div.box * { display:block; }
    dd { font-size:16px; font-weight:bold; line-height:24px; padding:0; color:#468; margin-left:10px; white-space:nowrap; }
    span { color:#000; padding-top:3px; font-size:12px; white-space:nowrap; }
    a { cursor:pointer; }
    .seller {}
    .order * { display:inline-block !important; }
    .caption { padding-top:10px; padding-bottom:10px; }
    .info { margin:10px 0 10px 0; }
    div.title { margin-top:10px; font-weight:bold; color:rgba(120, 100, 80, 0.6); }
    div.message { margin-top:10px; font-size:11px; }
    div.line { border-top:1px dotted #888; width:100%%; height:1px; margin:10px 0 10px 0; }
    div.line hr { display:none; }
  </style>
</head>
<body>
  <div class="box">
  <h1 class="center">Заказ снабжения</h1>
  <table>
  <tr><td class="info">Создан новый заказ на закупку/поставку товарной номенклатуры.</td></tr>
  <tr><td class="caption">Заказ:</td></tr>
  <tr><td><dd class="order"><a target="_blank" href="webperso&_id=%(id)s">[%(id)05d]</a>&nbsp;%(Article)s</dd></td></tr>
  <tr><td><span class="info">%(Date)s</span></td></tr>
  <tr><td>
    <div class="title">Заказчик: %(Subdivision)s. ФИО: %(Reviewer)s</div>
    <div class="message">%(Message)s</div>
  </td></tr>
  <tr><td><div class="line"><hr></div></td></tr>
  </table>
  </div>
</body>
</html>
'''

_REMOVE_ALARM_HTML = '''
<html>
<head>
  <style type="text/css">
    h1 { font-size:18px; padding:0; margin:0 0 10px 0; }
    div.box { font:normal 12px Verdana; }
    div.box * { display:block; }
    dd { font-size:16px; font-weight:bold; line-height:24px; padding:0; color:#468; margin-left:10px; white-space:nowrap; }
    span { color:#000; padding-top:3px; font-size:12px; white-space:nowrap; }
    a { cursor:pointer; }
    .seller {}
    .order * { display:inline-block !important; }
    .caption { padding-top:10px; padding-bottom:10px; }
    .info { margin:10px 0 10px 0; }
    div.title { margin-top:10px; font-weight:bold; color:rgba(120, 100, 80, 0.6); }
    div.remover { margin-top:10px; font-size:12px; font-weight:bold; color:#c72424; }
    div.line { border-top:1px dotted #888; width:100%%; height:1px; margin:10px 0 10px 0; }
    div.line hr { display:none; }
  </style>
</head>
<body>
  <div class="box">
  <h1 class="center">Заказ снабжения</h1>
  <table>
  <tr><td class="info">Заказ на закупку/поставку товарной номенклатуры удален.</td></tr>
  <tr><td class="caption">Заказ:</td></tr>
  <tr><td><dd class="order"><a target="_blank" href="webperso&_id=%(id)s">[%(id)05d]</a>&nbsp;%(Article)s</dd></td></tr>
  <tr><td><span class="info">%(Date)s</span></td></tr>
  <tr><td>
    <div class="title">Заказчик: %(Subdivision)s. ФИО: %(Reviewer)s</div>
    <div class="remover">Удалено: %(Remover)s</div>
  </td></tr>
  <tr><td><div class="line"><hr></div></td></tr>
  </table>
  </div>
</body>
</html>
'''

_REVIEW_ALARM_HTML = '''
<html>
<head>
  <style type="text/css">
    h1 { font-size:18px; padding:0; margin:0 0 10px 0; }
    div.box { font:normal 12px Verdana; }
    div.box * { display:block; }
    dd { font-size:16px; font-weight:bold; line-height:24px; padding:0; color:#468; margin-left:10px; white-space:nowrap; }
    span { color:#000; padding-top:3px; font-size:12px; white-space:nowrap; }
    a { cursor:pointer; }
    .seller {}
    .order * { display:inline-block !important; }
    .caption { padding-top:10px; padding-bottom:10px; }
    .info { padding-top:10px; display:inline-block; }
    .code { background-color:#333333; padding:5px 20px 5px 20px; border:1px solid #806080; text-align:center; color:white; width:fit-content; max-width:250px; display:inline-block; }
    .work { background-color:#888888; }
    .review { background-color:#886666; }
    .accept { background-color:#84C284; }
    .reject { background-color:#E4606A; }
    .confirm { background-color:#4B55CC; }
    .confirmation { background-color:#48BCD8; }
    .execute { background-color:#CC80CC; }
    .paid { background-color:#DEA248; }
    .finish { background-color:#488DA0; }
    div.title { margin-top:10px; font-weight:bold; color:rgba(120, 100, 80, 0.6); }
    div.message { margin-top:10px; font-size:11px; }
    div.line { border-top:1px dotted #888; width:100%%; height:1px; margin:10px 0 10px 0; }
    div.line hr { display:none; }
  </style>
</head>
<body>
  <div class="box">
  <h1 class="center">Уведомление %(Caption)s</h1>
  <table>
  <tr><td><dd class="code %(code)s">%(Code)s</dd></td></tr>
  <tr><td class="caption">Заказ:</td></tr>
  <tr><td><dd class="seller">%(Seller)s</dd></td></tr>
  <tr><td><dd class="order"><a target="_blank" href="webperso&_id=%(id)s">[%(id)05d]</a>&nbsp;%(Article)s</dd></td></tr>
  <tr><td><span class="info">%(Date)s</span></td></tr>
  <tr><td>
    <div class="title">%(Title)s. %(Reviewer)s</div>
    <div class="message">%(Message)s</div>
  </td></tr>
  <tr><td><div class="line"><hr></div></td></tr>
  </table>
  </div>
</body>
</html>
'''
_EMAIL_EOL = '\r\n'
_PROVISION_LINK = '%sprovision?sidebar=0'

_MODELS = {
    'A' : '№п/п;Обоснование;Наименование товара;Количество;Единици измерения;Желаемая дата поступления;Дата составления заявки;Исполнитель ;Направление закупки;Склад поступления;Цена за единицу;общее описание;Поставщик;Условия оплаты;сумма оплаты с учетом НДС;;Валюта платежа;№ счета;Необходимая дата оплаты;Дата согласования;Дата передачи заказа в работу;Дата прередачи заказа на доставку ;Предположительная дата поступления;Фактическая дата поступления;Возможная дата оплаты;Фактиическая дата оплаты;Комментарий;;',
    'B' : '№п/п;Обоснование;Наименование товара;Количество;Желаемая дата поступления;Дата составления заявки;Исполнитель ;Направление закупки;Склад поступления;Цена за единицу;Общее описание;Поставщик;Условия оплаты;сумма оплаты с учетом НДС;;Валюта платежа;№ счета;Необходимая дата оплаты;Дата согласования;Дата передачи заказа в работу;Дата прередачи заказа на доставку ;Предположительная дата поступления;Фактическая дата поступления;Возможная дата оплаты;Фактиическая дата оплаты;Комментарий;;',
    'C' : '№п/п;Обоснование;Наименование товара;Количество;Желаемая дата поступления;Дата составления заявки;Исполнитель ;Направление закупки;Склад поступления;Цена за единицу;Общее описание;Поставщик;Валюта платежа;Условия оплаты;сумма оплаты с учетом НДС;;№ счета;Необходимая дата оплаты;Дата согласования;Дата передачи заказа в работу;Дата прередачи заказа на доставку ;Предположительная дата поступления;Фактическая дата поступления;Возможная дата оплаты;Фактиическая дата оплаты;Комментарий;;',
    'D' : '№п/п;Обоснование;Наименование товара;Количество;Единица измерения;Желаемая дата поступления;Дата составления заявки;Исполнитель ;Направление закупки;Склад поступления;Цена за единицу;Общее описание;Поставщик;Условия оплаты;сумма оплаты с учетом НДС;;Валюта платежа;№ счета;Необходимая дата оплаты;Дата согласования;Дата передачи заказа в работу;Дата прередачи заказа на доставку ;Предположительная дата поступления;Фактическая дата поступления;Возможная дата оплаты;Фактиическая дата оплаты;Комментарий;;;;;;;;;;;;;;;',
    'E' : '№п/п;Обоснование;Наименование товара;Количество;Единица измерения;Желаемая дата поступления;Дата составления заявки;Исполнитель ;Направление закупки;Склад поступления;Цена за единицу;Общее описание;Поставщик;Валюта платежа;Условия оплаты;сумма оплаты с учетом НДС;;№ счета;Необходимая дата оплаты;Дата согласования;Дата передачи заказа в работу;Дата прередачи заказа на доставку ;Предположительная дата поступления;Фактическая дата поступления;Возможная дата оплаты;Фактиическая дата оплаты;Комментарий;;',
    'F' : '№п/п;Обоснование;Наименование товара;Количество;дата составления заказа;Желаемая дата поступления;Исполнитель ;Направление закупки;Склад поступления;Цена за единицу;Общее описание;Поставщик;Условия оплаты;сумма оплаты с учетом НДС;;Валюта платежа;№ счета;Необходимая дата оплаты;Дата согласования;Дата передачи заказа в работу;Дата прередачи заказа на доставку ;Предположительная дата поступления;Фактическая дата поступления;Возможная дата оплаты;Фактиическая дата оплаты;Комментарий;;;',
    'G' : '№п/п;Обоснование;Наименование товара;Количество;Дата составления заказа;Желаемая дата поступления;Исполнитель ;Направление закупки;Склад поступления;Цена за единицу;Общее описание;Поставщик;Валюта платежа;Условия оплаты;сумма оплаты с учетом НДС;;№ счета;Необходимая дата оплаты;Дата согласования;Дата передачи заказа в работу;Дата прередачи заказа на доставку ;Предположительная дата поступления;Фактическая дата поступления;Возможная дата оплаты;Фактиическая дата оплаты;Комментарий;;',
    'H' : '№;Наименование товара;Количество, шт.;Обоснование;Отдел;Цена за единицу;Валюта платежа;Сумма без учета НДС;Сумма с учетом НДС;Условия оплаты;Поставщик;Согласовано',
    'I' : '№п/п;Обоснование;Наименование товара;Количество;Дата составления заказа;Желаемая дата поступления;Исполнитель ;Направление закупки;Склад поступления;Цена за единицу;Общее описание;Поставщик;Валюта платежа;Условия оплаты;сумма оплаты с учетом НДС;;№ счета;Необходимая дата оплаты;Дата согласования;Дата передачи заказа в работу;Дата прередачи заказа на доставку ;Предположительная дата поступления;Фактическая дата поступления;Возможная дата оплаты;Фактиическая дата оплаты;Комментарий;;',
    '1' : ';;;;;;;;;;;;;;Первый платеж (предоплата);Второй платеж;;;;;;;;;;Заказчик;Снабжение;Бухгалтерия',
    '2' : ';;;;;;;;;;;;;Первый платеж (предоплата);Второй платеж;;;;;;;;;;;Заказчик;Снабжение;Бухгалтерия;',
}

exchange_rate = {
    'EUR:EUR' : 1.0,
    'USD:EUR' : 0.8859,
    'RUR:EUR' : 0.014,
}


def before(f):
    def wrapper(*args, **kw):
        global engine
        if engine is not None:
            engine.close()
        name = kw.get('engine') or 'provision'
        engine = BankPersoEngine(name=name, user=current_user, connection=CONNECTION[name])
        return f(*args, **kw)
    return wrapper

@before
def refresh(**kw):
    global instance, requested_object, is_no_price, exchange_rate
    instance = Provision(current_user)

    is_no_price = not (
        current_user.app_is_provision_manager or 
        current_user.app_is_office_direction or 
        current_user.app_is_office_execution or 
        #current_user.app_role_ceo or 
        #current_user.app_role_headoffice or 
        #current_user.app_role_cao or 
        current_user.app_role_assistant or 
        current_user.app_role_cto or 
        current_user.app_role_chief or 
        current_user.app_is_consultant
        ) and 1 or 0

    ExchangeRate.refresh(1)
    
    exchange_rate.update({
        'RUR:EUR' : ExchangeRate.get_cross('RUB:EUR'),
        'USD:EUR' : ExchangeRate.get_cross('USD:EUR'),
        'EUR:RUR' : ExchangeRate.get_cross('EUR:RUB'),
        'USD:RUR' : ExchangeRate.get_cross('USD:RUB'),
    })

    order_id = kw.get('order_id')
    if not order_id:
        return

    requested_object = _get_order(order_id).copy()

def status_columns():
    return is_no_price and ('Qty',) or ('Price',) #('RD',)

def calc_euro(total, currency):
    v = (total and (isinstance(total, str) and _get_money(total) or float(total)) or 0.0)
    rate = _get_exchange_rate('%s:EUR' % currency)
    return v * rate

def calc_rub(total, currency):
    v = (total and (isinstance(total, str) and _get_money(total) or float(total)) or 0.0)
    rate = currency == 'RUR' and 1.0 or _get_exchange_rate('%s:RUR' % currency)
    return v * rate

def select_items(order_id, template, encode_columns, handler=None, **kw):
    items = []
    selected_id = int(kw.get('id') or 0)
    selected_name = kw.get('name')

    view = _views[template]
    columns = database_config[view]['export']

    no_selected = kw.get('no_selected') and True or False

    if order_id:
        where = 'OrderID=%d%s%s' % (
            int(order_id), 
            selected_id and ' and TID=%d' % selected_id or '',
            selected_name and " and Name='%s'" % selected_name or '',
            )

        order = kw.get('order') or 'TID'

        cursor = engine.runQuery(view, columns=columns, where=where, order=order, as_dict=True, encode_columns=encode_columns)
        if cursor:
            IsSelected = False
            
            for n, row in enumerate(cursor):
                row['id'] = row['TID']

                if handler is not None:
                    handler(row)

                if not IsSelected and selected_id and row['id'] == selected_id and not no_selected:
                    row['selected'] = 'selected'
                    IsSelected = True

                items.append(row)

            if not IsSelected and not no_selected:
                row = items[0]
                selected_id = row['id']
                row['selected'] = 'selected'

    data = { 
        'data'    : items, 
        'columns' : columns, 
        'config'  : _get_view_columns(database_config[_views[template]]), 
        'total'   : len(items),
        'refer'   : None,
        'status'  : None,
    }

    return data


class ApplicationGenerator(DBEngine):
    
    _default_login = 'autoload'
    _default_order_size = 19
    _subqueries = ('item', 'param', 'payment', 'comment',)
    
    def __init__(self, connection):
        super().__init__(connection=connection)

        self.login = self._default_login
        self.default_values = {}

        self.headers = []
        self.columns = {}

        self.today = getDateOnly(getToday(), DEFAULT_DATE_FORMAT[1])

        self.size = 0

    @staticmethod
    def get_currency(value):
        v = value and value.lower() or None
        return v and (v in 'usd:доллары:$' and 'USD' or v in 'euro:евро' and 'EUR') or 'RUR'

    def check_mode(self, line, file):
        model = None
        for key in _MODELS.keys():
            if line.lower() in _MODELS[key].lower():
                model = key
                break
        if not model:
            return

        for n, x in enumerate([s.strip().lower() for s in _MODELS[model].split(';')]):
            if x and len(self.headers) > n:
                self.headers[n] = x
                continue
            self.headers.append(x)

        if len(self.headers) > 1:
            for n in range(len(self.headers)-1, -1, -1):
                if not self.headers[n]:
                    del self.headers[n]
                else:
                    break

        for n, key in enumerate(self.headers):
            column, header = None, ''

            if not key:
                pass
            elif key in '№:№п/п':
                column, header = '#', 'Номер заявки'
            elif key == 'обоснование':
                column, header = 'purpose', 'Обоснование'
            elif key == 'наименование товара':
                column, header = 'article', 'Наименование товара'
            elif key in 'количество:количество, шт.':
                column, header = 'qty', 'Количество'
            elif key == 'отдел':
                column, header = 'subdivision', 'Отдел'
            elif key in 'единици измерения:единица измерения':
                column, header = 'units', 'Единицы измерения'
            elif key == 'желаемая дата поступления':
                column, header = 'date_ready', 'Желаемая дата поступления'
            elif key == 'необходимая дата оплаты':
                column, header = 'date_payment_1', 'Необходимая дата оплаты'
            elif key == 'возможная дата оплаты':
                column, header = 'date_payment_2', 'Возможная дата оплаты'
            elif key in 'фактиическая дата оплаты:фактическая дата оплаты':
                column, header = 'date_payment_3', 'Фактическая дата оплаты'
            elif key == 'предположительная дата поступления':
                column, header = 'date_shipment', 'Предположительная дата поступления'
            elif key == 'дата согласования':
                column, header = 'date_accepted', 'Дата согласования'
            elif key in 'дата составления заявки:дата составления заказа':
                column, header = 'date_created', 'Дата заявки'
            elif key == 'исполнитель':
                column, header = 'author', 'Исполнитель'
            elif key == 'направление закупки':
                column, header = 'country', 'Направление закупки'
            elif key == 'склад поступления':
                column, header = 'warehouse', 'Склад поступления'
            elif key == 'цена за единицу':
                column, header = 'price', 'Цена за единицу'
            elif key in 'общее описание:общее описание':
                column, header = 'information', 'Общее описание'
            elif key == 'поставщик':
                column, header = 'seller', 'Поставщик'
            elif key == 'условия оплаты':
                column, header = 'condition', 'Условия оплаты'
            elif key == 'валюта платежа':
                column, header = 'currency', 'Валюта платежа'
            elif key in '№ счета:номер счета':
                column, header = 'account', 'Номер счета'
            elif key in 'первый платеж (предоплата):предоплата':
                column, header = 'payment1', 'Первый платеж (предоплата)'
            elif key == 'второй платеж':
                column, header = 'payment2', 'Второй платеж'
            elif key == 'заказчик':
                column, header = 'comment1', 'Заказчик'
            elif key == 'снабжение':
                column, header = 'comment2', 'Снабжение'
            elif key == 'бухгалтерия':
                column, header = 'comment3', 'Бухгалтерия'
            else:
                continue

            if column:
                self.columns[column] = (n, header)

        m = re.match(r'.*\((.*)\).*', file.filename)

        if m and m.group(1):
            self.default_values['subdivision'] = Capitalize(m.group(1), as_is=True)

        self.default_values['author'] = self._default_login

        self.size = len(self.columns)

    def get_values(self, items, saveback):
        values = {}

        def _value(name, with_header=None, as_date=None):
            index = name in self.columns and self.columns[name][0] or -1
            value = index > -1 and ' '.join(items[index].split()) or self.default_values.get(name) or ''
            if as_date:
                value = _conv_date(value)
            if with_header:
                return (index > -1 and self.columns[name][1] or '', value,)
            return value

        def _date_payment():
            return _value('date_payment_1', as_date=True) or \
                   _value('date_payment_2', as_date=True) or \
                   _value('date_payment_3', as_date=True) or \
                   self.today

        def _article():
            return Capitalize(_clean_links(_get_string(_value('article'))), as_is=True)

        def _purpose():
            return _value('purpose') and Capitalize(_get_string(_value('purpose')), as_is=True) or ''

        def _price():
            return _get_money(_value('price'))

        def _qty():
            return _value('qty') and \
                   int(not _value('qty').isdigit() and \
                   re.sub(r'([\d]*).*', r'\1', re.sub(r'\s', '', _value('qty'))) or _value('qty')) or 1

        def _get_line():
            if _value('article'):
                author = _value('author')
                subdivision = re.sub(r'(\w+)\s+\((\w+)\)', r'\1|\2', _value('subdivision'))

                price = _price()
                qty = _qty()

                if not (price > 0 and qty > 0) and IsLoaderExplicit:
                    return 0

                total = _get_total(price, qty)
                tax = _get_tax(total)

                condition = _value('condition') or 'Без условий'
                seller = _value('seller') and _get_title(_value('seller')) or ''

                if not seller and IsLoaderExplicit:
                    return 0

                currency = self.get_currency(_value('currency'))

                values['#'] = int(items[0])
                values['author'] = self._default_login
                values['article'] = _article()
                values['qty'] = qty
                values['purpose'] = _purpose()
                values['subdivision'] = subdivision
                values['equipment'] = _value('information')
                values['price'] = price
                values['total'] = total
                values['tax'] = tax
                values['condition'] = condition
                values['seller'] = seller
                values['currency'] = currency
                values['account'] = _value('account')
                #
                #   Параметры
                #
                values['param'] = {
                    'account'        : (_value('account', with_header=True),),
                    'date_ready'     : (_value('date_ready', with_header=True, as_date=True),),
                    'date_created'   : (_value('date_created', with_header=True, as_date=True),),
                    'date_shipment'  : (_value('date_shipment', with_header=True, as_date=True),),
                    'date_accepted'  : (_value('date_accepted', with_header=True, as_date=True),),
                    'date_payment_1' : (_value('date_payment_1', with_header=True, as_date=True),),
                    'date_payment_2' : (_value('date_payment_2', with_header=True, as_date=True),),
                    'date_payment_3' : (_value('date_payment_3', with_header=True, as_date=True),),
                    'author'         : (_value('author', with_header=True),),
                    'country'        : (_value('country', with_header=True),),
                    'warehouse'      : (_value('warehouse', with_header=True),),
                }
                #
                #   Платежи
                #
                values['payment'] = {
                    'payment1'     : (_value('payment1', with_header=True), _date_payment(),),
                    'payment2'     : (_value('payment2', with_header=True), _date_payment(),),
                }
                #
                #   Комментарии подразделений
                #
                values['comment'] = {
                    'comment1'     : (_value('comment1', with_header=True),),
                    'comment2'     : (_value('comment2', with_header=True),),
                    'comment3'     : (_value('comment3', with_header=True),),
                }
                #
                #   Расшифровка счета
                #
                values['item'] = {}

                saveback['line'] = saveback['n']

                return 1

        def _get_subline():
            line = saveback['line']

            try:
                purpose = _purpose()
                name = _get_string('%s%s' % (_article(), purpose and ' [%s]' % purpose or ''))
                price = _price()
                qty = _qty()
                units = _value('units')
                total = _get_total(price, qty)
                tax = _get_tax(total)
            except:
                return 0

            row = self.make_subitem('item', {'subline' : (name, qty, units, total, tax,)})

            if row:
                saveback['data'][line][self._default_order_size].append(row[0])

            return 0

        code = 0

        if items:
            items = [x.strip() for x in items]

            if self.columns:
                if not _value('article'):
                    pass
                elif items[0].isdigit():
                    code = _get_line()
                else:
                    code = _get_subline()

        return code and values or None

    def make_subitem(self, mode, values):
        items = []

        for key, x in values.items():
            name, value = '', None
            try:
                if mode == 'item':
                    name, qty, units, total, tax = x
                    if total:
                        items.append([0,0,0, self._default_login, name, qty, units, total, tax])
                elif mode == 'param':
                    name, value = x[0][0], x[0][1]
                    if value:
                        items.append([0,0,0,0, self._default_login, name, value])
                elif mode == 'payment':
                    name, value = x[0][0], _get_money(x[0][1])
                    if value:
                        date, tax, purpose = x[1], _get_tax(value), name
                        if date:
                            items.append([0,0,0,0, self._default_login, purpose, date, value, tax, 0])
                elif mode == 'comment':
                    name, value = x[0][0], x[0][1]
                    if value:
                        items.append([0,0,0,0, self._default_login, name, value])

            except:
                print_to(None, '>>> make_subitem error: %s [%s]' % (mode, value))
                if IsPrintExceptions:
                    print_exception()

        return items

    def upload(self):
        file = request.files.get('file')
        
        if file is None or not hasattr(file, 'stream'):
            return

        is_error = False

        data = []

        default_currency = 'RUR'
        default_rowspan = 0

        with file.stream as fi:
            self.size, saveback = 0, {'n' : 0}

            saveback['data'] = data

            for s in fi:
                line = re.sub(r'\"(.*);(.*)\"', r'\1\2', s.decode(default_encoding).strip())

                if not line:
                    continue

                if not line[0].isdigit():
                    if not data:
                        self.check_mode(line, file)
                        continue

                items = line.split(';')

                if len(items) < self.size:
                    continue

                values = self.get_values(items, saveback)

                if not values or not '#' in values:
                    continue

                row = [
                    0,
                    values.get('author'),
                    values.get('article'),
                    values.get('qty'),
                    values.get('purpose'),
                    values.get('price'),
                    values.get('currency') or default_currency,
                    values.get('total'),
                    values.get('tax'),
                    values.get('subdivision'),
                    values.get('equipment'),
                    values.get('seller'),
                    values.get('condition'),
                    values.get('account'),
                    '',
                    self.login,
                    0,
                    is_no_price,
                    default_rowspan,
                    ]

                for key in self._subqueries:
                    row.append(self.make_subitem(key, values.get(key)))

                data.append(row)

                saveback['n'] += 1

        if data:
            self.begin()

            sp = {}

            view = database_config['provision-register-order']
            sp['order'] = view['exec']+' '+view['args']

            for key in self._subqueries:
                view = database_config['provision-add-%s-order' % key]
                sp[key] = view['exec']+' '+view['args']

            for n, params in enumerate(data):
                order_id = 0

                row = self.run(sp['order'], tuple(params[0:self._default_order_size]))

                if self.engine_error:
                    break

                if not row or len(row[0]) < 2:
                    continue

                order_id = row[0][0]

                if not order_id:
                    continue

                for index, key in enumerate(self._subqueries):
                    values = params[self._default_order_size + index]

                    for p in values:
                        p[1] = order_id

                        row = self.run(sp[key], tuple(p))

                        if self.engine_error:
                            break
                    
                    if self.engine_error:
                        break

            self.close()


class ApplicationService(Connection):

    def __init__(self, connection, kw=None):
        super().__init__(connection, requested_object)

        self._kw = kw

        self.lastrowid = None

    def _get_args(self):
        where, order, args = _make_page_default(self._kw, back_where=True)

        self.where = where
        self.order = order
        self.args = args

        if IsDebug:
            print('>>> ApplicationService, where: [%s]' % self.where)

    def _sql(self, sql):
        return sql.replace('{where}', self.where and 'WHERE %s' % self.where or '')

    def download(self):
        self._get_args()

    def run(self, mode):
        self._get_args()

        errors = []

        self.open(0)

        try:
            if mode == 'delete-orders':
                self.connect(self._sql(_SQL['Params']['delete']), None)
                self.connect(self._sql(_SQL['Items']['delete']), None, check_error=True)
                self.connect(self._sql(_SQL['Payments']['delete']), None, check_error=True)
                self.connect(self._sql(_SQL['Comments']['delete']), None, check_error=True)
                self.connect(self._sql(_SQL['Reviews']['delete']), None, check_error=True)
                self.connect(self._sql(_SQL['OrderDates']['delete']), None, check_error=True)

                if not self.is_error:
                    self.connect(self._sql(_SQL['Orders']['delete']), None)

            elif mode == 'clear-history':
                self.connect(self._sql(_SQL['Reviews']['delete']), None)

                if not self.is_error:
                    self.connect(self._sql(_SQL['Orders']['set-status']), (0,))
        except:
            if IsPrintExceptions:
                print_exception()

        self.close()

        if self.is_error:
            errors.append(gettext('Error: SQL broken. See transaction log.'))

        return errors


class Provision:

    def __init__(self, user):
        self.user = user
        self.login = user.login
        self.reviewer = user.full_name()

        self.action_id = None
        self.status = None

        self._errors = []

    @staticmethod
    def _exception(self, errors):
        errors.append(gettext('Error: Unexpected exception'))

    def _get_refer_id(self):
        return int(self.status.split(':')[2])

    def _get_reviewers(self, order_id):
        """
            Список текущих рецензентов по заказу.

            Аргументы:
                order_id        -- ID заказа
        """
        users = []

        # Assigned reviewers
        for x in _get_order_reviewers(order_id, as_dict=True):
            reviewer = _get_user(x.get('Login'))

            if reviewer is not None:
                users.append(reviewer)

        return users

    def _get_reviewer_managers(self, mode, order_id, author, **kw):
        """
            Рецензент и список руководителей заказчика.

            Аргументы:
                mode            -- режим опроса, 
                    0           -- все менеджеры, 
                    1           -- прямые руководители, 
                    2           -- вышестоящие руководители

                order_id        -- ID заказа
                author          -- логин рецензента

                is_review_headoffice -- включить руководство компании

                with_headoffice -- исполнительный директор
                with_assistant  -- заместитель ГД
                with_root       -- ГД
        """
        reviewer = None

        is_review_headoffice = kw.get('is_review_headoffice') or False

        with_headoffice = kw.get('with_headoffice') or False
        with_assistant = kw.get('with_assistant') or False
        with_root = kw.get('with_root') or False

        order = kw.get('order') or requested_object.get('TID') == order_id and requested_object or _get_order(order_id)

        if author is None:
            author = order.get('Author')

        code = order.get('SubdivisionCode')

        reviewers = []

        try:
            if author:
                reviewer = _get_user(author)
        except:
            pass

        managers = []

        if code and mode in (0, 1):
            managers += User.get_managers(code)

        if reviewer is not None:
            if mode in (0, 1):
                managers += reviewer.managers(with_assistant=with_assistant)

            if mode in (0, 2) and is_review_headoffice:
                code = reviewer.subdivision_code == '0002' and '0001' or None
                with_headoffice = with_headoffice or not reviewer.has_subdivision_group(reviewer.subdivision_code)
                with_root = with_root or code == '0001'

                managers += reviewer.managers(id=reviewer.app_root('id', code=code), 
                    with_headoffice=with_headoffice, 
                    with_assistant=with_assistant, 
                    with_root=with_root
                    )

            if mode in (0, 1) and code:
                managers += reviewer.managers(id=reviewer.app_root('id', code=code))

        if mode in (0, 1):
            managers += self._get_reviewers(order_id)

        return reviewer, list(set(managers))

    def _check_review_timedelta(self, order_id, status, note=None):
        now = getToday()

        errors = []

        reviews = _get_reviews(order_id, login=self.login, cursor=1)

        for review in sorted(reviews, key=lambda k: k['StatusDate'], reverse=True):
            status_review = review['Status']
            status_date = review['StatusDate']

            if status == status_review and minutedelta(status_date, 15) > now and (
                not note or not is_unique_strings(note, review['Note'])):
                errors.append(gettext('Error: Confirmation review rules.'))
                break

        return errors

    def _mail(self, mode, html, reviewer, users, default_emails=None):
        errors = []
        done = 0

        emails = [user.email for user in users]

        def _send(addr_to, addr_cc, root):
            if not (addr_to and addr_to.replace(reviewer.email, '')):
                return 0

            timestamp = getDate(getToday(), format=UTC_FULL_TIMESTAMP)
            done = 1

            if not IsNoEmail:
                done = send_simple_mail(subject, 
                    html.replace('webperso', _PROVISION_LINK % root), 
                    addr_to, 
                    addr_cc=addr_cc
                    )

            if IsTrace:
                print_to(None, '>>> mail sent %s, login:%s, to:%s, cc:%s, root:[%s]' % (timestamp, 
                    self.login, addr_to, addr_cc, root))

            return done

        if reviewer is not None and emails:
            subject = 'PROVISION %s' % mode.upper()

            addrs = list(set(filter(None, emails)))

            # ---------------
            # Public web link
            # ---------------

            root = DEFAULT_ROOT.get('public')

            if root:
                addr_to = ';'.join(sorted(set([emails.pop(emails.index(x)) for x in _DEFAULT_EMAILS['public'] if x in addrs])))
                addr_cc = ';'.join(_DEFAULT_EMAILS['common'])

                done += _send(addr_to, addr_cc, root)

            # --------------
            # Local web link
            # --------------

            root = DEFAULT_ROOT.get('local')

            if root:
                addr_to = ';'.join(sorted(set(emails)))
                addr_cc = reviewer.email not in _DEFAULT_EMAILS['public'] and reviewer.email or None

                done += _send(addr_to, addr_cc, root)

        else:
            errors.append('Email recipient list is empty.')

        if done:
            print_to(None, '')

        return errors

    @staticmethod
    def combo_value(key, attrs, caller, template, default_key='Name', new_data=None):
        id = attrs.get(key) or None
        new = attrs.get('new_%s' % key) or ''

        value = new.strip()

        if not value and id and caller is not None:
            v = caller(id)
            if new_data:
                v.update(new_data)
            value = v and template and (template % v) or v and v.get(default_key)

        return value

    def set_attrs(self, attrs):
        self._article = _get_string(attrs.get('order_article'))
        self._subdivision_id = attrs.get('order_subdivision')
        self._subdivision_new = _get_string(attrs.get('new_order_subdivision'))
        self._category_id = attrs.get('order_category')
        self._category_new = _get_string(attrs.get('new_order_category'))
        self._qty = int(attrs.get('order_qty') or 1)
        self._purpose = _get_string(attrs.get('order_purpose'), save_links=True)
        self._price = _get_money(attrs.get('order_price') or 0)
        self._currency = attrs.get('order_currency')
        self._condition_id = attrs.get('order_condition')
        self._condition_new = _get_string(attrs.get('new_order_condition'))
        self._seller_id = attrs.get('order_seller')
        self._seller_new = _get_string(attrs.get('new_order_seller'))
        self._title = _get_string(attrs.get('order_title'))
        self._address = _get_string(attrs.get('order_address'), save_links=True)
        self._equipment = _get_string(attrs.get('order_equipment'))
        self._duedate = attrs.get('order_duedate')
        self._author = attrs.get('order_author')

        if not self._currency or self._currency == DEFAULT_UNDEFINED:
            self._currency = 'RUR'

        self._subdivision = self.combo_value('order_subdivision', attrs, _get_subdivision, '')
        self._category = self.combo_value('order_category', attrs, _get_category, '')
        self._condition = self.combo_value('order_condition', attrs, _get_condition, '')

        if self._seller_id:
            template = '%(Name)s||%(Title)s||%(Address)s'
            new_data = {}
            if self._title:
                new_data['Title'] = self._title
            if self._address:
                new_data['Address'] = self._address
            self._seller = self.combo_value('order_seller', attrs, _get_seller, template, new_data=new_data)
        elif not self._seller_new and self._address:
            self._errors.append(gettext('Error: Seller URL address should be present together with a new company name!'))
        elif not self._seller_new and self._title:
            self._errors.append(gettext('Error: Seller Title should be present together with a new company name!'))
        else:
            self._seller = '%s||%s||%s' % (self._seller_new, self._title, self._address)

        if self._errors:
            return None

        return {
            'Login'       : (0, self.login, 'Автор заявки',),
            'Subdivision' : (1, self._subdivision, 'ПОТРЕБИТЕЛЬ',),
            'Article'     : (2, self._article, 'Наименование товара',), 
            'Qty'         : (3, self._qty, 'Количество (шт)',),
            'Purpose'     : (4, self._purpose, 'Обоснование',),
            'Price'       : (5, self._price, 'Цена за единицу',),
            'Currency'    : (6, self._currency, 'Валюта платежа',),
            'Condition'   : (7, self._condition, 'Условия оплаты'),
            'Seller'      : (8, self._seller, 'Поставщик',),
            'Title'       : (9, self._title, 'Наименование организации поставщика',),
            'Address'     : (10, self._address, 'Адрес организации поставщика',),
            'Equipment'   : (11, self._equipment, 'Описание',), 
            'DueDate'     : (12, self._duedate, 'Срок исполнения',), 
            'Author'      : (13, self._author, 'Заказчик',), 
            'Category'    : (14, self._category, 'Категория',),
            }

    def set_order(self, attrs, is_check=None):
        """
            Check & Make Provision order
        """
        errors = []

        tag_params = self.set_attrs(attrs)

        if self._errors:
            return self._errors, None, None
        #
        # Check attrs are present
        #
        n = 0
        for index, value, title in sorted(tag_params.values(), key=itemgetter(0)):
            if index not in (5,6,7,8,9,10,12,13,14) and (not value or value == DEFAULT_UNDEFINED):
                errors.append('%s %s' % (gettext('Warning: Parameter is empty:'), title))
                n += 1

        if errors:
            if n >= 5:
                errors = [gettext('Warning: Provision form is empty!')]
            if is_check:
                return errors
            return errors, None, None

        if len(self._equipment) < 10:
            errors.append(gettext('Error: Equipment should be present!'))
            return errors, None, None

        if not is_unique_strings(self._article, self._equipment):
            errors.append('%s: %s + %s' % (gettext('Warning: Strings should be unique'), tag_params['Article'][2], tag_params['Equipment'][2]))
            return errors, None, None

        if not is_unique_strings(self._article, self._purpose):
            errors.append('%s: %s + %s' % (gettext('Warning: Strings should be unique'), tag_params['Article'][2], tag_params['Purpose'][2]))
            return errors, None, None

        if not is_unique_strings(self._purpose, self._equipment):
            errors.append('%s: %s + %s' % (gettext('Warning: Strings should be unique'), tag_params['Purpose'][2], tag_params['Equipment'][2]))
            return errors, None, None

        columns = sorted(list(tag_params.keys()))
        kw = dict(zip(map(lambda x: x.lower(), columns), [tag_params[x][1] for x in columns]))

        if not self._price:
            self._price = 0.0

        if not self._qty:
            self._qty = 1

        self._total = _get_total(self._price, self._qty)
        self._tax = _get_tax(self._total)

        if not self._subdivision:
            errors.append('%s %s' % (gettext('Error: Subdivision is underfined:'), self._subdivision))

        if not errors:
            kw['subdivision'] = self._subdivision
            kw['category'] = self._category or ''
            kw['seller'] = self._seller or ''
            kw['condition'] = self._condition or ''
            kw['total'] = self._total
            kw['tax'] = self._tax
            kw['duedate'] = self._duedate
            kw['status'] = 0
            # XXX
            kw['equipment'] = self._equipment
            kw['account'] = ''
            
            if kw['author']:
                kw.update({'login' : kw['author'], 'author' : self.login})
            else:
                kw['author'] = self.login

            kw['is_no_price'] = is_no_price

        if is_check:
            return errors

        return errors, tag_params, kw

    def create_order(self, attrs):
        """
            Create a new Provision order
        """
        errors, tag_params, kw = self.set_order(attrs)

        if not errors:
            errors = self.run('register', kw)

        if self.action():
            tag_params['TID'] = self.action_id
            tag_params['Status'] = 0
            self.send_create_mail(tag_params)

        return errors

    def update_order(self, id, attrs):
        """
            Update given Provision order
        """
        errors, tag_params, kw = self.set_order(attrs)

        if id and not errors:
            kw['id'] = id
            errors = self.run('refresh', kw)

        return errors

    def delete_order(self, id):
        """
            Remove Provision order
        """
        errors, kw = [], {}

        if not (id and id == requested_object.get('TID')):
            errors.append(gettext('Error: Order ID is invalid!'))

        if _is_disabled_delete():
            errors.append(gettext('Warning: Order cannot be removed!'))

        if not errors:
            kw['id'] = id
            kw['login'] = self.login
            errors = self.run('remove', kw)

            if not errors:
                seller_id = requested_object['SellerID']

                if seller_id:
                    kw['id'] = seller_id
                    self.run('del-seller', kw)

        if self.action():
            self.send_remove_mail(requested_object)

        return errors

    def clone_order(self, id, attrs):
        """
            Clone given Provision order
        """
        errors, tag_params, kw = self.set_order(attrs)

        if id and not errors:
            kw['id'] = None
            kw['account'] = ''
            kw['status'] = -1
            errors = self.run('register', kw)

        if self.action():
            tag_params['TID'] = self.action_id
            tag_params['Status'] = 0
            self.send_create_mail(tag_params)

        return errors

    def review_action(self, order_id, status, note, params=None, check_past=False):
        """
            Register Review Action.

            Arguments:
                reviewer -- dict, reviewer {login, name}

            Returns:
                Stored procedure response.
                If OK `ActionID`, `Status`
        """
        if not order_id:
            return

        self.action_id, self.status = 0, None
        command, review_duedate, with_mail = '', None, 0

        if isinstance(params, dict):
            command = params.get('command', None) or ''
            review_duedate = params.get('review_duedate', None) or ''
            with_mail = params.get('with_mail', None) or 0

        if not checkDate(review_duedate, LOCAL_EASY_DATESTAMP):
            review_duedate = ''

        if check_past and review_duedate and getDate(review_duedate, LOCAL_EASY_DATESTAMP, is_date=True) < getDateOnly(getToday()):
            self._errors.append(gettext('Error: Date is in past!'))
            return

        cursor, error_msg = engine.runProcedure('provision-register-review', 
                order_id=order_id,
                login=self.login, 
                reviewer=self.reviewer, 
                status=status,
                note=note,
                review_duedate=review_duedate,
                with_mail=with_mail,
                with_error=True,
                with_log=True,
            )

        if cursor:
            self.action_id = cursor[0][0]
            self.status = cursor[0][1]
        else:
            if IsTrace:
                print_to(None, '!!! review_action, no cursor: %s' % str(self.login))

        if error_msg and engine.engine_error:
            self._errors.append(error_msg)

        if self.action():
            if status in (2,3,4,5,6) or with_mail:
                self.send_review_mail(status, note, review_duedate=review_duedate)
        else:
            self._errors.append(gettext('Review Execution error'))

        if self._errors:
            if IsTrace or IsPrintExceptions:
                print_to(None, '!!! review_action, error: %s, action_id: %s, errors: %s' % (
                    self.status, self.action_id, repr(self._errors)))

    def set_unread(self, order_id, users, force=None):
        """
            Отметить как непрочтенное
        """
        logins = list(set([x.login for x in users if x is not None]))

        # Remove myself
        if not force and self.login in logins:
            logins.remove(self.login)

        if not logins:
            return

        cursor, error_msg = engine.runProcedure('provision-set-unread', 
                order_id=order_id,
                logins='|'.join(logins), 
                with_error=True,
            )

        if IsTrace:
            print_to(None, '>>> set_unread, login:%s, order:%d, users:%s' % (self.login, order_id, repr(logins)))

        if error_msg and engine.engine_error:
            print_to(None, '!!! set_unread, engine error: %s' % str(error_msg))
            self._errors.append(error_msg)

    def set_read(self, order_id, users, force=None):
        """
            Отметить как прочтенное
        """
        logins = list(set([x.login for x in users if x is not None]))

        if not logins:
            return

        cursor, error_msg = engine.runProcedure('provision-set-read', 
                order_id=order_id or 'null',
                logins='|'.join(logins), 
                with_error=True,
            )

        if IsTrace:
            print_to(None, '>>> set_read, login:%s, order:%s, users:%s' % (self.login, order_id, repr(logins)))

        if error_msg and engine.engine_error:
            print_to(None, '!!! set_read, engine error: %s' % str(error_msg))
            self._errors.append(error_msg)

    def notify(self, order_id, author, unreads=None):
        """
            Напомнить об изменениях
        """
        reviewer = None

        try:
            if author:
                reviewer = _get_user(author)
        except:
            pass

        users = []

        if reviewer is not None:
            users.append(reviewer)
            users += reviewer.managers()

        if unreads:
            users += [User.get_by_email(x) for x in unreads]

        self.set_unread(order_id, users+[reviewer])

    def send_order_notifications(self, order_id, params=None):
        """
            Проверить статус заказа "Требуется обоснование"
        """
        with_mail = params and params.get('with_mail', None) or not params and 1 or 0

        order = _get_order(order_id)

        reviewer, chiefs = self._get_reviewer_managers(1, order_id, None, order=order)

        reviewer, managers = self._get_reviewer_managers(2, order_id, None, is_review_headoffice=True, 
            with_headoffice=True, with_assistant=True, with_root=True, order=order)

        manager_logins = [x.login for x in managers]

        reviews = _get_reviews(order_id, order='TID asc', cursor=True)

        def _check_review(mode, user):
            if user is None:
                return

            has_confirmation = 0
            has_confirm = 0

            for row in reviews:
                login = row['Login']
                status = _get_review_status(row['Status']).lower()

                if status == 'confirmation' and has_confirm:
                    if mode == 'confirmation':
                        if login == user.login:
                            return True
                    else:
                        has_confirmation = 1

                if login in manager_logins:
                    if status == 'confirm':
                        has_confirm = 1
                        has_confirmation = 0
                    elif status in ('accept', 'reject',):
                        if mode == 'confirm' and has_confirm and has_confirmation:
                            if login == user.login:
                                return True
                        if mode == 'confirmation':
                            has_confirm = 0

            if mode == 'confirmation':
                return not (has_confirm and not has_confirmation) and True or False

            if mode == 'confirm':
                return not (has_confirm and has_confirmation) and True or False

            return False

        make_unreads = []
        users = []

        default_reviewers = [User.get_by_email(x) for x in _DEFAULT_EMAILS['review']]

        # ---------------------
        # Обоснование заказчика
        # ---------------------

        for user in chiefs + [reviewer] + default_reviewers:
            # Обоснования нет
            if not _check_review('confirmation', user):
                make_unreads.append(user)
                users.append(user)

        # ----------------------
        # Резолюция руководителя
        # ----------------------

        for user in managers:
            # Обоснование не просмотрено или решение не принято
            if not _check_review('confirm', user):
                make_unreads.append(user)
                users.append(user)

        self.set_unread(order_id, make_unreads)

        if IsTrace:
            print_to(None, '>>> send_order_notifications, login:%s, order:%d, users:%s, datetime:%s' % (self.login, order_id,
                repr([x.login for x in make_unreads]), getDate(getToday(), format=UTC_FULL_TIMESTAMP)))

        if not with_mail:
            return

        # From
        user = _get_user(self.login)

        # To
        users += [User.get_by_email(x) for x in _DEFAULT_EMAILS['common']]

        if not users:
            return

        props = {
            'id'          : order_id,
            'Seller'      : order.get('Seller'),
            'Article'     : order.get('Article'),
            'Date'        : getDate(getToday(), DEFAULT_DATETIME_INLINE_FORMAT),
            'Title'       : 'Запрос на согласование заказа снабжения',
            'Reviewer'    : 'Автор запроса: %s' % user.full_name(),
            'Message'     : 'Пожалуйста, ознакомьтесь с информацией о согласовании заказа.',
        }

        html = _EMAIL_EOL.join(_APPROVAL_ALARM_HTML.split('\n')) % props

        return self._mail('approval', html, user, users)

    def send_review_notifications(self, params=None):
        """
            Проверить статус заказов "На согласовании"
        """
        orders = _get_orders(where='Status in (1,2,4)')

        for row in orders:
            order_id = row['TID']
            self.send_order_notifications(order_id, params=params)

    def send_create_mail(self, attrs):
        """
            Уведомление о создании заказа
        """
        order_id = attrs.get('TID')

        if not order_id:
            return None

        # From
        user = _get_user(self.login)

        # To
        login = attrs.get('Author')
        author = login and len(login) == 3 and login[1] != DEFAULT_UNDEFINED and login[1] or None

        reviewer = None

        try:
            if author:
                reviewer = _get_user(author)
        except:
            pass

        users = []

        if reviewer is not None:
            users.append(reviewer)
            users += reviewer.managers()

        users += [User.get_by_email(x) for x in _DEFAULT_EMAILS['create']]
        users += [User.get_by_email(x) for x in _DEFAULT_EMAILS['common']]

        self.set_unread(order_id, users+[reviewer])

        props = {
            'id'          : order_id,
            'Seller'      : '',
            'Article'     : attrs.get('Article')[1],
            'Date'        : getDate(getToday(), DEFAULT_DATETIME_INLINE_FORMAT),
            'Title'       : '',
            'Subdivision' : attrs.get('Subdivision')[1],
            'Reviewer'    : user.full_name(),
            'Message'     : '',
        }

        html = _EMAIL_EOL.join(_CREATE_ALARM_HTML.split('\n')) % props

        return self._mail('new order', html, user, users)

    def send_remove_mail(self, attrs):
        """
            Уведомление об удалении заказа
        """
        order_id = attrs.get('TID')

        if not order_id:
            return None

        # Remover
        user = _get_user(self.login)

        # To
        author = attrs.get('Author')
        reviewer = author and _get_user(author) or None

        users = []

        if reviewer is not None:
            users.append(reviewer)
            users += reviewer.managers()

        users += [User.get_by_email(x) for x in _DEFAULT_EMAILS['remove']]
        users += [User.get_by_email(x) for x in _DEFAULT_EMAILS['common']]

        props = {
            'id'          : order_id,
            'Seller'      : attrs.get('Seller'),
            'Article'     : attrs.get('Article'),
            'Date'        : getDate(getToday(), DEFAULT_DATETIME_INLINE_FORMAT),
            'Title'       : '',
            'Subdivision' : attrs.get('Subdivision'),
            'Reviewer'    : reviewer and reviewer.full_name() or '',
            'Remover'     : '%s (%s)' % (user and user.full_name() or '---', self.login),
        }

        html = _EMAIL_EOL.join(_REMOVE_ALARM_HTML.split('\n')) % props

        return self._mail('order removed', html, user, users)

    def send_approval_mail(self, attrs):
        """
            Запрос на согласование
        """
        order_id = requested_object.get('TID')

        if not order_id:
            return None

        status = requested_object.get('Status')

        if not status < 5:
            return None

        # From
        user = _get_user(self.login)

        # To
        author = requested_object.get('Author')

        reviewer = None

        try:
            if author:
                reviewer = _get_user(author)
        except:
            pass

        users = []

        if reviewer is not None:
            users.append(reviewer)
            users += reviewer.managers(with_assistant=True)

            code = requested_object.get('SubdivisionCode')

            if code:
                users += reviewer.managers(id=reviewer.app_root('id', code=code))

        users += self._get_reviewers(order_id)

        users += [User.get_by_email(x) for x in _DEFAULT_EMAILS['approval']]
        users += [User.get_by_email(x) for x in _DEFAULT_EMAILS['common']]

        self.set_unread(order_id, users+[reviewer])

        props = {
            'id'          : order_id,
            'Seller'      : requested_object.get('Seller'),
            'Article'     : requested_object.get('Article'),
            'Date'        : getDate(getToday(), DEFAULT_DATETIME_INLINE_FORMAT),
            'Title'       : 'Запрос на согласование заказа снабжения',
            'Reviewer'    : 'Автор запроса: %s' % user.full_name(),
            'Message'     : attrs and _html_note(attrs.get('note') or ''),
        }

        html = _EMAIL_EOL.join(_APPROVAL_ALARM_HTML.split('\n')) % props

        return self._mail('approval', html, user, users)

    def send_review_mail(self, status, note=None, **kw):
        """
            Уведомление о поступлении рецензии
        """
        order_id = requested_object.get('TID')
        order_status = requested_object.get('Status')

        if not order_id:
            return None

        is_review_headoffice, with_headoffice, with_assistant, with_root = IsReviewHeadOffice, 0, 1, 0

        # Review Event
        if order_status in (1,2,3,4):
            with_root = 1

        # Paid Event
        if status == 6:
            is_review_headoffice, with_headoffice, with_root = 1, 1, 1

        if status not in (2,3,4,5,6):
            return None

        # From
        user = _get_user(self.login)

        # To
        author = requested_object.get('Author')

        reviewer, users = self._get_reviewer_managers(0, order_id, author, is_review_headoffice=is_review_headoffice, 
            with_headoffice=with_headoffice, with_assistant=with_assistant, with_root=with_root)

        users += [User.get_by_email(x) for x in _DEFAULT_EMAILS['review']]
        users += [User.get_by_email(x) for x in _DEFAULT_EMAILS['common']]

        self.set_unread(order_id, users+[reviewer])
        self.set_read(order_id, [user])

        if reviewer is not None:
            if status > 2 and author != self.login:
                users.append(reviewer)

        review_duedate = kw.get('review_duedate', None) or ''

        caption = order_status > 4 and 'об исполнении' or 'о согласовании'
        if status == 5:
            title = 'Обоснование по заказу снабжения'
        else:
            title = 'Информация %s заказа снабжения' % (status == 6 and 'об оплате' or 'о согласовании')
        reviewer = 'Автор рецензии: %s%s' % (user.full_name(), review_duedate and ( 
            '.<br>%s: %s' % (status == 6 and 'Дата оплаты' or status == 4 and 'Срок обоснования' or '', review_duedate)) or '')

        props = {
            'id'          : order_id,
            'Caption'     : caption,
            'Seller'      : requested_object.get('Seller'),
            'Article'     : requested_object.get('Article'),
            'Date'        : getDate(getToday(), DEFAULT_DATETIME_INLINE_FORMAT),
            'Title'       : title,
            'Reviewer'    : reviewer,
            'Message'     : _html_note(note or ''),
            'Code'        : _get_review_status(status, is_title=True),
            'code'        : _get_review_status(status).lower() or '',
        }

        html = _EMAIL_EOL.join(_REVIEW_ALARM_HTML.split('\n')) % props

        return self._mail('review', html, user, users)

    def accept(self, order_id, note):
        """
            Accept an order
        """
        errors = []

        status = _PROVISION_STATUSES['accepted'][0]

        if note:
            note = _get_string(note, save_links=True)

        if len(note) > MAX_CONFIRMATION_LEN:
            errors.append('%s' % gettext('Error: Confirmation Note is too long!'))

        errors += self._check_review_timedelta(order_id, status)

        if not errors:
            self.review_action(order_id, status, note)
            errors = self._errors

        return errors

    def reject(self, order_id, note):
        """
            Reject an order
        """
        errors = []

        status = _PROVISION_STATUSES['rejected'][0]

        if note:
            note = _get_string(note, save_links=True)

        if len(note) > MAX_CONFIRMATION_LEN:
            errors.append('%s' % gettext('Error: Confirmation Note is too long!'))

        errors += self._check_review_timedelta(order_id, status)

        if not errors:
            self.review_action(order_id, status, note)
            errors = self._errors

        return errors

    def confirm(self, order_id, note, params=None):
        """
            Confirm, request on information
        """
        errors = []

        status = _PROVISION_STATUSES['confirm'][0]

        if note:
            note = _get_string(note, save_links=True)

        if len(note) > MAX_CONFIRMATION_LEN:
            errors.append(gettext('Error: Confirmation Note is too long!'))

        errors += self._check_review_timedelta(order_id, status)

        if not errors:
            self.review_action(order_id, status, note, params=params, check_past=True)
            errors = self._errors

        return errors

    def confirmation(self, order_id, note):
        """
            Make confirmation on order
        """
        errors = []

        status = 5

        if note:
            note = _get_string(note, save_links=True)

        if not note:
            errors.append('%s' % gettext('Error: Empty confirmation Note'))
        elif len(note) > MAX_CONFIRMATION_LEN:
            errors.append('%s' % gettext('Error: Confirmation Note is too long!'))

        errors += self._check_review_timedelta(order_id, status, note=note)

        if not errors:
            self.review_action(order_id, status, note)
            errors = self._errors

        return errors

    def paid(self, order_id, note, params=None):
        """
            Order paid event
        """
        errors = []

        status = 6

        if note:
            note = _get_string(note, save_links=True)

        if requested_object.get('Status') < 5:
            errors.append('%s' % gettext('Error: Order cannot be paid until accepted!'))
        elif len(note) > MAX_CONFIRMATION_LEN:
            errors.append('%s' % gettext('Error: Confirmation Note is too long!'))

        errors += self._check_review_timedelta(order_id, status)

        if not errors:
            self.review_action(order_id, status, note, params=params)
            errors = self._errors

        return errors

    def params_action(self, order_id, attrs):
        """
            Actions with Order Params: ADD|DEL
        """
        command = attrs.get('command')
        id = int(attrs.get('id') or 0)
        param_id = int(attrs.get('param_id') or 0)
        new_param = attrs.get('new_param') or ''
        value = attrs.get('value')

        data, errors, kw, title = [], [], {}, ''

        if command in ('ADD_PARAM', 'SAVE_PARAM',):
            if not param_id and not new_param:
                errors.append('%s' % gettext('Error: Empty Param ID'))
            elif new_param:
                param_id = 0

            if not value:
                errors.append('%s' % gettext('Error: Empty Param value'))

            title = 'add-param'
            kw.update({
                'order_id'  : order_id,
                'param_id'  : param_id,
                'new_param' : new_param,
                'value'     : value,
                'id'        : id,
            })

        if command == 'DEL_PARAM':
            if not id:
                errors.append('%s' % gettext('Error: Empty Param ID'))

            title = 'del-param'
            kw.update({
                'order_id'  : order_id,
                'param_id'  : param_id,
                'id'        : id,
            })
        
        try:
            if not errors:
                kw['login'] = self.login
                errors = self.run(title, kw)
        except:
            if IsPrintExceptions:
                print_exception()

            self._exception(errors)

        data = _get_order_params(order_id, order='Name')

        if self.status and not self.status.startswith('Invalid') and new_param:
            data['refer'] = ('param', self._get_refer_id(), new_param)

        return data, '', errors

    def items_action(self, order_id, attrs):
        """
            Actions with Order Items: ADD|DEL
        """
        command = attrs.get('command')
        id = int(attrs.get('id') or 0)
        item = attrs.get('name') or ''
        qty = int(attrs.get('qty') or 0) or 1
        units = attrs.get('units') or 'шт.'
        total = _get_money(attrs.get('total'))
        account = attrs.get('account') or ''
        no_tax = attrs.get('no_tax') and True or False

        data, errors, kw, title = [], [], {}, ''

        if command in ('ADD_ITEM', 'SAVE_ITEM',):
            if not item:
                errors.append('%s' % gettext('Error: Empty Item name'))

            if not total and not self.user.app_is_author:
                errors.append('%s' % gettext('Error: Empty Item total value'))

            title = 'add-item'
            kw.update({
                'order_id'  : order_id,
                'item'      : item,
                'qty'       : qty,
                'units'     : units,
                'total'     : total,
                'tax'       : no_tax and _get_tax(total) or 0.0,
                'account'   : account,
                'id'        : id,
            })

        if command == 'DEL_ITEM':
            if not id:
                errors.append('%s' % gettext('Error: Empty Item ID'))

            title = 'del-item'
            kw.update({
                'order_id'  : order_id,
                'id'        : id,
            })
        
        try:
            if not errors:
                kw['login'] = self.login
                errors = self.run(title, kw)
        except:
            if IsPrintExceptions:
                print_exception()

            self._exception(errors)

        data = _get_order_items(order_id, order='Name')

        return data, '', errors

    def payments_action(self, order_id, attrs):
        """
            Actions with Order Payments: ADD|DEL
        """
        command = attrs.get('command')
        id = int(attrs.get('id') or 0)
        payment_id = int(attrs.get('payment_id') or 0)
        new_payment = attrs.get('new_payment') or ''
        date = attrs.get('date')
        total = _get_money(attrs.get('total'))
        status = int(attrs.get('status') or 0)

        data, errors, kw, title = [], [], {}, ''

        if command in ('ADD_PAYMENT', 'SAVE_PAYMENT',):
            if not payment_id and not new_payment:
                errors.append('%s' % gettext('Error: Empty Payment ID'))
            elif new_payment:
                payment_id = 0

            if not date:
                errors.append('%s' % gettext('Error: Empty Payment date'))

            if not total:
                errors.append('%s' % gettext('Error: Empty Payment total value'))

            title = 'add-payment'
            kw.update({
                'order_id'    : order_id,
                'payment_id'  : payment_id,
                'new_payment' : new_payment,
                'date'        : date,
                'total'       : total,
                'tax'         : _get_tax(total),
                'status'      : status,
                'id'          : id,
            })

        if command == 'DEL_PAYMENT':
            if not id:
                errors.append('%s' % gettext('Error: Empty Payment ID'))

            title = 'del-payment'
            kw.update({
                'order_id'    : order_id,
                'payment_id'  : payment_id,
                'id'          : id,
            })

        try:
            if not errors:
                kw['login'] = self.login
                errors = self.run(title, kw)
        except:
            if IsPrintExceptions:
                print_exception()
            
            self._exception(errors)

        data = _get_order_payments(order_id, order='Purpose')

        if self.status and not self.status.startswith('Invalid') and new_payment:
            data['refer'] = ('payment', self._get_refer_id(), new_payment)

        return data, 'XXX', errors

    def comments_action(self, order_id, attrs):
        """
            Actions with Order Comments: ADD|DEL
        """
        command = attrs.get('command')
        id = int(attrs.get('id') or 0)
        comment_id = int(attrs.get('comment_id') or 0)
        new_comment = attrs.get('new_comment') or ''
        note = attrs.get('note')

        data, errors, kw, title = [], [], {}, ''

        if command == 'ADD_COMMENT':
            if not comment_id and not new_comment:
                errors.append('%s' % gettext('Error: Empty Comment ID'))
            elif new_comment:
                comment_id = 0

            if not note:
                errors.append('%s' % gettext('Error: Empty Comment value'))

            title = 'add-comment'
            kw.update({
                'order_id'    : order_id,
                'comment_id'  : comment_id,
                'new_comment' : new_comment,
                'note'        : note,
                'id'          : id,
            })

        try:
            if not errors:
                kw['login'] = self.login
                errors = self.run(title, kw)
        except:
            if IsPrintExceptions:
                print_exception()

            self._exception(errors)

        data = _get_order_comments(order_id, order='Author')

        if self.status and not self.status.startswith('Invalid') and new_comment:
            data['refer'] = ('comment', self._get_refer_id(), new_comment)

        return data, '', errors

    def documents_action(self, order_id, attrs):
        """
            Actions with Order Documents: ADD|DEL
        """
        command = attrs.get('command')
        id = int(attrs.get('id') or 0)
        filename = attrs.get('filename') or ''
        value = attrs.get('value')

        data, errors, kw, title = [], [], {}, ''

        if command in ('ADD_DOCUMENT',):
            command = None

        if command == 'DEL_DOCUMENT':
            if not id:
                errors.append('%s' % gettext('Error: Empty Document ID'))

            title = 'del-document'
            kw.update({
                'order_id'  : order_id,
                'id'        : id,
            })

        try:
            if not errors and command:
                kw['login'] = self.login
                errors = self.run(title, kw)
        except:
            if IsPrintExceptions:
                print_exception()

            self._exception(errors)

        data = _get_order_documents(order_id, order='FileName')
        """
        if self.status and not self.status.startswith('Invalid'):
            data['refer'] = ('document', self._get_refer_id(), filename)
        """
        return data, '', errors

    def set_status(self, order_id, attrs, **kwargs):
        """
            Change status of Order
        """
        command = attrs.get('command')
        status = None

        is_extra = kwargs.get('is_extra') and True or False

        data, errors, kw, title = [], [], {}, 'set-status'

        if command.startswith('STATUS_'):
            key = command.split('_')[1].lower()

            if is_extra:
                pass
            elif key in ('review', 'execute',) and not requested_object.get('Price'):
                errors.append('%s' % gettext('Error: Price is not defined'))
            elif key == 'execute' and requested_object.get('Status') not in (_PROVISION_STATUSES['accepted'][0], _PROVISION_STATUSES['finish'][0],):
                errors.append('%s' % gettext('Error: Status of order cannot be changed.'))
            elif key == 'finish' and requested_object.get('Status') != _PROVISION_STATUSES['execute'][0]:
                errors.append('%s' % gettext('Error: Status of order cannot be changed.'))

            if not errors:
                status = _PROVISION_STATUSES.get(key)[0]

            kw.update({
                'order_id'  : order_id,
                'status'    : status,
            })

        try:
            if not errors:
                kw['login'] = self.login
                errors = self.run(title, kw)
        except:
            if IsPrintExceptions:
                print_exception()

            self._exception(errors)

        if not errors:
            self.notify(order_id, requested_object.get('Author'), 
                unreads=status in (5,6) and _DEFAULT_EMAILS['execute'] or _DEFAULT_EMAILS['review'])

        data = _get_status(status)

        return data, errors    

    def action(self):
        return not engine.engine_error and self.status and not self.status.startswith('Invalid') and self.action_id or None

    def run(self, title, kw):
        errors = []

        action = 'provision-%s-order' % title

        self.action_id, self.status = 0, None

        cursor = engine.runProcedure(action, with_log=True, **kw)

        if cursor:
            self.action_id = cursor[0][0]
            self.status = cursor[0][1]
        else:
            if IsTrace:
                print_to(None, '!!! %s, no cursor: %s' % (action, str(self.login)))

            errors.append(gettext('Execution error'))

        if not self.action():
            errors.append('%s %s' % (
                gettext('Error: Provision order %s error:' % title), 
                self.status or gettext('Error: SQL broken. See transaction log.')))

        if errors:
            if IsTrace or IsPrintExceptions:
                print_to(None, '!!! %s, run error, status: %s, login: %s, kw: %s, errors: %s' % (
                    action, self.status, str(self.login), repr(kw), repr(errors)))

        engine.engine_error = False

        return errors


class OrderImageLoader(FileDecoder):

    _allowed_types = ('jpg', 'gif', 'png', 'pdf', 'xls', 'xlsx', 'doc', 'docx', 'txt',)

    def __init__(self, **kw):
        if IsDeepDebug:
            print_to(None, 'OrderImageLoader.init')

        super(OrderImageLoader, self).__init__(**kw)

        self._source = ''
        self._uid = None
        self._size = 0
        self._content_type = ''
        self._lastrowid = None

        self.login = current_user.login

        self.errors = []

    def _init_state(self, **kw):
        if IsDeepDebug:
            print_to(None, 'OrderImageLoader.inistate')

        super(OrderImageLoader, self)._init_state(**kw)

        self._source = self.original

    def new_uid(self):
        self._uid = ('%s%s' % (self.request_id, getUID()))[:50].upper()

    @property
    def source(self):
        return self._source
    @property
    def size(self):
        return self._size
    @property
    def content_type(self):
        return self._content_type
    @property
    def lastrowid(self):
        return self._lastrowid
    @property
    def uid(self):
        return self._uid
    @property
    def is_error(self):
        return engine.is_error

    @staticmethod
    def get_data(cursor, index=0):
        rows = []
        for n, row in enumerate(cursor):
            rows.append(row)
        return rows and rows[index]

    @staticmethod
    def get_value(x):
        return x and len(x) > 0 and x[0][0] or None

    def getImage(self, uid, with_log=None):
        where = "UID='%s'" % uid
        encode_columns = ('FileName',)

        row = None

        cursor = engine.runQuery(_views['download'], where=where, encode_columns=encode_columns, with_log=with_log)
        if cursor:
            row = self.get_data(cursor)

        return row

    def setImage(self, order_id, note):
        self._lastrowid = None

        image = self.file_getter(self.tmp_compressed)

        if not image:
            return

        self.new_uid()

        sql = 'INSERT INTO [ProvisionDB].[dbo].[OrderDocuments_tb](UID, OrderID, Login, FileName, FileSize, ContentType, Note, Image) VALUES(%s,%d,%s,%s,%d,%s,%s,%s)'

        args = ( 
            self.uid,
            order_id, 
            self.login,
            self.original,
            self.size,
            self.content_type,
            note or '',
            image,
        )

        rows, error_msg = engine.run(sql, args=args, no_cursor=True, with_error=True)

        if not self.is_error:
            self._lastrowid = engine.getReferenceID(_views['order-documents'], 'UID', self.uid)

        if error_msg:
            self.errors.append('Engine error: %s' % error_msg)

    def download(self, uid, with_commit=None):
        data = None

        row = self.getImage(uid)

        if row is not None and len(row) == 4:
            self._source = row[0]
            self._size = row[1]
            self._content_type = row[2]
            data = row[3]

        if data is None:
            self.errors.append(gettext('Error: No data downloaded!'))
            return None

        self._decompress(self.tmp_decompressed, data)

        if not self._content_type:
            self._content_type = '.' in self._source and self._source.split('.')[-1].lower() or ''

        return self.file_getter(self.tmp_decompressed)

    def upload(self, order_id, stream, note, with_commit=None):
        if not self.original or '.' not in self.original or self.original.split('.')[-1].lower() not in self._allowed_types:
            self.errors.append('%s:<br>%s' % (gettext('Error: Type of uploaded files are the next'), ', '.join(self._allowed_types)))
            return
        
        with stream as fi:
            self._size = self.file_setter(self.tmp_image, fi.read())

        if self._size > MAX_UPLOADED_IMAGE:
            self.errors.append('%s:<br>%s' % (gettext('Error: Size of uploaded data should be less then'), MAX_UPLOADED_IMAGE))
            return

        self._compress(self.tmp_compressed, self.tmp_image)

        self.setImage(order_id, note)

##  -------------------
##  Page HTML arguments
##  -------------------

def _get_page_args():
    args = {}

    if has_request_item(EXTRA_):
        args[EXTRA_] = (EXTRA_, None)

    try:
        args.update({
            'subdivision' : ['SubdivisionID', int(get_request_item('subdivision') or '0')],
            'author'      : ['Author', get_request_item('author') or ''],
            'seller'      : ['SellerID', int(get_request_item('seller') or '0')],
            'category'    : ['CategoryID', int(get_request_item('category') or '0')],
            'currency'    : ['Currency', get_request_item('currency') or ''],
            'condition'   : ['ConditionID', int(get_request_item('condition') or '0')],
            'date_from'   : ['RD', get_request_item('date_from') or ''],
            'date_to'     : ['RD', get_request_item('date_to') or ''],
            'status'      : ['Status', get_request_item('status', check_int=True)],
            'reviewer'    : ['Reviewer', get_request_item('reviewer') or ''],
            'paid'        : ['ReviewStatus', int(get_request_item('paid') or '0')],
            'id'          : ['TID', get_request_item('_id', check_int=True)],
        })
    except:
        args.update({
            'subdivision' : ['SubdivisionID', 0],
            'author'      : ['Author', ''],
            'seller'      : ['SellerID', 0],
            'category'    : ['CategoryID', 0],
            'currency'    : ['Currency', ''],
            'condition'   : ['ConditionID', 0],
            'date_from'   : ['RD', ''],
            'date_to'     : ['RD', ''],
            'status'      : ['Status', None],
            'reviewer'    : ['Reviewer', ''],
            'paid'        : ['ReviewStatus', 0],
            'id'          : ['TID', None],
        })
        flash('Please, update the page by Ctrl-F5!')

    return args

## ==================================================== ##

def _is_provision_manager():
    return (current_user.is_owner() or current_user.app_is_provision_manager) and True or False

def _is_disabled_delete(ob=None):
    if ob is None:
        ob = requested_object
    status = ob.get('Status') or 0
    return (status > 0 and status < 9) and not _is_provision_manager() and True or status > 4 and True or False

def _is_disabled_edit(ob=None, force=None):
    if ob is None:
        ob = requested_object
    status = ob.get('Status') or 0
    return (force or not (force or _is_provision_manager())) and status > 0 and status not in (3, 4) and True or False

def _is_disabled_review(ob=None):
    if ob is None:
        ob = requested_object
    status = ob.get('Status') or 0
    return status > 4 or status == 2

def _is_valid_author(login):
    return login and login not in ('autoload',) and True or False

def _html_caption(value, **kw):
    return value and re.sub(r'(\n|\r\n)', '<br>', _check_link(value.strip(), **kw)) or ''

def _html_note(note):
    return re.sub(r'\r?\n', '<br>', note.strip())

def _html_status(title, value):
    return '<span class="status_stamp %s">%s</span>' % (_PROVISION_REVIEW_STATUSES[value][0], title)

def _get_link(value):
    m = value and 'http' in value and re.match(r'.*(%s).*' % _rlink, re.sub(r'\n', '', value.strip()))
    return m and [x for x in m.groups() if x.startswith('http') and len(x) > 7] or []

def _get_links(value):
    links = []
    while value:
        m = _rlink.search(value)
        if not m:
            break
        links.append(m.group(1))
        value = value[m.end():]
    return links

def _clean_links(value):
    if value and 'http' in value:
        for link in _get_links(value):
            value = value.replace(link, '')
    return value or ''

def _check_link(value, truncate=None):
    if value and 'http' in value:
        for link in _get_links(value):
            title = unquoted_url(link)
            if truncate:
                s = '/'.join([x for i, x in enumerate(link.split('/')) if i < truncate])
                title = unquoted_url('%s...' % (len(s) < MAX_LINK_LENGTH and s or s[:MAX_LINK_LENGTH]))
            value = value.replace(link, '<a target="_blank" href="%s">%s</a>' % (link, title))
    return value or ''

def _get_string(value, save_links=None):
    v = value and re.sub(r'[\']', '', re.sub(r'^\"(.*)\"$', r'\1', re.sub(r'\"+?', '"', value.strip()))) or ''
    return not save_links and _clean_links(v) or v

def _conv_date(value):
    if not value:
        return None
    v = value.split('.')
    if len(v) != 3:
        return None
    x = '%s-%s-%s' % (v[2], v[1], v[0])
    if not checkDate(x, DEFAULT_DATE_FORMAT[1]):
        return None
    return x

def _get_user(login):
    return _is_valid_author(login) and User.get_by_login(login) or None

def _get_top(per_page, page):
    if IsApplyOffset:
        top = per_page
    else:
        top = per_page * page
    offset = page > 1 and (page - 1) * per_page or 0
    return top, offset

def _get_max_page(per_page_options, total_lines):
    page, per_page = 1, max(per_page_options)
    for x in per_page_options:
        if x > total_lines:
            per_page = x
            page = 1
            break
    return page, per_page

def _get_title(value):
    return re.sub(r'""+', '"', re.sub(r'^\"(.*)\"$', r'\1', value.strip()))

def _get_money(value):
    default_value = 0.0
    try:
        x = value and ''.join([s for s in value if s and s.isdigit() or s in '.,']).replace(',', '.')
        return x and float(x) or default_value
    except:
        if IsPrintExceptions:
            print_exception()
    return default_value

def _get_excel_money(value):
    v = re.sub(r'\s', '', str(value).replace('.', ','))
    if ',' not in v:
        v += ',00'
    return v

def _get_total(price, qty):
    return price * qty

def _get_tax(total, is_clean=None):
    x = float(total)
    if is_clean:
        return x * 0.2
    return x - (x / 1.2)

def _get_currency(value, **kw):
    v = value and locale.currency(value, grouping=True) or None
    if not v:
        return ''
    return kw.get('points') and v[:-2].replace(',', '.') or v[:-2]

def _get_exchange_rate(value):
    return exchange_rate.get(value) or 1.0

def _get_date(value):
    return getDate(value, DEFAULT_DATETIME_INLINE_SHORT_FORMAT)

def _check_order_status(ob=None):
    """
        Returns complex Order's CSS class and title by Status value as 'X.Y'
    """
    if ob is None:
        ob = requested_object
    order_status = '%s.%s' % (ob['Status'], ob['ReviewStatus'])
    return order_status in _PROVISION_SUB_STATUSES and (
        _PROVISION_SUB_STATUSES[order_status], _PROVISION_STATUSES[_PROVISION_SUB_STATUSES[order_status]][4].upper()
        ) or (None, '')

def _get_status(value):
    """
        Returns Order's CSS class, title and complex title by Status value
    """
    d = _PROVISION_STATUSES
    if value is None or value not in range(0, 10):
        s = d['work']
    else:
        s = [d[x] for x in d if d[x][1] and d[x][0] == value][0]
    return s[1], s[2].upper()

def _get_review_status(value, is_title=None):
    return value in _PROVISION_REVIEW_STATUSES and _PROVISION_REVIEW_STATUSES[value][is_title and 1 or 0].upper() or ''

def _get_payment_status(value):
    s = value == 0 and 'в ожидании' or \
        value == 1 and 'на исполнении' or \
        value == 2 and 'исполнено' or ''
    return s

def _get_columns(name):
    return ','.join(database_config[name].get('columns'))

def _get_view_columns(view):
    columns = []
    for name in view.get('columns') or []:
        columns.append({
            'name'       : name,
            'header'     : view['headers'].get(name),
            'with_class' : 0, #name == 'StatusDate' and 1 or 0,
        })
    return columns

def _get_order(order_id):
    columns = database_config[default_template]['export']
    where = 'TID=%s' % order_id
    encode_columns = _default_encode_columns
    cursor = engine.runQuery(default_template, columns=columns, top=1, where=where, as_dict=True, encode_columns=encode_columns)
    return cursor and cursor[0] or {}

def _get_orders(**kw):
    columns = database_config[default_template]['export']
    where = kw.get('where') or ''
    encode_columns = _default_encode_columns
    cursor = engine.runQuery(default_template, columns=columns, where=where, as_dict=True, encode_columns=encode_columns)
    return cursor or []

def _get_reviews(order_id, **kw):
    reviews = []
    selected_id = None

    view = _views['reviews']
    columns = database_config[view]['export']

    login = kw.get('login') or None
    review_id = kw.get('review_id') or None
    reviewer = kw.get('reviewer') or None

    where = 'OrderID=%d%s%s' % (
        int(order_id), 
        login and (" and Login='%s'" % login) or '',
        reviewer and (" and Reviewer='%s'" % reviewer) or '',
        )

    encode_columns = ('Article', 'Qty', 'Seller', 'Reviewer', 'Note',)

    order = kw.get('order') or 'TID'

    cursor = engine.runQuery(view, columns=columns, where=where, order=order, as_dict=True, encode_columns=encode_columns)
    
    if kw.get('cursor'):
        return cursor

    if cursor:
        IsSelected = False

        for n, row in enumerate(cursor):
            status = _PROVISION_REVIEW_STATUSES.get(row['Status'])

            row['cls'] = status and status[0] or ''

            row['Status'] = _html_status(_get_review_status(row['Status'], is_title=True), row['Status'])
            row['StatusDate'] = _get_date(row['StatusDate'])
            row['Note'] = _html_caption(row['Note'])

            row['id'] = row['TID']
            row['selected'] = ''

            reviews.append(row)

        if not IsSelected:
            row = reviews[0]
            selected_id = row['id']
            row['selected'] = 'selected'

    return reviews, selected_id

def _get_order_params(order_id, **kw):
    return select_items(order_id, 'order-params', ('Name', 'Value',), **kw)

def _get_order_reviewers(order_id, **kw):
    view = _views['order-reviewers']
    where = 'OrderID=%d' % order_id
    return engine.runQuery(view, where=where, as_dict=kw.get('as_dict') or False)

def _get_subdivisions(**kw):
    view = _views['subdivisions']
    columns = database_config[view]['export']
    encode_columns = ('Name', 'Manager', 'FullName',)

    where = '%s' % (
        kw.get('code') and "Code like '%s%%'" % kw.get('code') or ''
    )

    return engine.runQuery(view, columns=columns, where=where, order='TID', as_dict=True, encode_columns=encode_columns)

def _get_categories(**kw):
    view = _views['categories']
    columns = database_config[view]['export']
    encode_columns = ('Name',)

    return engine.runQuery(view, columns=columns, where=where, order='TID', as_dict=True, encode_columns=encode_columns)

def _calc_total_status(data):
    if not data or not data.get('data'):
        return data
    x = sum([_get_money(row.get('Total')) for row in data['data']])
    data['status'] = x > 0 and ' (Σ: %s)' % _get_currency(x) or ''
    return data

def _handler_items(row):
    for column in ('Total', 'Tax',):
        row[column] = _get_currency(row[column]) or '0.0' #'<dd class="no-tax">-</dd>'

    row['Name'] = _html_caption(row['Name'])

def _get_order_items(order_id, **kw):
    return _calc_total_status(select_items(order_id, 'order-items', ('Name', 'Units', 'Account',), handler=_handler_items, **kw))

def _handler_payments(row):
    for column in ('Total', 'Tax',):
        row[column] = _get_currency(row[column])

    for column in ('PaymentDate', 'RD',):
        row[column] = getDate(row[column], LOCAL_EASY_DATESTAMP)

    row['StatusID'] = row['Status']
    row['Status'] = _get_payment_status(row['Status'])

def _get_order_payments(order_id, **kw):
    return _calc_total_status(select_items(order_id, 'order-payments', ('Purpose',), handler=_handler_payments, **kw))

def _get_order_comments(order_id, **kw):
    return select_items(order_id, 'order-comments', ('Author', 'Note',), **kw)

def _handler_documents(row):
    if row.get('IsExist'):
        row['FileName'] = '<a href="/provision/image/%s" target="_blank">%s</a>' % (row['UID'], row['FileName'])
    row['Note'] = _html_caption(row['Note'])

def _get_order_documents(order_id, **kw):
    return select_items(order_id, 'order-documents', ('FileName', 'Note',), handler=_handler_documents, **kw)

def _handler_changes(row):
    row['RD'] = getDate(row['RD'], DEFAULT_DATETIME_FORMAT)

def _get_subdivision(id, key=None):
    if not id:
        return None

    view = _views['subdivisions']
    columns = database_config[view]['export']
    where = 'TID=%s' % id
    encode_columns = ('Name', 'Manager', 'FullName')
    cursor = engine.runQuery(view, columns=columns, top=1, where=where, as_dict=True, encode_columns=encode_columns)
    return cursor and (key and cursor[0][key] or cursor[0]) or None

def _get_category(id, key=None, **kw):
    cursor = None
    if 'Category' in kw:
        cursor = {
            'Name'    : kw.get('Category'),
            }
        return key and cursor[key] or cursor or None

    if not id:
        return None

    view = _views['categories']
    columns = database_config[view]['export']
    where = 'TID=%s' % id
    encode_columns = ('Name',)
    cursor = engine.runQuery(view, columns=columns, top=1, where=where, as_dict=True, encode_columns=encode_columns)
    return cursor and (key and cursor[0][key] or cursor[0]) or None

def _get_condition(id, key=None, **kw):
    cursor = None
    if 'Condition' in kw:
        cursor = {
            'Name'    : kw.get('Condition'),
            }
        return key and cursor[key] or cursor or None

    if not id:
        return None

    view = _views['conditions']
    columns = database_config[view]['export']
    where = 'TID=%s' % id
    encode_columns = ('Name',)
    cursor = engine.runQuery(view, columns=columns, top=1, where=where, as_dict=True, encode_columns=encode_columns)
    return cursor and (key and cursor[0][key] or cursor[0]) or None

def _get_seller(id, key=None, **kw):
    cursor = None
    if 'Seller' in kw:
        cursor = {
            'Name'    : kw.get('Seller'),
            'Title'   : kw.get('SellerTitle'), 
            'Address' : kw.get('SellerAddress'),
            }
        return key and cursor[key] or cursor or None

    if not id:
        return None

    view = _views['sellers']
    columns = database_config[view]['export']
    where = 'TID=%s' % id
    encode_columns = ('Name', 'Title', 'Address',)
    cursor = engine.runQuery(view, columns=columns, top=1, where=where, as_dict=True, encode_columns=encode_columns)
    return cursor and (key and cursor[0][key] or cursor[0]) or None

def _get_equipment(id, key=None, **kw):
    cursor = None
    if 'Equipment' in kw:
        cursor = {
            'Name'    : kw.get('EquipmentName'),
            'Title'   : kw.get('Equipment'), 
            }
        return key and cursor[key] or cursor or None

    if not id:
        return None

    view = _views['equipments']
    columns = database_config[view]['export']
    where = 'TID=%s' % id
    encode_columns = ('Name', 'Title',)
    cursor = engine.runQuery(view, columns=columns, top=1, where=where, as_dict=True, encode_columns=encode_columns)
    return cursor and (key and cursor[0][key] or cursor[0]) or None

def _get_order_dates(**kw):
    order_id = kw.get('order_id') or requested_object.get('TID')

    default_format = '%d.%m.%Y'

    def _date(value):
        return value and getDate(value, default_format) or ''

    dates = { 
        'Created'       : [1, 'Дата создания', ''],
        'ReviewDueDate' : [2, 'Дата обоснования', ''],
        'Approved'      : [3, 'Дата согласования', ''],
        'Paid'          : [4, 'Дата оплаты', ''],
        'Delivered'     : [5, 'Дата исполнения', ''],
    }

    view = _views['dates']
    where = order_id and 'OrderID=%s' % order_id or ''

    cursor = engine.runQuery(view, top=1, where=where, as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in dates.keys():
                if row[key]:
                    dates[key][2] = _date(row[key])

    return [(x[0].lower(), x[1][1], x[1][2]) for x in sorted(dates.items(), key=itemgetter(1))]

def _check_extra_tabs(row):
    return {}

def _valid_extra_action(action, row=None):
    tabs = _check_extra_tabs(row or requested_object)
    return (action not in _extra_action or action in list(tabs.values())) and action

def _serialize(value):
    return value is not None and str(value) or ''

## ==================================================== ##

def getTabParams(order_id, review_id, param_name=None, format=None, **kw):
    data = []
    number = 0
    columns = is_no_price and database_config[default_template]['noprice'] or database_config[default_template]['columns']
    props = {'id' : review_id, 'disabled_review' : _is_disabled_review(), 'disabled_edit' : _is_disabled_edit()}

    return number and data or [], columns, props

def getTabChanges(order_id, **kw):
    view = 'order-changes'
    props = {'OrderID' : order_id}
    order = 'TID desc'

    data = select_items(order_id, view, ('Name', 'Value',), handler=_handler_changes, order=order, no_selected=True)
    
    return data, props

## ==================================================== ##

def registerReview(order_id, status, note, params):
    errors = []
    if instance is None or not order_id:
        return errors, None

    if not status:
        return errors, None
    elif status == _PROVISION_STATUSES['accepted'][0]:
        errors = instance.accept(order_id, note)
    elif status == _PROVISION_STATUSES['rejected'][0]:
        errors = instance.reject(order_id, note)
    elif status == _PROVISION_STATUSES['confirm'][0]:
        errors = instance.confirm(order_id, note, params=params)
    elif status == 5:
        errors = instance.confirmation(order_id, note)
    elif status == 6:
        errors = instance.paid(order_id, note, params=params)

    return errors, instance.action()

def createOrder():
    """
        Create a new Provision order
    """
    errors = None

    try:
        errors = instance.create_order(request.form)
    except:
        if IsPrintExceptions:
            print_exception()

    return errors

def updateOrder(order_id):
    """
        Update Provision order
    """
    errors = None

    try:
        errors = instance.update_order(order_id, request.form)
    except:
        if IsPrintExceptions:
            print_exception()

    return errors

def deleteOrder(order_id):
    """
        Delete Provision order
    """
    errors = None

    try:
        errors = instance.delete_order(order_id)
    except:
        if IsPrintExceptions:
            print_exception()

    return errors

def cloneOrder(order_id):
    """
        Clone Provision order
    """
    errors = None

    try:
        errors = instance.clone_order(order_id, request.form)
    except:
        if IsPrintExceptions:
            print_exception()

    return errors

## ==================================================== ##

def _make_export(kw):
    """
        Экспорт журнала заказов в Excel
    """
    view = kw['config'][default_template]
    columns = [x for x in view['export'] if x in view['headers']]
    headers = [view['headers'][x][0] for x in columns]
    rows = []

    for data in kw['orders']:
        row = []
        for column in columns:
            if column not in data:
                continue
            try:
                v = data[column]
                if column == 'RD':
                    v = re.sub(r'\s+', ' ', re.sub(r'<.*?>', ' ', str(v))).strip()
                    #v = getDate(v, UTC_FULL_TIMESTAMP, is_date=True)
                    #v = getDate(v, LOCAL_EXCEL_TIMESTAMP)
                elif column == 'Status':
                    v = _get_status(v)[1]
                elif column in ('Price', 'Tax', 'Total'):
                    v = _get_excel_money(v)
                row.append(v)
            except:
                print_exception()

        rows.append(row)

    rows.insert(0, headers)
    return rows

def _make_response_name(name=None):
    return '%s-%s' % (getDate(getToday(), LOCAL_EXPORT_TIMESTAMP), name or 'perso')

def _make_xls_content(rows, title, name=None):
    output = makeCSVContent(rows, title, True)
    ext = 'csv'
    response = make_response(output)
    response.headers["Content-Disposition"] = "attachment; filename=%s.%s" % (_make_response_name(name), ext)
    return response

def _make_refreshed_order(params, **kw):
    """
        Make Order data for update
    """
    columns = []
    props = {}
    data = {}

    is_extra = kw.get('is_extra') and True or False

    is_update = params.get('command') == 'updateorder'
    is_clone = params.get('command') == 'cloneorder'
    ob = (is_update or is_clone) and requested_object or {}
    status = ob.get('Status')

    for x, key in (('order_id', 'TID'), ('author', 'Author'),):
        columns.append(x)
        props[x] = {'type' : 0, 'disabled' : False}
        data[x] = ob.get(key) or 0

    for key in database_config[_views['orders']]['updated']:
        column = key.lower()
        value = ob.get(key)

        props[column] = {'type' : 0}

        if key in ('Price', 'Total', 'Tax'):
            value = _serialize(not is_clone and value or None)
        elif key in ('Currency',):
            if value is None or is_clone:
                value = DEFAULT_UNDEFINED
        elif key.endswith('ID'):
            column = column[:-2].lower()
            props[column] = {'type' : 1}
            if value is None:
                value = 0

        data[column] = value
        columns.append(column)

    if is_clone:
        data['CategoryID'] = 0

    if props.get('equipment') and props['equipment']['type'] == 1:
        equipment = _get_equipment(ob.get('EquipmentID'))

        data['equipment'] = equipment and equipment.get('Title') or ''

    if props.get('seller') and props['seller']['type'] == 1:
        seller = _get_seller(ob.get('SellerID'))

        data['seller'] = ob.get('SellerID')
        data['title'] = seller and seller.get('Title') or ''
        data['address'] = seller and seller.get('Address') or ''

        for x in ('title', 'address'):
            if x not in columns:
                columns.append(x)
            props[x] = {'type' : 0}

    for x in ('duedate',):
        columns.append(x)
        props[x] = {'type' : 0}
        data[x] = ''
    
    # ---------------------------
    # Check `disable` form's mode
    # ---------------------------
    
    users = [data.get('author')]

    # Don't allow to edit anybody besides author
    #users += current_user.managers(key='login')
    
    keys = [x.lower() for x in database_config[_views['orders']]['noprice'] if x not in ('TID', 'RD',)]

    is_disabled = not is_extra and current_user.login not in users
    is_frozen = not is_extra and not is_clone and _is_disabled_edit(ob, force=True) and is_update #status not in (0, 3, 4)

    def _disable(key, force=None):
        return is_frozen or is_update and (key in keys or force) and is_disabled or False

    for key in columns:
        props[key]['disabled'] = _disable(key)

    # ----------------
    # Add DueDate item
    # ----------------
    
    order_id = data['order_id']

    if order_id:
        key = 'duedate'
        x = _get_order_params(order_id, name='Срок исполнения')
        if x and x['data'] and len(x['data']) > 0:
            data[key] = x['data'][0].get('Value') or ''
            props[key]['disabled'] = _disable(key, force=True)
        columns.append(key)

    return data, columns, props

def _make_current_order_info(no_extra=None, **kw):
    order_id = kw.get('order_id') or requested_object.get('TID')
    review_id = kw.get('review_id') or 0

    order = isinstance(kw, dict) and kw or {}
    if 'id' in order:
        del order['id']
    
    def _get(key):
        return order.get(key) if order and key in order else requested_object.get(key)

    login = _get('EditedBy')
    user = _get_user(login)
    order_name = _get('Article')
    seller_id = _get('SellerID')
    seller = _get_seller(seller_id, **order)
    equipment_id = _get('EquipmentID')
    equipment = _get_equipment(equipment_id, **order)
    purpose = _get('Purpose')
    total = _get('Total')
    tax = _get('Tax')
    currency = _get('Currency')
    status = _get('Status')
    category_id = _get('CategoryID')
    category = _get_category(category_id, 'Name', **order)

    num = '%05d' % int(order_id or 0)

    info = {
        'num'       : num,
        'order'     : order_id and '[%s]: %s' % (num, order_name),
        'author'    : user and 'Исп. %s' % user.full_name() or '',
        'category'  : category_id and category_id < 4 and {
            'title' : category, 
            'class' : 'cc%s' % category_id,
            'code'  : category[0].upper(),
        },
        'purpose'   : _html_caption(purpose, truncate=10),
        'status'    : _get_status(status),
        'EUR'       : None,
    }
    
    if not is_no_price:
        info.update({
            'EUR'       : _get_currency(calc_euro(total, currency), points=1) or '0.00',
            'cross'     : str(_get_exchange_rate('%s:EUR' % currency)),
            'tax'       : _get_currency(calc_rub(tax, currency), points=1) or '0.00',
            'rate'      : str(_get_exchange_rate(currency == 'RUR' and 'EUR:RUR' or '%s:RUR' % currency)),
        })

    if equipment:
        title = equipment.get('Title')
        name = equipment.get('Name')

        info.update({
            'equipment_title' : title,
            'equipment_name'  : name and name != title and name,
        })

    if seller:
        info.update({
            'seller_name'     : _check_link(seller.get('Name')),
            'seller_title'    : seller.get('Title'),
            'seller_address'  : _html_caption(seller.get('Address')),
        })

    if not no_extra:
        info['tabs'] = { 
            'params'    : _get_order_params(order_id, order='Name'),
            'items'     : not is_no_price and _get_order_items(order_id, order='Name') or None,
            'payments'  : not is_no_price and _get_order_payments(order_id) or None,
            'comments'  : _get_order_comments(order_id),
            'documents' : _get_order_documents(order_id),
        }

    if not no_extra:
        info['dates'] = _get_order_dates(order_id=order_id)

    return order_id, info, review_id

def _make_page_default(kw, back_where=None):
    order_id = int(kw.get('order_id') or 0)
    review_id = int(kw.get('review_id') or 0)

    is_admin = current_user.is_administrator()
    is_provision_manager = _is_provision_manager()
    is_office_direction = current_user.app_is_office_direction
    is_office_execution = current_user.app_is_office_execution
    is_assistant = current_user.app_role_assistant
    is_cao = current_user.app_role_cao
    is_cto = current_user.app_role_cto

    model_users = get_users_dict(as_dict=True)

    root = '%s/' % request.script_root

    is_mobile = kw.get('is_mobile')

    if IsDebug:
        print('--> current_user:[%s] %s%s%s%s%s%s' % (current_user.login, 
            is_admin and 1 or 0, 
            is_provision_manager and 1 or 0, 
            is_office_direction and 1 or 0, 
            is_office_execution and 1 or 0, 
            is_cao and 1 or 0, 
            is_cto and 1 or 0, 
            ))

    args = _get_page_args()

    order_name = ''
    
    qf = '' # SQL Query filter
    qs = '' # URL Query string

    # -------------------------------
    # Представление БД (default_view)
    # -------------------------------

    default_view = database_config[default_template]

    # --------------------------------------------
    # Позиционирование строки в журнале (position)
    # --------------------------------------------

    position = get_request_item('position').split(':')
    line = len(position) > 3 and int(position[3]) or 1

    # -----------------------------------
    # Параметры страницы (page, per_page)
    # -----------------------------------

    page, per_page = get_page_params(default_page)
    top, offset = _get_top(per_page, page)

    per_page_options = (5, 10, 20, 30, 40, 50, 100,)
    if is_admin or is_provision_manager:
        per_page_options += (250, 500)

    # ------------------------
    # Поиск контекста (search)
    # ------------------------

    search = get_request_item('search')
    is_search_order = False
    items = []

    TID = None

    # ----------------------------------------------
    # Поиск ID файла, номера ТЗ (search is a number)
    # ----------------------------------------------

    if search:
        is_search_order = True

        try:
            TID = int(search)
            items.append('(TID=%s)' % TID)
        except:
            context = search.encode(default_encoding).decode(default_encoding)
            items.append("(Article like '%%%s%%' or Account like '%%%s%%')" % (search, context))

    # -----------------------------------
    # Команда панели управления (сommand)
    # -----------------------------------

    command = get_request_item('command')

    # -------------
    # Фильтр (args)
    # -------------

    SubdivisionID = args['subdivision'][1]
    SellerID = args['seller'][1]
    ConditionID = args['condition'][1]
    CategoryID = args['category'][1]

    reviewer = args['reviewer'][1]
    
    default_date_format = DEFAULT_DATE_FORMAT[1]
    today = getDate(getToday(), default_date_format)
    date_from = None

    if args:

        # -----------------
        # Параметры фильтра
        # -----------------

        for key in args:
            if key == EXTRA_ or key in DATE_KEYWORDS:
                continue
            name, value = args[key]
            if value == DEFAULT_UNDEFINED:
                continue
            elif value:
                if key in ('author', 'reviewer',):
                    items.append("%s='%s'" % (name, value))
                elif key == 'date_from':
                    if checkDate(value, DEFAULT_DATE_FORMAT[1]):
                        items.append("%s >= '%s 00:00'" % (name, value))
                    else:
                        args['date_from'][1] = ''
                        continue
                elif key == 'date_to':
                    if checkDate(value, DEFAULT_DATE_FORMAT[1]):
                        items.append("%s <= '%s 23:59'" % (name, value))
                    else:
                        args['date_to'][1] = ''
                        continue
                elif key == 'id':
                    items.append("%s=%s" % (name, value))
                    is_search_order = True
                elif key in ('subdivision', 'category', 'seller', 'condition', 'status',):
                    items.append("%s=%s" % (name, value))
                elif key == 'paid':
                    if value == 3:
                        items.append("%s=6" % name)
                    elif value == 2:
                        items.append("%s!=6" % name)
                    elif value == 1:
                        items.append("(Price=0 or (Status > 0 and %s is null))" % name)
                else:
                    items.append("%s='%s'" % (name, value,))

                qf += "&%s=%s" % (key, value)

            elif value == 0:
                if key in ('status',):
                    items.append("%s=%s" % (name, value))
                    qf += "&%s=%s" % (key, value)

    is_args = len(items) > 0

    # ----------------------
    # Скрыть архив + корзину
    # ----------------------

    if not args.get('id')[1] and (not args.get('status')[1] or args['status'][1] < valid_status) and not TID:
        items.append('Status < %d' % valid_status)

    if items:
        qs += ' and '.join(items)

    # --------------------------------------------------------
    # Область видимости по умолчанию (полномочия пользователя)
    # --------------------------------------------------------

    aq = '' # Access Query

    if current_user.is_owner():
        pass

    elif is_office_direction:
        if not is_args:
            aq = 'Status in (1,2,3,4)'

    elif is_assistant:
        aq = "SubdivisionCode like '%s%%'" % current_user.subdivision_code[:3]

    elif is_cto:
        aq = "(SubdivisionCode > '003%%' or SubdivisionCode='0012')"

    elif is_office_execution:
        if not is_args:
            aq = 'Status in (2,3,5,6)'

    elif args.get('id')[1]:
        is_search_order = True

    elif not is_provision_manager:
        items = []
        #if current_user.app_is_author:
        #    items.append("Author='%s'" % current_user.login)
        if current_user.app_is_manager and current_user.subdivision_id > 2:
            subdivision_id = engine.getReferenceID('provision-subdivisions', key='Name', value=current_user.subdivision_name)
            if subdivision_id:
                pass
            else:
                name = current_user.subdivision_fullname
                if name:
                    subdivision_id = engine.getReferenceID('provision-subdivisions', key='Name', value=name)

            ids = None

            if subdivision_id:
                code = current_user.subdivision_code
                try:
                    if code and code[:3] > '001':
                        ids = [str(row['TID']) for row in _get_subdivisions(code=code[:3])]
                    if ids:
                        items.append('SubdivisionID in (%s)' % ','.join(ids))
                except:
                    if IsPrintExceptions:
                        print_exception()

            if not ids:
                items.append('SubdivisionID=%d' % (subdivision_id or 0))

        if items:
            aq = ' or '.join(items)
            if len(items) > 1:
                aq = '(%s)' % aq

    # -------------------
    # Полномочия "автора"
    # -------------------

    if aq and 'Author' not in aq:
        aq = '(%s)' % ' or '.join(list(filter(None, [aq, "Author='%s'" % current_user.login])))

    # -----------------------
    # Полномочия "рецензента"
    # -----------------------

    if aq and IsWithReviewersTemplate:
        aq = '(%s)' % ' or '.join(list(filter(None, [aq, "%s.dbo.CHECK_IsInReviewers_fn(TID, '%s')=1" % (engine.database, current_user.login)])))

    where = ' and '.join(list(filter(None, [aq, qs])))

    # -----------
    # НЕ ПРОЧТЕНО
    # -----------
    
    if IsApplyUnion and not is_search_order:
        sql = "'%s' in (select item from %s.dbo.GET_SplittedStrings_fn(UnreadByLogin, ':'))" % (current_user.login, engine.database)
        union = ((None, None, sql), (offset, top, where,))
    else:
        union = where

    # ---------------------------------
    # Сортировка журнала (current_sort)
    # ---------------------------------

    current_sort = int(get_request_item('sort') or '0')
    if current_sort == 7:
        order = 'Status, ReviewStatus'
    elif current_sort > 0:
        order = '%s' % default_view['export'][current_sort]
    else:
        order = 'TID'

    if current_sort in (0,3,4,5,8):
        order += " desc"

    if current_sort != 0:
        order += '%s%s' % (order and ',' or '', 'TID desc')

    if IsDebug:
        print('--> where:[%s] order:[%s], args: %s' % (where, order, args))

    if back_where:
        return where, order, args

    pages = 0
    total_orders = 0
    total_cards = 0
    total_sum = 0
    orders = []
    subdivisions = []
    categories = []
    authors = []
    sellers = []
    reviews = []
    reviewtypes = []
    reviewers = []
    currencies = []
    conditions = []
    statuses = []
    
    params = []
    payments = []
    comments = []

    payment_statuses = []

    rowspan_columns = ('Total', 'Tax', 'Condition', 'Seller')

    selected_row = {}

    # ======================
    # Выборка данных журнала
    # ======================

    if engine != None:

        # --------------------------------------------------
        # Кол-во записей по запросу в журнале (total_orders)
        # --------------------------------------------------

        cursor = engine.runQuery(default_template, columns=('count(*)', 'sum(Qty)',), where=where, distinct=True)
        if cursor:
            total_orders, total_cards = cursor[0]
            if total_cards is None:
                total_cards = 0

        if command == 'export':
            top = 10000

        # --------------------------------------
        # Установить максимальный размер журнала
        # --------------------------------------

        if IsMaxPerPage and not get_request_item('per_page'):
            page, per_page = _get_max_page(per_page_options, total_orders)
            top, offset = _get_top(per_page, page)

        # ===============
        # Заявки (orders)
        # ===============

        cursor = engine.runQuery(default_template, columns=default_view['export'], top=top, offset=offset, where=union, order='%s' % order, 
                                 distinct=True, as_dict=True, encode_columns=_default_encode_columns)
        if cursor:
            IsSelected = False
            login = '%s:' % current_user.login

            unreads = 0

            for n, row in enumerate(cursor):
                #if not IsApplyUnion and offset and n < offset:
                #    continue

                row['RowSpan'] = 1

                status = row['Status']

                if order_id and order_id == row['TID']:
                    order_name = row['Article']

                    row['selected'] = 'selected'
                    selected_row = row

                    IsSelected = True

                if not is_no_price:
                    total_sum += calc_euro(row['Total'], row['Currency'])

                row['Total'] = _get_currency(row['Total'])
                row['Tax'] = _get_currency(row.get('Tax'))

                for x in row:
                    if not row[x] or str(row[x]).lower() == 'none':
                        row[x] = ''

                row['classes'] = {}
                row['title'] = {}
                row['rowspan'] = {}
                row['none'] = []

                _status = None

                for column in default_view['columns']:
                    classes = [default_view['headers'][column][1]]

                    if status and column in status_columns():
                        _status, _title = _check_order_status(row)
                        if _status:
                            classes.append(_status)
                            classes.append('noselected')

                            row['title'][column] = _title
                        else:
                            if status > 1:
                                classes.append(_default_statuses.get(status))
                                classes.append('noselected')
                            elif status == 1 and not is_office_direction:
                                classes.append('review')
                                classes.append('noselected')

                            row['title'][column] = _get_status(status)[1]

                    row['classes'][column] = ' '.join([x for x in classes if x])

                row['status'] = _status or _default_statuses.get(status) or ''
                row['unread'] = row['UnreadByLogin'] and login in row['UnreadByLogin'] and 'unread' or ''

                row['id'] = row['TID']
                row['TID'] = '%05d' % row['id']
                row['RD'] = _get_date(row['RD'])

                if row['SellerID']:
                    row['Seller'] = '<a target="_blank" href="/%s/seller/%s">%s</s>' % (default_locator, row['SellerID'], row['Seller'])
                    row['classes']['Seller'] += ' link'

                if row['unread'] and not is_search_order:
                    row['title']['Article'] = gettext('Contains unread information')
                    orders.insert(unreads, row)
                    unreads += 1
                else:
                    orders.append(row)

            if line > len(orders):
                line = 1

            if not IsSelected and len(orders) >= line:
                row = orders[line-1]
                order_name = row['Article']
                order_id = row['id']
                row['selected'] = 'selected'
                selected_row = row

            selected_row['order_id'] = order_id

            if unreads:
                for row in orders:
                    if not row['unread']:
                        row['union'] = unreads
                        break

        if len(orders) == 0:
            order_id = 0
            order_name = ''
            review_id = 0

        if total_orders:
            pages = int(total_orders / per_page)
            if pages * per_page < total_orders:
                pages += 1

        # ======================
        # Согласования (reviews)
        # ======================

        if order_id:
            reviews, review_id = _get_reviews(order_id, review_id=review_id, reviewer=reviewer)

        # -----------------------------------------------------------
        # Справочники фильтра запросов (sellers, reviewers, statuses)
        # -----------------------------------------------------------

        subdivisions.append((0, DEFAULT_UNDEFINED,))
        where = ''
        """
        if current_user.app_is_author and current_user.subdivision_id and not current_user.app_is_office_direction:
            where = 'TID=%d' % current_user.subdivision_id
        """
        cursor = engine.runQuery(_views['subdivisions'], where=where, order='Name', distinct=True, encode_columns=(1,))
        subdivisions += [(x[0], x[1]) for x in cursor]

        categories.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery(_views['categories'], order='Name', distinct=True, encode_columns=(1,))
        categories += [(x[0], x[1]) for x in cursor]

        sellers.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery(_views['sellers'], order='Name', distinct=True, encode_columns=(1,))
        sellers += [(x[0], x[1]) for x in cursor]

        currencies.append(DEFAULT_UNDEFINED)
        cursor = engine.runQuery(_views['orders'], columns=('Currency',), order='Currency', distinct=True, encode_columns=(0,))
        currencies += [x[0] for x in cursor if x[0] and x[0].strip()]

        conditions.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery(_views['conditions'], order='Name', distinct=True, encode_columns=(1,))
        conditions += [(x[0], x[1]) for x in cursor if x[1]]

        statuses.append(('', DEFAULT_UNDEFINED,))
        statuses += [(x, _get_status(x)[1].lower()) for x in range(0, valid_status + 1) if x in _default_statuses]
        
        if is_provision_manager:
            statuses.append((9, _get_status(9)[1].lower(),))

        payment_statuses.append((0, DEFAULT_UNDEFINED,))
        payment_statuses += [(x, _get_payment_status(x).lower()) for x in range(1,3)]

        params.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery(_views['params'], order='Name', distinct=True, encode_columns=(1,))
        params += [(x[0], x[1]) for x in cursor]

        payments.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery(_views['payments'], order='Name', distinct=True, encode_columns=(1,))
        payments += [(x[0], x[1]) for x in cursor]

        comments.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery(_views['comments'], order='Name', distinct=True, encode_columns=(1,))
        comments += [(x[0], x[1]) for x in cursor]
        engine.dispose()

    # ---------------------
    # Орг.штатная структура
    # ---------------------

    authors.append(('', DEFAULT_UNDEFINED,))
    cursor = engine.runQuery(_views['authors'], order='Author', distinct=True)
    authors += sorted([(x[0], model_users[x[0]]['full_name']) for x in cursor if x[0] in model_users], key=itemgetter(1))

    users = [(x, '%s %s [%s]' % (model_users[x]['subdivision_code'], model_users[x]['full_name'], model_users[x]['subdivision_name'])) 
        for x, v in sorted(list(model_users.items()), key=lambda k: k[1]['full_name'])]
    users.insert(0, ('', DEFAULT_UNDEFINED,))

    paids = [(0, DEFAULT_UNDEFINED,), (1, 'не обработано',), (2, 'не оплачено',), (3, 'оплачено',)]

    # --------------------------------------
    # Нумерация страниц журнала (pagination)
    # --------------------------------------

    iter_pages = []
    for n in range(1, pages+1):
        if checkPaginationRange(n, page, pages):
            iter_pages.append(n)
        elif iter_pages[-1] != -1:
            iter_pages.append(-1)

    query_string = 'per_page=%s' % per_page
    base = '%s?%s' % (default_locator, query_string)

    is_extra = has_request_item(EXTRA_)

    modes = [(default_view['export'].index(x), '%s' % default_view['headers'][x][0]) for n, x in enumerate(default_view['sorted'])]
    sorted_by = default_view['headers'][default_view['sorted'][current_sort]]

    pagination = {
        'total'             : '%s / %s' % (total_orders, _get_currency(total_sum) or '0.00'), # EUR[€]
        'per_page'          : per_page,
        'pages'             : pages,
        'current_page'      : page,
        'iter_pages'        : tuple(iter_pages),
        'has_next'          : page < pages,
        'has_prev'          : page > 1,
        'per_page_options'  : per_page_options,
        'link'              : '%s%s%s%s' % (base, qf,
                                             (search and "&search=%s" % search) or '',
                                             (current_sort and "&sort=%s" % current_sort) or '',
                                             ),
        'sort'              : {
            'modes'         : modes,
            'sorted_by'     : sorted_by,
            'current_sort'  : current_sort,
        },
        'position'          : '%d:%d:%d:%d' % (page, pages, per_page, line),
    }

    loader = '/%s/loader' % default_locator

    is_full_container = 0
    short = get_request_item('short')
    if short:
        is_full_container = short != '0' and 1 or 0
    elif is_mobile:
        is_full_container = 0

    if is_extra:
        pagination['extra'] = 1
        loader += '?%s' % EXTRA_

    kw.update({
        'base'              : base,
        'page_title'        : gettext('WebPerso Provision Orders View'),
        'header_subclass'   : 'left-header',
        'show_flash'        : True,
        'hide_menu'         : True,
        'is_hidden'         : is_office_direction and 1 or 0,
        'is_full_container' : is_full_container,
        'is_no_price'       : is_no_price,
        'is_show_menu'      : 1,
        'is_show_documents' : 1,
        'is_with_blink'     : 0, #is_office_direction and 1 or 0,
        'loader'            : loader,
        'semaphore'         : initDefaultSemaphore(),
        'args'              : args,
        'current_order'     : _make_current_order_info(**selected_row),
        'tabs'              : {},
        'navigation'        : get_navigation(),
        'config'            : database_config,
        'columns'           : is_no_price and 'noprice' or 'columns',
        'pagination'        : pagination,
        'orders'            : orders,
        'reviews'           : reviews,
        'subdivisions'      : subdivisions,
        'authors'           : authors,
        'sellers'           : sellers,
        'currencies'        : currencies,
        'conditions'        : conditions,
        'statuses'          : statuses,
        'params'            : params,
        'payments'          : payments,
        'comments'          : comments,
        'categories'        : categories,
        'payment_statuses'  : payment_statuses,
        'users'             : users,
        'paids'             : paids,
        'search'            : search or '',
    })

    return kw

## ==================================================== ##

@provision.route('/provision', methods=['GET', 'POST'])
@login_required
def start():
    try:
        return index()
    except:
        if IsPrintExceptions:
            print_exception()

def index():
    debug, kw = init_response('WebPerso Provision Page')
    kw['product_version'] = product_version

    is_admin = current_user.is_administrator()
    is_operator = current_user.is_operator()

    command = get_request_item('command')

    order_id = int(get_request_item('order_id') or '0')
    review_id = int(get_request_item('review_id') or '0')

    if IsDebug:
        print('--> command:%s, order_id:%s, review_id:%s' % (
            command, 
            order_id, 
            review_id,
        ))

    reset = int(get_request_item('reset') or '0')
    if reset:
        kw['order_id'] = None
        kw['review_id'] = None

    refresh(order_id=order_id)

    IsMakePageDefault = True

    errors = []

    if command.startswith('admin'):
        command = command.split(DEFAULT_HTML_SPLITTER)[1]

        if get_request_item('OK') != 'run':
            command = ''

        if command == 'createorder':
            errors = createOrder()

            if not errors:
                kw['order_id'] = instance.action()

        elif command == 'updateorder':
            errors = updateOrder(order_id)

        elif command == 'deleteorder':
            errors = deleteOrder(order_id)

            if not errors:
                del kw['order_id']

        elif command == 'cloneorder':
            errors = cloneOrder(order_id)

            if not errors:
                kw['order_id'] = instance.action()

        elif not is_admin:
            flash('You have not permission to run this action!')
            command = ''

        elif command == 'upload':
            gen = ApplicationGenerator(CONNECTION['provision'])
            gen.upload()

        elif command == 'download':
            srv = ApplicationService(CONNECTION['provision'], kw)
            srv.download()

        elif command == 'delete-orders':
            srv = ApplicationService(CONNECTION['provision'], kw)
            errors = srv.run(command)

        elif command == 'clear-history':
            srv = ApplicationService(CONNECTION['provision'], kw)
            errors = srv.run(command)

    kw['errors'] = errors and '<br>'.join(errors) or ''
    kw['OK'] = ''

    try:
        if IsMakePageDefault:
            kw = _make_page_default(kw)

        if IsTrace:
            print_to(errorlog, '--> provision:%s %s [%s:%s] %s%s' % (
                     command, current_user.login, request.remote_addr, kw.get('browser_info'), order_id, 
                     reset and ' reset:%s' % reset or ''), 
                     request=request)
    except:
        print_exception()

    kw['vsc'] = vsc()

    if command:
        is_extra = has_request_item(EXTRA_)

        if not command.strip():
            pass

        elif command in 'createorder':
            if kw['errors']:
                flash('Provision Generator done with errors!')
            else:
                kw['OK'] = gettext('Message: Order was %s successfully.' % (
                    command == 'deleteorder' and 'removed' or 'created'))

        elif command == 'export':
            return _make_xls_content(_make_export(kw), 'Журнал заявок снабжения', 'provision')

    return make_response(render_template('provision.html', debug=debug, **kw))

@provision.after_request
def make_response_no_cached(response):
    instance, requested_object = None, None
    if engine is not None:
        engine.close()
    # response.cache_control.no_store = True
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response

@before
def downloader(uid, action):
    if IsTrace:
        print_to(None, '>>> downloader:%s %s' % (action, uid))

    loader, image, errors = None, None, None

    try:
        # Decode and download
        loader = OrderImageLoader()

        loader._init_state()
        image = loader.download(uid, with_commit=False)

        errors = loader.errors

        status = (errors or loader.is_error) and 'fail' or 'success'
    
    except:
        if IsPrintExceptions:
            print_exception()

        if errors is None:
            errors = []

        errors.append(gettext('Error: Download failed'))

        status = 'exception'

    if image is None:
        image = 'No data'

    if IsTrace:
        print_to(None, '--> done:%s %s, uid:%s, size:%s [%s] %s' % (
            action, 
            current_user.login, 
            uid, 
            len(image), 
            status, 
            errors or ''
            ), encoding=default_encoding)

    loader.dispose()

    response = make_response(image)
    
    if not loader.content_type:
        response.headers.set('Content-Type', 'text/html')
    elif loader.content_type in ('jpeg', 'jpg',):
        response.headers.set('Content-Type', 'image/jpeg')
    elif loader.content_type in ('png', 'gif',):
        response.headers.set('Content-Type', 'image/%s' % loader.content_type)
    elif loader.content_type == 'pdf':
        response.headers.set('Content-Type', 'application/pdf')
    elif loader.content_type.startswith('doc'):
        response.headers.set('Content-Type', 'application/msword')
    elif loader.content_type.startswith('xls'):
        response.headers.set('Content-Type', 'application/vnd.ms-excel')
    else:
        response.headers["Content-Disposition"] = "attachment; filename=%s.dump" % uid

    del loader
    
    return response

@provision.route('/provision/image/<uid>', methods = ['GET'])
@login_required
def image(uid):
    return downloader(uid, 'image')

@provision.route('/provision/uploader', methods = ['POST'])
@login_required
def uploader():
    action = get_request_item('action') or 'upload'

    response = {}

    order_id = int(get_request_item('order_id') or '0')
    note = get_request_item('note') or ''

    file = original = size = None

    errors = None

    try:
        # Uploaded document file
        file = request.files.get('file')
    
        if file is None or not hasattr(file, 'stream'):
            return None
    
        original, size = file.filename, file.content_length
    
    except:
        if IsPrintExceptions:
            print_exception()

    if IsTrace:
        print_to(None, '>>> uploader:%s %s [%s:%s]' % (
            action, 
            current_user.login, 
            order_id, 
            original
            ), encoding=default_encoding)

    refresh(order_id=order_id)

    try:
        # Decode and upload
        loader = OrderImageLoader()

        loader._init_state(original=original)
        loader.upload(order_id, file.stream, note)

        errors = loader.errors

        status = (errors or loader.is_error) and 'fail' or 'success'
    
    except:
        if IsPrintExceptions:
            print_exception()

        if errors is None:
            errors = []

        errors.append(gettext('Error: Upload failed, uid:%s' % loader.uid))

        status = 'exception'

    if IsTrace:
        print_to(None, '--> done: [%s] uid:%s, size:%s, content_type:%s, lastrowid:%s [%s]' % (
            loader.source, 
            loader.uid,
            loader.size, 
            loader.content_type, 
            loader.lastrowid,
            status,
            ), encoding=default_encoding)

    loader.dispose()

    del loader

    response.update({
        'action'    : action,
        'status'    : status,
        'errors'    : errors,
    })

    return jsonify(response)

@provision.route('/provision/seller/<uid>', methods = ['GET'])
@login_required
def seller(uid):
    debug, kw = init_response('WebPerso Provision Seller Page')
    kw['product_version'] = product_version
    kw['module'] = 'seller'

    if IsTrace:
        print_to(None, '>>> seller:%s %s' % (uid, current_user.login))

    refresh()

    config = database_config[default_template]

    ob = Seller(engine, uid)
    ob._init_state(
        attrs={
            'config' : config,
        }, 
        factory={
            'get_seller' : _get_seller,
            'get_orders' : _get_orders,
            'get_order'  : _get_order,
            'get_money'  : _get_money,
            'info'       : _make_current_order_info,
        }
    )

    kw.update({
        'uid'    : uid,
        'config' : config,
        'vsc'    : vsc(),
        'width'  : 1080,
    })

    if debug:
        return ob.render_html()

    try:
        kw.update(ob.render())

    except Exception as ex:
        print_to(None, ['', 'seller:uid Exception: %s' % (uid, str(ex))])

        if IsPrintExceptions:
            print_exception()
    
    return make_response(render_template('ext/seller.html', debug=debug, **kw))

@provision.route('/provision/loader', methods = ['GET', 'POST'])
@login_required
def loader():
    exchange_error = ''
    exchange_message = ''

    is_extra = has_request_item(EXTRA_)

    action = get_request_item('action') or default_action
    selected_menu_action = get_request_item('selected_menu_action') or action != default_action and action or default_log_action

    response = {}

    order_id = int(get_request_item('order_id') or '0')
    review_id = int(get_request_item('review_id') or '0')
    note = get_request_item('note') or ''

    refresh(order_id=order_id)

    params = get_request_item('params') or ''

    if IsDebug:
        print('--> action:%s order_id:%s review_id:%s' % (action, order_id, review_id))

    if IsTrace:
        print_to(None, '--> loader:%s %s [%s:%s] %s%s%s' % (
            action, 
            current_user.login, 
            order_id, 
            review_id, 
            selected_menu_action,
            params and (' params:%s' % reprSortedDict(params, is_sort=True)) or '',
            note and ' note:[%s]' % note or ''
            ), encoding=default_encoding)

    currentfile = None
    reviews = []
    config = None

    data = ''
    number = ''
    columns = []
    total = 0
    status = ''

    review = None
    props = None
    errors = None

    tabs = _check_extra_tabs(requested_object)

    try:
        if action in (default_action, default_log_action) and not review_id or action == default_print_action:
            """
                Default Action (LINE|SUBLINE)
            """
            reviews, review_id = _get_reviews(order_id)
            currentfile = _make_current_order_info(review_id=review_id)
            config = _get_view_columns(database_config[_views['reviews']])
            action = _valid_extra_action(selected_menu_action) or default_log_action

        review_actions = (None, None, '832', '833', '834', '835', '846')

        if not action:
            pass

        elif action == '831':
            data, columns, props = getTabParams(order_id, review_id)

        elif action in review_actions:
            """
                Review actions
            """
            errors, review_id = registerReview(order_id, review_actions.index(action), note, params)
            reviews = _get_reviews(order_id)[0]
            currentfile = _make_current_order_info(review_id=review_id)
            config = _get_view_columns(database_config[_views['reviews']])
            action = default_log_action

        elif action == '836':
            """
                Actions with Order Params
            """
            data, status, errors = instance.params_action(order_id, params)

        elif action == '837':
            """
                Actions with Order Items
            """
            data, status, errors = instance.items_action(order_id, params)

        elif action == '838':
            """
                Actions with Order Payments
            """
            data, status, errors = instance.payments_action(order_id, params)

        elif action == '839':
            """
                Actions with Order Comments
            """
            data, status, errors = instance.comments_action(order_id, params)

        elif action == '840':
            """
                Update status of order in LINE area (review status)
            """
            view = database_config[default_template]
            columns = view['columns']
            props = [columns.index(x) for x in status_columns()]
            data = _default_statuses.get(requested_object.get('Status'))

        elif action == '841':
            """
                Refresh content for Edit action
            """
            command = params.get('command').lower()
            if 'param' in command:
                data = _get_order_params(order_id, **params)
            elif 'item' in command:
                data = _get_order_items(order_id, **params)
            elif 'payment' in command:
                data = _get_order_payments(order_id, **params)
            elif 'comment' in command:
                data = _get_order_comments(order_id, **params)
            elif 'document' in command:
                data = _get_order_documents(order_id, **params)

        elif action == '842':
            """
                Change status of Order
            """
            data, errors = instance.set_status(order_id, params, is_extra=is_extra)

        elif action == '843':
            """
                Refresh content for Create/Update/Clone an Order
            """
            data, columns, props = _make_refreshed_order(params, is_extra=is_extra)

        elif action == '844':
            """
                Send a request for approval
            """
            errors = instance.send_approval_mail(params)

        elif action == '845':
            """
                Validate form before submit
            """
            errors = instance.set_order(params, is_check=True)

        elif action == '847':
            """
                Actions with Order Documents
            """
            data, status, errors = instance.documents_action(order_id, params)

        elif action == '848':
            """
                Set unread
            """
            errors = instance.set_unread(order_id, [current_user], force=True)

        elif action == '849':
            """
                Set read
            """
            if params.get('mode') == 'all':
                order_id = None
            errors = instance.set_read(order_id, [current_user], force=True)

        elif action == '851':
            """
                Send review notifications
            """
            errors = instance.send_review_notifications()

        elif action == '852':
            """
                Send the Order's review notifications
            """
            errors = instance.send_order_notifications(order_id, params=params)

        elif action == '853':
            """
                Order Changes History data
            """
            data, props = getTabChanges(order_id, params=params)

    except:
        print_exception()

    response.update({
        'action'           : action,
        # --------------
        # Service Errors
        # --------------
        'exchange_error'   : exchange_error,
        'exchange_message' : exchange_message,
        # -----------------------------
        # Results (Log page parameters)
        # -----------------------------
        'order_id'         : order_id,
        'review_id'        : review_id,
        # ----------------------------------------------
        # Default Lines List (sublines equal as reviews)
        # ----------------------------------------------
        'currentfile'      : currentfile,
        'sublines'         : reviews,
        'config'           : config,
        'tabs'             : list(tabs.keys()),
        # --------------------------
        # Results (Log page content)
        # --------------------------
        'total'            : total or len(data),
        'data'             : data,
        'status'           : status,
        'props'            : props,
        'columns'          : columns,
        'errors'           : errors,
    })

    return jsonify(response)
