# -*- coding: utf-8 -*-

__all__ = ['DicClients', 'reference_factory',]

import types
from operator import itemgetter

from flask.ext.babel import gettext

from config import (
     IsDebug, IsDeepDebug, IsTrace, IsPrintExceptions, errorlog, print_to, print_exception,
     default_unicode, default_encoding, default_iso
     )

from ..database import getReferenceConfig
from ..booleval import Token, new_token

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
    #value = query.get(key)
    if field is None or value is None:
        return ''
    selector = field.get('selector')
    return selector and value and ('%s%s' % (where and (operator or ' AND ') or '', selector % str(value))) or ''

def getSqlOrder(fields):
    for key in fields.keys():
        field = fields[key]
        if 'order' in field and field['order']:
            return ('%s %s' % (key, field['order'])).strip()
    return ''


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

    def _check_search_query(self, value):
        q = []
        if isinstance(value, str):
            #
            # Query items can be `Token` class instance such as: (bank || client) && citi
            #
            token = new_token()
            token._init_state(value)

            n = 1
            for x in token.get_token():
                if callable(x) or isinstance(x, types.FunctionType):
                    item = ('operator%s' % n, x(1,0) and ' OR ' or ' AND ')
                elif x in '()':
                    item = ('_%s' % n, x)
                    n += 1
                else:
                    if x.isdigit():
                        item = (self.id, int(x))
                    else:
                        item = (self.value, x)
                q.append(item)
        
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
                if key.startswith('_'):
                    where += value
                elif key.startswith('operator'):
                    operator = value
                else:
                    where += addSqlFilterItem(has_items, key, value, self._fields, operator)
                    has_items = True
        return where

    def _set_order(self, order=None):
        return order or getSqlOrder(self._fields) or ''

    def _set_encoding(self):
        return [key for key in self._fields if self._fields[key].get('encoding')]

    def getItems(self, query=None, **kw):
        """
            Get reference items list with SQL-query.
            
            Arguments:
                query   -- Dict, query parameters: {'key':'value', ...}

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
        except:
            if IsPrintExceptions:
                print_exception()

        return rows

    def calculateId(self):
        cursor = self.engine.runQuery(self.view, columns=(self._id,), top=1, order='TID DESC')
        id = cursor and int(cursor[0][0]) or 0
        return id + 1

    def getItemById(self, id):
        pass

    def run(self, sql, errors):
        """
            Run SQL-command.
            
            Arguments:
                sql     -- String, sql-command text
                errors  -- List, errors (mutable)
        """
        if not (sql and self._is_ready()):
            return

        try:
            rows, error_msg = self.engine.runCommand(sql, with_error=True)

            if error_msg:
                errors.append((_UNDEFINED_ERROR, error_msg))
        except:
            if IsPrintExceptions:
                print_exception()

        errors = [x[1] for x in sorted(errors, key=itemgetter(0), reverse=True)]

    def addItem(self, items, id=None, **kw):
        """
            Add new item into the reference.

            Arguments:
                id      -- Int|String, PK, `None` is used for calculated value
                items   -- List, field values: [(key, value), ...]

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

        values = items and ', '.join([
            '%s' % (self._fields[key].get('type') in ('varchar', 'datetime',) and ("'%s'" % str(value)) or value) 
                for key, value in items]) or ''
        sql = ''

        if not self._is_ready():
            errors.append((_ERROR, gettext('Error: Class is not ready')))

        elif id is None:
            if kw.get('calculated_pk'):
                id = self.calculateId()
            elif not kw.get('with_identity'):
                errors.append((_ERROR, gettext('Error: Missing Primary Key for insert')))

        if not values:
            errors.append((_WARNING, gettext('Warning: No values present')))
        elif id:
            values = '%s, %s' % (id, values)

        if not errors:
            sql = command % values

        # --------------
        # Execute $ Exit
        # --------------

        self.run(sql, errors)

        return errors 

    def updateItem(self, id, items):
        """
            Update item values into the reference.

            Arguments:
                id      -- Int|String, PK, `None` is used for calculated value
                items   -- List, field values: [(key, value), ...]

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

        values = items and ', '.join([
            '%s=%s' % (key, 
                       self._fields[key].get('type') in ('varchar', 'datetime',) and ("'%s'" % str(value)) or value) 
                for key, value in items]) or ''
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

        self.run(sql, errors)

        return errors 

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

        self.run(sql, errors)

        return errors 

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

class DicFileStatus(AbstractReference):

    def __init__(self, engine):
        super(DicFileStatus, self).__init__(engine, 'reference.file-status')

    def addItem(self, items, id=None, **kw):
        return super(DicFileStatus, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Статусы файлов'

class DicBatchStatus(AbstractReference):

    def __init__(self, engine):
        super(DicBatchStatus, self).__init__(engine, 'reference.batch-status')

    def addItem(self, items, id=None, **kw):
        return super(DicBatchStatus, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Статусы партий'

class DicOperList(AbstractReference):

    def __init__(self, engine):
        super(DicOperList, self).__init__(engine, 'reference.oper-list')

    def addItem(self, items, id=None, **kw):
        return super(DicOperList, self).addItem(items, calculated_pk=True)

    @property
    def title(self):
        return 'Операции'

class DicTagParams(AbstractReference):

    def __init__(self, engine):
        super(DicTagParams, self).__init__(engine, 'reference.tag-params')

    def addItem(self, items, id=None, **kw):
        return super(DicTagParams, self).addItem(items, calculated_pk=True)

    @property
    def value(self):
        return 'PName'

    @property
    def title(self):
        return 'Параметры партий'


reference_factory = {
    'clients'     : DicClients,
    'file-status' : DicFileStatus,
    'batch-status': DicBatchStatus,
    'oper-list'   : DicOperList,
    'tag-params'  : DicTagParams,
}
