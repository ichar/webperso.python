# -*- coding: utf-8 -*-

import re
import zlib
import random
from operator import itemgetter

from lxml import etree

from config import (
     CONNECTION, BP_ROOT, 
     IsDebug, IsDeepDebug, IsTrace, IsUseDecodeCyrillic, IsUseDBLog, IsForceRefresh, IsPrintExceptions, IsDecoderTrace, LocalDebug,
     errorlog, print_to, print_exception,
     default_print_encoding, default_unicode, default_encoding, default_iso, image_encoding, cr,
     LOCAL_EXCEL_TIMESTAMP, LOCAL_EASY_DATESTAMP, LOCAL_EXPORT_TIMESTAMP, UTC_FULL_TIMESTAMP,
     email_address_list
     )

from . import bankperso

from ..settings import *
from ..database import database_config, BankPersoEngine
from ..utils import (
     getToday, getDate, getDateOnly, checkDate, cdate, indentXMLTree, isIterable, 
     makeXLSContent, makeIDList,
     checkPaginationRange, getMaskedPAN, getParamsByKeys, decoder, pickupKeyInLine,
     default_indent, Capitalize
     )
from ..worker import getClientConfig, getPersoLogInfo, getSDCLogInfo, getExchangeLogInfo, getBOM
from ..booleval import new_token
from ..barcodes import genBarcode
from ..reporter import make_materials_attachment
from ..mails import send_materials_order

from ..orderstate.views import getTabInfoExchangeLog
from ..semaphore.views import initDefaultSemaphore

##  ===================================
##  BankPerso View Presentation Package
##  ===================================

default_page = 'bankperso'
default_action = '300'
default_template = 'orders'
engine = None

IsLocalDebug = LocalDebug[default_page]

_views = {
    'orders'             : 'orders',
    'batches'            : 'batches',
    'client'             : 'orders',
    'logs'               : 'logs',
    'image'              : 'image',
    'body'               : 'body',
    'filestatuses'       : 'filestatuses',
    'TZ'                 : 'TZ',
    'orderlog-messages'  : 'orderlog-messages',
    'orderstate-aliases' : 'orderstate-aliases',
    'clients'            : 'clients',
    'banks'              : 'banks',
    'types'              : 'types',
    'statuses'           : 'statuses',
    'batchtypelist'      : 'batchtypelist',
    'filestatuslist'     : 'filestatuslist',
    'batchstatuslist'    : 'batchstatuslist',
}

requested_order = {}

def before(f):
    def wrapper(**kw):
        global engine
        if engine is not None:
            engine.close()
        engine = BankPersoEngine(current_user, connection=CONNECTION[kw.get('engine') or 'bankperso'])
        return f(**kw)
    return wrapper

@before
def refresh(**kw):
    global requested_order

    if 'file_id' in kw and kw.get('file_id'):
        requested_order = _get_order(kw['file_id']).copy()

def _get_columns(name):
    return ','.join(database_config[name]['columns'])

def _get_view_columns(view):
    columns = []
    for name in view['columns']:
        columns.append({
            'name'   : name,
            'header' : view['headers'].get(name)
        })
    return columns

def _get_page_args():
    args = {}

    if has_request_item(EXTRA_):
        args[EXTRA_] = (EXTRA_, None)

    try:
        args.update({
            'bank'        : ['ClientID', int(get_request_item('bank') or '0')],
            'type'        : ['FileTypeID', int(get_request_item('type') or '0')],
            'status'      : ['FileStatusID', int(get_request_item('status') or '0')],
            'batchtype'   : ['BatchTypeID', int(get_request_item('batchtype') or '0')],
            'batchstatus' : ['BatchStatusID', int(get_request_item('batchstatus') or '0')],
            'date_from'   : ['RegisterDate', get_request_item('date_from') or ''],
            'date_to'     : ['RegisterDate', get_request_item('date_to') or ''],
            'id'          : ['FileID', int(get_request_item('_id') or '0')],
        })
    except:
        args.update({
            'bank'        : ['ClientID', 0],
            'type'        : ['FileTypeID', 0],
            'status'      : ['FileStatusID', 0],
            'batchtype'   : ['BatchTypeID', 0],
            'batchstatus' : ['BatchStatusID', 0],
            'date_from'   : ['RegisterDate', ''],
            'date_to'     : ['RegisterDate', ''],
            'id'          : ['FileID', 0],
        })
        flash('Please, update the page by Ctrl-F5!')

    return args

def _get_order(file_id):
    where = 'FileID=%s' % file_id
    encode_columns = ('BankName', 'FileStatus',)
    cursor = engine.runQuery(default_template, top=1, where=where, as_dict=True, encode_columns=encode_columns)
    return cursor and cursor[0] or {}

def _get_client(file_id):
    return file_id and engine.getReferenceID(default_template, key='FileID', value=file_id, tid='BankName') or None

def _get_batches(file_id, **kw):
    batches = []
    batch_id = kw.get('batch_id') or None
    pers_tz = kw.get('pers_tz') or None
    batchtype = kw.get('batchtype') or None
    batchstatus = kw.get('batchstatus') or None
    selected_id = None

    where = 'FileID=%s%s%s' % (
        file_id, 
        batchtype and (' and BatchTypeID=%s' % batchtype) or '',
        batchstatus and (' and BatchStatusID=%s' % batchstatus) or ''
        )

    cursor = engine.runQuery('batches', where=where, order='TID', as_dict=True)
    if cursor:
        IsSelected = False
        
        for n, row in enumerate(cursor):
            row['BatchType'] = row['BatchType'].encode(default_iso).decode(default_encoding)
            row['Status'] = row['Status'].encode(default_iso).decode(default_encoding)
            row['StatusDate'] = getDate(row['StatusDate'], DEFAULT_DATETIME_INLINE_FORMAT)
            row['Ready'] = 'обработка завершена' in row['Status'] and True or False
            row['Found'] = pers_tz and row['TZ'] == pers_tz
            row['id'] = row['TID']

            if (batch_id and batch_id == row['TID']) or (pers_tz and pers_tz == row['TZ']):
                row['selected'] = 'selected'
                selected_id = batch_id
                IsSelected = True
            else:
                row['selected'] = ''

            batches.append(row)

        if not IsSelected:
            row = batches[0]
            selected_id = row['id']
            row['selected'] = 'selected'

    return batches, selected_id

def _get_logs(file_id):
    logs = []
    
    cursor = engine.runQuery('logs', where='TID=%s' % file_id, order='LID', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            if 'LID' in row:
                row['id'] = row['LID']
            row['Status'] = row['Status'].encode(default_iso).decode(default_encoding)
            row['ModDate'] = getDate(row['ModDate'], DEFAULT_DATETIME_INLINE_FORMAT)
            logs.append(row)
    
    return logs

def _decode_image(data, file_id, encoding=None):
    #
    # Get$Decompress `Image` body content
    #
    image = None

    is_trace = IsDecoderTrace

    if data is not None:
        client = requested_order.get('BankName')
        #
        # Picking up convenient encoding from 'config.image_encoding' dictionary
        #
        if encoding is None:
            encodings = client and image_encoding.get(client) or image_encoding['default']
        else:
            encodings = (encoding,)

        try:
            data = zlib.decompress(data)
        except:
            if IsTrace:
                print_to(errorlog, '>>> _decompress error:%s client:%s' % (file_id, client), request=request)
            data = None

        image, encoding = decoder(data, encodings, info='%s %s' % (file_id, client), is_trace=is_trace)

    return image, encoding

def _mask_image_content(item, mask='//', **kw):
    """
        Hide security fields (make masked confidential keys: PAN, etc.)
    """
    forced_tag = kw.get('tag')

    for tag in PAN_TAGS.split(':'):
        if forced_tag:
            if tag != forced_tag:
                continue
            item.text = getMaskedPAN(item.text)
            return
        else:
            for pan in item.xpath('%s%s' % (mask, tag)):
                pan.text = getMaskedPAN(pan.text)

    for x in database_config['cardholders']['tags'][2]:
        for name in (isinstance(x, str) and [x] or x):
            if forced_tag:
                if name != forced_tag:
                    continue
                item.text = getMaskedPAN(item.text)
                return
            else:
                for tag in item.xpath('%s%s' % (mask, name)):
                    if tag.text is not None:
                        tag.text = '*' * len(tag.text)

def _decode_cyrillic(item, key='default', client=None, **kw):
    #
    # Try to decode cyrillic from `image_tags_todecode_cyrillic` tags for given `client`
    #
    if not IsUseDecodeCyrillic:
        return

    if client is None:
        client = requested_order.get('BankName')
    
    default = IMAGE_TAGS_DECODE_CYRILLIC.get('default')
    schemes = client and IMAGE_TAGS_DECODE_CYRILLIC.get(client) or \
                         default or \
                         None

    if not schemes:
        return

    splitter = '||'
    max_len = 8000

    def _decode(text, mode):
        if not mode:
            pass
        elif mode == 'dostowin':
            text = text.encode(default_print_encoding).decode(default_encoding)
        elif mode == 'wintodos':
            text = text.encode(default_encoding).decode(default_print_encoding)
        elif mode == 'iso':
            try:
                text = text.encode(default_print_encoding).decode(default_encoding)
            except:
                text = text.encode(default_unicode).decode(default_unicode)
        return text

    is_string_type = isinstance(item, str)
    forced_tag = kw.get('tag')

    for mode, scheme in schemes:
        if key not in scheme:
            continue

        tags = []
        values = []
        s = ''

        for parent in scheme[key].keys():
            for name in scheme[key][parent].split(':'):
                if is_string_type or not name:
                    break
                else:
                    if forced_tag:
                        if name != forced_tag:
                            continue
                        tags = [item]
                        s = item.text
                        break
                    else:
                        mask = parent == '.' and ('./%s' % name) or ('//%s//%s' % (parent, name))
                        for tag in item.xpath(mask):
                            if tag.text is not None and len(tag.text.strip()):
                                tags.append(tag)
                                if len(s) > 0:
                                    s += splitter
                                s += tag.text

        while s:
            n = len(s) > max_len and s.rfind(splitter, 0, max_len) or -1
            values += _decode(n > 0 and s[0:n] or s, mode).split(splitter)
            s = n > -1 and s[n+len(splitter):] or ''

        for n, tag in enumerate(tags):
            if is_string_type:
                break
            else:
                tag.text = values[n]

def _get_image(file_id, encoding=None):
    #
    # Get original file body (FBody:OrderFilesBodyImage_tb)
    #
    if not file_id:
        return None, encoding

    image = None

    params = "%s" % file_id
    cursor = engine.runQuery('image', as_dict=True, params=params)
    if cursor:
        image, encoding = _decode_image(cursor[0]['FBody'], file_id, encoding)

    if image is None or len(image) == 0:
        return None, encoding

    try:
        n = image.find('<FileData>')
        return n > -1 and etree.fromstring(image[n:]) or image, encoding
    except:
        print_to(errorlog, '>>> _get_image xml error:%s %s' % (file_id, current_user.login), request=request)
        print_exception()
        image = None

    return image, encoding

def _get_body(file_id, file_status=None, encoding=None):
    #
    # Get file body (IBody:OrderFilesBody_tb) in given status
    #
    if not file_id:
        return None, encoding

    body = None

    params = "%s, %s" % (file_id, file_status or 'null')
    cursor = engine.runQuery('body', as_dict=True, params=params)
    if cursor:
        body, encoding = _decode_image(cursor[0]['IBody'], file_id, encoding)

    if body is None or len(body) == 0:
        return None, encoding

    try:
        n = body.find('<FileData>')
        body = n > -1 and body[n:] or ''
        return etree.fromstring(body), encoding
    except:
        print_to(errorlog, '>>> _get_body xml error:%s %s' % (file_id, current_user.login), request=request)
        print_exception()
        body = None

    return body, encoding

def _get_bodystate(file_id, file_status=None, limit=None, is_extra=False):
    #
    # Get$Make readable file body content
    #
    xml = ''

    try:
        root, encoding = _get_body(file_id, file_status)
        xml = '%s<?xml version="1.0" encoding="%s"?>%s' % (getBOM(default_unicode), encoding, cr)

        if root is not None:
            _decode_cyrillic(root)
            if not is_extra:
                _mask_image_content(root)
            indentXMLTree(root, limit=limit and MAX_XML_TREE_NODES or None)
            xml += etree.tostring(root, encoding='unicode')

    except Exception as e:
        print_exception()

    return xml

def _get_filestatuses(file_id, order='TID'):
    statuses = []

    cursor = engine.runQuery('filestatuses', where='FileID=%s' % file_id, order=order, as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            statuses.append(row['FileStatusID'])

    return statuses

def _get_cardholders(file_id, view):
    root, encoding = _get_body(file_id)

    def xml_tag_value(node, tag):
        try:
            return node.find(tag).text.strip()
        except:
            return ''

    items = []
    
    if root is None or len(root) == 0:
        return items
    
    records = root.findall('.//%s' % view['root'])
    for record in records:
        item  = {}
        if len(items) > MAX_CARDHOLDER_ITEMS:
            break

        for n, tags in enumerate(view['tags']):
            column = view['columns'][n]

            for tag in tags:
                value = ''
                if isIterable(tag):
                    for key in tag:
                        if value:
                            value += ' '
                        value += xml_tag_value(record, key) or ''
                else:
                    value = xml_tag_value(record, tag)

                if value:
                    item[column] = column in view['func'] and view['func'][column](value) or value
                    break

        if 'FileRecNo' in item:
            item['id'] = item['FileRecNo']

        items.append(item)

    return items

def _get_file_keywords(file_id, no_batch=False):
    keys = []
    dates = ()
    client = ''
    file_name = ''

    if file_id:
        keys.append(str(file_id))

        file_name = ''

        top = 1
        where = 'FileID = %s' % file_id

        # ---------------------------
        # Get Common File/Client info
        # ---------------------------

        cursor = engine.runQuery(default_template, top=top, where=where, as_dict=True)
        if cursor is not None and len(cursor):
            row = cursor[0]
            file_name = row['FName']
            client = row['BankName']

            if row['RegisterDate']:
                date_from = getDateOnly(row['RegisterDate'])
            if row['StatusDate']:
                date_to = row['StatusDate']

            dates = (date_from, date_to,)

        if file_name:
            keys.append(file_name)
            if '.' in file_name:
                keys.append(file_name.split('.')[0])

        # -------------------
        # Get Batches/TZ info
        # -------------------

        if not no_batch:
            cursor = engine.runQuery('batches', where='FileID=%s' % file_id, order='TID', as_dict=True)
            if cursor:
                for n, row in enumerate(cursor):
                    keys.append(str(row['TID']))
                    keys.append(str(row['TZ']))

    keys = sorted(set(keys))

    return keys, dates, client, file_name

def _get_materials(file_id, show=1, order=None):
    data = []
    props = []
    errors = []

    _UNDEFINED_ERROR = 2
    _ERROR = 1
    _WARNING = 0

    qty = 0
    batch_qty = 0

    exec_params = {'file_id' : file_id, 'show' : show}
    encode_columns = ('BatchType', 'MName',)

    cursor = engine.runQuery('materials.order', exec_params=exec_params, order=order, as_dict=True, encode_columns=encode_columns)
    if cursor:
        for n, row in enumerate(cursor):
            batch_qty += int(row['BatchQty'])
            qty += int(row['Qty'])
            data.append(row)

    """
    rows, error_msg = engine.runProcedure('materials.check', 
                                          file_id=file_id, file_status_ids=makeIDList(COMPLETE_STATUSES), check=1, 
                                          no_cursor=False, with_error=True
                                          )
    
    if error_msg:
        errors.append((_ERROR, error_msg))
    """
    
    exec_params = {'file_id' : file_id, 'file_status_ids' : makeIDList(COMPLETE_STATUSES), 'check' : 1}
    rows = engine.runQuery('materials.check', exec_params=exec_params)

    check = (rows is not None and len(rows) == 0) and True or False

    props = {
        'headers'    : ('Тип партии', 'Кол-во в партиях', 'Материал', 'Количество',),
        'total'      : (len(data), batch_qty, qty,),
        'ClientName' : requested_order.get('BankName'),
        'FileName'   : requested_order.get('FName'),
        'Now'        : getDate(getToday(), LOCAL_EXCEL_TIMESTAMP),
        'Today'      : getDate(getToday(), DEFAULT_DATETIME_TODAY_FORMAT),
        'send'       : qty > 0 and check,
        'show'       : 0,
    }

    if not data:
        errors.append((_ERROR, gettext('Error: Materials for the given file is not defined.'),))

    errors = [x[1] for x in sorted(errors, key=itemgetter(0), reverse=True)]

    return data, props, errors

## ==================================================== ##

def getTabParams(file_id, batch_id, param_name=None, format=None, **kw):
    """
        Get Batch Parameters list.

        Arguments:
            file_id     -- Int, ID файла-заказа
            batch_id    -- Int, ID партии
            param_name  -- String, идентификатор параметра
            format      -- Int, формат выходных данных хранимой процедуры ({1|2|3}, default: 1)

        Keyword parameters (kw):
            `is_short`              -- Bool, 1/0, short output format, equivalent of the next items:
            `without_RegisterDate`  -- Bool, 1/0, RegisterDate should be output or not
            `without_TZ_ERP`        -- Bool, 1/0, TZ ERP should be output or not
            `without_TZ`            -- Bool, 1/0, parameters TZ should be output or not
            `without_barcode`       -- Bool, 1/0, barcode should be output or not

        Returns:
            data     -- List, Список параметров партии:
                        [{
                           'PName'      -- название параметра
                           'PValue'     -- значение параметра
                           'PSortIndex' -- порядок в ТЗ
                           'PType'      -- тип параметра: 0 - параметр партии, 1 - параметр ТЗ
                           'class_name' -- html-класс
                        }, ... ]

            batch    -- Dictionary, Информация о партии: 
                        {
                           'id'         -- ID партии
                           'number'     -- номер ТЗ
                           'name'       -- название типа партии
                           'no'         -- кол-во карт в партии
                           'file'       -- имя файла-заказа
                           'cards'      -- кол-во карт в файле
                           'status'     -- ID статуса
                           'activate'   -- активация партии разрешена 1|0
                        }
    """
    data = []
    parameters = {}
    number = 0

    filter_field = re.compile(r'\$\{FILTERFIELD\.(.*)\}')
    batch = {'id' : batch_id}

    is_short = kw.get('is_short') and True or False

    default_format = 1

    rows = engine.runQuery('batches.preview', where='TID=%s' % file_id, distinct=True)

    if rows or batch_id:
        batch['exists_inactive'] = False
        batch['exists_materials'] = False

    try:
        if file_id and batch_id:
            params = "%s, %s, '%s', %s, ''" % (file_id, batch_id, param_name or '', format or default_format)
            cursor = engine.runQuery('TZ', as_dict=True, params=params)

            for n, row in enumerate(cursor):
                try:
                    row['PName'] = row['PName'].encode(default_iso).decode(default_encoding)
                    row['PValue'] = row['PValue'].encode(default_iso).decode(default_encoding)
                    row['class_name'] = row['PSortIndex'] == 999 and 'sort_index' or ''

                    if row['PType'] == 0 and row['PValue'][:1] != '$':
                        parameters[row['PName']] = row['PValue']

                    data.append(row)
                except:
                    print_exception()

            # -----------------------------
            # Обязательные параметры партии
            # -----------------------------

            if not (is_short or kw.get('without_RegisterDate', False)):
                if 'RegisterDate' not in parameters:
                    where = 'FileID=%s' % file_id
                    cursor = engine.runQuery(default_template, columns=('RegisterDate',), where=where)

                    if cursor is not None and len(cursor):
                        parameters['RegisterDate'] = cursor[0][0]
                        data.append({
                            'PName'      : 'Время регистрации файла',
                            'PValue'     : '${FILTERFIELD.RegisterDate}',
                            'PSortIndex' : 990,
                            'PType'      : 0,
                            'ElementQty' : 0,
                        })

            if not (is_short or kw.get('without_TZ_ERP', False)):
                if 'TZ_ERP' not in parameters:
                    params = "%s, %s, 'ERPTZ', 0, ''" % (file_id, batch_id)
                    cursor = engine.runQuery('TZ', as_dict=True, params=params)

                    if cursor is not None and len(cursor):
                        row = cursor[0]
                        parameters['TZ_ERP'] = row['PValue']

            # ------------
            # Параметры ТЗ
            # ------------

            TZ = []

            if not (is_short or kw.get('without_TZ', False)):
                for row in data:
                    if row['PSortIndex'] is None:
                        row['PSortIndex'] = 0

                    if 'FILTERFIELD' in row['PValue']:
                        m = filter_field.search(row['PValue'])
                        if not m:
                            continue
                        name = m.group(1)
                        value = name in parameters and parameters[name] or None
                        if value:
                            TZ.append({
                                'PName'      : row['PName'],
                                'PValue'     : value,
                                'PSortIndex' : name == 'RegisterDate' and 999 or row['PSortIndex'],
                                'PType'      : 1,
                                'ElementQty' : row['ElementQty'],
                                'class_name' : 'filter_field',
                            })

                    elif row['PValue'] == '${ERPTZ}':
                        if 'TZ_ERP' in parameters:
                            TZ.append({
                                'PName'      : row['PName'],
                                'PValue'     : parameters['TZ_ERP'],
                                'PSortIndex' : row['PSortIndex'],
                                'PType'      : 1,
                                'ElementQty' : row['ElementQty'],
                                'class_name' : 'filter_field',
                            })

                    elif row['PName'] == 'Клиент':
                        row['PSortIndex'] = 0

            if TZ:
                data = TZ + data

            if len(data):
                data = sorted(data, key=lambda k: k['PSortIndex'])

            # -------------------
            # Информация о партии
            # -------------------

            view = 'batches'
            columns = database_config[view]['export']
            encode_columns = ('BatchType','Status')
            where = 'TID=%s' % batch_id
            
            cursor = engine.runQuery(view, columns=columns, top=1, where=where, as_dict=True, encode_columns=encode_columns)

            if cursor is not None and len(cursor):
                row = cursor[0]
                if row:
                    number = row['TZ']
                    batch.update({
                        'number' : number,
                        'name'   : row['BatchType'],
                        'no'     : row['ElementQty'],
                        'status' : row['BatchStatusID'],
                    })

            where = 'FileID=%s' % file_id
            cursor = engine.runQuery(default_template, top=1, where=where, as_dict=True)

            if cursor is not None and len(cursor):
                row = cursor[0]
                if row:
                    batch.update({
                        'file'   : row['FName'],
                        'cards'  : row['FQty'],
                    })

            # -------------
            # Баркод ЕРП ТЗ
            # -------------

            if not (is_short or kw.get('without_barcode', False)):
                batch['barcode'] = ''

                if parameters.get('TZ_ERP'):
                    barcode = genBarcode(
                        '{0:<#10}{1:>010}{2:>06}'.format(int(parameters['TZ_ERP']), int(batch['number']), int(batch['no'])),
                        text='ERP_Barcode',
                    )
                    if barcode.get('output'):
                        batch['barcode'] = barcode['output']
                else:
                    barcode = {}

                if IsDebug:
                    print('--> barcode: %s ERP_TZ: [%s] code: [%s]' % ( 
                        len(batch['barcode']), parameters.get('TZ_ERP') or '', barcode.get('code')))

            # ------------------------------------
            # Признак <активация партии разрешена>
            # ------------------------------------

            batch['activate'] = batch['status'] == 1 and current_user.is_operator() and 1 or 0

            # -----------------
            # Файл на обработку
            # -----------------

            rows = engine.runQuery('batches.preview', where='TID=%s and BatchStatusID=1' % file_id, distinct=True)
            batch['exists_inactive'] = rows and True or False

        rows = engine.runQuery('batches.preview', where='TID=%s and IsPrintMaterialOrder=0' % file_id, distinct=True)
        for row in rows:
            id = row[0]
            d, p, e = _get_materials(id, show=1)
            if p['send'] and not e:
                batch['exists_materials'] = True

    except:
        print_exception()

    return number and data or [], batch

def getTabLogs(file_id):
    return _get_logs(file_id)

def getTabCardholders(file_id):
    return _get_cardholders(file_id, database_config['cardholders'])

def getTabIBody(file_id, limit=MAX_XML_BODY_LEN, **kw):
    xml = ''
    total = None
    is_extra = kw.get('is_extra') and True or False

    if SETTINGS_PARSE_XML and current_user.is_administrator():
        xml = _get_bodystate(file_id, limit=limit, is_extra=is_extra)

        total = len(xml)

        if xml is not None and limit and total > limit:
            xml = xml[:limit] + cr + '...'

    return xml, total

def getTabProcessErrMsg(file_id):
    xml = ''
    total = None

    tag = 'PROCESS_ERR_MSG'

    if SETTINGS_PARSE_XML: # and current_user.is_administrator():
        try:
            root, encoding = _get_body(file_id)
            if root is not None:
                items = root.xpath('.//RPT_Record[descendant::%s]' % tag)
            else:
                items = []

            total = len(items)

            for item in items:
                _decode_cyrillic(item, key='errors')
                _mask_image_content(item, mask='./')
                indentXMLTree(item, limit=MAX_XML_TREE_NODES)
                xml += '...' + cr + etree.tostring(item, encoding="unicode")

        except Exception as e:
            if IsPrintExceptions:
                print_exception()

    return xml, total

def getTabDBLog(source_type, view, **kw):
    client = kw.get('client') or None
    file_id = kw.get('file_id') or None

    data = []

    columns = view['columns']
    keys, dates, client, filename = _get_file_keywords(file_id)
    date_format = DEFAULT_DATETIME_FORMAT

    if file_id is not None:
        where = "FileID = %s and SourceType = '%s'" % (file_id, source_type)

        refresh(engine='orderlog')

        # ---------------------------------------------
        # Get OrderLog for given source type and FileID
        # ---------------------------------------------

        cursor = engine.runQuery('orderlog-messages', where=where, order='EventDate', as_dict=True)
        if cursor:
            for n, row in enumerate(cursor):
                """
                ob = dict(zip(columns, [row[x] for x in columns if x in row]))
                ob['Error'] = row['IsError']
                """
                ob = { \
                    'filename' : '[%s] %s' % (row['IP'], row['LogFile']),
                    'Date'     : cdate(row['EventDate'], date_format),
                    'Code'     : row['Code'],
                    'Module'   : '%s%s' % (row['Module'], row['Count'] > 1 and '[%d]' % row['Count'] or ''),
                }

                message = row['Message']

                if not kw.get('no_span'):
                    s = ''
                    for key in keys:
                        if key in s:
                            continue
                        s += ':%s' % key
                        message = pickupKeyInLine(message, key)

                ob['Message'] = message

                data.append(ob)

    return data

def getTabPersoLog(columns, **kw):
    file_name = ''
    client = kw.get('client') or None

    keys = []

    date_from = getDateOnly(getToday())
    date_to = getToday()

    file_id = kw.get('file_id') or None

    if file_id is not None:
        keys, dates, client, filename = _get_file_keywords(file_id)
    else:
        keys, dates = kw.get('keys') or [], kw.get('dates') or (date_from, date_to,)

    return getPersoLogInfo(keys=keys, split_by = '\t', columns=columns, dates=dates, client=client,
                           fmt=DEFAULT_DATETIME_PERSOLOG_FORMAT, 
                           date_format=kw.get('date_format'),
                           case_insensitive=kw.get('case_insensitive'),
                           no_span=kw.get('no_span'),
                           )

def getTabSDCLog(columns, **kw):
    file_name = ''
    client = kw.get('client') or None

    keys = []
    aliases = []

    date_from = getDateOnly(getToday())
    date_to = getToday()

    file_id = kw.get('file_id') or None

    if file_id is not None:
        keys, dates, client, filename = _get_file_keywords(file_id)
    else:
        keys, dates = kw.get('keys') or [], kw.get('dates') or (date_from, date_to,)

    if client:
        aliases.append(client)

        # -----------------------
        # Get Client Aliases list
        # -----------------------

        where = "Aliases like '%" + client +"%' or Name='" + client + "'"
    
        cursor = engine.runQuery('orderstate-aliases', where=where, as_dict=True)
        if cursor:
            for n, row in enumerate(cursor):
                if row['Aliases'] is not None and len(row['Aliases']):
                    aliases.extend(row['Aliases'].split(':'))

    if len(aliases):
        aliases = list(set(aliases))

    return getSDCLogInfo(keys=keys, split_by = '\t', columns=columns, dates=dates, client=client, aliases=aliases,
                         fmt=DEFAULT_DATETIME_SDCLOG_FORMAT, 
                         date_format=kw.get('date_format'),
                         case_insensitive=kw.get('case_insensitive'),
                         no_span=kw.get('no_span'),
                         )

def getTabExchangeLog(columns, **kw):
    file_name = ''
    client = kw.get('client') or None
    split_by = '\t'

    keys = []
    aliases = []

    date_from = getDateOnly(getToday())
    date_to = getToday()

    file_id = kw.get('file_id') or None

    if file_id is not None:
        keys, dates, client, filename = _get_file_keywords(file_id, no_batch=True)
    else:
        keys, dates = kw.get('keys') or [], kw.get('dates')

    if client:
        aliases.append(client)

        # -----------------------
        # Get Client Aliases list
        # -----------------------

        where = "Aliases like '%" + client +"%' or Name='" + client + "'"

        cursor = engine.runQuery('orderstate-aliases', where=where, as_dict=True)
        if cursor:
            for n, row in enumerate(cursor):
                if row['Aliases'] is not None and len(row['Aliases']):
                    aliases.extend(row['Aliases'].split(':'))

    if file_name:
        if file_name.startswith('OCG') or file_name.startswith('PPCARD'):
            aliases += 'JZDO'
            split_by = ' '

    if len(aliases):
        aliases = list(set(aliases))

    return getExchangeLogInfo(keys=keys, split_by=split_by, columns=columns, dates=dates, client=client, aliases=aliases,
                              fmt=DEFAULT_DATETIME_EXCHANGELOG_FORMAT, 
                              date_format=kw.get('date_format'),
                              case_insensitive=kw.get('case_insensitive'),
                              no_span=kw.get('no_span'),
                              )

def getBodyState(file_id, with_image=False, no_body=False, limit=None, **kw):
    statuses = _get_filestatuses(file_id) #, order=None
    is_extra = kw.get('is_extra') and True or False

    spacer = '# %s' % ('-' * 30)
    xml = getBOM(default_unicode)

    if with_image:
        image, encoding = _get_image(file_id)
        if IsUseDecodeCyrillic:
            _decode_cyrillic(image, key='image')
        s = '--> BODY_IMAGE[%s]' % encoding
        spacer = '# %s' % ('-' * len(s))
        xml += '%s%s# %s%s%s%s%s' % (spacer, cr, s, cr, spacer, cr, cr)
        xml += str(image or '')
        xml += cr

    if no_body:
        return xml

    for status in statuses:
        xml += '%s%s# --> FileStatusID=%s%s%s%s%s' % (spacer, cr, status, cr, spacer, cr, cr)
        xml += _get_bodystate(file_id, file_status=status, limit=limit, is_extra=is_extra)
        xml += cr

    return xml

def getLogSearchDump(logsearch):
    context, apply_filter, log_exchange, log_perso, log_sdc, log_infoexchange = ('',0,0,0,0,0)
    args = _get_page_args()

    def _column_format(name, logs, default_size=0):
        return '{:<%s}' % (max([0]+[len(ob[name]) for ob in logs if name in ob and ob[name]])+1 or default_size)

    def _formatted_dump(logs, columns):
        filename = ''
        dump = ''

        module_format = _column_format('Module', logs, 34)
        code_format = _column_format('Code', logs, 8)

        rows = 0
        num_columns = len(columns)-1

        for ob in logs:
            if 'exception' in ob:
                flash(ob['exception'])
                continue

            if ob['filename'] != filename:
                filename = ob['filename']
                spacer = '# %s' % ('-' * len(filename))
                dump += '%s%s# %s%s%s%s' % (spacer, cr, filename, cr, spacer, cr,)

            line = ''
            for n, x in enumerate(columns):
                column = x['name']
                if not (column and column in ob):
                    continue
                elif column == 'Date':
                    line += '{:<20}'.format(ob[column])
                elif column == 'Module':
                    line += module_format.format(ob[column])
                elif column == 'Code':
                    line += code_format.format(ob[column])
                else:
                    line += '{}'.format(ob[column].strip())
                if n < num_columns:
                    line += '\t'

            dump += line + cr
            rows += 1

        dump += '%s%s: %d%s' % (cr, gettext('Total lines'), rows, cr)

        return dump

    try:
        if len(logsearch):
            x = logsearch.split('::')
            context = x[0].strip()
            apply_filter = x[1] == '1' and 1 or 0
            log_exchange = x[2] == '1' and 1 or 0
            log_perso = x[3] == '1' and 1 or 0
            log_sdc = x[4] == '1' and 1 or 0

            if len(x) > 5:
                log_infoexchange = x[5] == '1' and 1 or 0
    except:
        pass

    info = 'logsearch:%s apply_filter:%s logs:%s%s%s%s' % (context, apply_filter, log_exchange, log_perso, log_sdc, log_infoexchange)

    if IsDebug:
        print('--> %s' % info)

    dump = getBOM(default_unicode)

    if not context or len(context) < 5:
        return dump + gettext('Illegal search context') + '!'

    # --------------------------
    # Check LogSearch parameters
    # --------------------------

    token = new_token()
    token._init_state(context.lower())

    client_id = args.get('bank')[1]
    client = client_id and engine.getReferenceID('clients', key='TID', value=client_id, tid='CName') or ''

    date_format = LOCAL_EASY_DATESTAMP

    x = args.get('date_from')[1]
    date_from = checkDate(x, date_format) and getDate(x, date_format, is_date=True) or None

    x = args.get('date_to')[1]
    date_to = checkDate(x, date_format) and getDate(x, date_format, is_date=True) or None

    dates = (date_from or date_to) and [date_from, date_to,]

    # ---------
    # Dump Logs
    # ---------

    items = ( \
        (log_exchange, 'exchangelog', getTabExchangeLog, 'Exchange Logs',),
        (log_perso, 'persolog', getTabPersoLog, 'BankPerso Logs',),
        (log_sdc, 'sdclog', getTabSDCLog, 'SDC Logs',),
        (log_infoexchange, 'infoexchangelog', getTabInfoExchangeLog, 'InfoExchange Logs (OutReceiver)',),
    )

    for logtype, name, handler, title in items:
        if not logtype:
            continue

        view = database_config[name]
        columns = _get_view_columns(view)

        logs = handler(view['export'], keys=token, client=client, dates=dates, 
                       date_format=UTC_FULL_TIMESTAMP,
                       case_insensitive=True,
                       no_span=True,
                       engine=engine,
                       )

        if logs:
            s = '%s [%s]' % (title, context)
            spacer = '# %s' % ('=' * len(s))
            dump += cr + \
                '%s%s# %s%s%s%s' % (spacer, cr, s, cr, spacer, cr) + \
                _formatted_dump(logs, columns) + cr

    if len(dump) < 4:
        dump += gettext('No data') + '!'

    return dump

def getTagSearchDump(file_id, tagsearch, **kw):
    """
        Output from given Order body selected Tags list
    """
    xml = ''
    is_extra = kw.get('is_extra') and True or False

    if tagsearch:
        try:
            root, encoding = _get_body(file_id)
            xml = '%s<?xml version="1.0" encoding="%s"?>%s' % (getBOM(default_unicode), encoding, cr)

            if root is None:
                return xml

            level1 = '%s%s' % (cr, default_indent)
            level2 = '%s%s' % (cr, default_indent * 2)
            spacer = '%s...' % level2

            for record in root.xpath('//FileBody_Record'):
                recno = record.xpath('./FileRecNo')[0]

                items = [x for tag in tagsearch.split(DEFAULT_HTML_SPLITTER) 
                           for x in record.xpath('.//%s' % tag)]

                content = ''

                for item in items:
                    tag = item.tag
                    _decode_cyrillic(item, key='record', tag=tag)
                    if not is_extra:
                        _mask_image_content(item, tag=tag)
                    content += '%s%s' % (level2, etree.tostring(item, encoding="unicode").strip())

                xml += '%s<FileBody_Record>%s<FileRecNo>%s</FileRecNo>%s%s%s%s</FileBody_Record>' % (
                    level1,
                    level2,
                    recno.text,
                    spacer,
                    content,
                    spacer,
                    level1,
                )

        except Exception as e:
            if IsPrintExceptions:
                print_exception()

    return xml

def calculateMaterials(file_id, order=None):
    """
        Get `Materials Order` Parameters list
    """
    return _get_materials(file_id, order=order)

def sendMaterialsOrder(file_id, order=None):
    """
        Send `Materials Order` mail request to the Warehouse
    """
    data, props, errors = _get_materials(file_id, show=0, order=order)

    _UNDEFINED_ERROR = 2
    _ERROR = 1
    _WARNING = 0

    subject = 'Заявка на расходные материалы'
    style = None
    filename = props['FileName']

    errors = []

    try:
        document = make_materials_attachment(subject, data, props, style=style)

        if not send_materials_order(subject, props, document, filename,
                                    addr_from=email_address_list.get('adminbd'),
                                    addr_to=email_address_list.get('warehouse'),
            ):
            errors.append((_ERROR, gettext('Error: Materials request email error.'),))
        else:
            rows, error_msg = engine.runProcedure('materials.approval', 
                                                  file_id=file_id, file_status_ids='', 
                                                  no_cursor=True, with_error=True
                                                  )
            if error_msg:
                errors.append(error_msg)

    except:
        if IsPrintExceptions:
            print_exception()

        errors.append((_UNDEFINED_ERROR, gettext('Error: Unexpected error.'),))

    errors = [x[1] for x in sorted(errors, key=itemgetter(0), reverse=True)]

    return errors

def calculateContainerList(file_id, is_group=False, **kw):
    """
        Generates `Container List` output form
    """
    data = {}
    props = {}
    errors = []

    if 'data' in kw:
        data = kw.get('data')

    _UNDEFINED_ERROR = 2
    _ERROR = 1
    _WARNING = 0

    filter_field = re.compile(r'\$\{FILTERFIELD\.(.*)\}')
    rtype = re.compile(r'((дизайн|вид)\s*[№#]?\s*([\d]+))', re.I+re.DOTALL)

    PERSO_BATCH_TYPE = 7
    PLASTIC_TYPE_KEYWORD = 'Тип пластика'
    CARD_TYPE_KEYWORD = 'Тип карт'
    QTY_NAME = 'ElementQty'
    
    batches, selected_id = _get_batches(file_id, batchtype=PERSO_BATCH_TYPE)

    TZ = kw.get('TZ', [])
    items = kw.get('items', [])

    keyword = ''
    total = 0

    def _get_type_keyword(items):
        for key in (PLASTIC_TYPE_KEYWORD, CARD_TYPE_KEYWORD):
            if len([1 for item in items if item['PName'] == key]) > 0:
                return key

    try:
        for batch in batches:
            batch_id = batch['id']

            batch_data, batch_params = getTabParams(file_id, batch_id) #, param_name=CARD_TYPE_KEYWORD, format=3, is_short=True

            if not keyword:
                keyword = _get_type_keyword(batch_data)

            name = ''

            for item in batch_data:
                if name and item['PName'] == name or item['PName'] == keyword:
                    value = item['PValue'] or ''

                    if 'FILTERFIELD' in value:
                        m = filter_field.search(item['PValue'])
                        name = m and m.group(1) or ''
                        continue

                    m = rtype.search(value)
                    value = Capitalize(m and m.group(1) or value)

                    if value not in data:
                        data[value] = 0

                        items.append((
                            m and int(m.group(3)) or 0, 
                            value
                            ))

                    qty = item.get(QTY_NAME) or 0
                    data[value] += qty
                    total += qty

            TZ.append(batch['TZ'])

        if not is_group and total != requested_order['FQty']:
            errors.append((_ERROR, gettext('Error: Final sum of batches Qty is unmatched.'),))

    except:
        if IsPrintExceptions:
            print_exception()

        errors.append((_UNDEFINED_ERROR, gettext('Error: Unexpected error.'),))

    finally:
        props = {
            'items'      : [x[1] for x in sorted(items, key=itemgetter(0))],
            'ClientName' : requested_order['BankName'],
            'FileName'   : requested_order['FName'],
            'FQty'       : requested_order['FQty'],
            'TZ'         : ', '.join([str(x) for x in TZ]),
            'Now'        : getDate(getToday(), LOCAL_EXCEL_TIMESTAMP),
            'Today'      : getDate(getToday(), DEFAULT_DATETIME_TODAY_FORMAT),
            'show'       : 0,
        }

    errors = [x[1] for x in sorted(errors, key=itemgetter(0), reverse=True)]

    return data, props, errors

def calculateGroupContainerList(file_ids=None):
    """
        Generates `Container List` output form for files group
    """
    data = {}
    props = {}
    errors = []

    _UNDEFINED_ERROR = 2
    _ERROR = 1
    _WARNING = 0

    TZ = []
    items = []

    client_name = ''
    filenames = []
    fqty = 0
    tzs = []

    for file_id in file_ids:
        order = _get_order(file_id)

        data, p, e = calculateContainerList(file_id, is_group=True, data=data, items=items)

        if e:
            errors.append((_ERROR, e,))
            break

        if client_name and (client_name != p['ClientName'] or client_name != order['BankName']):
            errors.append((_ERROR, gettext('Error: Clients for selected files are not unique.'),))
            break
        else:
            client_name = p['ClientName']

        filenames.append(order['FName'])
        fqty += order['FQty']
        tzs.append(p['TZ'])

    if len(items) > 0:
        props = {
            'items'      : [x[1] for x in sorted(items, key=itemgetter(0))],
            'ClientName' : client_name,
            'FileName'   : '<br>'.join(filenames),
            'FQty'       : fqty,
            'TZ'         : ''.join(['<p>%s</p>' % x for x in tzs]),
            'Now'        : getDate(getToday(), LOCAL_EXCEL_TIMESTAMP),
            'Today'      : getDate(getToday(), DEFAULT_DATETIME_TODAY_FORMAT),
            'show'       : 0,
        }

    errors = [x[1] for x in sorted(errors, key=itemgetter(0), reverse=True)]

    return data, props, errors

## ==================================================== ##

def _make_report_kp(kw):
    """
        Отчет: Статистика КП БинБанка
    """
    headers = ['КЛИЕНТ', 'ID файла', 'ФАЙЛ', 'КП', 'Кол-во',]
    rows = []

    for order in kw['orders']:
        row = []
        file_id = order['FileID']

        items = {}

        batches, selected_id = _get_batches(file_id)
        for batch in batches:
            batch_id = batch['id']

            params, data = getTabParams(file_id, batch_id)
            for param in params:
                if not (param['PType'] == 1 and param['PName'] == 'КП'):
                    continue
                key = param['PValue'].strip() or 'undefined'
                if not key.startswith('$'):
                    if key not in items:
                        items[key] = 0

                    items[key] += data['no']

        for key in sorted(items.keys()):
            rows.append([
                order['BankName'],
                file_id,
                order['FName'],
                key,
                items[key],
            ])

    rows.insert(0, headers)
    return rows

def _make_report_branch_list(kw):
    """
        Отчет: Статистика КП БинБанка
    """
    headers = ['Тип карты', 'Филиал', 'Кол-во',]
    rows = []

    _BRANCH = 'Доставка'
    _CARD_TYPE = 'PlasticType'
    _ID_VSP = 'ID_VSP'

    for order in kw['orders']:
        if order.get('selected', '') != 'selected':
            continue

        row = []
        file_id = order['FileID']

        items = {}
        batches, selected_id = _get_batches(file_id, batchtype=BATCH_TYPE_PERSO)
        for batch in batches:
            batch_id = batch['id']

            params, data = getTabParams(file_id, batch_id)
            ps = getParamsByKeys(params, [_BRANCH, _CARD_TYPE, _ID_VSP])

            if ps and len(ps.keys()) == 3:
                try:
                    branch_name = ps[_BRANCH]['PValue']
                    card_type = ps[_CARD_TYPE]['PValue']
                    id_vsp = ps[_ID_VSP]['PValue']
                except:
                    continue
                
                if id_vsp not in items:
                    items[id_vsp] = [card_type, branch_name, 0]
            
                items[id_vsp][2] += data['no']

        for key in sorted(items.keys()):
            rows.append([
                items[key][0],
                items[key][1],
                items[key][2],
            ])

    rows = sorted(rows, key=itemgetter(1))

    rows.insert(0, headers)
    return rows

def _make_export(kw):
    """
        Экспорт журнала заказов в Excel
    """
    view = kw['config']['orders']
    columns = view['columns']
    headers = [view['headers'][x][0] for x in columns]
    rows = []

    for data in kw['orders']:
        row = []
        for column in columns:
            try:
                v = data[column]
                if 'Date' in column and v:
                    v = re.sub(r'\s+', ' ', re.sub(r'<.*?>', ' ', v)).strip()
                    v = getDate(v, UTC_FULL_TIMESTAMP, is_date=True)
                    v = getDate(v, LOCAL_EXCEL_TIMESTAMP)
                row.append(v)
            except:
                print_exception()

        rows.append(row)

    rows.insert(0, headers)
    return rows

def _make_response_name(name=None):
    return '%s-%s' % (getDate(getToday(), LOCAL_EXPORT_TIMESTAMP), name or 'perso')

def _make_xls_content(rows, title, name=None):
    xls = makeXLSContent(rows, title, True)
    response = make_response(xls)
    response.headers["Content-Disposition"] = "attachment; filename=%s.xls" % _make_response_name(name)
    return response

def _make_page_default(kw):
    file_id = int(kw.get('file_id'))
    batch_id = int(kw.get('batch_id'))

    is_admin = current_user.is_administrator()
    is_operator = current_user.is_operator()

    args = _get_page_args()

    file_name = ''
    filter = ''
    qs = ''

    # -------------------------------
    # Представление БД (default_view)
    # -------------------------------

    default_view = database_config[default_template]

    # -----------------------------------------
    # Поиск номера ТЗ в списке партий (pers_tz)
    # -----------------------------------------

    pers_tz = int(get_request_item('pers_tz') or '0')

    # --------------------------------------------
    # Позиционирование строки в журнале (position)
    # --------------------------------------------

    position = get_request_item('position').split(':')
    line = len(position) > 3 and int(position[3]) or 1

    # -----------------------------------
    # Параметры страницы (page, per_page)
    # -----------------------------------

    page, per_page = get_page_params(default_page)
    top = per_page * page
    offset = page > 1 and (page - 1) * per_page or 0

    # ------------------------
    # Поиск контекста (search)
    # ------------------------

    search = get_request_item('search')
    IsSearchBatch = False
    items = []
    preview_items = []
    TZ = None

    # ----------------------------------------------
    # Поиск ID файла, номера ТЗ (search is a number)
    # ----------------------------------------------

    if search:
        try:
            FileID = TZ = int(search)
            items.append('(FileID=%s OR TZ=%s)' % (FileID, TZ))
            IsSearchBatch = True
            pers_tz = TZ
        except:
            TZ = 0
            items.append("FName like '%%%s%%'" % search)

    # -----------------------------------
    # Команда панели управления (сommand)
    # -----------------------------------

    command = get_request_item('command')

    # -------------
    # Фильтр (args)
    # -------------

    ClientID = args['bank'][1]
    FileTypeID = args['type'][1]
    FileStatusID = args['status'][1]
    BatchTypeID = args['batchtype'][1]
    BatchStatusID = args['batchstatus'][1]

    if args:
        for key in args:
            if key in (EXTRA_,):
                continue
            name, value = args[key]
            if value:
                if key in ('batchtype', 'batchstatus',):
                    pass
                elif key == 'date_from':
                    if checkDate(value, DEFAULT_DATE_FORMAT[1]):
                        items.append("%s >= '%s 00:00'" % (name, value))
                        preview_items.append("%s >= '%s 00:00'" % (name, value))
                    else:
                        args['date_from'][1] = ''
                        continue
                elif key == 'date_to':
                    if checkDate(value, DEFAULT_DATE_FORMAT[1]):
                        items.append("%s <= '%s 23:59'" % (name, value))
                        preview_items.append("%s >= '%s 00:00'" % (name, value))
                    else:
                        args['date_to'][1] = ''
                        continue
                elif key in ('id', 'bank', 'type', 'status',):
                    items.append("%s=%s" % (name, value))
                else:
                    items.append("%s like '%s%%'" % (name, value,))

                filter += "&%s=%s" % (key, value)

    if items:
        qs += ' and '.join(items)

    where = qs or ''

    # ---------------------------------
    # Сортировка журнала (current_sort)
    # ---------------------------------

    current_sort = int(get_request_item('sort') or '0')
    if current_sort > 0:
        order = '%s' % default_view['columns'][current_sort]
    else:
        order = 'FileID'

    if current_sort in (0,2,5,7,8,):
        order += " desc"

    if IsDebug:
        print('--> where:[%s] order:[%s], args: %s' % (where, order, args))

    pages = 0
    total_orders = 0
    total_cards = 0
    orders = []
    batches = []
    banks = []
    types = []
    statuses = []
    batchtypes = []
    batchstatuses = []
    xml = ''

    # ----------------------
    # Условие отбора (state)
    # ----------------------

    state = get_request_item('state')
    IsState = state and state != 'R0' and True or False

    args.update({
        'state' : ('State', state)
    })

    # --------------------
    # Файлы <на обработку>
    # --------------------

    if state == 'R4':
        rows = engine.runQuery('batches.preview', where='BatchStatusID=1', distinct=True)
        ids = [x[0] for x in rows]

        """
        rows = engine.runProcedure('materials.check',
                                   file_id='null', file_status_ids=makeIDList(COMPLETE_STATUSES), check=2, 
                                   no_cursor=False, distinct=True
                                   )
        """
        exec_params = {'file_id' : 'null', 'file_status_ids' : makeIDList(COMPLETE_STATUSES), 'check' : 2}
        rows = engine.runQuery('materials.check', exec_params=exec_params)

        if rows:
            for id in [x[0] for x in rows]:
                if id not in ids:
                    data, props, errors = _get_materials(id, show=1)
                    if props['send'] and not errors:
                        ids.append(id)

        if ids:
            where = '%s%sFileID in (%s)' % ( \
                where, 
                where and ' and ' or '', 
                ','.join([str(x) for x in sorted(ids)])
                )

    confirmed_file_id = 0

    # ======================
    # Выборка данных журнала
    # ======================

    if engine != None:

        # ------------------------------------------------
        # Поиск заказа по ID или номеру ТЗ (IsSearchBatch)
        # ------------------------------------------------
        
        if IsSearchBatch:
            file_id = 0

            cursor = engine.runQuery('batches', columns=('FileID',), where=where)
            for n, row in enumerate(cursor):
                file_id = row[0]

            if not file_id:
                where = 'FileID=%s' % FileID

                cursor = engine.runQuery(default_template, columns=('FileID',), where=where)
                for n, row in enumerate(cursor):
                    file_id = row[0]

            where = 'FileID=%s' % file_id

        # --------------------------------------------------
        # Кол-во записей по запросу в журнале (total_orders)
        # --------------------------------------------------

        cursor = engine.runQuery(default_template, columns=('count(*)', 'sum(FQty)',), where=where)
        if cursor:
            total_orders, total_cards = cursor[0]
            if total_cards is None:
                total_cards = 0

        if IsState:
            top = 1000
        if command == 'export':
            top = 10000

        # ===============
        # Заказы (orders)
        # ===============

        cursor = engine.runQuery(default_template, top=top, where=where, order='%s' % order, as_dict=True,
                                 encode_columns=('BankName','FileStatus'))
        if cursor:
            IsSelected = False
            
            for n, row in enumerate(cursor):
                x = row['FileStatus'].lower()

                state_error = 'ошибка' in x or 'отбраков' in x
                state_ready = 'заказ обработан' in x or 'готов к отгрузке' in x

                if state == 'R1' and (state_ready or state_error):
                    continue
                if state == 'R2' and not state_ready:
                    continue
                if state == 'R3' and not state_error:
                    continue

                if not IsState and offset and n < offset:
                    continue

                if file_id:
                    if not confirmed_file_id and file_id == row['FileID']:
                        confirmed_file_id = file_id
                    if not file_name and file_id == row['FileID']:
                        file_name = row['FName']

                    if file_id == row['FileID']:
                        row['selected'] = 'selected'
                        IsSelected = True
                else:
                    row['selected'] = ''

                for x in row:
                    if not row[x] or str(row[x]).lower() == 'none':
                        row[x] = ''

                row['Error'] = state_error
                row['Ready'] = state_ready
                row['StatusDate'] = getDate(row['StatusDate'])
                row['RegisterDate'] = getDate(row['RegisterDate'])
                row['ReadyDate'] = getDate(row['ReadyDate'])
                row['FQty'] = str(row['FQty']).isdigit() and int(row['FQty']) or 0
                row['id'] = row['FileID']

                #total_cards += row['FQty']
                orders.append(row)

            if line > len(orders):
                line = 1

            if not IsSelected and len(orders) >= line:
                row = orders[line-1]
                confirmed_file_id = file_id = row['id'] = row['FileID']
                file_name = row['FName']
                row['selected'] = 'selected'

        if len(orders) == 0:
            file_id = 0
            file_name = ''
            batch_id = 0
        elif confirmed_file_id != file_id or not file_id:
            row = orders[0]
            file_id = row['FileID']
            file_name = row['FName']
        elif not confirmed_file_id:
            file_id = 0
            file_name = ''

        if IsState and orders:
            total_orders = len(orders)
            total_cards = 0
            orders = orders[offset:offset+per_page]
            IsSelected = False

            for n, row in enumerate(orders):
                if file_id == row['FileID']:
                    row['selected'] = 'selected'
                    file_name = row['FName']
                    IsSelected = True
                else:
                    row['selected'] = ''
                total_cards += row['FQty']

            if not IsSelected and orders:
                row = orders[0]
                row['selected'] = 'selected'
                file_id = row['FileID']
                file_name = row['FName']

        if total_orders:
            pages = int(total_orders / per_page)
            if pages * per_page < total_orders:
                pages += 1

        # ================
        # Партии (batches)
        # ================

        if file_id:
            batches, batch_id = _get_batches(file_id, batch_id=batch_id, pers_tz=pers_tz, batchtype=BatchTypeID, batchstatus=BatchStatusID)

        # --------------------------------------------------------------------------------
        # Справочники фильтра запросов (banks, types, statuses, batchtypes, batchstatuses)
        # --------------------------------------------------------------------------------

        banks.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery('banks', order='BankName', distinct=True, encode_columns=(1,))
        banks += [(x[0], x[1]) for x in cursor]

        types.append((0, DEFAULT_UNDEFINED,))
        where = ClientID and ('ClientID = %s' % ClientID) or ''
        cursor = engine.runQuery('types', where=where, order='CName', distinct=True)
        types += [(x[0], x[1]) for x in cursor]

        statuses.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery('statuses', order='CName', distinct=True, encode_columns=(1,))
        statuses += [(x[0], x[1]) for x in cursor]

        batchtypes.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery('batchtypelist', order='CName', distinct=True, encode_columns=(1,))
        batchtypes += [(x[0], x[1]) for x in cursor]

        batchstatuses.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery('batchstatuslist', order='CName', distinct=True, encode_columns=(1,))
        batchstatuses += [(x[0], x[1]) for x in cursor]

        engine.dispose()

    # ----------------------
    # Условия отбора заказов
    # ----------------------

    states = [
        ('R0', DEFAULT_UNDEFINED),
        ('R1', 'Файлы "В работе"'),
        ('R2', 'Завершено'),
        ('R3', 'Ошибки'),
    ]

    if is_operator:
        states.insert(1, ('R4', 'Файлы "На обработку"'))

    # --------------------------------------
    # Нумерация страниц журнала (pagination)
    # --------------------------------------

    iter_pages = []
    for n in range(1, pages+1):
        if checkPaginationRange(n, page, pages):
            iter_pages.append(n)
        elif iter_pages[-1] != -1:
            iter_pages.append(-1)

    root = '%s/' % request.script_root
    query_string = 'per_page=%s' % per_page
    base = 'bankperso?%s' % query_string

    per_page_options = (5, 10, 20, 30, 40, 50, 100,)
    if is_admin:
        per_page_options += (250, 500)

    is_extra = has_request_item(EXTRA_)

    modes = [(n, '%s' % default_view['headers'][x][0]) for n, x in enumerate(default_view['columns'])]
    sorted_by = default_view['headers'][default_view['columns'][current_sort]]

    pagination = {
        'total'             : '%s / %s' % (total_orders, total_cards),
        'per_page'          : per_page,
        'pages'             : pages,
        'current_page'      : page,
        'iter_pages'        : tuple(iter_pages),
        'has_next'          : page < pages,
        'has_prev'          : page > 1,
        'per_page_options'  : per_page_options,
        'link'              : '%s%s%s%s%s' % (base, filter,
                                             (search and "&search=%s" % search) or '',
                                             (current_sort and "&sort=%s" % current_sort) or '',
                                             (state and "&state=%s" % state) or '',
                                             ),
        'sort'              : {
            'modes'         : modes,
            'sorted_by'     : sorted_by,
            'current_sort'  : current_sort,
        },
        'position'          : '%d:%d:%d:%d' % (page, pages, per_page, line),
    }

    loader = '/bankperso/loader'

    if is_extra:
        pagination['extra'] = 1
        loader += '?%s' % EXTRA_

    kw.update({
        'base'              : base,
        'page_title'        : gettext('WebPerso Order Registry View'),
        'header_subclass'   : 'left-header',
        'show_flash'        : True,
        'loader'            : loader,
        'semaphore'         : initDefaultSemaphore(),
        'args'              : args,
        'current_file'      : (file_id, file_name, batch_id, pers_tz),
        'navigation'        : get_navigation(),
        'config'            : database_config,
        'pagination'        : pagination,
        'orders'            : orders,
        'batches'           : batches,
        'banks'             : banks,
        'types'             : types,
        'statuses'          : statuses,
        'batchtypes'        : batchtypes,
        'batchstatuses'     : batchstatuses,
        'batches_tab'       : args['batchstatus'][1] and 'active' or 'all',
        'states'            : states,
        'xml'               : xml,
        'search'            : search or '',
    })

    sidebar = get_request_item('sidebar')
    if sidebar:
        kw['sidebar']['state'] = int(sidebar)

    return kw

## ==================================================== ##

@bankperso.route('/demo', methods = ['GET','POST'])
def demo(**kw):
    connection = CONNECTION[kw.get('engine') or 'bankperso']
    """
    conn = pymssql.connect(connection['server'], connection['user'], connection['password'], connection['database'])
    cursor = conn.cursor(as_dict=False)
    cursor.execute('SELECT count(*) FROM [BankDB].[dbo].[WEB_OrdersStatus_vw]')
    total_orders = cursor.fetchone()[0]
    """
    refresh()
    
    cursor = engine.execute('SELECT count(*) FROM [BankDB].[dbo].[WEB_OrdersStatus_vw]')
    total_orders = cursor.fetchone()[0]

    banks = []
    types = []
    statuses = []
    params = []
    TZ = []

    file_id = 218107
    batch_id = 1184030

    try:
        cursor = engine.runQuery('banks', order='BankName', distinct=True)
        c1 = cursor
        banks += [x[1] for x in c1]

        cursor = engine.runQuery('types', order='CName', distinct=True, encode_columns=(1,))
        c2 = cursor
        types += [x[1] for x in c2]
        
        cursor = engine.runQuery('statuses', order='CName', distinct=True)
        c3 = cursor
        statuses += [x[1].encode(default_iso).decode(default_encoding) for x in c3]
        
        cursor = engine.runQuery('params', as_dict=True, params="%s, %s, '', 0, ''" % (file_id, batch_id))
        c4 = cursor
        for row in c4:
            row['PName'] = row['PName'].encode(default_iso).decode(default_encoding)
            row['PValue'] = row['PValue'].encode(default_iso).decode(default_encoding)
            row['TValue'] = row['TValue'].encode(default_iso).decode(default_encoding)
            params.append(row)
        
        cursor = engine.runQuery('TZ', as_dict=True, params="%s, %s, '', 1, ''" % (file_id, batch_id))
        c5 = cursor
        for row in c5:
            row['PName'] = row['PName'].encode(default_iso).decode(default_encoding)
            row['PValue'] = row['PValue'].encode(default_iso).decode(default_encoding)
            key = row['PName']
            if key in database_config['TZ']['rename']:
                x = database_config['TZ']['rename'][key]
                row['PName'] = x[0]
                row['PSortIndex'] = x[1]
            TZ.append(row)

        exclude = database_config['TZ']['exclude']
        TZ = sorted([x for x in TZ if x['PType'] in (0,1) and x['PName'] not in exclude], key=lambda x: x['PSortIndex'],
                    reverse=False)
    except:
        print_exception()

    else:
        if IsDebug:
            print_to(None, '--> demo check: %s' % 'OK')

    kw = { \
        'title'        : 'demo',
        'connection'   : connection,
        'config'       : database_config,
        'banks'        : banks,
        'types'        : types,
        'statuses'     : statuses,
        'params'       : params,
        'TZ'           : TZ,
        'total'        : total_orders,
    }
    return render_template('demo.html', **kw)

@bankperso.route('/', methods = ['GET'])
@bankperso.route('/bankperso', methods = ['GET','POST'])
@login_required
def index():
    debug, kw = init_response('WebPerso Main Page')
    kw['product_version'] = product_version

    is_admin = current_user.is_administrator()
    is_operator = current_user.is_operator()

    command = get_request_item('command')
    
    file_id = int(get_request_item('file_id') or '0')
    batch_id = int(get_request_item('batch_id') or '0')

    if IsDebug:
        print('--> command:%s, file_id:%s, batch_id:%s' % (command, file_id, batch_id))

    refresh(file_id=file_id)

    IsMakePageDefault = True
    logsearch = ''
    tagsearch = ''
    info = ''

    errors = []

    if command.startswith('admin'):
        command = command.split(DEFAULT_HTML_SPLITTER)[1]

        if not is_operator:
            flash('You have not permission to run this action!')
            command = ''

        elif command == 'activate':

            # -------------------------
            # Activate selected batches
            # -------------------------

            selected_batch_ids = get_request_item('selected_batch_ids') or ''
            info = 'selected_batch_ids:%s' % selected_batch_ids

            for batch_id in selected_batch_ids.split(DEFAULT_HTML_SPLITTER):
                rows, error_msg = engine.runProcedure('activate', batch_id=batch_id, no_cursor=True, with_error=True)

                if error_msg:
                    errors.append(error_msg)

        elif not is_admin:
            flash('You have not permission to run this action!')
            command = ''

        elif command == 'create':
            info = 'file_id:%s' % file_id

            # --------------
            # Re-Create file
            # --------------

            engine.runProcedure('createfile', file_id=file_id, no_cursor=True)

        elif command == 'delete':
            info = 'file_id:%s' % file_id

            # -----------
            # Delete file
            # -----------

            engine.runProcedure('deletefile', file_id=file_id, no_cursor=True)

        elif command == 'change-filestatus':
            new_file_status = int(get_request_item('status_file_id') or '0')
            check_file_status = 'null'
            info = 'new_file_status:%s' % new_file_status

            # ---------------------
            # Change status of file
            # ---------------------

            statuses = _get_filestatuses(file_id)

            if statuses:
                if new_file_status in statuses:
                    check_file_status = new_file_status
                elif new_file_status < statuses[-1]:
                    check_file_status = new_file_status

            engine.runProcedure('changefilestatus', file_id=file_id, new_file_status=new_file_status, 
                                check_file_status=check_file_status, no_cursor=True)

        elif command == 'change-batchstatus':
            new_batch_status = int(get_request_item('status_batch_id') or '0')
            info = 'new_batch_status:%s' % new_batch_status

            # ----------------------
            # Change status of batch
            # ----------------------

            engine.runProcedure('changebatchstatus', file_id=file_id, batch_id=batch_id, 
                                new_batch_status=new_batch_status, no_cursor=True)

        elif command == 'logsearch':
            logsearch = get_request_item('logsearch') or ''
            info = 'logsearch:%s' % logsearch

            # --------------------
            # Dump LogSearch items
            # --------------------

            IsMakePageDefault = False

        elif command == 'tagsearch':
            tagsearch = get_request_item('tagsearch') or ''
            info = 'tagsearch:%s' % tagsearch

            # --------------------
            # Dump TagSearch items
            # --------------------

            IsMakePageDefault = False

        if IsDebug:
            print('--> %s' % info)

        if IsTrace:
            print_to(errorlog, '--> command:%s' % command)

    elif command.startswith('service'):
        command = command.split(DEFAULT_HTML_SPLITTER)[1]

    kw['errors'] = '<br>'.join(errors)
    kw['OK'] = ''

    try:
        if IsMakePageDefault:
            kw = _make_page_default(kw)

        if IsTrace:
            print_to(errorlog, '--> bankperso:%s %s %s %s' % ( \
                     command, current_user.login, str(kw.get('current_file')), info,), 
                     request=request)
    except:
        print_exception()

    kw['vsc'] = (IsDebug or IsIE() or IsForceRefresh) and ('?%s' % str(int(random.random()*10**12))) or ''

    if command:
        is_extra = has_request_item(EXTRA_)

        if not command.strip():
            pass

        elif command == 'activate':
            if kw['errors']:
                flash('Batch activation done with errors!')
            else:
                kw['OK'] = gettext('Message: Activation is perfomed successfully.')

        elif command == 'unload':
            dump, total = getTabIBody(int(kw.get('file_id')), limit=None, is_extra=is_extra)
            response = make_response(dump)
            response.headers["Content-Disposition"] = "attachment; filename=body%s.dump" % kw.get('file_id')
            return response

        elif command == 'imageunload':
            dump = getBodyState(int(kw.get('file_id')), with_image=True, no_body=True, limit=None, is_extra=is_extra)
            response = make_response(dump)
            response.headers["Content-Disposition"] = "attachment; filename=image%s.dump" % kw.get('file_id')
            return response

        elif command == 'fullunload':
            dump = getBodyState(int(kw.get('file_id')), with_image=True, limit=None, is_extra=is_extra)
            response = make_response(dump)
            response.headers["Content-Disposition"] = "attachment; filename=full%s.dump" % kw.get('file_id')
            return response

        elif command == 'logsearch':
            dump = getLogSearchDump(logsearch)
            response = make_response(dump)
            response.headers["Content-Disposition"] = "attachment; filename=%s.dump" % _make_response_name('logsearch')
            return response

        elif command == 'tagsearch':
            dump = getTagSearchDump(file_id, tagsearch, is_extra=is_extra)
            response = make_response(dump)
            response.headers["Content-Disposition"] = "attachment; filename=%s.dump" % _make_response_name('tagsearch')
            return response

        elif command == 'kp':
            return _make_xls_content(_make_report_kp(kw), 'Статистика КП', 'kp')

        elif command == 'branch-list':
            try:
                filename = kw.get('current_file')[1] or ''
            except:
                filename = ''
            return _make_xls_content(_make_report_branch_list(kw), filename or 'Статистика доставки по филиалам', 'branch_list')

        elif command == 'export':
            return _make_xls_content(_make_export(kw), 'Журнал заказов')

    return make_response(render_template('bankperso.html', debug=debug, **kw))

@bankperso.after_request
def make_response_no_cached(response):
    if engine is not None:
        engine.close()
    # response.cache_control.no_store = True
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response

@bankperso.route('/bankperso/loader', methods = ['GET', 'POST'])
@login_required
def loader():
    exchange_error = ''
    exchange_message = ''

    is_extra = has_request_item(EXTRA_)

    action = get_request_item('action') or default_action
    selected_menu_action = get_request_item('selected_menu_action') or action != default_action and action or '301'

    response = {}

    file_id = int(get_request_item('file_id') or '0')
    batch_id = int(get_request_item('batch_id') or '0')
    batchtype = int(get_request_item('batchtype') or '0')
    batchstatus = int(get_request_item('batchstatus') or '0')
    params = get_request_item('params') or None

    refresh(file_id=file_id)

    if IsDebug:
        print('--> action:%s file_id:%s batch_id:%s batchtype:%s batchstatus:%s' % (action, file_id, batch_id, batchtype, batchstatus))

    if IsTrace:
        print_to(errorlog, '--> loader:%s %s [%s:%s:%s:%s:%s]%s' % (
                 action, 
                 current_user.login, 
                 file_id, batch_id, 
                 batchtype, 
                 batchstatus, 
                 selected_menu_action,
                 params and ' params:[%s]' % params or '',
            ))

    currentfile = None
    batches = []
    config = None

    data = ''
    number = ''
    columns = []
    total = None

    props = None
    errors = None

    try:
        if action == default_action:
            batches, batch_id = _get_batches(file_id, batchtype=batchtype, batchstatus=batchstatus)
            currentfile = [requested_order.get('FileID'), requested_order.get('FName'), batch_id]
            config = _get_view_columns(database_config['batches'])
            action = selected_menu_action

        if not action:
            pass

        elif action == '201':
            cursor = engine.runQuery('filestatuslist', order='TID', distinct=True)
            data = [{'id':x[0], 'value':x[2].encode(default_iso).decode(default_encoding)} for x in cursor]

        elif action == '202':
            cursor = engine.runQuery('batchstatuslist', order='TID', distinct=True)
            data = [{'id':x[0], 'value':x[1].encode(default_iso).decode(default_encoding)} for x in cursor]

        elif action == '301':
            data, props = getTabParams(file_id, batch_id)

        elif action == '302':
            view = database_config['logs']
            columns = _get_view_columns(view)
            data = getTabLogs(file_id)

        elif action == '303':
            view = database_config['cardholders']
            columns = _get_view_columns(view)
            data = getTabCardholders(file_id)

        elif action == '304':
            data, total = getTabIBody(file_id, is_extra=is_extra)

        elif action == '305':
            data, total = getTabProcessErrMsg(file_id)

        elif action == '306':
            view = database_config['persolog']
            columns = _get_view_columns(view)
            if IsUseDBLog:
                data = getTabDBLog('Bankperso', view, file_id=file_id)
            else:
                data = getTabPersoLog(view['export'], file_id=file_id)

        elif action == '307':
            view = database_config['sdclog']
            columns = _get_view_columns(view)
            if IsUseDBLog:
                data = getTabDBLog('SDC', view, file_id=file_id)
            else:
                data = getTabSDCLog(view['export'], file_id=file_id)

        elif action == '308':
            view = database_config['exchangelog']
            columns = _get_view_columns(view)
            if False and IsUseDBLog:
                data = getTabDBLog('Exchange', view, file_id=file_id)
            else:
                data = getTabExchangeLog(view['export'], file_id=file_id)

        elif action == '309':
            view = database_config['materials.order']
            columns = _get_view_columns(view)
            data, props, errors = calculateMaterials(file_id=file_id)

        elif action == '310':
            errors = sendMaterialsOrder(file_id=file_id)

        elif action == '311':
            data, props, errors = calculateContainerList(file_id=file_id)

        elif action == '312':
            file_ids = [int(x) for x in params.split(DEFAULT_HTML_SPLITTER)]
            data, props, errors = calculateGroupContainerList(file_ids=file_ids)

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
        'file_id'          : file_id,
        'batch_id'         : batch_id,
        # ----------------------------------------------
        # Default Lines List (sublines equal as batches)
        # ----------------------------------------------
        'currentfile'      : currentfile,
        'sublines'         : batches,
        'config'           : config,
        # --------------------------
        # Results (Log page content)
        # --------------------------
        'total'            : total or len(data),
        'data'             : data,
        'props'            : props,
        'columns'          : columns,
        'errors'           : errors,
    })

    return jsonify(response)

