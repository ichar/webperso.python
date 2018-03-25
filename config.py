# -*- coding: utf-8 -*-

import os
import sys
import codecs
import datetime
import traceback
import imp

from collections import Iterable

basedir = os.path.abspath(os.path.dirname(__file__))
errorlog = os.path.join(basedir, 'traceback.log')

# ----------------------------
# Global application constants
# ----------------------------

IsDebug                = 1  # Debug[stdout]: prints general info (1 - forbidden with apache!)
IsDeepDebug            = 0  # Debug[stdout]: prints detailed info (1 - forbidden with apache!)
IsTrace                = 1  # Trace[errorlog]: output execution trace for http-requests
IsSemaphoreTrace       = 0  # Trace[errorlog]: output trace for semaphore actions
IsLogTrace             = 1  # Trace[errorlog]: output detailed trace for Log-actions
IsUseDecodeCyrillic    = 1  # Flag: sets decode cyrillic mode
IsUseDBLog             = 1  # Flag: sets DB OrderLog enabled to get log-messages
IsPrintExceptions      = 1  # Flag: sets printing of exceptions
IsForceRefresh         = 1  # Flag: sets http forced refresh for static files (css/js)
IsDecoderTrace         = 1  # Flag: sets decoder output
IsShowLoader           = 0  # Flag: sets page loader show enabled
IsFuture               = 0  # Flag: opens inactive future menu items
IsDemo                 = 0  # Flag: sets demo-mode (inactive)

LocalDebug = {
    'bankperso'    : 0,
    'configurator' : 0,
    'cards'        : 1,
    'database'     : 0,
    'mails'        : 0,
    'models'       : 0,
    'orderstate'   : 0,
    'profile'      : 0,
    'reporter'     : 0,
    'semaphore'    : 0,
    'settings'     : 0,
    'worker'       : 0,
}

LOCAL_FULL_TIMESTAMP   = '%d-%m-%Y %H:%M:%S'
LOCAL_EXCEL_TIMESTAMP  = '%d.%m.%Y %H:%M:%S'
LOCAL_EASY_TIMESTAMP   = '%d-%m-%Y %H:%M'
LOCAL_EASY_DATESTAMP   = '%Y-%m-%d'
LOCAL_EXPORT_TIMESTAMP = '%Y%m%d%H%M%S'
UTC_FULL_TIMESTAMP     = '%Y-%m-%d %H:%M:%S'
UTC_EASY_TIMESTAMP     = '%Y-%m-%d %H:%M'
DATE_TIMESTAMP         = '%d/%m'
DATE_STAMP             = '%Y%m%d'

default_print_encoding = 'cp866'
default_unicode        = 'utf-8'
default_encoding       = 'cp1251'
default_iso            = 'ISO-8859-1'

CONNECTION = {
    'bankperso'    : { 'server':'localhost', 'user':'sa', 'password':'***', 'database':'BankDB',     'timeout':15 },
    'cards'        : { 'server':'localhost', 'user':'sa', 'password':'***', 'database':'Cards',      'timeout':15 },
    'orderstate'   : { 'server':'localhost', 'user':'sa', 'password':'***', 'database':'OrderState', 'timeout':15 },
    'preload'      : { 'server':'localhost', 'user':'sa', 'password':'***', 'database':'BankDB',     'timeout':15 },
    'configurator' : { 'server':'localhost', 'user':'sa', 'password':'***', 'database':'BankDB',     'timeout':15 },
    'orderlog'     : { 'server':'localhost', 'user':'sa', 'password':'***', 'database':'OrderLog',   'timeout':15 },
}

smtphost = {
    'host' : 'mail2.company.ru', 
    'port' : 25
}

email_address_list = {
    'adminbd'      : 'admin@company.ru',     
    'support'      : 'support@company.ru',
    'warehouse'    : 'user@company.ru',
}

image_encoding = {
    'default'      : (default_encoding, default_unicode, default_iso,),
    'CITI_BANK'    : (default_print_encoding, default_encoding,),
}

BP_ROOT = { 
    'default'      : (default_unicode, 'Z:/bankperso/default',), #'//persotest/bankperso'
    'VTB24'        : (default_unicode, 'Z:/bankperso/VTB24',),
    'CITI_BANK'    : (default_unicode, 'Z:/bankperso/CITI',),
}

INFOEXCHANGE_ROOT = {
    'default'      : (default_unicode, 'Z:/#Save/infoexchange',),
}

SDC_ROOT = {
    'default'      : (default_unicode, 'Z:/SDC/default', 'sdc_(.*)_(\d{2}\.\d{2}\.\d{4}).*', 'with_aliases',),
    'VTB24'        : (default_unicode, 'Z:/SDC/VTB24', 'sdc_(.*)_(\d{2}\.\d{2}\.\d{4}).*', ''),
    'CITI_BANK'    : (default_unicode, 'Z:/SDC/CITI', 'sdc_(.*)_(\d{2}\.\d{2}\.\d{4}).*', ''),
}

EXCHANGE_ROOT = {
    'default'      : (default_unicode, 'Z:/exchange/11.01', '(.*)_(\d{2}\.\d{2}\.\d{4}).*', 'with_aliases:jzdo:unique:count',),
    'CITI_BANK'    : (default_unicode, 'Z:/exchange/11.02', '(.*)_(\d{2}\.\d{2}\.\d{4}).*', '*',),
}

ansi = not sys.platform.startswith("win")

n_a = 'n/a'
cr = '\n'

def isIterable(v):
    return not isinstance(v, str) and isinstance(v, Iterable)

#######################################################################################################

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SSL_DISABLE = False

    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    WTF_CSRF_ENABLED = False

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'storage', 'app.db.debug')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'storage', 'app.db')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)


config = { \
    'production' : ProductionConfig,
    'default'    : DevelopmentConfig,
}

##  --------------------------------------- ##

def setup_console(sys_enc=default_unicode):
    """
    Set sys.defaultencoding to `sys_enc` and update stdout/stderr writers to corresponding encoding
    .. note:: For Win32 the OEM console encoding will be used istead of `sys_enc`
    http://habrahabr.ru/post/117236/
    http://www.py-my.ru/post/4bfb3c6a1d41c846bc00009b
    """
    global ansi
    reload(sys)
    
    try:
        if sys.platform.startswith("win"):
            import ctypes
            enc = "cp%d" % ctypes.windll.kernel32.GetOEMCP()
        else:
            enc = (sys.stdout.encoding if sys.stdout.isatty() else
                        sys.stderr.encoding if sys.stderr.isatty() else
                            sys.getfilesystemencoding() or sys_enc)

        sys.setdefaultencoding(sys_enc)

        if sys.stdout.isatty() and sys.stdout.encoding != enc:
            sys.stdout = codecs.getwriter(enc)(sys.stdout, 'replace')

        if sys.stderr.isatty() and sys.stderr.encoding != enc:
            sys.stderr = codecs.getwriter(enc)(sys.stderr, 'replace')
    except:
        pass

def print_to(f, v, mode='ab', request=None, encoding=default_encoding):
    items = not isIterable(v) and [v] or v
    if not f:
        f = getErrorlog()
    fo = open(f, mode=mode)
    def _out(s):
        fo.write(s.encode(encoding, 'ignore'))
        fo.write(cr.encode())
    for text in items:
        try:
            if IsDeepDebug:
                print(text)
            if request:
                _out('%s>>> %s [%s]' % (cr, datetime.datetime.now().strftime(UTC_FULL_TIMESTAMP), request.url))
            _out(text)
        except Exception as e:
            pass
    fo.close()

def print_exception(stack=None):
    print_to(errorlog, '%s>>> %s:%s' % (cr, datetime.datetime.now().strftime(LOCAL_FULL_TIMESTAMP), cr))
    traceback.print_exc(file=open(errorlog, 'a'))
    if stack is not None:
        print_to(errorlog, '%s>>> Traceback stack:%s' % (cr, cr))
        traceback.print_stack(file=open(errorlog, 'a'))

def getErrorlog():
    return errorlog

def getCurrentDate():
    return datetime.datetime.now().strftime(LOCAL_EASY_DATESTAMP)
