# -*- coding: utf-8 -*-

import re
from decimal import *
from operator import itemgetter

from flask.ext.babel import gettext

from config import (
     IsDebug, IsDeepDebug, IsTrace, IsPrintExceptions, errorlog, print_to, print_exception,
     default_unicode, default_encoding, default_iso,
     )

from ..database import getReferenceConfig
from ..utils import isIterable, getToday, spent_time


class Base:

    def __init__(self, engine, *args, **kwargs):
        if IsDeepDebug:
            print('Base init')

        super().__init__(*args, **kwargs)

        self.engine = engine

    def _init_state(self, attrs, factory, *args, **kwargs):
        if IsDeepDebug:
            print('Base initstate')

        super().__init__(*args, **kwargs)

    @staticmethod
    def set_factory(key, factory):
        if factory is not None and isinstance(factory, dict):
            x = factory.get(key)
            if x is not None and callable(x):
                return x
        return None


class Seller(Base):
    
    def __init__(self, engine, id, **kw):
        if IsDeepDebug:
            print('Seller init')

        super().__init__(engine)

        self._id = id

    def _init_state(self, attrs=None, factory=None):
        if IsDeepDebug:
            print('Seller initstate')

        super()._init_state(attrs, factory)

        self._config = attrs.get('config')

        self._get_seller = self.set_factory('get_seller', factory)
        self._get_orders = self.set_factory('get_orders', factory)
        self._get_order = self.set_factory('get_order', factory)
        self._get_money = self.set_factory('get_money', factory)
        self._info = self.set_factory('info', factory)

    @property
    def is_error(self):
        return self.engine.is_error
    @property
    def id(self):
        return self._id

    def render(self, **kw):
        """
            Render Seller data by the given ID
        """
        orders = []
        items = {}

        self._started = getToday()

        if IsTrace:
            print_to(None, '>>> seller started')

        columns = (
            'np',
            #'TID', 
            'Article', 
            'Qty', 
            'Subdivision', 
            'Price', 
            'Currency', 
            'Total', 
            #'Condition', 
            #'RD',
        )

        seller = self._get_seller(self.id)

        where = 'SellerID=%s' % self.id

        total = 0
        sum_price = Decimal(0.0)
        n = 0

        for order in self._get_orders(where=where):
            order_id = order['TID']
            """
            if not order['Price']:
                continue
            """
            n += 1

            order['np'] = n

            info = self._info(order_id=order_id, no_extra=True, **order)
            items[order_id] = info[1]

            euro = re.sub(r'\s', '', info[1].get('EUR') or '')

            total += 1
            sum_price += euro and Decimal(euro) or 0

            if not order['Price']:
                order['Price'] = '0'
                order['Total'] = '0.00'

            if not order['Currency']:
                order['Currency'] = 'RUR'

            orders.append(order)

            if IsTrace:
                print_to(None, '>>> seller %02d: %s' % (n, getToday()))

        keys = (
            'num',
            'equipment_title',
            'purpose',
            'author',
            'EUR',
        )

        headers = {
            'num'             : 'Номер заявки',
            'equipment_title' : 'Описание',
            'purpose'         : 'Обоснование',
            'author'          : 'Автор',
            'EUR'             : 'Цена в ЕВРО',
        }

        data = {
            'seller'    : seller,
            'columns'   : columns,
            'headers'   : headers,
            'keys'      : keys,
            'orders'    : orders,
            'items'     : items,
            'total'     : total,
            'sum_price' : self._get_money(str(sum_price)),
        }

        self._finished = getToday()

        if IsTrace:
            print_to(None, '>>> seller finished: %s sec' % spent_time(self._started, self._finished))

        return data

    def render_html(self):
        where = 'SellerID=%s' % self.id

        orders = self._get_orders(where=where)

        content = '<div>%s</div>' % '<br>'.join(['<span>%s</span>' % x['Article'] for x in orders])

        return 'Seller ID: %s, Total orders: %d %s<br>Is_Error:%s' % (self.id, len(orders), content, self.is_error)

