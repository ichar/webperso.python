# -*- coding: utf-8 -*-

__all__ = ['DicClients', 'reference_factory',]

import types
import re
from operator import itemgetter

from flask.ext.babel import gettext

from config import (
     IsDebug, IsDeepDebug, IsTrace, IsPrintExceptions, errorlog, print_to, print_exception,
     default_unicode, default_encoding, default_iso,
     )

from ..database import getReferenceConfig
from ..booleval import Token, new_token
from ..utils import isIterable

_UNDEFINED_ERROR = 2
_ERROR = 1
_WARNING = 0

##  ========================
##  Abstract Reference Class
##  ========================

def addSqlFilterItem(where, key, value, fields, operator=None):
    if not key:
        return ''
    field = fields.get(key)
    if field is None or value is None:
        return ''
    selector = field.get('selector')
    return selector and value and ('%s%s' % (where and (operator or ' AND ') or '', selector % str(value))) or ''

def getSqlOrder(fields):
    orders = []
    for name in fields:
        field = fields[name]
        if field.get('order'):
            index = 0
            order = field['order']
            if '-' in order:
                x = order.split('-')
                index = x[0] and x[0].isdigit() and int(x[0]) or 0
                order = x[1]

            orders.append((name, index, order or 'asc'))

    return orders and \
        ', '.join(['%s %s' % (name, order) for name, index, order in sorted(orders, key=itemgetter(1), reverse=False)]) or ''


class AbstractReference(object):
    
    def __init__(self, engine, view, id=None):
        self.engine = engine
        self.view = view

        self._id = id or 'TID'
        self._config = getReferenceConfig(self.view)

        self._fields = self._config.get('fields')
        self._table = self._config.get('view')

    def _is_ready(self):
        return self.engine and self._table and True or False

    def _get_errors(self, errors):
        return [x[1] for x in sorted(errors, key=itemgetter(0), reverse=True)]

    @property
    def id(self):
        return self._id

    @property
    def value(self):
        return 'CName'

    @property
    def table(self):
        return self._table

    @property
    def config(self):
        return self._config

    @property
    def columns(self):
        return self._config['columns']

    @property
    def sorted_columns(self):
        return self.columns

    @property
    def headers(self):
        return self._config['headers']

    @property
    def fields(self):
        return self._config['fields']

    @property
    def title(self):
        pass

    @property
    def searchable(self):
        """ Searchable Text fields list or single field name """
        return None

    @property
    def numeric(self):
        pass

    @property
    def editable_columns(self):
        pass

    @property
    def has_links(self):
        return False

    def _check_search_query(self, value):
        q = []
        if isinstance(value, str):
            #
            # Query items can be `Token` class instance such as: (bank || client) && citi
            #
            token = new_token()
            token._init_state(value)
            tokens = token.get_token()

            if IsDeepDebug:
                print('--> %s' % repr(tokens))

            n = 1
            for x in tokens:
                if callable(x) or isinstance(x, types.FunctionType):
                    item = ('operator%s' % n, x(1,0) and ' OR ' or ' AND ')
                elif x in '()':
                    item = ('_%s' % n, x)
                    n += 1
                else:
                    if x.isdigit():
                        item = (self.numeric or self.id, int(x))
                    else:
                        item = (self.searchable or self.value, x)

                q.append(item)

            if IsDeepDebug:
                print('--> %s' % repr(q))

        elif isinstance(value, list):
            #
            # Query is a list: [(<key>, <value>),...]
            #
            q = value[:]

        return q

    def _set_where(self, query):
        where = ''
        has_items = False
        if query:
            operator = None
            for key, value in self._check_search_query(query):
                if isIterable(key):
                    s = ' OR '.join([addSqlFilterItem(0, x, value, self._fields) for x in key])
                    where += '(%s)' % s
                elif key.startswith('_'):
                    where += value
                elif key.startswith('operator'):
                    where += value
                else:
                    where += addSqlFilterItem(has_items, key, value, self._fields, operator)
        return where

    def _set_order(self, order=None):
        return order or getSqlOrder(self._fields) or ''

    def _set_encoding(self):
        return [key for key in self._fields if self._fields[key].get('encoding')]

    def getBlank(self, attrs, default=None):
        row = {}

        blank_field_values = {
            'int' : 0,
            'varchar' : '',
            'text' : '',
        }

        for name in self.columns:
            header = self.headers[name]
            field = self.fields[name]

            value = blank_field_values.get(field['type'], '')

            if name in attrs:
                value = attrs[name]

            row[name] = value
            alias = header['alias']

            if alias:
                if alias == name and header['link'] and header['style'] == 'varchar':
                    row[name] = ''
                else:
                    field = self.fields.get(alias)
                    if field:
                        value = blank_field_values.get(field['type'], '')

                        if alias in attrs:
                            value = attrs[name]
                        elif default and alias in default:
                            value = default[name]

                        row[alias] = value

        return row

    def _selected(self, rows, id):
        if rows and id:
            selected_id = int(id)

            for row in rows:
                if row.get('TID') == selected_id:
                    row['selected'] = 'selected'
                else:
                    row['selected'] = ''

    def getLinks(self, query, attrs, id, **kw):
        """
            Get linked reference items list with SQL-query.
            
            Arguments:
                query   -- Dict, query parameters: {'key':'value', ...}
                attrs   -- Dict, query attributes:
                
                'FileTypeID'          : Int, file type ID
                'FileTypeBatchTypeID' : Int, file type batch type ID
                'FBLinkID'            : Int, file type batch type ID
                ...
                'BatchTypeID'         : Int, filtered batch type ID
                'Tag'                 : Int or String, filtered tag ID/Name
                'TagValue'            : String, filtered tag value

                id      -- Int or String, selected item id

            Returns:
                rows    -- List, mappings list: [{'key':'value', ...}].
        """
        rows = []

        try:
            columns = self.columns
            where = self._set_where(query)
            
            s = ' AND '.join(['%s=%s' % (name, isinstance(value, int) and value or ("'%s'" % value))
                    for name, value in attrs.items() if name in columns and value]
                )

            if s:
                where = where and '(%s) AND (%s)' % (where, s) or s

            order = self._set_order(kw.get('order'))
            encode_columns = self._set_encoding()

            rows = self.engine.runQuery(self.view, columns=columns, where=where, order=order, 
                                        encode_columns=encode_columns, 
                                        as_dict=True,
                                        config=self._config,
                                        )
            self._selected(rows, id)

        except:
            if IsPrintExceptions:
                print_exception()

        return rows

    def getItems(self, query=None, id=None, **kw):
        """
            Get reference items list with SQL-query.
            
            Arguments:
                query   -- Dict, query parameters: {'key':'value', ...}
                id      -- Int or String, selected item id

            Returns:
                rows    -- List, mappings list: [{'key':'value', ...}].
        """
        rows = []

        try:
            columns = self.columns
            where = self._set_where(query)
            order = self._set_order(kw.get('order'))
            encode_columns = self._set_encoding()

            rows = self.engine.runQuery(self.view, columns=columns, where=where, order=order, 
                                        encode_columns=encode_columns, 
                                        as_dict=True,
                                        config=self._config,
                                        )
            self._selected(rows, id)

        except:
            if IsPrintExceptions:
                print_exception()

        return rows

    def calculateId(self):
        cursor = self.engine.runQuery(self.view, columns=(self._id,), top=1, order='TID DESC',
                                      config=self._config,
                                      )
        id = cursor and int(cursor[0][0]) or 0
        return id + 1

    def getItemById(self, id):
        pass

    def count(self, where=None):
        cursor = self.engine.runQuery(self.view, columns=('count(*)',), where=where,
                                      config=self._config,
                                      )
        return cursor and cursor[0] or 0

    def _dbtype(self, name):
        if self.fields.get(name)['type'] in ('varchar', 'datetime', 'text,'):
            return 'varchar'
        if self.headers.get(name)['link']:
            return 'null'
        else:
            return 'int'

    def _default_value(self, name):
        if self._dbtype(name) == 'varchar':
            return ''
        if self._dbtype(name) == 'null':
            return 'null'
        else:
            return 0

    def _value(self, items, name):
        value = items.get(name)
        if value and isinstance(value, str):
            value = re.sub(r'([\"\'])', '\"', value)
        return value or self._default_value(name)

    def addItem(self, items, id=None, **kw):
        """
            Add new item into the reference.

            Arguments:
                id      -- Int|String, PK, `None` is used for calculated value
                items   -- Dict, field values: {name : value, ...}

            Keyword arguments:
                with_identity -- Boolean: PK is <Identity> field
                calculated_pk -- Boolean: PK should be calculated integer as max scope value

            Returns:
                errors  -- List, Errors list: ['error', ...], sorted by error code: 2,1,0. Empty is success.
        """
        errors = []

        # --------------------
        # SQL-command template
        # --------------------

        command = 'INSERT INTO ' + self._table + ' VALUES(%s)'

        # -----------------------------------
        # Get item values and set SQL-command
        # -----------------------------------

        columns = self.editable_columns or []

        if not self._is_ready():
            errors.append((_ERROR, gettext('Error: Class has not editable columns')))

        values = items and ', '.join([
            '%s' % (self._dbtype(name) in 'varchar' and ("'%s'" % str(self._value(items, name))) or self._value(items, name))
                for name in columns if name != self.id]) or ''
        sql = ''

        calculated_pk = kw.get('calculated_pk') and True or False
        with_identity = kw.get('with_identity') and True or False

        if not self._is_ready():
            errors.append((_ERROR, gettext('Error: Class is not ready')))

        elif id is None:
            if calculated_pk:
                id = self.calculateId()
            elif not with_identity:
                errors.append((_ERROR, gettext('Error: Missing Primary Key for insert')))

        if not values:
            errors.append((_WARNING, gettext('Warning: No values present')))
        elif id:
            values = '%s, %s' % (id, values)

        if not errors:
            sql = command % values

            if IsDeepDebug:
                print('--> with_identity:%s' % with_identity)

            if with_identity:
                sql += ' SELECT SCOPE_IDENTITY()'
                no_cursor = False
            else:
                no_cursor = True

            # --------------
            # Execute $ Exit
            # --------------

            rows = self.run(sql, errors, no_cursor=no_cursor)
            
            if with_identity and rows:
                id = int(rows[0][0])

            if IsDeepDebug:
                print('--> new item: ID[%s]' % id)

        return id, self._get_errors(errors)

    def updateItem(self, id, items):
        """
            Update item values into the reference.

            Arguments:
                id      -- Int|String, PK, `None` is used for calculated value
                items   -- Dict, field values: {name : value, ...}

            Returns:
                errors  -- List, Errors list: ['error', ...], sorted by error code: 2,1,0. Empty is success.
        """
        errors = []

        # --------------------
        # SQL-command template
        # --------------------

        command = 'UPDATE ' + self._table + ' SET %s WHERE TID=%s'

        # ---------------------------------------
        # Get item values, ID and set SQL-command
        # ---------------------------------------

        columns = self.editable_columns or []

        if not self._is_ready():
            errors.append((_ERROR, gettext('Error: Class has not editable columns')))

        values = items and ', '.join([
            '%s=%s' % (name, 
                       self._dbtype(name) in 'varchar' and ("'%s'" % str(self._value(items, name))) or self._value(items, name)) 
                for name in columns if name != self.id and name in self.fields and name in items]) or '' # and items[name]
        sql = ''

        if not self._is_ready():
            errors.append((_ERROR, gettext('Error: Class is not ready')))

        elif id is None:
            errors.append((_ERROR, gettext('Error: Missing Primary Key for update')))

        if not values:
            errors.append((_WARNING, gettext('Warning: No values present')))

        if not errors:
            sql = command % (values, id)

            # --------------
            # Execute $ Exit
            # --------------

            rows = self.run(sql, errors)

        return self._get_errors(errors)

    def removeItem(self, id):
        """
            Delete item with given id from the reference.

            Arguments:
                id      -- Int|String, PK, `None` is used for calculated value

            Returns:
                errors  -- List, Errors list: ['error', ...], sorted by error code: 2,1,0. Empty is success.
        """
        errors = []

        # --------------------
        # SQL-command template
        # --------------------

        command = 'DELETE FROM ' + self._table + ' WHERE TID=%s'

        # -------------------------------
        # Get item ID and set SQL-command
        # -------------------------------

        sql = ''

        if not self._is_ready():
            errors.append((_ERROR, gettext('Error: Class is not ready')))

        elif id is None:
            errors.append((_ERROR, gettext('Error: Missing Primary Key for update')))

        if not errors:
            sql = command % id

            # --------------
            # Execute $ Exit
            # --------------

            rows = self.run(sql, errors)

        return self._get_errors(errors)

    def run(self, sql, errors, **kw):
        """
            Run SQL-command.
            
            Arguments:
                sql     -- String, sql-command text
                errors  -- List, errors (mutable)
        """
        if not (sql and self._is_ready()):
            return None

        try:
            rows, error_msg = self.engine.runCommand(sql, with_error=True, **kw)

            if error_msg:
                errors.append((_UNDEFINED_ERROR, error_msg))

        except:
            if IsPrintExceptions:
                print_exception()

        return rows

##  =================
##  BankDB.References
##  =================

class DicClients(AbstractReference):

    def __init__(self, engine):
        super(DicClients, self).__init__(engine, 'reference.clients')

    def addItem(self, items, id=None, **kw):
        return super(DicClients, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Клиенты'

    @property
    def editable_columns(self):
        return ('CName',)


class DicFileStatus(AbstractReference):

    def __init__(self, engine):
        super(DicFileStatus, self).__init__(engine, 'reference.file-status')

    def addItem(self, items, id=None, **kw):
        return super(DicFileStatus, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Статусы файлов'

    @property
    def editable_columns(self):
        return ('StatusTypeID', 'CName',)


class DicFileType(AbstractReference):

    def __init__(self, engine):
        super(DicFileType, self).__init__(engine, 'reference.file-type')

    def addItem(self, items, id=None, **kw):
        return super(DicFileType, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Типы файлов'

    @property
    def searchable(self):
        return ('CName', 'ReportPrefix',)

    @property
    def numeric(self):
        return ('TID', 'ClientID',)

    @property
    def editable_columns(self):
        return ('ClientID', 'CName', 'ReportPrefix',)


class DicBatchCreateType(AbstractReference):

    def __init__(self, engine):
        super(DicBatchCreateType, self).__init__(engine, 'reference.batch-create-type')

    def addItem(self, items, id=None, **kw):
        return super(DicBatchCreateType, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Признак создания партии'

    @property
    def editable_columns(self):
        return ('CName',)


class DicBatchResultType(AbstractReference):

    def __init__(self, engine):
        super(DicBatchResultType, self).__init__(engine, 'reference.batch-result-type')

    def addItem(self, items, id=None, **kw):
        return super(DicBatchResultType, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Признак создания файла результата партии'

    @property
    def editable_columns(self):
        return ('CName',)


class DicBatchStatus(AbstractReference):

    def __init__(self, engine):
        super(DicBatchStatus, self).__init__(engine, 'reference.batch-status')

    def addItem(self, items, id=None, **kw):
        return super(DicBatchStatus, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Статусы партий'

    @property
    def editable_columns(self):
        return ('CName',)


class DicBatchType(AbstractReference):

    def __init__(self, engine):
        super(DicBatchType, self).__init__(engine, 'reference.batch-type')

    def addItem(self, items, id=None, **kw):
        return super(DicBatchType, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Типы партий'

    @property
    def editable_columns(self):
        return ('CName',)


class DicOperList(AbstractReference):

    def __init__(self, engine):
        super(DicOperList, self).__init__(engine, 'reference.oper-list')

    def addItem(self, items, id=None, **kw):
        return super(DicOperList, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Операции'

    @property
    def editable_columns(self):
        return ('TypeID', 'CName',)


class DicOperType(AbstractReference):

    def __init__(self, engine):
        super(DicOperType, self).__init__(engine, 'reference.oper-type')

    def addItem(self, items, id=None, **kw):
        return super(DicOperType, self).addItem(items, calculated_pk=True)

    @property
    def value(self):
        return 'SName'

    @property
    def title(self):
        return 'Типы операций'

    @property
    def searchable(self):
        return ('CName', 'SName',)

    @property
    def editable_columns(self):
        return ('CName', 'SName',)


class DicTagParams(AbstractReference):

    def __init__(self, engine):
        super(DicTagParams, self).__init__(engine, 'reference.tag-params')

    def addItem(self, items, id=None, **kw):
        return super(DicTagParams, self).addItem(items, with_identity=True)

    @property
    def value(self):
        return 'PName'

    @property
    def title(self):
        return 'Параметры тегов'

    @property
    def searchable(self):
        return ('PName', 'Comment',)

    @property
    def editable_columns(self):
        return ('PName', 'Comment',)


class DicFTBPost(AbstractReference):

    def __init__(self, engine):
        super(DicFTBPost, self).__init__(engine, 'reference.ftb-post')

    def addItem(self, items, id=None, **kw):
        return super(DicFTBPost, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Параметры почты'

    @property
    def searchable(self):
        return ('PValue', 'Comment',)

    @property
    def numeric(self):
        return ('TID', 'FBLinkID', 'TagParamID',)

    @property
    def editable_columns(self):
        return ('FBLinkID', 'TagParamID', 'PValue', 'PSortIndex', 'Comment',)


class DicFTVOperParams(AbstractReference):

    def __init__(self, engine):
        super(DicFTVOperParams, self).__init__(engine, 'reference.ftv-oper-params')

    def addItem(self, items, id=None, **kw):
        return super(DicFTVOperParams, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Параметры персонализации'

    @property
    def searchable(self):
        return ('PName', 'PValue',)

    @property
    def numeric(self):
        return ('TID', 'FTV_OPER_ID',)

    @property
    def editable_columns(self):
        return ('FTV_OPER_ID', 'PName', 'PValue',)


class DicLinkedBatches(AbstractReference):

    def __init__(self, engine):
        super(DicLinkedBatches, self).__init__(engine, 'reference.linked-batches')

    @property
    def title(self):
        return 'Партии типа файла (***)'

    @property
    def value(self):
        return 'BatchType'

    @property
    def searchable(self):
        return ('FileType', 'BatchType',)

    @property
    def numeric(self):
        return ('TID', 'FileTypeID', 'BatchTypeID',)

    @property
    def editable_columns(self):
        return []

    @property
    def has_links(self):
        return True


class DicLinkedOpers(AbstractReference):

    def __init__(self, engine):
        super(DicLinkedOpers, self).__init__(engine, 'reference.linked-opers')

    @property
    def title(self):
        return 'Операции типа файла (***)'

    @property
    def value(self):
        return 'OperType'

    @property
    def searchable(self):
        return ('FileType', 'BatchType', 'OperTypeName', 'OperType',)

    @property
    def numeric(self):
        return ('TID', 'FBLinkID', 'FileTypeID', 'BatchTypeID', 'OperID', 'OperSortIndex',)

    @property
    def editable_columns(self):
        return []

    @property
    def has_links(self):
        return True


class DicLinkedTags(AbstractReference):

    def __init__(self, engine):
        super(DicLinkedTags, self).__init__(engine, 'reference.linked-tags')

    @property
    def title(self):
        return 'Теги типа файла (***)'

    @property
    def value(self):
        return 'TName'

    @property
    def searchable(self):
        return ('FileType', 'TName',)

    @property
    def numeric(self):
        return ('TID', 'FileTypeID',)

    @property
    def editable_columns(self):
        return []

    @property
    def has_links(self):
        return True


class DicLinkedTagValues(AbstractReference):

    def __init__(self, engine):
        super(DicLinkedTagValues, self).__init__(engine, 'reference.linked-tagvalues')

    @property
    def title(self):
        return 'Значения тегов типа файла (***)'

    @property
    def value(self):
        return 'TagValue'

    @property
    def searchable(self):
        return ('FileType', 'TName', 'TValue',)

    @property
    def numeric(self):
        return ('TID', 'FTLinkID', 'FileTypeID',)

    @property
    def editable_columns(self):
        return []

    @property
    def has_links(self):
        return True


class DicLinkedTagOpers(AbstractReference):

    def __init__(self, engine):
        super(DicLinkedTagOpers, self).__init__(engine, 'reference.linked-tagopers')

    @property
    def title(self):
        return 'Операции персонализации (***)'

    @property
    def value(self):
        return 'PValue'

    @property
    def searchable(self):
        return ('FileType', 'TName', 'TValue', 'OperType', 'Oper', 'PName', 'PValue', 'Comment',)

    @property
    def numeric(self):
        return ('TID', 'FTVLinkID', 'FileTypeID', 'TagParamID', 'OperTypeID', 'OperSortIndex',)

    @property
    def editable_columns(self):
        return []

    @property
    def has_links(self):
        return True


class DicFileType_BatchType(AbstractReference):

    def __init__(self, engine):
        super(DicFileType_BatchType, self).__init__(engine, 'reference.file-type-batch-type')

    def addItem(self, items, id=None, **kw):
        return super(DicFileType_BatchType, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Тип партии файла'

    @property
    def configurator(self):
        return 'configurator-batches'

    @property
    def editable_columns(self):
        return ('FileTypeID', 'BatchTypeID', 'BatchCreateTypeID', 'BatchResultTypeID', 'BatchMaxQty', 'IsErpBatch', 'CreateBatchSortIndex', 'CreateBatchGroupIndex',)


class DicOrderFileProcess(AbstractReference):

    def __init__(self, engine):
        super(DicOrderFileProcess, self).__init__(engine, 'reference.order-file-process')

    def addItem(self, items, id=None, **kw):
        return super(DicOrderFileProcess, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Сценарии типа файла'

    @property
    def configurator(self):
        return 'configurator-processes'

    @property
    def editable_columns(self):
        return ('LinkID', 'CurrFileStatusID', 'NextFileStatusID', 'CloseFileStatusID', 'Memo', 'ActivateBatchStatus', 'ARMBatchStatus',)


class DicFileType_BatchType_OperList(AbstractReference):

    def __init__(self, engine):
        super(DicFileType_BatchType_OperList, self).__init__(engine, 'reference.file-type-batch-type-opers')

    def addItem(self, items, id=None, **kw):
        return super(DicFileType_BatchType_OperList, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Операции типа файла'

    @property
    def configurator(self):
        return 'configurator-opers'

    @property
    def editable_columns(self):
        return ('FBLinkID', 'OperID', 'OperSortIndex',)


class DicFileType_BatchType_OperList_Params(AbstractReference):

    def __init__(self, engine):
        super(DicFileType_BatchType_OperList_Params, self).__init__(engine, 'reference.file-type-batch-type-operparams')

    def addItem(self, items, id=None, **kw):
        return super(DicFileType_BatchType_OperList_Params, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Параметры операций типа файла'

    @property
    def configurator(self):
        return 'configurator-operparams'

    @property
    def editable_columns(self):
        return ('FBOLinkID', 'PName', 'PValue', 'Comment',)


class DicFileType_TagList(AbstractReference):

    def __init__(self, engine):
        super(DicFileType_TagList, self).__init__(engine, 'reference.file-type-tags')

    def addItem(self, items, id=None, **kw):
        return super(DicFileType_TagList, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Теги типа файла'

    @property
    def configurator(self):
        return 'configurator-tags'

    @property
    def editable_columns(self):
        return ('FileTypeID', 'TName', 'TMemo',)


class DicFileType_TagList_TagValues(AbstractReference):

    def __init__(self, engine):
        super(DicFileType_TagList_TagValues, self).__init__(engine, 'reference.file-type-tagvalues')

    def addItem(self, items, id=None, **kw):
        return super(DicFileType_TagList_TagValues, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Значения тегов типа файла'

    @property
    def configurator(self):
        return 'configurator-tagvalues'

    @property
    def editable_columns(self):
        return ('FTLinkID', 'TValue',)


class DicFileType_BatchType_FilterShema(AbstractReference):

    def __init__(self, engine):
        super(DicFileType_BatchType_FilterShema, self).__init__(engine, 'reference.file-type-batch-type-filters')

    def addItem(self, items, id=None, **kw):
        return super(DicFileType_BatchType_FilterShema, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Фильтры типа файла'

    @property
    def configurator(self):
        return 'configurator-filters'

    @property
    def sorted_columns(self):
        return ('TID', 'FileTypeID', 'FBLinkID', 'FTLinkID', 'CriticalValues',)

    @property
    def editable_columns(self):
        return ('FBLinkID', 'FTLinkID', 'CriticalValues',)


class DicFTV_TZ(AbstractReference):

    def __init__(self, engine):
        super(DicFTV_TZ, self).__init__(engine, 'reference.file-type-tzs')

    def addItem(self, items, id=None, **kw):
        return super(DicFTV_TZ, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Параметры ТЗ'

    @property
    def configurator(self):
        return 'configurator-tzs'

    @property
    def editable_columns(self):
        return ('FTVLinkID', 'TagParamID', 'PValue', 'Comment', 'PSortIndex',)


class DicFTV_ERPCODE(AbstractReference):

    def __init__(self, engine):
        super(DicFTV_ERPCODE, self).__init__(engine, 'reference.file-type-erpcodes')

    def addItem(self, items, id=None, **kw):
        return super(DicFTV_ERPCODE, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Коды ЕРП'

    @property
    def configurator(self):
        return 'configurator-erpcodes'

    @property
    def sorted_columns(self):
        return ('TID', 'BatchTypeID', 'FTVLinkID', 'ERP_CODE', 'AdditionalInfo',)

    @property
    def editable_columns(self):
        return ('FTVLinkID', 'ERP_CODE', 'BatchTypeID', 'AdditionalInfo',)


class DicFTV_MATERIAL(AbstractReference):

    def __init__(self, engine):
        super(DicFTV_MATERIAL, self).__init__(engine, 'reference.file-type-materials')

    def addItem(self, items, id=None, **kw):
        return super(DicFTV_MATERIAL, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Материалы'

    @property
    def configurator(self):
        return 'configurator-materials'

    @property
    def sorted_columns(self):
        return ('TID', 'BatchTypeID', 'FTVLinkID', 'TagParamID', 'QtyMode', 'MMin', 'MBadPercent',)

    @property
    def editable_columns(self):
        return ('FTVLinkID', 'TagParamID', 'BatchTypeID', 'MMin', 'MBadPercent', 'QtyMode',)


class DicFTV_POST(AbstractReference):

    def __init__(self, engine):
        super(DicFTV_POST, self).__init__(engine, 'reference.file-type-posts')

    def addItem(self, items, id=None, **kw):
        return super(DicFTV_POST, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Почтовые параметры'

    @property
    def configurator(self):
        return 'configurator-posts'

    @property
    def sorted_columns(self):
        return ('TID', 'FTVLinkID', 'TagParamID', 'PValue', 'Comment',)

    @property
    def editable_columns(self):
        return ('FTVLinkID', 'TagParamID', 'PValue', 'Comment',)


class DicFTV_OPER(AbstractReference):

    def __init__(self, engine):
        super(DicFTV_OPER, self).__init__(engine, 'reference.file-type-tagopers')

    def addItem(self, items, id=None, **kw):
        return super(DicFTV_OPER, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Операции персонализации'

    @property
    def configurator(self):
        return 'configurator-tagopers'

    @property
    def sorted_columns(self):
        return ('TID', 'FTVLinkID', 'TagParamID', 'OperTypeID', 'PValue', 'OperSortIndex', 'Comment',)

    @property
    def editable_columns(self):
        return ('FTVLinkID', 'TagParamID', 'OperTypeID', 'PValue', 'Comment', 'OperSortIndex',)


class DicFTV_OPER_PARAMS(AbstractReference):

    def __init__(self, engine):
        super(DicFTV_OPER_PARAMS, self).__init__(engine, 'reference.file-type-tagoperparams')

    def addItem(self, items, id=None, **kw):
        return super(DicFTV_OPER_PARAMS, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Параметры операций персонализации'

    @property
    def configurator(self):
        return 'configurator-tagoperparams'

    @property
    def sorted_columns(self):
        return ('TID', 'FTV_OPER_ID', 'PName', 'PValue',)

    @property
    def editable_columns(self):
        return ('FTV_OPER_ID', 'PName', 'PValue',)


class DicFTV_PROCESSPARAMS(AbstractReference):

    def __init__(self, engine):
        super(DicFTV_PROCESSPARAMS, self).__init__(engine, 'reference.file-type-processparams')

    def addItem(self, items, id=None, **kw):
        return super(DicFTV_PROCESSPARAMS, self).addItem(items, with_identity=True)

    @property
    def title(self):
        return 'Параметры процессов'

    @property
    def configurator(self):
        return 'configurator-processparams'

    @property
    def sorted_columns(self):
        return ('TID', 'FTVLinkID', 'TagParamID', 'PValue', 'PSortIndex', 'Comment',)

    @property
    def editable_columns(self):
        return ('FTVLinkID', 'TagParamID', 'PValue', 'Comment', 'PSortIndex',)


reference_factory = {
    # ----------
    # References
    # ----------
    'batch-create-type'     : DicBatchCreateType,
    'batch-result-type'     : DicBatchResultType,
    'batch-status'          : DicBatchStatus,
    'batch-type'            : DicBatchType,
    'clients'               : DicClients,
    'file-status'           : DicFileStatus,
    'file-type'             : DicFileType,
    'ftb-post'              : DicFTBPost,
    'ftv-oper-params'       : DicFTVOperParams,
    'oper-list'             : DicOperList,
    'oper-type'             : DicOperType,
    'tag-params'            : DicTagParams,
    # ----
    # Tabs
    # ----
    'batches'               : DicFileType_BatchType,
    'processes'             : DicOrderFileProcess,
    'opers'                 : DicFileType_BatchType_OperList,
    'operparams'            : DicFileType_BatchType_OperList_Params,
    'tags'                  : DicFileType_TagList,
    'tagvalues'             : DicFileType_TagList_TagValues,
    'filters'               : DicFileType_BatchType_FilterShema,
    'tzs'                   : DicFTV_TZ,
    'erpcodes'              : DicFTV_ERPCODE,
    'materials'             : DicFTV_MATERIAL,
    'posts'                 : DicFTV_POST,
    'tagopers'              : DicFTV_OPER,
    'tagoperparams'         : DicFTV_OPER_PARAMS,
    'processparams'         : DicFTV_PROCESSPARAMS,
    # -----------------
    # Linked references
    # -----------------
    'linked-batches'        : DicLinkedBatches,
    'linked-opers'          : DicLinkedOpers,
    'linked-tags'           : DicLinkedTags,
    'linked-tagvalues'      : DicLinkedTagValues,
    'linked-tagopers'       : DicLinkedTagOpers,
}
