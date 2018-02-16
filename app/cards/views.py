# -*- coding: utf-8 -*-

import re
import random
from operator import itemgetter

from config import (
     CONNECTION, BP_ROOT, 
     IsDebug, IsDeepDebug, IsTrace, IsForceRefresh, IsPrintExceptions, LocalDebug,
     errorlog, print_to, print_exception,
     default_print_encoding, default_unicode, default_encoding, default_iso, image_encoding, cr,
     LOCAL_FULL_TIMESTAMP, LOCAL_EXCEL_TIMESTAMP, LOCAL_EASY_TIMESTAMP, LOCAL_EASY_DATESTAMP, LOCAL_EXPORT_TIMESTAMP, 
     UTC_FULL_TIMESTAMP, UTC_EASY_TIMESTAMP, DATE_STAMP
     )

from . import cards

from ..settings import *
from ..database import database_config, BankPersoEngine
from ..utils import (
     getToday, getDate, getDateOnly, checkDate, cdate, indentXMLTree, isIterable, makeXLSContent, makeIDList, 
     checkPaginationRange, getMaskedPAN
     )

from ..semaphore.views import initDefaultSemaphore

##  ===============================
##  Cards View Presentation Package
##  ===============================

default_page = 'cards'
default_action = '700'
default_template = 'cards.batches'
engine = None

IsLocalDebug = LocalDebug[default_page]

TEMPLATE_TID_INDEX   = 0
TEMPLATE_QUERY_INDEX = 1
TEMPLATE_FKEY_INDEX  = 2
TEMPLATE_VIEW_INDEX  = 3

_views = {
    'batches' : ('TID', 'pers_id',  'PersBatchID',     'cards.batches',),
    'opers'   : ('TID', 'oper_id',  'PersBatchOperID', 'cards.pers-batch-opers'),
    'logs'    : ('TID', 'batch_id', 'BatchID',         'cards.batches-log'),
    'units'   : ('TID', 'batch_id', 'BatchID',         'cards.batch-units'),
    'params'  : ('TID', 'batch_id', 'BatchID',         'cards.batch-params'),
}

requested_batch = {}

##  --------------------------------------------------------------------------------------------------
##  batch_id:   [ID ТЗ ???] BatchList_tb.TID, PersBatchList_tb.BatchID WEB_Batches_vw.BatchID (BatchID)
##  pers_id:    [ID партии] PersBatchList_tb.TID, WEB_Batches_vw.TID (PersBatchID)
##  --------------------------------------------------------------------------------------------------

def before(f):
    def wrapper(**kw):
        global engine
        if engine is not None:
            engine.close()
        engine = BankPersoEngine(current_user, connection=CONNECTION[kw.get('engine') or 'cards'])
        return f(**kw)
    return wrapper

@before
def refresh(**kw):
    global requested_batch

    if 'pers_id' in kw and kw.get('pers_id'):
        requested_batch = _get_batch(kw['pers_id']).copy()

def getBatchInfo(pers_id):
    #getDate(requested_batch.get('StatusDate'), UTC_EASY_TIMESTAMP)
    #requested_batch.get('FName')
    return 'ID [%s-%s]' % (pers_id, requested_batch.get('BatchID'))

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
            'client'     : ('Client', get_request_item('client') or ''),
            'filename'   : ('FName', get_request_item('filename') or ''),
            'status'     : ('StatusID', int(get_request_item('status') or '0')),
            'persstatus' : ('PersStatus', get_request_item('persstatus') or ''),
            'perstype'   : ('PersTypeID', int(get_request_item('perstype') or '0')),
            'date_from'  : ('StatusDate', get_request_item('date_from') or ''),
            'date_to'    : ('StatusDate', get_request_item('date_to') or ''),
            'id'         : ('TID', int(get_request_item('_id') or '0')),
        })
    except:
        args.update({
            'client'     : ('Client', ''),
            'filename'   : ('FName', ''),
            'status'     : ('StatusID', 0),
            'persstatus' : ('PersStatus', ''),
            'perstype'   : ('PersTypeID', 0),
            'date_from'  : ('StatusDate', ''),
            'date_to'    : ('StatusDate', ''),
            'id'         : ('TID', 0),
        })
        flash('Please, update the page by Ctrl-F5!')

    return args

def _get_batch(id):
    where = 'TID=%s' % id
    cursor = engine.runQuery(default_template, top=1, where=where, as_dict=True, 
                             encode_columns=('Client','FName','PersType','Status','PersStatus',),
                             columns=database_config[default_template].get('export'))
    return cursor and cursor[0] or {}

def _get_batch_ids(pers_ids):
    where = 'TID in (%s)' % makeIDList(pers_ids)
    cursor = engine.runQuery(default_template, where=where, columns=('BatchID',))
    return cursor and [row[0] for row in cursor] or []

def _get_bankperso_batches(ids):
    where = 'TZ in (%s) AND BatchTypeID in (7,14) AND FileStatusID not in (%s)' % (makeIDList(ids), makeIDList(COMPLETE_STATUSES))
    cursor = engine.runQuery('batches', where=where, order='TID desc', as_dict=True, 
                             encode_columns=('Status',),
                             columns=database_config['batches'].get('export'))
    return cursor or []

def _get_client(id):
    return id and engine.getReferenceID(default_template, key='TID', value=id, tid='Client') or None

def _get_opers(pers_id, **kw):
    opers = []
    oper_id = kw.get('oper_id') or None
    pers_tz = kw.get('pers_tz') or None
    selected_id = None

    is_simple = kw.get('is_simple') and True or False

    where = 'PersBatchID=%s' % pers_id

    cursor = engine.runQuery('cards.pers-batch-opers', where=where, order='PersOperTypeID', as_dict=True,
                             encode_columns=('Status',))
    if cursor:
        IsSelected = False
        
        for n, row in enumerate(cursor):
            if is_simple:
                pass
            else:
                row['StatusDate'] = getDate(row['StatusDate'], DEFAULT_DATETIME_INLINE_FORMAT)
                row['Ready'] = 'обработка завершена' in row['Status'] and True or False
                row['Found'] = pers_tz and row['TID'] == pers_tz
                row['id'] = row['TID']

                if (oper_id and oper_id == row['TID']):
                    row['selected'] = 'selected'
                    selected_id = oper_id
                    IsSelected = True
                else:
                    row['selected'] = ''

            opers.append(row)

        if not is_simple and not IsSelected:
            row = opers[0]
            selected_id = row['id']
            row['selected'] = 'selected'

    if is_simple:
        return opers

    return opers, selected_id

def _get_batchstatuses(id, order='StatusID'):
    statuses = []

    cursor = engine.runQuery('cards.batch-statuses', where='TID=%s' % id, order=order, as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            statuses.append(row['StatusID'])

    return statuses

def _get_logs(batch_id):
    view = 'cards.batches-log'
    logs = []

    cursor = engine.runQuery(view, where='BatchID=%s' % batch_id, order='LID', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            row['id'] = row['LID']
            row['Status'] = row['Status'].encode(default_iso).decode(default_encoding)
            row['StatusDate'] = getDate(row['StatusDate'], DEFAULT_DATETIME_INLINE_FORMAT)
            row['ModDate'] = getDate(row['ModDate'], DEFAULT_DATETIME_INLINE_FORMAT)

            logs.append(row)

    return logs

def _get_oper_logs(pers_id):
    view = 'cards.batch-opers-log'
    logs = []

    cursor = engine.runQuery(view, where='PersBatchID=%s' % pers_id, order='LID', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            row['id'] = row['LID']
            row['Status'] = row['Status'].encode(default_iso).decode(default_encoding)
            row['StatusDate'] = getDate(row['StatusDate'], DEFAULT_DATETIME_INLINE_FORMAT)
            row['ModDate'] = getDate(row['ModDate'], DEFAULT_DATETIME_INLINE_FORMAT)

            logs.append(row)

    return logs

def _get_units(batch_id):
    view = 'cards.batch-units'
    units = []

    cursor = engine.runQuery(view, where='BatchID=%s' % batch_id, order='TID', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            row['id'] = row['TID']
            row['PAN'] = getMaskedPAN(row['PAN'])
            row['Status'] = row['Status'].encode(default_iso).decode(default_encoding)
            row['StatusDate'] = getDate(row['StatusDate'], DEFAULT_DATETIME_INLINE_FORMAT)

            units.append(row)

    return units

def _get_params(batch_id, **kw):
    view = 'cards.batch-params'
    params = []

    where = kw.get('where') or ('BatchID=%s' % batch_id)

    cursor = engine.runQuery(view, where=where, order='PType', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            row['id'] = row['TID']
            row['PName'] = row['PName'].encode(default_iso).decode(default_encoding)
            row['PValue'] = row['PValue'].encode(default_iso).decode(default_encoding)

            params.append(row)

    return params

## ==================================================== ##

def getTabOperParams(pers_id, oper_id):
    """
        Get Oper Parameters list.

        Arguments:
            pers_id  -- ID ТЗ персонализации
            oper_id  -- ID операции
        
        Returns:
            data     -- List, Список параметров партии:
                        [{
                           'PName'      -- название параметра
                           'PValue'     -- значение параметра
                           'PSortIndex' -- порядок в ТЗ
                           'PType'      -- тип параметра: 0 - параметр партии, 1 - параметр ТЗ
                           'class_name' -- html-класс
                        }, ... ]

            props    -- Dictionary, Информация о партии: 
                        {
                           'id'     -- ID партии
                           'number' -- номер ТЗ
                           'name'   -- название типа партии
                           'no'     -- кол-во карт в партии
                           'file'   -- имя файла-заказа
                           'cards'  -- кол-во карт в файле
                        }
    """
    data = []
    props = {'id' : oper_id}

    try:
        if pers_id and oper_id:
            where = 'TID=%s' % oper_id
            cursor = engine.runQuery('cards.pers-batch-opers', columns=('PersOperTypeID',), top=1, where=where)
            oper_type_id = cursor[0][0] if cursor is not None and len(cursor) else None

            if oper_type_id is not None:
                where = 'PersBatchID=%s AND BatchOperTypeID=%s' % (pers_id, oper_type_id)
                cursor = engine.runQuery('cards.batch-oper-params', where=where, as_dict=True)

                for n, row in enumerate(cursor):
                    try:
                        row['PName'] = row['PName'].encode(default_iso).decode(default_encoding)
                        row['PValue'] = row['PValue'].encode(default_iso).decode(default_encoding)
                        row['PSortIndex'] = 0
                        row['PType'] = 1
                        row['class_name'] = ''

                        data.append(row)
                    except:
                        print_exception()

            # -------------------
            # Информация о партии
            # -------------------

            where = 'TID=%s' % pers_id
            cursor = engine.runQuery(default_template, top=1, where=where, as_dict=True)

            if cursor is not None and len(cursor):
                row = cursor[0]
                if row:
                    number = row['TZ']
                    props.update({
                        'number' : number,
                        'name'   : row['PersType'].encode(default_iso).decode(default_encoding),
                        'no'     : row['PQty'],
                        'file'   : row['FName'],
                        'cards'  : row['BQty'],
                    })

    except:
        print_exception()

    return data or [], props

def getTabLogs(batch_id):
    return _get_logs(batch_id)

def getTabOperLogs(pers_id):
    return _get_oper_logs(pers_id)

def getTabUnits(batch_id):
    return _get_units(batch_id)

def getTabParams(batch_id):
    return _get_params(batch_id)

def getFileBatches(pers_id=None):
    """
        Returns `PersBatchID` list for the file selected by requested batch (pers_id).
        Note: Check existing of `IDX_BatchList_OrderFName` index.
    """
    if pers_id is not None:
        filename = _get_batch(pers_id).get('FName')
    else:
        filename = requested_batch.get('FName')

    PERS_STATUS_RUN = 'обработка не начиналась'

    where = "FName='%s'" % (filename or '')
    cursor = engine.runQuery(default_template, where=where, columns=('TID', 'PersStatus',), encode_columns=('PersStatus',), as_dict=True)
    ids = cursor and [row['TID'] for row in cursor if row['PersStatus'] == PERS_STATUS_RUN] or []
    
    return ids

def activateBatches(pers_ids):
    """
        Check & Activate selected Batches.

        Arguments:
            pers_ids -- List, Selected `PersBatchID` pers_ids to activate (String)
        
        Returns:
            data     -- List, Stored procedures response+Batches paramaters list:
                        [view1, view2, ...], 
                        
                <0,1,...> -- List (mapped list), view (response) values: 
                        
                        {<column1> : <value>, <column2> : <value>, ...}

            props    -- Dict, Response info, 
            
                <key>     -- Dict, `view` (stored procedure) name: 
                        {
                            'index'   -- Int, data list view index
                            'columns' -- List, view columns list
                        }

            Other Keywords in `props`:

                `batches` -- Dict, selected batches from default_template: 
                
                        {<pers_id> : <batch>, ...}

                `params`  -- Tuple, parameters list by `batch_id`:
                
                        {<batch_id> : ((<PName>, <PValue>), ...), ...}

                `opers`   -- Tuple, parameters list by `pers_id`:
                
                        {<pers_id> : ((<Oper>,), ...), ...}

            errors   -- List, Errors list: ['error', ...], sorted by error code: 2,1,0.
    """
    data = []
    props = {}
    errors = []

    ids = sorted([int(x) for x in pers_ids])

    rfname = re.compile(r'(\([\d]+\s*шт\))', re.I+re.DOTALL)
    views = ('cards.plastic-params', 'cards.plastic-params-new',)
    sql_params = {'pers_ids' : makeIDList(pers_ids)}
    batch_ids = _get_batch_ids(ids)

    _INDEX = 1
    _ENCODED = 3
    _DEFAULT_VALUE = 4
    _UNDEFINED_ERROR = 2
    _ERROR = 1
    _WARNING = 0

    dbconfig = None
    params = fields = columns = encode_columns = None

    IsError = 0

    check_params = {}
    sumQty = sumQtyControl = 0
    responses = None

    def _get_query_params():
        params = dbconfig['params'] % sql_params
        fields = dbconfig['fields']
        columns = [x[0] for x in sorted(fields.items(), key=itemgetter(_INDEX))]
        encode_columns = [x for x in columns if fields[x][_ENCODED]]
        return params, fields, columns, encode_columns

    def _get_items(cursor):
        items = []
        for n, row in enumerate(cursor):
            for column in columns:
                if row[column] is None:
                    row[column] = fields[column][_DEFAULT_VALUE]
            items.append(row)
        return items

    def _is_param_valid(row, param):
        name, id, error = param.split(':')
        if not id in row:
            errors.append((_WARNING, gettext('Warning: Missing parameter:') + id,))
            return False
        elif check_params.get(name):
            if row[id] != check_params[name]:
                errors.append((_ERROR, gettext('Error: %s.' % error),))
                return False
        elif not row[id]:
            errors.append((_WARNING, gettext('Warning: Parameter is empty:') + id,))
            return False
        else:
            check_params[name] = row[id]
        return True

    try:
        indexes = []

        # ------------------------
        # Get Batch view responses
        # ------------------------

        for index, view in enumerate(views):
            dbconfig = database_config[view]
            params, fields, columns, encode_columns = _get_query_params()

            items = _get_items(engine.runQuery(
                    view,
                    columns=columns,
                    params=params,
                    encode_columns=encode_columns,
                    as_dict=True,
                    top=1,
                ))

            if 'BatchesInfo' in columns:
                pass

            data.append(items)

            props[view] = {
                'index'   : index,
                'columns' : columns,
            }

            indexes.append(index)

        # ---------------------
        # Get Batches Info list
        # ---------------------

        cursor = engine.runQuery(default_template, 
                                 columns=database_config[default_template].get('export'), 
                                 where='TID in (%s)' % sql_params['pers_ids'], 
                                 order='TID', 
                                 encode_columns=('Client','FName','PersType','Status','PersStatus',),
                                 as_dict=True,
                                 )

        batches = cursor and dict(zip([int(id) for id in ids], cursor)) or {}

        props['batches'] = batches

        # ---------------
        # Get Params list
        # ---------------
        
        params = {}

        for batch_id in batch_ids:
            params[batch_id] = tuple([(x['PName'], x['PValue']) for x in _get_params(batch_id)])

        props['params'] = params

        # --------------
        # Get Opers list
        # --------------
        
        opers = {}

        for id in ids:
            opers[id] = tuple([(x['Oper'],) for x in _get_opers(id, is_simple=1)])

        props['opers'] = opers

        # ---------------
        # Get Blanks list
        # ---------------

        blanks = []

        for i, row in enumerate(data[0]):
            batch_id = row['BatchID']

            blank = None
            for param in params[batch_id]:
                if param[0] == 'Бланк листовки':
                    blank = param[1]
                    break

            if not blank:
                continue

            blanks.append({
                'SysBatchID'  : row['SysBatchID'],
                'PersBatchID' : row['PersBatchID'],
                'BQty'        : row['BQty'],
                'Blank'       : blank,
            })

        props['blanks'] = blanks

        # ----------
        # Check data
        # ----------

        responses = len(indexes) == len(views) and data[0:len(indexes)] or None

        if not responses or len(list(filter(None, responses))) < len(responses):
            errors.append((_UNDEFINED_ERROR, gettext('Error: Empty or missed responses list.'),))
            IsError = 1
            raise 1

        if IsLocalDebug:

            # -----------------------------
            # Local Debug Data Construction
            # -----------------------------

            for n, response in enumerate(responses):
                for i, row in enumerate(response):
                    if n == 0:
                        id = row['PersBatchID']
                        b = batches[id]

                        row['ClientName'] = b['Client']
                        row['FileName'] = b['FName']
                        row['FQty'] = b['PQty']
                        row['SumQty'] = b['PQty']
                        row['Urgency'] = 'Внимание! Тест!!!'
                        row['ReadyDate'] = getDate(b['StatusDate'], DEFAULT_DATETIME_READY_FORMAT)
                    else:
                        b = responses[0][i]

                        row['ClientName'] = b['ClientName']
                        row['FileName'] = b['FileName']
                        row['ReadyDate'] = b['ReadyDate']

        else:
            bankperso_batches = _get_bankperso_batches([x['SysBatchID'] for x in responses[0]])

            # -------------------------------
            # Validate BankPerso associations
            # -------------------------------

            if len(bankperso_batches) != len(responses[0]):
                errors.append((_UNDEFINED_ERROR, gettext('Error: Perhaps, processing of selected orders was finished.'),))
                IsError = 1
                raise 1

            # --------------------
            # Check Batch Statuses
            # --------------------

            status = None

            for batch in bankperso_batches:
                if not status:
                    status = batch['BatchStatusID']
                if status == batch['BatchStatusID']:
                    continue

                errors.append((_ERROR, gettext('Error: Selected batches with different status.'),))
                IsError = 1
                raise 1

        for n, response in enumerate(responses):
            for row in response:
                if n == 0:
                    if not (row['ClientName'] and row['FileName'] and row['FQty']):
                        errors.append((_UNDEFINED_ERROR, gettext('Error: Batch contains empty basic parameters:') + row['PersBatchID'],))
                        continue

                    if not _is_param_valid(row, 'client_id:ClientIDStr:Client ID is not unique'):
                        break
                    if not _is_param_valid(row, 'client_name:ClientName:Client name is not unique'):
                        break
                    if not _is_param_valid(row, 'filename:FileName:There were selected batches from a few Order files'):
                        break

                    if not row['ReadyDate'].strip():
                        row['ReadyDate'] = ' '*20;

                    if row['SumQty'] == 0:
                        errors.append((_ERROR, gettext('Error: Batch SumQty is zero.'),))
                    else:
                        sumQty += row['SumQty']

                else:
                    sumQtyControl += row['Qty']

        if sumQty < sumQtyControl or sumQtyControl == 0:
            errors.append((_UNDEFINED_ERROR, gettext('Error: Final sum of batches is unmatched.'),))

        if not check_params.get('client_name'):
            errors.append((_ERROR, gettext('Error: Client name is not present.'),))

        if not check_params.get('filename'):
            errors.append((_ERROR, gettext('Error: File name is not present.'),))

        # -------------------
        # Plastic type groups
        # -------------------
        
        group = ''
        
        for n, item in enumerate(responses[0]):
            x = '%s:%s:%s' % (item['CardsName'], item['CardsType'], item['PlasticType']) #
            if x != group:
                group = x
                item['rowspan'] = 1
                item['SumQty'] = item['BQty']
                rowspan = n
            else:
                responses[0][rowspan]['rowspan'] += 1
                item['CardsName'] = item['CardsType'] = item['PlasticType'] = ''

                responses[0][rowspan]['SumQty'] += item['BQty']

                item['SumQty'] = 0

        props['r1:rowspan'] = (1,2,3,9)

    except:
        if IsError:
            pass
        elif IsPrintExceptions:
            print_exception()

    finally:
        if responses:
            b = responses[0][0]

            filename = b['FileName'].strip()
            m = rfname.search(filename)
            if m is None:
                filename = '%s (%s шт)' % (filename, b['FQty'])

            props.update({
                'has_mir'      : False,
                'has_protocol' : sumQtyControl > 10 and True or False,
                'ids'          : ids,
                'ClientName'   : b['ClientName'],
                'FileName'     : filename,
                'ReadyDate'    : b['ReadyDate'],
                'Total'        : sumQtyControl, #sumQty XXX !
                'Now'          : getDate(getToday(), LOCAL_EXCEL_TIMESTAMP),
                'Today'        : getDate(getToday(), DEFAULT_DATETIME_TODAY_FORMAT),
                'show'         : 0,
            })

    errors = [x[1] for x in sorted(errors, key=itemgetter(0), reverse=True)]

    return responses, props, errors

## ==================================================== ##

def _make_response_name(name=None):
    return '%s-%s' % (getDate(getToday(), LOCAL_EXPORT_TIMESTAMP), name or 'cards')

def _make_xls_content(rows, title, name=None):
    xls = makeXLSContent(rows, title, True)
    response = make_response(xls)
    response.headers["Content-Disposition"] = "attachment; filename=%s.xls" % _make_response_name(name)
    return response

def _make_page_default(kw):
    pers_id = int(kw.get('pers_id'))
    oper_id = int(kw.get('oper_id'))

    is_admin = current_user.is_administrator()

    args = _get_page_args()

    file_name = ''
    filter = ''
    qs = ''

    # -------------------------------
    # Представление БД (default_view)
    # -------------------------------

    default_view = database_config[default_template]

    # ---------------------------------------------
    # Поиск номера ТЗ в списке партий (pers_tz)
    # ---------------------------------------------

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
    IsSearchByNumber = False
    items = []
    TZ = None

    # -----------------------------------------------
    # Поиск ID партии, номера ТЗ (search is a number)
    # -----------------------------------------------

    if search:
        try:
            TID = BatchID = TZ = int(search)
            items.append('(TID=%s OR BatchID=%s OR TZ=%s)' % (TID, BatchID, TZ))
            IsSearchByNumber = True
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

    Client = args['client'][1]
    StatusID = args['status'][1]
    PersTypeID = args['perstype'][1]

    StatusDate = None

    if args:
        for key in args:
            if key in (EXTRA_,):
                continue
            name, value = args[key]
            if value:
                if key in ('...'):
                    pass
                elif key == 'date_from':
                    if checkDate(value, DEFAULT_DATE_FORMAT[1]):
                        items.append("%s >= '%s 00:00'" % (name, value))
                        StatusDate = value
                    else:
                        args['date_from'][1] = ''
                        continue
                elif key == 'date_to':
                    if checkDate(value, DEFAULT_DATE_FORMAT[1]):
                        items.append("%s <= '%s 23:59'" % (name, value))
                    else:
                        args['date_to'][1] = ''
                        continue
                elif key in ('id', 'perstype', 'status',):
                    items.append("%s=%s" % (name, value))
                elif key in ('client', 'persstatus',):
                    items.append("%s='%s'" % (name, value))
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
        order = 'TID'

    if current_sort in (0,3,4,5,9,10):
        order += " desc"

    if IsDebug:
        print('--> where:[%s] order:[%s], args: %s' % (where, order, args))

    pages = 0
    total_pers = 0
    total_cards = 0
    batches = []
    opers = []
    clients = []
    filenames = []
    statuses = []
    persstatuses = []
    perstypes = []
    xml = ''

    # ----------------------
    # Условие отбора (state)
    # ----------------------

    state = get_request_item('state')
    IsState = state and state != 'R0' and True or False

    args.update({
        'state' : ('State', state)
    })

    confirmed_pers_id = 0

    # ======================
    # Выборка данных журнала
    # ======================

    if engine != None:

        # ---------------------------------------------------
        # Поиск партии по ID или номеру ТЗ (IsSearchByNumber)
        # ---------------------------------------------------
        
        if IsSearchByNumber:
            pers_id = 0

            cursor = engine.runQuery('cards.pers-batch-opers', columns=('PersBatchID',), where='TID=%s' % TZ, top=1)
            for n, row in enumerate(cursor):
                pers_id = row[0]

            if not pers_id:
                cursor = engine.runQuery(default_template, columns=('TID',), where=where)
                for n, row in enumerate(cursor):
                    pers_id = row[0]

            where = 'TID=%s' % pers_id

        # ---------------------------------------------------
        # Кол-во записей по запросу в журнале (total_pers)
        # ---------------------------------------------------

        cursor = engine.runQuery(default_template, columns=('count(*)', 'sum(BQty)',), where=where)
        if cursor:
            total_pers, total_cards = cursor[0]
            if total_cards is None:
                total_cards = 0

        if IsState:
            top = 1000
        if command == 'export':
            top = 10000

        # ================
        # Заказы (batches)
        # ================

        cursor = engine.runQuery(default_template, top=top, where=where, order='%s' % order, as_dict=True,
                                 encode_columns=('Client','FName','PersType','Status','PersStatus',),
                                 columns=database_config[default_template].get('export'))
        if cursor:
            IsSelected = False
            
            for n, row in enumerate(cursor):
                x = row['Status'].lower()

                state_error = 'брак' in x
                state_ready = 'отправлен отчет' in x

                if state == 'R1' and (state_ready or state_error):
                    continue
                if state == 'R2' and not state_ready:
                    continue
                if state == 'R3' and not state_error:
                    continue

                if not IsState and offset and n < offset:
                    continue

                if pers_id:
                    if not confirmed_pers_id and pers_id == row['TID']:
                        confirmed_pers_id = pers_id
                    if not file_name and pers_id == row['TID']:
                        file_name = row['FName']

                    if pers_id == row['TID']:
                        row['selected'] = 'selected'
                        IsSelected = True
                else:
                    row['selected'] = ''

                row['TZ'] = row['TZ'] and '<a class="persolink" href="/bankperso?sidebar=0&search=%s" target="_self">%s</a>' % (
                    row['TZ'], row['TZ']) or ''

                for x in row:
                    if not row[x] or str(row[x]).lower() == 'none':
                        row[x] = ''

                row['Error'] = state_error
                row['Ready'] = state_ready
                row['StatusDate'] = getDate(row['StatusDate'])
                row['BQty'] = str(row['BQty']).isdigit() and int(row['BQty']) or 0
                row['PQty'] = str(row['PQty']).isdigit() and int(row['PQty']) or 0
                row['id'] = row['TID']

                batches.append(row)

            if line > len(batches):
                line = 1

            if not IsSelected and len(batches) >= line:
                row = batches[line-1]
                confirmed_pers_id = pers_id = row['id'] = row['TID']
                file_name = row['FName']
                row['selected'] = 'selected'

        if len(batches) == 0:
            file_name = ''
            pers_id = 0
        elif confirmed_pers_id != pers_id or not pers_id:
            row = batches[0]
            pers_id = row['TID']
            file_name = row['FName']
        elif not confirmed_pers_id:
            pers_id = 0
            file_name = ''

        if IsState and batches:
            total_pers = len(batches)
            total_cards = 0
            batches = batches[offset:offset+per_page]
            IsSelected = False

            for n, row in enumerate(batches):
                if pers_id == row['TID']:
                    row['selected'] = 'selected'
                    file_name = row['FName']
                    IsSelected = True
                else:
                    row['selected'] = ''
                total_cards += row['BQty']

            if not IsSelected:
                row = batches[0]
                row['selected'] = 'selected'
                pers_id = row['TID']
                file_name = row['FName']

        if total_pers:
            pages = int(total_pers / per_page)
            if pages * per_page < total_pers:
                pages += 1

        # ================
        # Операции (opers)
        # ================

        if pers_id:
            opers, oper_id = _get_opers(pers_id, oper_id=oper_id, pers_tz=pers_tz, perstype=PersTypeID)

        # ----------------------------------------------------------------
        # Справочники фильтра запросов (clients, perstypes, statuses)
        # ----------------------------------------------------------------

        clients.append(DEFAULT_UNDEFINED)
        cursor = engine.runQuery('cards.clients', order='Client', distinct=True, encode_columns=(0,))
        clients += [x[0] for x in cursor]
        """
        filenames.append(DEFAULT_UNDEFINED)
        items = []
        if Client:
            items.append("Client='%s'" % Client)
        if StatusDate:
            items.append("StatusDate>='%s'" % getDate(getDate(StatusDate, LOCAL_EASY_DATESTAMP, is_date=True), DATE_STAMP))
        where = ' AND '.join(items)
        cursor = engine.runQuery('cards.files', columns=('FileName',), where=where, order='FileName', encode_columns=(0,))
        filenames += [x[0] for x in cursor]
        """
        statuses.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery('cards.statuses', order='CName', distinct=True, encode_columns=(1,))
        statuses += [(x[0], x[1]) for x in cursor]

        persstatuses.append(DEFAULT_UNDEFINED)
        cursor = engine.runQuery('cards.persstatuses', order='CName', encode_columns=(0,))
        persstatuses += [x[0] for x in cursor]

        perstypes.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery('cards.perstypes', order='CName', distinct=True, encode_columns=(1,))
        perstypes += [(x[0], x[1]) for x in cursor]

        engine.dispose()

    # ----------------------
    # Условия отбора заказов
    # ----------------------

    states = [
        ('R0', DEFAULT_UNDEFINED),
        ('R1', 'первичная'),
        ('R2', 'брак'),
    ]

    refresh(pers_id=pers_id)

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
    base = 'cards?%s' % query_string

    per_page_options = (5, 10, 20, 30, 40, 50, 100,)
    if is_admin:
        per_page_options += (250, 500)

    is_extra = has_request_item(EXTRA_)

    modes = [(n, '%s' % default_view['headers'][x][0]) for n, x in enumerate(default_view['columns'])]
    sorted_by = default_view['headers'][default_view['columns'][current_sort]]

    pagination = {
        'total'             : '%s / %s' % (total_pers, total_cards),
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

    loader = '/cards/loader'

    if is_extra:
        pagination['extra'] = 1
        loader += '?%s' % EXTRA_

    kw.update({
        'base'              : base,
        'page_title'        : gettext('WebPerso Cards Batch View'),
        'header_subclass'   : 'left-header',
        'show_flash'        : True,
        'loader'            : loader,
        'semaphore'         : initDefaultSemaphore(template='cards.semaphore'),
        'args'              : args,
        'current_file'      : (pers_id, getBatchInfo(pers_id), oper_id, pers_tz),
        'navigation'        : get_navigation(),
        'config'            : database_config,
        'pagination'        : pagination,
        'batches'           : batches,
        'opers'             : opers,
        'clients'           : clients,
        'filenames'         : filenames,
        'statuses'          : statuses,
        'persstatuses'      : persstatuses,
        'perstypes'         : perstypes,
        'states'            : states,
        'xml'               : xml,
        'search'            : search or '',
    })

    sidebar = get_request_item('sidebar')
    if sidebar:
        kw['sidebar']['state'] = int(sidebar)

    return kw

## ==================================================== ##

@cards.route('/', methods = ['GET'])
@cards.route('/cards', methods = ['GET','POST'])
@login_required
def index():
    debug, kw = init_response('WebPerso Cards Admin Page')
    kw['product_version'] = product_version

    is_admin = current_user.is_administrator()
    is_operator = current_user.is_operator()

    command = get_request_item('command')
    
    pers_id = int(get_request_item('pers_id') or '0')
    oper_id = int(get_request_item('oper_id') or '0')

    if IsDebug:
        print('--> command:%s, pers_id:%s, oper_id:%s' % (command, pers_id, oper_id))

    refresh(pers_id=pers_id)

    IsMakePageDefault = True
    logsearch = ''
    tagsearch = ''
    info = ''

    errors = []

    if command and command.startswith('admin'):
        command = command.split(DEFAULT_HTML_SPLITTER)[1]

        if not is_operator:
            flash('You have not permission to run this action!')
            command = ''
        
        elif command == 'activate':
            selected_pers_ids = get_request_item('selected_pers_ids') or ''
            info = 'selected_pers_ids:%s' % selected_pers_ids

            # -------------------------
            # Activate selected batches
            # -------------------------

            for pers_id in selected_pers_ids.split(DEFAULT_HTML_SPLITTER):
                rows, error_msg = engine.runProcedure('cards.activate', pers_id=pers_id, no_cursor=True, with_error=True)

                if error_msg:
                    errors.append(error_msg)

        elif command == 'reject':
            selected_pers_ids = get_request_item('selected_pers_ids') or ''
            info = 'selected_pers_ids:%s' % selected_pers_ids

            # --------------------------------------
            # Reject activation for selected batches
            # --------------------------------------

            for pers_id in selected_pers_ids.split(DEFAULT_HTML_SPLITTER):
                rows, error_msg = engine.runProcedure('cards.reject', pers_id=pers_id, no_cursor=True, with_error=True)

                if error_msg:
                    errors.append(error_msg)

        if IsDebug:
            print('--> %s' % info)

        if IsTrace:
            print_to(errorlog, '--> command:%s' % command)

    kw['errors'] = '<br>'.join(errors)
    kw['OK'] = ''

    try:
        if IsMakePageDefault:
            kw = _make_page_default(kw)

        if IsTrace:
            print_to(errorlog, '--> cards:%s %s %s %s' % ( \
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

        elif command == 'reject':
            if kw['errors']:
                flash('Reject for the given batch is not done!')
            else:
                kw['OK'] = gettext('Message: Reject performed successfully.')

        elif command == 'export':
            return _make_xls_content(_make_export(kw), 'Журнал персонализации')

    return make_response(render_template('cards.html', debug=debug, **kw))

@cards.after_request
def make_response_no_cached(response):
    if engine is not None:
        engine.close()
    # response.cache_control.no_store = True
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response

@cards.route('/cards/loader', methods = ['GET', 'POST'])
@login_required
def loader():
    exchange_error = ''
    exchange_message = ''

    is_extra = has_request_item(EXTRA_)

    action = get_request_item('action') or default_action
    selected_menu_action = get_request_item('selected_menu_action') or action != default_action and action or '701'

    response = {}

    pers_id = int(get_request_item('pers_id') or '0')
    oper_id = int(get_request_item('oper_id') or '0')
    perstype = int(get_request_item('perstype') or '0')

    refresh(pers_id=pers_id)

    if IsDebug:
        print('--> action:%s pers_id:%s oper_id:%s perstype:%s' % (action, pers_id, oper_id, perstype))

    if IsTrace:
        print_to(errorlog, '--> loader:%s %s [%s:%s:%s:%s]' % (action, current_user.login, pers_id, oper_id, perstype, selected_menu_action))

    batch_id = requested_batch and requested_batch['BatchID'] or None

    currentfile = None
    opers = []
    config = None

    data = ''
    number = ''
    columns = []
    total = None

    props = None
    errors = None

    try:
        if action == default_action:
            opers, oper_id = _get_opers(pers_id, perstype=perstype)
            currentfile = [requested_batch.get('TID'), getBatchInfo(pers_id), oper_id]
            config = _get_view_columns(database_config['cards.pers-batch-opers'])
            action = selected_menu_action

        if not action:
            pass

        elif action == '701':
            data, props = getTabOperParams(pers_id, oper_id)

        elif action == '702':
            """
            view = database_config['cards.batches-log']
            columns = _get_view_columns(view)
            data = getTabLogs(batch_id)
            """
            view = database_config['cards.batch-opers-log']
            columns = _get_view_columns(view)
            data = getTabOperLogs(pers_id)

        elif action == '703':
            view = database_config['cards.batch-units']
            columns = _get_view_columns(view)
            data = getTabUnits(batch_id)

        elif action == '704':
            view = database_config['cards.batch-params']
            columns = _get_view_columns(view)
            data = getTabParams(batch_id)

        elif action == '705':
            data = getFileBatches()

        elif action == '710':
            items = get_request_item('selected-items').split(':') or []

            if IsTrace:
                print_to(errorlog, '--> activate items:%s' % items)

            currentfile = [requested_batch.get('TID'), getBatchInfo(pers_id), oper_id]
            data, props, errors = activateBatches(items)

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
        'pers_id'          : pers_id,
        'oper_id'          : oper_id,
        # ----------------------------------------------
        # Default Lines List (sublines equal as opers)
        # ----------------------------------------------
        'currentfile'      : currentfile,
        'sublines'         : opers,
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
