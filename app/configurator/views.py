# -*- coding: utf-8 -*-

import re
import random

from config import (
     CONNECTION, IsDebug, IsDeepDebug, IsTrace, IsForceRefresh, errorlog, print_to, print_exception,
     default_unicode, default_encoding, default_iso
     )

from . import configurator

from ..settings import *
from ..database import database_config, BankPersoEngine
from ..utils import (
     getToday, getDate, checkDate, indentXMLTree, isIterable, makeXLSContent, 
     getWhereFilter, checkPaginationRange
     )

from ..semaphore.views import initDefaultSemaphore

from .references import *

##  ======================================
##  Configurator View Presentation Package
##  ======================================

default_page = 'configurator'
default_action = '600'
engine = None

def before(f):
    def wrapper(**kw):
        global engine
        engine = BankPersoEngine(current_user, connection=CONNECTION['configurator'])
        return f(**kw)
    return wrapper

@before
def refresh(**kw):
    return

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

    try:
        args = { \
            'client'    : ('ClientID', int(get_request_item('client') or '0')),
            'filetype'  : ('FileTypeID', int(get_request_item('filetype') or '0')),
            'batchtype' : ('BatchTypeID', int(get_request_item('batchtype') or '0')),
            'tag'       : ('TName', get_request_item('tag')),
            'tagvalue'  : ('TValue', get_request_item('tagvalue')),
        }
    except:
        args = { \
            'client'    : ('ClientID', 0),
            'filetype'  : ('FileTypeID', 0),
            'batchtype' : ('BatchTypeID', 0),
            'tag'       : ('TName', ''),
            'tagvalue'  : ('TValue', ''),
        }
        flash('Please, update the page by Ctrl-F5!')

    return args

def _get_file(file_id):
    default_config_item = 'configurator-files'
    default_view = database_config[default_config_item]

    where = 'TID=%s' % file_id
    
    cursor = engine.runQuery(default_config_item, columns=default_view['export'], top=1, where=where, as_dict=True)
    
    return cursor and cursor[0]

def _get_batches(file_id, batch_id=None):
    batches = []
    selected_id = None

    where = 'FileTypeID=%s%s' % (
        file_id, 
        batch_id and (' and BatchTypeID=%s' % batch_id) or '')

    cursor = engine.runQuery('configurator-batches', where=where, order='SortIndex', as_dict=True)
    if cursor:
        IsSelected = False
        
        for n, row in enumerate(cursor):
            row['BatchType'] = row['BatchType'].encode(default_iso).decode(default_encoding)
            if 'CreateType' in row:
                row['CreateType'] = row['CreateType'].encode(default_iso).decode(default_encoding)
            if 'ResultType' in row:
                row['ResultType'] = row['ResultType'].encode(default_iso).decode(default_encoding)

            row['id'] = row['TID']

            if (batch_id and batch_id == row['TID']):
                row['selected'] = 'selected'
                IsSelected = True
            else:
                row['selected'] = ''

            batches.append(row)

        if not IsSelected:
            row = batches[0]
            selected_id = row['id']
            row['selected'] = 'selected'

    return batches, selected_id

def _get_processes(file_id, **kw):
    processes = []

    BatchTypeID = kw.get('filter')[0] or None
    where = 'FileTypeID=%s%s' % (
        file_id, 
        BatchTypeID and (' and BatchTypeID=%s' % BatchTypeID) or ''
        )

    cursor = engine.runQuery('configurator-processes', where=where, order='BatchTypeID', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('BatchType', 'CurrFileStatus', 'NextFileStatus', 'CloseFileStatus', 'ActivateBatchStatus', 'ARMBatchStatus', 'Memo',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            processes.append(row)

    return processes

def _get_opers(file_id, **kw):
    opers = []

    BatchTypeID = kw.get('filter')[0] or None
    where = 'FileTypeID=%s%s' % (
        file_id, 
        BatchTypeID and (' and BatchTypeID=%s' % BatchTypeID) or ''
        )

    cursor = engine.runQuery('configurator-opers', where=where, order='BatchTypeID', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('BatchType', 'OperTypeName', 'OperType',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            opers.append(row)

    return opers

def _get_operparams(file_id, **kw):
    operparams = []

    BatchTypeID = kw.get('filter')[0] or None
    where = 'FileTypeID=%s%s' % (
        file_id, 
        BatchTypeID and (' and BatchTypeID=%s' % BatchTypeID) or ''
        )

    cursor = engine.runQuery('configurator-operparams', where=where, order='BatchTypeID', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('BatchType', 'OperTypeName', 'OperType', 'PName', 'PValue', 'Comment',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            operparams.append(row)

    return operparams

def _get_filters(file_id, **kw):
    filters = []

    BatchTypeID = kw.get('filter')[0] or None
    tag = kw.get('filter')[1] or None
    where = 'FileTypeID=%s%s%s' % (
        file_id, 
        BatchTypeID and (' and BatchTypeID=%s' % BatchTypeID) or '',
        tag and (" and TName='%s'" % tag) or '',
        )

    cursor = engine.runQuery('configurator-filters', where=where, order='BatchTypeID, TName', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('BatchType', 'TName', 'CriticalValues',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            filters.append(row)

    return filters

def _get_tags(file_id, **kw):
    tags = []

    tag = kw.get('filter')[1] or None
    where = 'FileTypeID=%s%s' % (
        file_id,
        tag and (" and TName='%s'" % tag) or '',
        )

    cursor = engine.runQuery('configurator-tags', where=where, order='TName', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('TName', 'TMemo',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            tags.append(row)

    return tags

def _get_tagvalues(file_id, **kw):
    tagvalues = []

    tag = kw.get('filter')[1] or None
    tagvalue = kw.get('filter')[2] or None
    where = 'FileTypeID=%s%s%s' % (
        file_id,
        tag and (" and TName='%s'" % tag) or '',
        tagvalue and (" and TValue='%s'" % tagvalue) or '',
        )

    cursor = engine.runQuery('configurator-tagvalues', where=where, order='TName, TValue', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('TName', 'TValue',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            tagvalues.append(row)

    return tagvalues

def _get_tzs(file_id, **kw):
    tzs = []

    tag = kw.get('filter')[1] or None
    tagvalue = kw.get('filter')[2] or None
    where = 'FileTypeID=%s%s%s' % (
        file_id,
        tag and (" and TName='%s'" % tag) or '',
        tagvalue and (" and TValue='%s'" % tagvalue) or '',
        )

    cursor = engine.runQuery('configurator-tzs', where=where, order='TName, TValue, PSortIndex', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('TName', 'TValue', 'PName', 'PValue', 'Comment',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            tzs.append(row)

    return tzs

def _get_erpcodes(file_id, **kw):
    erpcodes = []

    BatchTypeID = kw.get('filter')[0] or None
    tag = kw.get('filter')[1] or None
    tagvalue = kw.get('filter')[2] or None
    where = 'FileTypeID=%s%s%s%s' % (
        file_id,
        BatchTypeID and (' and BatchTypeID=%s' % BatchTypeID) or '',
        tag and (" and TName='%s'" % tag) or '',
        tagvalue and (" and TValue='%s'" % tagvalue) or '',
        )

    cursor = engine.runQuery('configurator-erpcodes', where=where, order='BatchTypeID, TName, TValue', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('TName', 'TValue',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            erpcodes.append(row)

    return erpcodes

def _get_materials(file_id, **kw):
    materials = []

    BatchTypeID = kw.get('filter')[0] or None
    tag = kw.get('filter')[1] or None
    tagvalue = kw.get('filter')[2] or None
    where = 'FileTypeID=%s%s%s%s' % (
        file_id,
        BatchTypeID and (' and BatchTypeID=%s' % BatchTypeID) or '',
        tag and (" and TName='%s'" % tag) or '',
        tagvalue and (" and TValue='%s'" % tagvalue) or '',
        )

    cursor = engine.runQuery('configurator-materials', where=where, order='BatchTypeID, TName, TValue, PName', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('BatchType', 'TName', 'TValue', 'PName',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            materials.append(row)

    return materials

def _get_posts(file_id, **kw):
    posts = []

    tag = kw.get('filter')[1] or None
    tagvalue = kw.get('filter')[2] or None
    where = 'FileTypeID=%s%s%s' % (
        file_id,
        tag and (" and TName='%s'" % tag) or '',
        tagvalue and (" and TValue='%s'" % tagvalue) or '',
        )

    cursor = engine.runQuery('configurator-posts', where=where, order='TName, TValue, PName', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('TName', 'TValue', 'PName', 'PValue', 'Comment',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            posts.append(row)

    return posts

def _get_processparams(file_id, **kw):
    params = []

    tag = kw.get('filter')[1] or None
    tagvalue = kw.get('filter')[2] or None
    where = 'FileTypeID=%s%s%s' % (
        file_id,
        tag and (" and TName='%s'" % tag) or '',
        tagvalue and (" and TValue='%s'" % tagvalue) or '',
        )

    cursor = engine.runQuery('configurator-processparams', where=where, order='TName, TValue, PName', as_dict=True)
    if cursor:
        for n, row in enumerate(cursor):
            for key in ('TName', 'TValue', 'PName', 'PValue', 'Comment',):
                row[key] = row[key] and row[key].encode(default_iso).decode(default_encoding) or ''
            #row['PSortIndex'] = str(row['PSortIndex'] not is None and row['PSortIndex']) or ''
            params.append(row)

    return params

## ==================================================== ##

def getTabBatchInfo(batch_id):
    data = []
    number = str(batch_id)

    try:
        if batch_id:
            params = "%s, 1, ''" % (batch_id)
            cursor = engine.runQuery('configurator-batchinfo', as_dict=True, params=params)
            for n, row in enumerate(cursor):
                row['PName'] = row['PName'].encode(default_iso).decode(default_encoding)
                row['PValue'] = row['PValue'].encode(default_iso).decode(default_encoding)

                if row['PType'] == -1:
                    row['PName'] = '<nobr>%s</nobr>' % row['PName']
                    row['PValue'] = '<span class="counting">%s</span>' % row['PValue']

                data.append(row)
    except:
        print_exception()

    batch = {'id':batch_id, 'number':number}

    return number and data or [], batch

def getTabProcesses(file_id, **kw):
    return _get_processes(file_id, **kw)

def getTabOpers(file_id, **kw):
    return _get_opers(file_id, **kw)

def getTabOperParams(file_id, **kw):
    return _get_operparams(file_id, **kw)

def getTabFilters(file_id, **kw):
    return _get_filters(file_id, **kw)

def getTabTags(file_id, **kw):
    return _get_tags(file_id, **kw)

def getTabTagValues(file_id, **kw):
    return _get_tagvalues(file_id, **kw)

def getTabTZs(file_id, **kw):
    return _get_tzs(file_id, **kw)

def getTabERPCodes(file_id, **kw):
    return _get_erpcodes(file_id, **kw)

def getTabMaterials(file_id, **kw):
    return _get_materials(file_id, **kw)

def getTabPosts(file_id, **kw):
    return _get_posts(file_id, **kw)

def getTabProcessParams(file_id, **kw):
    return _get_processparams(file_id, **kw)

## ==================================================== ##

def getReference(mode):
    reference = reference_factory.get(mode)
    if reference is None:
        return [], None, None, None
    ob = reference(engine)
    data = ob.getItems()
    props = {'id' : ob.id, 'value' : ob.value, 'mode' : mode, 'table' : ob.table, 'title' : ob.title}
    return data, props, ob.columns, ob.config

## ==================================================== ##

def _make_page_default(kw):
    file_id = int(kw.get('file_id'))
    batch_id = int(kw.get('batch_id'))

    is_admin = current_user.is_administrator()

    args = _get_page_args()

    file_name = ''
    filter = ''
    qs = ''

    # -------------------------------
    # Представление БД (default_view)
    # -------------------------------

    default_view = database_config['configurator-files']

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
    IsSearchEvent = False
    items = []

    if search:
        items.append("FileType like '%%%s%%'" % search)

    # -------------
    # Фильтр (args)
    # -------------

    ClientID = FileTypeID = BatchTypeID = None
    TagName = args['tag'][1]

    if args:
        for key in args:
            name, value = args[key]
            id = None
            if name == 'ClientID':
                id = ClientID = value or None
            elif name == 'FileTypeID':
                id = FileTypeID = value or None
            elif name == 'BatchTypeID':
                id = BatchTypeID = value or None
                
            if id and name in ('ClientID', 'FileTypeID',):
                items.append("%s=%s" % (name, id))
            
            if value:
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
        order = 'Client, FileType'

    if IsDebug:
        print('--> where:%s %s, order:%s' % (where, args, order))

    pages = 0
    total_files = 0
    total_batches = 0
    files = []
    batches = []
    clients = []
    filetypes = []
    batchtypes = []
    tags = []
    tagvalues = []

    confirmed_file_id = 0

    # ======================
    # Выборка данных журнала
    # ======================

    if engine != None:

        # -------------------------------------------------
        # Кол-во записей по запросу в журнале (total_files)
        # -------------------------------------------------

        cursor = engine.runQuery('configurator-files', columns=('count(*)',), where=where)
        if cursor:
            total_files = cursor[0][0]

        # ===================
        # Типы файлов (files)
        # ===================

        cursor = engine.runQuery('configurator-files', columns=database_config['configurator-files']['columns'], 
                                 top=top, where=where, order=order, as_dict=True,
                                 )
        if cursor:
            IsSelected = False

            for n, row in enumerate(cursor):
                if offset and n < offset:
                    continue

                if file_id:
                    if not confirmed_file_id and file_id == row['TID']:
                        confirmed_file_id = file_id
                    if not file_name and file_id == row['TID']:
                        file_name = row['FileType']

                    if file_id == row['TID']:
                        row['selected'] = 'selected'
                        IsSelected = True
                else:
                    row['selected'] = ''

                for x in row:
                    if not row[x] or str(row[x]).lower() == 'none':
                        row[x] = ''

                row['id'] = row['TID']
                row['Client'] = row['Client'].encode(default_iso).decode(default_encoding)

                files.append(row)

            if line > len(files):
                line = 1

            if not IsSelected and len(files) >= line:
                row = files[line-1]
                confirmed_file_id = file_id = row['id'] = row['TID']
                file_name = row['FileType']
                row['selected'] = 'selected'

        if len(files) == 0:
            file_id = 0
            file_name = ''
            batch_id = 0
        elif confirmed_file_id != file_id or not file_id:
            row = files[0]
            file_id = row['TID']
            file_name = row['FileType']
        elif not confirmed_file_id:
            file_id = 0
            file_name = ''

        if total_files:
            pages = int(total_files / per_page)
            if pages * per_page < total_files:
                pages += 1

        # =====================
        # Типы партий (batches)
        # =====================

        cursor = engine.runQuery('configurator-batches', columns=('count(*)',), where=where)
        if cursor:
            total_batches = cursor[0][0]

        if file_id:
            batches, batch_id = _get_batches(file_id, batch_id=BatchTypeID)

        # ------------------------------------------------------------------------------
        # Справочники фильтра запросов (clients, filetypes, batchtypes, tags, tagvalues)
        # ------------------------------------------------------------------------------

        clients.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery('configurator-clients', order='CName', distinct=True)
        clients += [(x[0], x[1].encode(default_iso).decode(default_encoding)) for x in cursor]

        filetypes.append((0, DEFAULT_UNDEFINED,))
        where = ClientID and ("ClientID=%s" % ClientID) or ''
        cursor = engine.runQuery('configurator-filetypes', where=where, order='CName', distinct=True)
        filetypes += [(x[0], x[1].encode(default_iso).decode(default_encoding)) for x in cursor]

        batchtypes.append((0, DEFAULT_UNDEFINED,))
        cursor = engine.runQuery('configurator-batchtypes', order='CName', distinct=True)
        batchtypes += [(x[0], x[1].encode(default_iso).decode(default_encoding)) for x in cursor]

        tags.append(DEFAULT_UNDEFINED)
        cursor = engine.runQuery('configurator-tags', columns=('TName',), order='TName', distinct=True)
        tags += [x[0].encode(default_iso).decode(default_encoding) for x in cursor]

        tagvalues.append(DEFAULT_UNDEFINED)
        where = file_id and ('FileTypeID=%s%s' % (file_id, TagName and (' and TName=\'%s\'' % TagName) or '')) or ''
        cursor = engine.runQuery('configurator-tagvalues', columns=('TValue',), where=where, order='TValue', distinct=True)
        tagvalues += [x[0].encode(default_iso).decode(default_encoding) for x in cursor]

        engine.dispose()

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
    base = 'configurator?%s' % query_string

    modes = [(n, '%s' % default_view['headers'][x][0]) for n, x in enumerate(default_view['columns'])]
    sorted_by = default_view['headers'][default_view['columns'][current_sort]]

    pagination = {
        'total'             : '%s / %s' % (total_files, total_batches),
        'per_page'          : per_page,
        'pages'             : pages,
        'current_page'      : page,
        'iter_pages'        : tuple(iter_pages),
        'has_next'          : page < pages,
        'has_prev'          : page > 1,
        'per_page_options'  : (5,10,20,30,40,50,100),
        'link'              : '%s%s%s%s' % (base, filter,
                                           (search and "&search=%s" % search) or '',
                                           (current_sort and "&sort=%s" % current_sort) or ''
                                           ),
        'sort'              : {
            'modes'         : modes,
            'sorted_by'     : sorted_by,
            'current_sort'  : current_sort,
        },
        'position'          : '%d:%d:%d:%d' % (page, pages, per_page, line),
    }

    kw.update({
        'base'              : base,
        'page_title'        : gettext('WebPerso Configurator View'),
        'header_subclass'   : 'left-header',
        'loader'            : '/configurator/loader',
        'semaphore'         : initDefaultSemaphore(),
        'args'              : args,
        'current_file'      : (file_id, file_name, batch_id),
        'navigation'        : get_navigation(),
        'config'            : database_config,
        'pagination'        : pagination,
        'files'             : files,
        'batches'           : batches,
        'clients'           : clients,
        'filetypes'         : filetypes,
        'batchtypes'        : batchtypes,
        'tags'              : tags,
        'tagvalues'         : tagvalues,
        'search'            : search or '',
    })

    sidebar = get_request_item('sidebar')
    if sidebar:
        kw['sidebar']['state'] = int(sidebar)

    return kw

## ==================================================== ##

@configurator.route('/', methods = ['GET'])
@configurator.route('/configurator', methods = ['GET','POST'])
@login_required
def index():
    debug, kw = init_response('WebPerso Configurator Page')
    kw['product_version'] = product_version

    command = get_request_item('command')

    if IsDebug:
        print('--> command:%s, file_id:%s, batch_id:%s' % (
            command,
            kw.get('file_id'),
            kw.get('batch_id')
        ))

    refresh()

    errors = []

    if command and command.startswith('admin'):
        pass

    kw['errors'] = '<br>'.join(errors)
    kw['OK'] = ''

    try:
        kw = _make_page_default(kw)

        if IsTrace:
            print_to(errorlog, '--> configurator:%s %s %s' % (command, current_user.login, str(kw.get('current_file')),), request=request)
    except:
        print_exception()

    kw['vsc'] = (IsDebug or IsIE() or IsForceRefresh) and ('?%s' % str(int(random.random()*10**12))) or ''

    if command and command.startswith('admin'):
        pass

    elif command == 'export':
        columns = kw['config']['files']['export']
        rows = []
        for data in kw['files']:
            row = []
            for column in columns:
                if column == 'FinalMessage':
                    continue
                v = data[column]
                if 'Date' in column:
                    v = re.sub(r'\s+', ' ', re.sub(r'<.*?>', ' ', v))
                row.append(v)

            rows.append(row)

        rows.insert(0, columns)

        xls = makeXLSContent(rows, 'Конфигуратор BankPerso', True)

        response = make_response(xls)
        response.headers["Content-Disposition"] = "attachment; filename=configurator.xls"
        return response

    return make_response(render_template('configurator.html', debug=debug, **kw))

@configurator.after_request
def make_response_no_cached(response):
    if engine is not None:
        engine.close()
    # response.cache_control.no_store = True
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response

@configurator.route('/configurator/loader', methods = ['GET', 'POST'])
@login_required
def loader():
    exchange_error = ''
    exchange_message = ''

    refresh()

    action = get_request_item('action') or default_action
    selected_menu_action = get_request_item('selected_menu_action') or action != default_action and action or '601'

    response = {}

    file_id = int(get_request_item('file_id') or '0')
    batch_id = int(get_request_item('batch_id') or '0')

    filter = (int(get_request_item('filter-batchtype') or '0'),
              get_request_item('filter-tag'),
              get_request_item('filter-tagvalue'),
              )

    params = get_request_item('params') or ''

    if IsDebug:
        print('--> action:%s file_id:%s batch_id:%s filter:%s:%s:%s params:[%s]' % (
            action, file_id, batch_id, filter[0], filter[1], filter[2], params,
        ))

    if IsTrace:
        print_to(errorlog, '--> loader:%s %s [%s:%s:%s] params:%s' % ( 
            action, current_user.login, file_id, batch_id, selected_menu_action, params
            ))

    currentfile = None
    batches = []
    config = None

    data = ''
    number = ''
    columns = []

    props = None

    #ob = DicClients(engine)
    #errors = ob.addItem([('value', 'xxx'),])
    #errors = ob.updateItem(388, [('value', 'x1'),])
    #errors = ob.removeItem(388)
    #clients = ob.getItems()

    try:
        if action == default_action:
            file = _get_file(file_id)
            batches, batch_id = _get_batches(file_id)
            currentfile = [file['TID'], file['FileType'], batch_id]
            config = _get_view_columns(database_config['configurator-batches'])
            action = selected_menu_action

        if not action:
            pass

        elif action == '601':
            data, props = getTabBatchInfo(batch_id)

        elif action == '602':
            columns = _get_view_columns(database_config['configurator-processes'])
            data = getTabProcesses(file_id, filter=filter)

        elif action == '603':
            columns = _get_view_columns(database_config['configurator-opers'])
            data = getTabOpers(file_id, filter=filter)

        elif action == '604':
            columns = _get_view_columns(database_config['configurator-operparams'])
            data = getTabOperParams(file_id, filter=filter)

        elif action == '605':
            columns = _get_view_columns(database_config['configurator-filters'])
            data = getTabFilters(file_id, filter=filter)

        elif action == '606':
            columns = _get_view_columns(database_config['configurator-tags'])
            data = getTabTags(file_id, filter=filter)

        elif action == '607':
            columns = _get_view_columns(database_config['configurator-tagvalues'])
            data = getTabTagValues(file_id, filter=filter)

        elif action == '608':
            columns = _get_view_columns(database_config['configurator-tzs'])
            data = getTabTZs(file_id, filter=filter)

        elif action == '609':
            columns = _get_view_columns(database_config['configurator-erpcodes'])
            data = getTabERPCodes(file_id, filter=filter)

        elif action == '610':
            columns = _get_view_columns(database_config['configurator-materials'])
            data = getTabMaterials(file_id, filter=filter)

        elif action == '611':
            columns = _get_view_columns(database_config['configurator-posts'])
            data = getTabPosts(file_id, filter=filter)

        elif action == '612':
            columns = _get_view_columns(database_config['configurator-processparams'])
            data = getTabProcessParams(file_id, filter=filter)

        elif action == '620':
            mode = params.split(DEFAULT_HTML_SPLITTER)[1]
            data, props, columns, config = getReference(mode)

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
        'total'            : len(data),
        'data'             : data,
        'props'            : props,
        'columns'          : columns,
    })

    return jsonify(response)

