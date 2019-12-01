# -*- coding: utf-8 -*-

import re
from sqlalchemy import create_engine
from copy import deepcopy
import pymssql

from config import (
     CONNECTION, IsDebug, IsDeepDebug, IsTrace, IsPrintExceptions,
     default_unicode, default_encoding, default_iso,
     print_to, print_exception
     )

from .utils import out, splitter, worder, getMaskedPAN, getEANDBarcode, isIterable

default_connection = CONNECTION['bankperso']

database_config = { 
    # =========
    # BANKPERSO
    # =========
    'orders' : { 
        'columns' : ('FileID', 'FName', 'FQty', 'BankName', 'FileType', 'StatusDate', 'FileStatus', 'RegisterDate', 'ReadyDate',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersStatus_vw]',
        'headers' : { 
            'FileID'       : ('ID файла',          '',),
            'FName'        : ('ФАЙЛ',              'nowrap',),
            'FQty'         : ('Кол-во',            '',),
            'BankName'     : ('КЛИЕНТ',            'nowrap',),
            'FileType'     : ('Тип файла',         '',),
            'StatusDate'   : ('Дата статуса',      '',),
            'FileStatus'   : ('СТАТУС',            'breakable',),
            'RegisterDate' : ('Дата регистрации',  '',),
            'ReadyDate'    : ('Дата отгрузки',     '',),
        },
        'clients' : 'ClientID',
        'export'  : ('FileID', 'FileTypeID', 'ClientID', 'FileStatusID', 'FName', 'FQty', 'BankName', 'FileType', 'StatusDate', 'FileStatus', 'RegisterDate', 'ReadyDate',),
    },
    'batches' : { 
        'columns' : ('TZ', 'TID', 'BatchType', 'BatchNo', 'ElementQty', 'Status', 'StatusDate',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersBatchList_vw]',
        'headers' : { 
            'TZ'           : 'ТЗ',
            'TID'          : 'ID партии',
            'BatchType'    : 'Тип',
            'BatchNo'      : '№ партии',
            'ElementQty'   : 'Кол-во',
            'Status'       : 'Статус партии',
            'StatusDate'   : 'Дата статуса',
        },
        'export'  : ('TZ', 'TID', 'BatchType', 'BatchNo', 'ElementQty', 'Status', 'StatusDate', 'FileID', 'FileStatusID', 'BatchStatusID', 'BatchTypeID',) #  'ERP_TZ', 'ClientID', 'FileTypeID', 'FileStatusID', 'FName', 'FQty', 'RegisterDate', 'BankName'
    },
    'batches.preview' : { 
        'columns' : ('TID',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersBatchPreview_vw]',
        'export'  : ('TID', 'IsPrintMaterialOrder', 'BatchStatusID', 'FileStatusID', 'RegisterDate',),
    },
    'logs' : { 
        'columns' : ('LID', 'ModDate', 'FileStatusID', 'Status', 'Oper', 'HostName', 'ApplName', 'UserName',), # 'LID', 'TID',
        'view'    : '[BankDB].[dbo].[WEB_OrdersLog_vw]',
        'headers' : { 
            'LID'          : 'ID',
            'TID'          : 'ID файла',
            'ModDate'      : 'Дата статуса',
            'FileStatusID' : 'Код статуса',
            'Status'       : 'Наименование статуса',
            'Oper'         : 'Код операции',
            'HostName'     : 'Хост',
            'ApplName'     : 'Приложение',
            'UserName'     : 'Оператор',
        },
    },
    'banks' : { 
        'columns' : ('ClientID', 'BankName',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersStatus_vw]',
        'headers' : { 
            'BankName'     : 'Клиент',
        },
        'clients' : 'ClientID',
    },
    'clients' : { 
        'columns' : ('TID', 'CName'),
        'view'    : '[BankDB].[dbo].[DIC_Clients_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'CName'        : 'Наименование',
        },
        'clients' : 'TID',
    },
    'types' : { 
        'columns' : ('TID', 'CName', 'ClientID',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'ClientID'     : 'ID клиента',
            'CName'        : 'Тип файла',
        },
        'clients' : 'ClientID',
    },
    'statuses' : { 
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_FileStatus_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'Status'       : 'Статус файла',
        },
    },
    'filestatuses' : { 
        'columns' : ('FileID', 'FileStatusID',),
        'view'    : '[BankDB].[dbo].[OrderFilesBody_tb]',
        'headers' : { 
            'Status'       : 'Статус файла',
        },
    },
    'filestatuslist' : { 
        'columns' : ('TID', 'StatusTypeID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_FileStatus_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'StatusTypeID' : 'Тип cтатуса',
            'CName'        : 'Наименование',
        },
    },
    'batchstatuslist' : { 
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_BatchStatus_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'CName'        : 'Наименование',
        },
    },
    'batchtypelist' : { 
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_BatchType_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'CName'        : 'Наименование',
        },
    },
    'params' : { 
        'columns' : ('TID', 'PName', 'PValue', 'PSortIndex', 'TName', 'TValue', 'FTVLinkID', 'TagParamID', 'FileTypeID', 'FileID', 'BatchID', 'PERS_TZ', 'BatchTypeID', 'ElementQty',),
        'exec'    : '[BankDB].[dbo].[WEB_GetBatchParamValues_sp]',
        'headers' : { 
            'TID'          : 'ID параметра',
            'PName'        : 'Название параметра',
            'PValue'       : 'Значение',
            'PSortIndex'   : 'Индекс сортировки',
            'TName'        : 'Параметр конфигурации',
            'TValue'       : 'Код значения',
            'FTVLinkID'    : 'ID значения тега',
            'TagParamID'   : 'ID параметра',
            'FileTypeID'   : 'ID типа файла',
            'FileID'       : 'ID файла',
            'BatchID'      : 'ID партии',
            'PERS_TZ'      : 'Номер ТЗ',
            'BatchTypeID'  : 'ID типа партии',
            'ElementQty'   : 'Количество элементов в партии',
        },
    },
    'image': { 
        'columns' : ('FileID', 'FBody',),
        'exec'    : '[BankDB].[dbo].[WEB_GetOrderFileBodyImage_sp]',
        'headers' : { 
            'FileID'       : 'ID файла',
            'FBody'        : 'Контент заказа',
        },
    },
    'body': { 
        'columns' : ('FileID', 'FileStatusID', 'IBody',),
        'exec'    : '[BankDB].[dbo].[WEB_GetOrderFileBody_sp]',
        'headers' : { 
            'FileID'       : 'ID файла',
            'FileStatusID' : 'ID статуса файла',
            'IBody'        : 'Контент заказа',
        },
    },
    'TZ' : { 
        'columns' : ('PName', 'PValue', 'PSortIndex', 'PType', 'ElementQty',),
        'exec'    : '[BankDB].[dbo].[WEB_GetBatchParamValues_sp]',
        'headers' : { 
            'PName'        : 'Название параметра',
            'PValue'       : 'Значение',
            'ElementQty'   : 'Количество элементов в партии',
            'PSortIndex'   : 'Индекс сортировки',
            'PType'        : 'Тип параметра',
        },
        'exclude' : ('CLIENTID', 'DeliveryType', 'PackageCode',),
        'rename'  : { 
            'PlasticType'  : ('', 25),
        },
    },
    'search.batch_by_param' : { 
        'columns' : ('PERS_TZ', 'Comment', 'TagValue', 'ElementQty',),
        'params'  : "%(tz)s,%(batchtype_id)s,'%(param_name)s'",
        'exec'    : '[BankDB].[dbo].[WEB_SearchBatchForBlanks_sp]',
    },
    'materials.order' : { 
        'columns' : ('BatchType', 'ERP_TZ', 'MName', 'BatchQty', 'Qty',),
        'params'  : "%(file_id)s,%(show)s",
        'exec'    : '[BankDB].[dbo].[WEB_MaterialForFile_sp]',
        'headers' : { 
            'BatchType'    : 'Тип партии',
            'ERP_TZ'       : 'ЕРП ТЗ',
            'MName'        : 'Наименование материала',
            'BatchQty'     : 'Количество элементов в партии',
            'Qty'          : 'Зарезервировать на складе',
        },
    },
    'materials.approval' : { 
        'params'  : "%(file_id)s,'%(file_status_ids)s',0",
        'exec'    : '[BankDB].[dbo].[WEB_ApprovalMaterialOrder_sp]',
    },
    'materials.check' : { 
        'params'  : "%(file_id)s,'%(file_status_ids)s',%(check)s",
        'exec'    : '[BankDB].[dbo].[WEB_ApprovalMaterialOrder_sp]',
    },
    'persolog': { 
        'columns' : ('Date', 'Code', 'Message',),
        'headers' : { 
            'Date'         : 'Дата Время',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
        'export'  : ('Date', 'Code', 'Message',),
    },
    'infoexchangelog': { 
        'columns' : ('Date', 'Code', 'Message',),
        'headers' : { 
            'Date'         : 'Дата Время',
            'Time'         : 'Время',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
        'export' : ('Date', 'Code', 'Message',), # , 'Time'
    },
    'sdclog': { 
        'columns' : ('Date', 'Code', 'Message',),
        'headers' : { 
            'Date'         : 'Дата Время',
            'Time'         : 'Время',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
        'export'  : ('Date', 'Time', 'Code', 'Message',),
    },
    'exchangelog': { 
        'columns' : ('Date', 'Module', 'Code', 'Message',),
        'headers' : { 
            'Date'         : 'Дата Время',
            'Time'         : 'Время',
            'Module'       : 'Модуль',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
        'export'  : ('Date', 'Time', 'Module', 'Code', 'Message',),
    },
    'bankperso.semaphore': { 
        'columns' : ('LID', 'Status', 'Oper',),
        'params'  : "%(mode)s,%(oid)s,%(bid)s,null,''",
        'exec'    : '[BankDB].[dbo].[WEB_SemaphoreEvents_sp]',
    },
    # --------------------------------
    # Представления на контенте заказа
    # --------------------------------
    'cardholders' : { 
        'root'    : 'FileBody_Record',
        'tags'    : ( \
            ('FileRecNo',),
            ('PAN', 'PANWIDE',),
            ('EMBNAME1', 'FIO', 'ClientName', 'CardholderName', 'CardholderFIO', 'Cardholder', 'EMBNAME', ('FIRSTNAME', 'SECONDNAME', 'LASTNAME'), 
                ('LSTN', 'FRSN'), ('FirstName', 'SurName', 'SecondName', 'LastName'), 'EmbName', 'TRACK1NAME',),
            ('ExpireDate', 'ExpiryDate', 'EDATE', 'EDATE_YYMM', 'EXPDATE', 'EDATE_YYYYMM',),
            ('PLASTIC_CODE', 'PLASTIC_TYPE', 'PlasticID', 'ProductDesign',),
            ('CardType', 'CLIENT_ID', 'CHIP_ID', 'Card_Type',),
            ('KIND', 'PlasticType',),
            ('DeliveryType',),
            ('BRANCH_SEND_TO', 'FactAddress', 'BRANCH_NAME', 'DEST_NAME', 'DEST_BRANCH', 'DeliveryAddress', 'FACTADRESS',),
            ('EAND', 'BarCode', 'LoyaltyBarcode', 'Barcode', 'BarcodeNum', 'MPR_Barcode',),
            ('StampCode',),
            ('PackageType',),
            ('PackageCode',),
        ),
        'columns' : ('FileRecNo', 'PAN', 'Cardholder', 'ExpireDate', 'PLASTIC_CODE', 'CardType', 'KIND', 'DeliveryType', 'FactAddress', 'Barcode', 'StampCode', 'PackageType', 'PackageCode',),
        'clients' : {
            'Barcode'      : 'VBRR:CITI_BANK:BIN_BANK:PostBank',
            'StampCode'    : 'PostBank',
            'PackageCode'  : 'PostBank',
            'PackageType'  : 'PostBank',
        },
        'headers' : { 
            'FileRecNo'    : '#',
            'PAN'          : 'PAN',
            'Cardholder'   : 'ФИО клиента',
            'ExpireDate'   : 'Дата истечения',
            'PLASTIC_CODE' : 'Код пластика',
            'CardType'     : 'Тип карты',
            'KIND'         : 'Вид',
            'DeliveryType' : 'Тип доставки',
            'FactAddress'  : 'Адрес доставки',
            'Barcode'      : 'Штрих-код карты',
            'StampCode'    : 'Пломба',
            'PackageCode'  : 'Код упаковки',
            'PackageType'  : 'Упаковка',
        },
        'func'    : {'PAN' : getMaskedPAN},
    },
    'indigo' : { 
        'root'    : 'FileBody_Record',
        'tags'    : ( \
            'FileRecNo', 'ImageName', 'PAN', 'CardholderName', 'EAND',
        ),
        'unique'  : 'ImageName',
        'values'  : { 
            'Design'       : '%(ImageName)s_%(ImagePosition)s.%(ImageType)s',
            'ImageName'    : '%(ImageName)s',
            'Value'        : '%(FileRecNo)s: %(PAN)s %(EAND)s - %(CardholderName)s',
            'Count'        : '0',
            'Files'        : '',
        },
        'columns' : ('Design', 'ImageName', 'Value', 'Count', 'Files',),
        'headers' : { 
            'Design'       : 'Дизайн карты',
            'ImageName'    : 'Идентификатор',
            'Value'        : 'Список карт (FileRecNo: PAN { BARCODE } - CardholderName)',
            'Count'        : 'Кол-во',
            'Files'        : 'Файлы изображений',
        },
        'func'    : {'PAN' : getMaskedPAN, 'EAND' : getEANDBarcode },
    },
    # ---------------
    # Операции BankDB
    # ---------------
    'activate' : { 
        'params'  : '%(batch_id)s',
        'exec'    : '[BankDB].[dbo].[WEB_BatchActivate_sp]',
    },
    'changefilestatus' : { 
        'params'  : "null,null,0,%(file_id)s,%(check_file_status)s,%(new_file_status)s,null,null,null,1,%(run_batch)s,0,0,%(keep_history)s",
        'exec'    : '[BankDB].[dbo].[WEB_ChangeOrderState_sp]',
    },
    'changebatchstatus' : { 
        'params'  : "null,null,0,%(file_id)s,null,null,%(batch_id)s,null,%(new_batch_status)s,0,1,0,0",
        'exec'    : '[BankDB].[dbo].[WEB_ChangeOrderState_sp]',
    },
    'deletefile' : { 
        'params'  : "null,null,0,%(file_id)s,null,0,null,null,0,1,1,1,1",
        'exec'    : '[BankDB].[dbo].[WEB_ChangeOrderState_sp]',
    },
    'createfile'  : { 
        'params'  : "null,null,0,%(file_id)s,1,1,null,null,0,1,1,1,0",
        'exec'    : '[BankDB].[dbo].[WEB_ChangeOrderState_sp]',
    },
    'dostowin' : { 
        'params'  : "0,'%s'",
        'exec'    : '[BankDB].[dbo].[WEB_DecodeCyrillic_sp]',
    },
    'wintodos' : { 
        'params'  : "1,'%s'",
        'exec'    : '[BankDB].[dbo].[WEB_DecodeCyrillic_sp]',
    },
    # ==================
    # CARDS PERSOSTATION
    # ==================
    'cards.batches' : { 
        'columns' : ('TID', 'Client', 'FName', 'TZ', 'BQty', 'PQty', 'PersType', 'PersStatus', 'Status',), # 'BatchID', 'StatusDate'
        'view'    : '[Cards].[dbo].[WEB_Batches_vw]',
        'headers' : { 
            'TID'          : ('ID партии',       '',),
            'BatchID'      : ('ID ТЗ',           '',),
            'Client'       : ('КЛИЕНТ',          'nowrap',),
            'FName'        : ('ФАЙЛ ЗАКАЗА',     'breakable',),
            'TZ'           : ('№ ТЗ',            '',),
            'BQty'         : ('Кол-во в ТЗ',     'BQty',),
            'PQty'         : ('Кол-во в партии', 'PQty',),
            'PersType'     : ('Тип партии',      '',),
            'Status'       : ('Статус ТЗ',       'nowrap',),
            'PersStatus'   : ('Статус партии',   'nowrap',),
            'StatusDate'   : ('Дата статуса',    '',),
        },
        'export'  : ('TID', 'BatchID', 'Client', 'FName', 'TZ', 'BQty', 'PQty', 'PersType', 'Status', 'PersStatus', 'StatusDate', 'StatusID', 'PersTypeID',),
    },
    'cards.batches-log' : { 
        'columns' : ('LID', 'Status', 'StatusID', 'StatusDate', 'Oper', 'HostName', 'ApplName', 'UserName', 'ModDate'),
        'view'    : '[Cards].[dbo].[WEB_BatchesLog_vw]',
        'headers' : { 
            'LID'          : 'ID',
            'BatchID'      : 'ID ТЗ',
            'FName'        : 'ФАЙЛ ЗАКАЗА',
            'TZ'           : '№ ТЗ',
            'FQty'         : 'Кол-во',
            'Status'       : 'Наименование статуса',
            'StatusID'     : 'Код статуса',
            'StatusDate'   : 'Дата статуса',
            'Oper'         : 'Код операции',
            'HostName'     : 'Хост',
            'ApplName'     : 'Приложение',
            'UserName'     : 'Оператор',
            'ModDate'      : 'Дата изменения',
        },
        'export'  : ('LID', 'BatchID', 'TZ', 'Client', 'FName', 'FQty', 'Status', 'StatusID', 'StatusDate', 'Oper', 'HostName', 'ApplName', 'UserName', 'ModDate'),
    },
    'cards.batch-opers' : { 
        'columns' : ('TID', 'CName', 'Status', 'StatusDate',),
        'view'    : '[Cards].[dbo].[WEB_BatchOpers_vw]',
        'headers' : { 
            'TID'          : 'ID операции',
            'CName'        : 'Тип операции',
            'Status'       : 'Статус операции',
            'StatusDate'   : 'Дата статуса',
        },
        'export'  : ('TID', 'CName', 'Status', 'StatusDate', 'BatchID', 'StatusID', 'PersOperTypeID',),
    },
    'cards.batch-opers-log' : { 
        'columns' : ('LID', 'PersOperType', 'Status', 'StatusID', 'StatusDate', 'Oper', 'HostName', 'ApplName', 'UserName', 'ModDate'),
        'view'    : '[Cards].[dbo].[WEB_PersBatchOpersLog_vw]',
        'headers' : { 
            'LID'          : 'ID',
            'BatchOperID'  : 'ID операции',
            'PersBatchID'  : 'ID партии',
            'PersOperType' : 'Операция',
            'Status'       : 'Наименование статуса',
            'StatusID'     : 'Код статуса',
            'StatusDate'   : 'Дата статуса',
            'Oper'         : 'Код операции',
            'HostName'     : 'Хост',
            'ApplName'     : 'Приложение',
            'UserName'     : 'Оператор',
            'ModDate'      : 'Дата изменения',
        },
        'export'  : ('LID', 'BatchOperID', 'PersBatchID', 'Status', 'StatusID', 'StatusDate', 'PersOperTypeID', 'PersOperType', 'Oper', 'HostName', 'ApplName', 'UserName', 'ModDate'),
    },
    'cards.batch-params' : { 
        'columns' : ('TID', 'PType', 'PName', 'PValue',),
        'view'    : '[Cards].[dbo].[WEB_BatchParams_vw]',
        'headers' : { 
            'TID'          : 'ID параметра',
            'PType'        : 'Тип параметра',
            'PName'        : 'Наименование параметра',
            'PValue'       : 'Значение',
        },
        'export'  : ('TID', 'BatchID', 'TZ', 'PType', 'PName', 'PValue',),
    },
    'cards.pers-batch-opers' : { 
        'columns' : ('TID', 'Oper', 'Status', 'StatusDate',),
        'view'    : '[Cards].[dbo].[WEB_PersBatchOpers_vw]',
        'headers' : { 
            'TID'          : 'ID операции',
            'Oper'         : 'Тип операции',
            'Status'       : 'Статус операции',
            'StatusDate'   : 'Дата статуса',
        },
        'export'  : ('TID', 'Oper', 'Status', 'StatusDate', 'PersBatchID', 'PersOperTypeID', 'PersBatchOperStatusID',),
    },
    'cards.batch-oper-params' : { 
        'columns' : ('TID', 'PName', 'PValue',),
        'view'    : '[Cards].[dbo].[WEB_BatchOperParams_vw]',
        'headers' : { 
            'TID'          : 'ID параметра',
            'PName'        : 'Наименование параметра',
            'PValue'       : 'Значение',
        },
        'export'  : ('TID', 'PName', 'PValue', 'BatchID', 'PersBatchID', 'BatchOperID', 'BatchOperTypeID',),
    },
    'cards.batch-units' : { 
        'columns' : ('TID', 'FileRecNo', 'PAN', 'Status', 'StatusDate',), #, 'BatchStatus'
        'view'    : '[Cards].[dbo].[WEB_BatchUnits_vw]',
        'headers' : { 
            'TID'          : 'ID карты',
            'FileRecNo'    : 'Номер записи',
            'PAN'          : 'PAN',
            'Status'       : 'Наименование статуса',
            'BatchStatus'  : 'Статус партии',
            'StatusDate'   : 'Дата статуса',
        },
        'export'  : ('TID', 'FileRecNo', 'PAN', 'Status', 'BatchStatus', 'StatusDate', 'BatchID', 'StatusID'),
    },
    'cards.clients' : { 
        'columns' : ('Client',),
        'view'    : '[Cards].[dbo].[WEB_Clients_vw]',
    },
    'cards.files' : { 
        'columns' : ('Client', 'FileName',),
        'view'    : '[Cards].[dbo].[WEB_Files_vw]',
    },
    'cards.perstypes' : { 
        'columns' : ('TID', 'CName',),
        'view'    : '[Cards].[dbo].[WEB_PersTypes_vw]',
    },
    'cards.statuses' : { 
        'columns' : ('TID', 'CName',),
        'view'    : '[Cards].[dbo].[WEB_Statuses_vw]',
    },
    'cards.persstatuses' : { 
        'columns' : ('CName',),
        'view'    : '[Cards].[dbo].[WEB_GetPersBatchStatuses_fn]()',
    },
    'cards.semaphore': { 
        'columns' : ('LID', 'Status', 'Oper',),
        'params'  : "%(mode)s,%(oid)s,%(bid)s,null,''",
        'exec'    : '[Cards].[dbo].[WEB_SemaphoreEvents_sp]',
    },
    # --------------
    # Операции Cards
    # --------------
    'cards.activate' : { 
        'params'  : "%(pers_id)s",
        'exec'    : '[Cards].[dbo].[WEB_PersBatch_Activate_sp]',
    },
    'cards.reject' : { 
        'params'  : "%(pers_id)s",
        'exec'    : '[Cards].[dbo].[WEB_PersBatch_Reject_sp]',
    },
    # -------------------------------
    # Параметры партий персонализации
    # -------------------------------
    'cards.plastic-params' : { 
        'exec'    : '[Cards].[dbo].[WEB_BatchFreeParams_For_PlasticOrder_sp]',
        'params'  : "'%(pers_ids)s'",
        'fields'  : { 
            'BatchID'      : (0,  'BatchID',       'ID партии',               0, None),
            'ClientIDStr'  : (1,  'ClientIDStr',   'Идентификатор клиента',   0, ''),
            'BQty'         : (2,  'Qty',           'Кол-во (в партии/ТЗ)',    0, 0),
            'PersBatchType': (3,  'PersBatchType', 'Тип партии',              1, None),
            'PersBatchID'  : (4,  'PersBatchID',   'ID ТЗ',                   0, None),
            'SysBatchID'   : (5,  'SysBatchID',    '№ ТЗ',                    0, None),
            'CardsName'    : (6,  'Column1',       'Наименование карт',       1, ''),
            'CardsType'    : (7,  'Column2',       'Вид карт',                1, ''),
            'PlasticType'  : (8,  'Column3',       'Тип карт',                1, ''),
            'ERP_TZ'       : (10, 'Column4',       'ERP ТЗ',                  0, None),
            'BlankPaper'   : (11, 'Column10',      'Бланк листовки',          1, ''),
            'Urgency'      : (12, 'Column5',       'Срочность:[СРОЧНО 6ч.!]', 1, ''),
            'FileName'     : (13, 'Column6',       'Имя файла',               0, ''),
            'ReadyDate'    : (14, 'Column7',       'Ожидаемая дата отгрузки', 0, ''),
            'ClientName'   : (15, 'Column8',       'Имя клиента',             1, ''),
            'FQty'         : (16, 'Column9',       'Кол-во (в файле)',        0, 0),
            'SumQty'       : (17, 'Column11',      'Сумма',                   0, 0),
        },
        'TZ' : { 
            'Column1'      : 'Клиент',
            'Column2'      : 'Тип карт',
            'Column3'      : 'Тип пластика',
            'Column4'      : 'ERP ТЗ',
        },
    },
    'cards.plastic-params-new' : { 
        'exec'    : '[Cards].[dbo].[WEB_BatchFreeParams_For_PlasticOrderNew_sp]',
        'params'  : "'%(pers_ids)s'",
        'fields'  : { 
            'Qty'          : (0, 'Qty',     'Кол-во',                         0, 0),
            'CardsName'    : (1, 'Column1', 'Наименование карт',              1, ''),
            'CardsType'    : (2, 'Column2', 'Вид карт',                       0, ''),
            'PlasticType'  : (3, 'Column3', 'Тип карт',                       1, ''),
            'ERP_TZ'       : (4, 'Column4', 'ERP_TZ',                         0, None),
            'BatchesInfo'  : (5, 'Column5', '[(№ ТЗ/партии, кол-во XXX)...]', 1, ''),
            'FileName'     : (6, 'Column6', 'Имя файла',                      0, ''),
            'ReadyDate'    : (7, 'Column7', 'Ожидаемая дата отгрузки',        0, ''),
            'ClientName'   : (8, 'Column8', 'Имя клиента',                    1, ''),
        },
        'TZ' : { 
            'Column1'      : 'Клиент',
            'Column2'      : 'Тип карт',
            'Column3'      : 'Тип пластика',
            'Column4'      : 'ERP ТЗ',
        },
    },
    'cards.plastic-params-info' : { 
        'exec'    : '[Cards].[dbo].[W_GetClientIDStr_fn]',
        'params'  : "%(pers_id)s",
        'fields'  : { 
            'ClientIDStr'  : (0, 'ClientIDStr',         'Идентификатор клиента',   0, ''),
            'SysBatchID'   : (1, 'SysBatchID',          '№ ТЗ',                    0, None),
            'BQty'         : (2, 'BatchElementQty',     'Кол-во (в ТЗ)',           0, 0),
            'PQty'         : (3, 'PersBatchElementQty', 'Кол-во (в партии)',       0, 0),
            'PersBatchType': (4, 'PersBatchType',       'Тип партии',              1, None),
            'FileName'     : (5, 'OrderFName',          'Имя файла',               0, ''),
        },
    },
    # ==================
    # PRELOADER HANDLERS
    # ==================
    'preloads' : { 
        'columns' : ('PreloadID', 'FName', 'FQty', 'BankName', 'StartedDate', 'FinishedDate', 'ErrorCode', 'OrderNum', 'FinalMessage', 'RegisterDate',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersPreload_vw]',
        'headers' : { 
            'PreloadID'    : ('ID загрузки',                    '',),
            'FName'        : ('ФАЙЛ',                           '',),
            'FQty'         : ('Кол-во',                         '',),
            'BankName'     : ('КЛИЕНТ',                         '',),
            'StartedDate'  : ('Дата старта',                    '',),
            'FinishedDate' : ('Дата завершения',                '',),
            'ErrorCode'    : ('Код ошибки',                     '',),
            'OrderNum'     : ('НОМЕР ЗАКАЗА ПРОИЗВОДСТВА (1С)', '',),
            'FinalMessage' : ('Сообщение обработчика',          '',),
            'RegisterDate' : ('Дата регистрации',               '',),
        },
        'clients' : 'ClientID',
        'export'  : ('PreloadID', 'FName', 'FQty', 'BankName', 'StartedDate', 'FinishedDate', 'ErrorCode', 'OrderNum', 'RegisterDate',),
    },
    'articles' : { 
        'columns' : ('[#]', 'Article', 'BIN', 'V', 'Q', 'unavailable',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersPreloadArticleList_vw]',
        'headers' : { 
            '[#]'          : '№',
            'Article'      : 'Артикул',
            'BIN'          : 'БИН',
            'V'            : 'Вид',
            'Q'            : 'Резерв',
            'unavailable'  : 'Наличие на складе',
        },
    },
    # =======================================
    # BANKPERSO ORDER STATE MANAGEMENT SYSTEM
    # =======================================
    'orderstate-orders' : { 
        'columns' : ('TID', 'Client', 'BP_FileID', 'PackageName', 'Qty', 'Host', 'BaseFolder', 'ArchiveFolder', 'RD',),
        'view'    : '[OrderState].[dbo].[SHOW_Orders_vw]',
        'headers' : { 
            'TID'          : ('ID заказа',              '',),
            'ClientID'     : ('ID клиента',             '',),
            'Client'       : ('КЛИЕНТ',                 '',),
            'Aliases'      : ('Алиасы клиента',         '',),
            'BP_FileID'    : ('ID файла BP',            '',),
            'PackageName'  : ('ИДЕНТИФИКАТОР ПАКЕТА',   '',),
            'Qty'          : ('Кол-во',                 '',),
            'Host'         : ('ХОСТ',                   '',),
            'BaseFolder'   : ('Базовый маршрут',        '',),
            'ArchiveFolder': ('АРХИВ',                  '',),
            'RD'           : ('Дата регистрации',       '',),
            'HasError'     : ('ОШИБКИ',                 '',),
        },
        'clients' : 'ClientID',
        'export'  : ('TID', 'ClientID', 'Client', 'Aliases', 'BP_FileID', 'PackageName', 'Qty', 'Host', 'BaseFolder', 'ArchiveFolder', 'RD', 'HasError',),
    },
    'orderstate-orders:by-type' : { 
        'columns' : 'self',
        'params'  : "%(client_id)s,%(config_id)s,%(action_id)s,'%(type)s','%(date_from)s','%(date_to)s',%(sort)s,''",
        'exec'    : '[OrderState].[dbo].[WEB_GetOrdersByConfigType_sp]',
        'headers' : 'self',
        'clients' : 'ClientID',
        'export'  : 'self',
    },
    'orderstate-events' : { 
        'columns' : ('TID', 'Action', 'Type', 'ToFolder', 'Result',), #, 'Started', 'Finished', 'Duration', 'Weight', 'RD',
        'view'    : '[OrderState].[dbo].[SHOW_vw]',
        'headers' : { 
            'TID'          : 'ID события',
            'ClientID'     : 'ID клиента',
            'ConfigID'     : 'ID сценария',
            'OrderID'      : 'ID заказа',
            'ActionID'     : 'ID операции',
            'Address'      : 'Событие',
            'Action'       : 'Операция', 
            'Type'         : 'Тип', 
            'ToFolder'     : 'МАРШРУТ НАЗНАЧЕНИЯ', 
            'Started'      : 'Дата старта', 
            'Finished'     : 'Дата завершения', 
            'Duration'     : '(мсек)', 
            'Weight'       : '%', 
            'Result'       : 'Результат', 
            'ErrorMessage' : 'Текст ошибки', 
            'RD'           : 'Дата регистрации',
        },
        'export'  : ('TID', 'ClientID', 'ConfigID', 'ActionID', 'OrderID', 'DestinationFileID', 'Address', 'Action', 'Type', 'ToFolder', 'Started', 'Finished', 'Duration', 'Weight', 'Result', 'ErrorMessage', 'RD'),
    },
    'orderstate-files' : { 
        'columns' : ('TID', 'Address', 'Name', 'IsError'), #, 'ConfigID', 'OrderID'
        'view'    : '[OrderState].[dbo].[SHOW_Files_vw]',
        'headers' : { 
            'TID'          : 'ID файла',
            'ConfigID'     : 'ID сценария',
            'OrderID'      : 'ID заказа',
            'Address'      : 'Событие',
            'Name'         : 'ИМЯ ФАЙЛА', 
            'IsError'      : 'Ошибка',
        },
        'export'  : ('TID', 'ConfigID', 'OrderID', 'Address', 'Name', 'IsError'),
    },
    'orderstate-errors' : { 
        'columns' : ('SourceFileID', 'OrderID', 'Address', 'Started', 'Finished', 'Result', 'ErrorMessage', 'RD',),
        'view'    : '[OrderState].[dbo].[SHOW_Errors_vw]',
        'headers' : { 
            'SourceFileID' : 'ID файла', 
            'OrderID'      : 'ID заказа',
            'Address'      : 'Событие',
            'Started'      : 'Дата старта', 
            'Finished'     : 'Дата завершения', 
            'Duration'     : '(мсек)', 
            'Weight'       : '%', 
            'Result'       : 'Результат', 
            'ErrorMessage' : 'СООБЩЕНИЕ ОБ ОШИБКЕ', 
            'RD'           : 'Дата регистрации',
        },
        'export'  : ('SourceFileID', 'OrderID', 'Address', 'Started', 'Finished', 'Duration', 'Weight', 'Result', 'ErrorMessage', 'RD'),
    },
    'orderstate-certificates' : { 
        'columns' : ('Event', 'Info', 'RD',),
        'view'    : '[OrderState].[dbo].[SHOW_OrderCertificates_vw]',
        'headers' : { 
            'TID'          : 'ID сертификата',
            'OrderID'      : 'ID заказа',
            'FileID'       : 'ID файла',
            'Address'      : 'Событие',
            'Name'         : 'Имя файла', 
            'Event'        : 'Событие/Файл',
            'Info'         : 'ИНФОРМАЦИЯ О СЕРТИФИКАТЕ',
            'RD'           : 'Дата регистрации',
        },
        'export'  : ('TID', 'OrderID', 'FileID', 'Address', 'Name', 'Info', 'RD',),
    },
    'orderstate-aliases' : { 
        'columns' : ('TID', 'Name', 'Title', 'Aliases',),
        'view'    : '[OrderState].[dbo].[SHOW_Aliases_vw]',
        'headers' : { 
            'TID'          : 'ID клиента',
            'Name'         : 'Клиент', 
            'Title'        : 'Полное наименование',
            'Aliases'      : 'Алиасы',
        },
        'export'  : ('TID', 'Name', 'Title', 'Aliases',),
    },
    'orderstate-actions' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[OrderState].[dbo].[DIC_Actions_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Операция',
        },
        'clients' : 'TID',
    },
    'orderstate-clients' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[OrderState].[dbo].[DIC_Clients_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Клиент',
        },
        'clients' : 'TID',
    },
    'orderstate-configs' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[OrderState].[dbo].[DIC_Configs_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Сценарий',
        },
        'clients' : 'TID',
    },
    'orderstate-types' : { 
        'columns' : ('Type',),
        'view'    : '[OrderState].[dbo].[DIC_Configs_tb]',
    },
    'orderstate-eventinfo' : { 
        'columns' : ('PName', 'PValue', 'PSortIndex', 'PType',),
        'exec'    : '[OrderState].[dbo].[WEB_GetEventInfo_sp]',
        'headers' : { 
            'PName'        : 'Название параметра',
            'PValue'       : 'Значение',
            'PSortIndex'   : 'Индекс сортировки',
            'PType'        : 'Тип параметра',
        },
    },
    'orderstate-log': { 
        'columns' : ('Date', 'Code', 'Message',),
        'headers' : { 
            'Date'         : 'Дата Время',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
    },
    # ======================
    # BANKPERSO CONFIGURATOR
    # ======================
    'configurator-files-default' : { \
        'columns' : ('TID', 'ClientID', 'Client', 'FileType', 'ReportPrefix',),
        'view'    : '[BankDB].[dbo].[WEB_FileTypesDefault_vw]',
        'headers' : { \
            'TID'          : ('ID типа файла',  '',),
            'ClientID'     : ('ID клиента',     '',),
            'Client'       : ('КЛИЕНТ',         '',),
            'FileType'     : ('ТИП ФАЙЛА',      '',),
            'ReportPrefix' : ('Префикс отчета', '',),
        },
        'clients' : 'ClientID',
        'export'  : (
            'TID', 
            'Client', 'FileType', 'ReportPrefix', 
            'ClientID', 'FileTypeID',
            ),
    },
    'configurator-files' : { 
        'columns' : ('TID', 'ClientID', 'Client', 'FileType', 'ReportPrefix',),
        'view'    : '[BankDB].[dbo].[WEB_FileTypes_vw]',
        'headers' : { 
            'TID'          : ('ID типа файла',  '',),
            'ClientID'     : ('ID клиента',     '',),
            'Client'       : ('КЛИЕНТ',         '',),
            'FileType'     : ('ТИП ФАЙЛА',      '',),
            'ReportPrefix' : ('Префикс отчета', '',),
        },
        'clients' : 'ClientID',
        'export'  : (
            'TID', 
            'Client', 'FileType', 'ReportPrefix', 
            'ClientID', 'FileTypeID', 
            'BatchTypeID',
            ),
    },
    'configurator-batches' : { 
        'columns'   : ('TID', 'BatchTypeID', 'BatchType', 'BatchMaxQty', 'IsErpBatch', 'CreateBatchSortIndex', 'CreateBatchGroupIndex',), #, 'BatchCreateType', 'BatchResultType'
        'view'      : '[BankDB].[dbo].[WEB_BatchTypes_vw]',
        'headers'   : { 
            'TID'                   : 'ID партии',
            'BatchTypeID'           : 'ID типа партии',
            'FileType'              : 'Тип файла',
            'BatchType'             : 'ТИП ПАРТИИ',
            'CreateType'            : 'Тип создания',
            'ResultType'            : 'Тип результата',
            'BatchMaxQty'           : 'Максимальное количество карт',
            'IsErpBatch'            : 'Флаг ERP', 
            'CreateBatchSortIndex'  : 'Индекс сортировки', 
            'CreateBatchGroupIndex' : 'Индекс группировки', 
        },
        'export'    : (
            'TID', 
            'FileType', 'BatchType', 'BatchCreateType', 'BatchResultType', 'BatchMaxQty', 'IsErpBatch', 'CreateBatchSortIndex', 'CreateBatchGroupIndex', 
            'FileTypeID', 'BatchTypeID', 'BatchCreateTypeID', 'BatchResultTypeID',
        ),
    },
    'configurator-processes' : { 
        'columns' : ('TID', 'FileType', 'BatchType', 'CurrFileStatus', 'NextFileStatus', 'CloseFileStatus', 'ActivateBatchStatus_', 'ARMBatchStatus_', 'Memo'),
        'view'    : '[BankDB].[dbo].[WEB_FileProcesses_vw]',
        'headers' : { 
            'TID'                 : 'ID сценария',
            'FileType'            : 'Тип файла', 
            'BatchType'           : 'Тип партии',
            'CurrFileStatus'      : 'Текущий статус файла', 
            'NextFileStatus'      : 'Следующий статус файла', 
            'CloseFileStatus'     : 'Конечный статус файла', 
            'ActivateBatchStatus_': 'Статус активации партии', 
            'ARMBatchStatus_'     : 'Статус партии в АРМ', 
            'Memo'                : 'Примечания',
        },
        'export'  : (
            'TID', 
            'FileType', 'BatchType', 'CurrFileStatus', 'NextFileStatus', 'CloseFileStatus', 'ActivateBatchStatus_', 'ARMBatchStatus_', 'Memo', 
            'ActivateBatchStatus', 'ARMBatchStatus', 'CurrFileStatusID', 'NextFileStatusID', 'CloseFileStatusID', 'LinkID', 'FileTypeID', 'BatchTypeID', 'BatchCreateTypeID', 'BatchResultTypeID',
            ),
    },
    'configurator-opers' : { 
        'columns' : ('TID', 'FileType', 'BatchType', 'OperTypeName', 'OperType', 'OperSortIndex',),
        'view'    : '[BankDB].[dbo].[WEB_FileOpers_vw]',
        'headers' : { 
            'TID'                 : 'ID операции',
            'FileType'            : 'Тип файла', 
            'BatchType'           : 'Тип партии',
            'OperTypeName'        : 'Тип операции',
            'OperType'            : 'ОПЕРАЦИЯ',
            'OperSortIndex'       : 'Индекс сортировки',
        },
        'export'  : (
            'TID', 
            'FileType', 'BatchType', 'OperTypeName', 'OperType', 'OperSortIndex', 
            'FBLinkID', 'OperID', 'BatchTypeID', 'FileTypeID'
            ),
    },
    'configurator-operparams' : { 
        'columns' : ('TID', 'FileType', 'BatchType', 'OperTypeName', 'OperType', 'PName', 'PValue', 'Comment',),
        'view'    : '[BankDB].[dbo].[WEB_FileOperParams_vw]',
        'headers' : { 
            'TID'                 : 'ID параметра',
            'FileType'            : 'Тип файла', 
            'BatchType'           : 'Тип партии',
            'OperTypeName'        : 'Тип операции',
            'OperType'            : 'Операция',
            'PName'               : 'ПАРАМЕТР',
            'PValue'              : 'Значение параметра',
            'Comment'             : 'Примечания',
        },
        'export'  : (
            'TID', 
            'FileType', 'BatchType', 'OperTypeName', 'OperType', 'PName', 'PValue', 'Comment', 
            'FBOLinkID', 'FileTypeID', 'BatchTypeID', 'FBLinkID', 'OperID',
            ),
    },
    'configurator-filters' : { 
        'columns' : ('TID', 'FileType', 'BatchType', 'TName', 'CriticalValues',),
        'view'    : '[BankDB].[dbo].[WEB_FileFilters_vw]',
        'headers' : { 
            'TID'                 : 'ID фильтра',
            'FileType'            : 'Тип файла', 
            'BatchType'           : 'Тип партии',
            'TName'               : 'Тег',
            'CriticalValues'      : 'КРИТИЧЕСКОЕ ЗНАЧЕНИЕ',
        },
        'export'  : (
            'TID', 
            'FileType', 'BatchType', 'TName', 'CriticalValues', 
            'FileTypeID', 'BatchTypeID', 'FBLinkID', 'FTLinkID',
            ),
    },
    'configurator-tags' : { 
        'columns' : ('TID', 'FileType', 'TName', 'TMemo',),
        'view'    : '[BankDB].[dbo].[WEB_FileTags_vw]',
        'headers' : { 
            'TID'                 : 'ID тега',
            'FileType'            : 'Тип файла', 
            'TName'               : 'ТЕГ',
            'TMemo'               : 'Примечания',
        },
        'export'  : (
            'TID', 
            'FileType', 'TName', 'TMemo', 
            'FileTypeID', 'ClientID',
            ),
    },
    'configurator-tagvalues' : { 
        'columns' : ('TID', 'FileType', 'TName', 'TValue',),
        'view'    : '[BankDB].[dbo].[WEB_FileTagValues_vw]',
        'headers' : { 
            'TID'                 : 'ID параметра',
            'FileType'            : 'Тип файла', 
            'TName'               : 'Тег',
            'TValue'              : 'ЗНАЧЕНИЕ',
            'TagValue'            : 'Тег ТЗ'
        },
        'export'  : (
            'TID', 
            'FileType', 'TName', 'TValue', 'TagValue',
            'FTLinkID', 'FileTypeID', 'ClientID',
            ),
    },
    'configurator-tzs' : { 
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'PName', 'PValue', 'PSortIndex', 'Comment',),
        'view'    : '[BankDB].[dbo].[WEB_FileTZs_vw]',
        'headers' : { 
            'TID'                 : 'ID параметра',
            'FileType'            : 'Тип файла', 
            'TName'               : 'Тег',
            'TValue'              : 'Значение тега',
            'PName'               : 'ПАРАМЕТР ТЗ',
            'PValue'              : 'ЗНАЧЕНИЕ', 
            'PSortIndex'          : 'Индекс сортировки',
            'Comment'             : 'Примечания',
        },
        'export'  : (
            'TID', 
            'FileType', 'TName', 'TValue', 'TagValue', 'PName', 'PValue', 'Comment', 'PSortIndex', 
            'FileTypeID', 'FTVLinkID', 'TagParamID',
            ),
    },
    'configurator-erpcodes' : { 
        'columns' : ('TID', 'FileType', 'BatchType', 'TName', 'TValue', 'ERP_CODE', 'AdditionalInfo',),
        'view'    : '[BankDB].[dbo].[WEB_FileERPCodes_vw]',
        'headers' : { 
            'TID'                 : 'ID параметра',
            'FileType'            : 'Тип файла', 
            'BatchType'           : 'Тип партии',
            'TName'               : 'Тег',
            'TValue'              : 'Значение тега',
            'ERP_CODE'            : 'КОД ЕРП', 
            'AdditionalInfo'      : 'Дополнительная информация',
        },
        'export'  : (
            'TID', 
            'FileType', 'BatchType', 'TName', 'TValue', 'TagValue', 'ERP_CODE', 'AdditionalInfo', 
            'FileTypeID', 'BatchTypeID', 'FTVLinkID',
            ),
    },
    'configurator-materials' : { 
        'columns' : ('TID', 'FileType', 'BatchType', 'TName', 'TValue', 'PName', 'QtyMode', 'MMin', 'MBadPercent',),
        'view'    : '[BankDB].[dbo].[WEB_FileMaterials_vw]',
        'headers' : { 
            'TID'                 : 'ID параметра',
            'FileType'            : 'Тип файла', 
            'BatchType'           : 'Тип партии',
            'TName'               : 'Тег',
            'TValue'              : 'Значение',
            'PName'               : 'МАТЕРИАЛ', 
            'QtyMode'             : 'Кол-во', 
            'MMin'                : 'Мин', 
            'MBadPercent'         : 'Брак, %',
        },
        'export'  : (
            'TID', 
            'FileType', 'BatchType', 'TName', 'TValue', 'TagValue', 'PName', 'QtyMode', 'MMin', 'MBadPercent', 
            'FileTypeID', 'BatchTypeID', 'FTVLinkID', 'TagParamID',
            ),
    },
    'configurator-posts' : { 
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'PName', 'PValue', 'Comment',),
        'view'    : '[BankDB].[dbo].[WEB_FilePosts_vw]',
        'headers' : { 
            'TID'                 : 'ID параметра',
            'FileType'            : 'Тип файла', 
            'TName'               : 'Тег',
            'TValue'              : 'Значение',
            'PName'               : 'ПАРАМЕТР ПОЧТЫ', 
            'PValue'              : 'Значение', 
            'Comment'             : 'Примечания',
        },
        'export'  : (
            'TID', 
            'FileType', 'TName', 'TValue', 'TagValue', 'PName', 'PValue', 'Comment', 
            'FileTypeID', 'FTVLinkID', 'TagParamID',
            ),
    },
    'configurator-tagopers' : { 
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'OperType', 'Oper', 'PName', 'PValue', 'OperSortIndex', 'Comment',),
        'view'    : '[BankDB].[dbo].[WEB_FileTagOpers_vw]',
        'headers' : { 
            'TID'                 : 'ID параметра',
            'FileType'            : 'Тип файла', 
            'TName'               : 'Тег',
            'TValue'              : 'Значение тега',
            'PName'               : 'Параметр тега', 
            'OperType'            : 'Тип операции', 
            'Oper'                : 'ОПЕРАЦИЯ', 
            'PValue'              : 'ЗНАЧЕНИЕ', 
            'OperSortIndex'       : 'Индекс сортировки',
            'Comment'             : 'Примечания',
        },
        'export'  : (
            'TID', 
            'FileType', 'TName', 'TValue', 'TagValue', 'PName', 'PValue', 'OperType', 'Oper', 'OperSortIndex', 'Comment', 
            'FileTypeID', 'FTVLinkID', 'TagParamID', 'OperTypeID'
            ),
    },
    'configurator-tagoperparams' : { 
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'OperTypeValue', 'OperValue', 'PName', 'PValue',),
        'view'    : '[BankDB].[dbo].[WEB_FileTagOperParams_vw]',
        'headers' : { 
            'TID'                 : 'ID параметра',
            'FileType'            : 'Тип файла', 
            'TName'               : 'Тег',
            'TValue'              : 'Значение тега',
            'OperTypeValue'       : 'Тип операции', 
            'Oper'                : 'Операция',
            'PName'               : 'ПАРАМЕТР ОПЕРАЦИИ', 
            'OperValue'           : 'Операция', 
            'PValue'              : 'ЗНАЧЕНИЕ', 
        },
        'export'  : (
            'TID', 
            'FileType', 'TName', 'TValue', 'TagValue', 'OperType', 'Oper', 'OperTypeValue', 'OperValue', 'PName', 'PValue', 
            'FileTypeID', 'FTV_OPER_ID', 'TagParamID',
            ),
    },
    'configurator-processparams' : { 
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'PName', 'PValue', 'Comment', 'PSortIndex',),
        'view'    : '[BankDB].[dbo].[WEB_FileProcessParams_vw]',
        'headers' : { 
            'TID'                 : 'ID параметра',
            'FileType'            : 'Тип файла', 
            'TName'               : 'Тег',
            'TValue'              : 'Значение',
            'PName'               : 'ПАРАМЕТР ПРОЦЕССА', 
            'PValue'              : 'ЗНАЧЕНИЕ', 
            'Comment'             : 'Примечания',
            'PSortIndex'          : 'Индекс сортировки',
        },
        'export'  : (
            'TID', 
            'FileType', 'TName', 'TValue', 'TagValue', 'PName', 'PValue', 'Comment', 'PSortIndex', 
            'FileTypeID', 'FTVLinkID', 'TagParamID',
            ),
    },
    # --------------------
    # Фильтр конфигуратора
    # --------------------
    'configurator-clients' : { 
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_Clients_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'CName'        : 'Клиент',
        },
        'clients' : 'TID',
    },
    'configurator-filetypes' : { 
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'CName'        : 'Тип файла',
        },
        'filetypes' : 'TID',
    },
    'configurator-batchtypes' : { 
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_BatchType_tb]',
        'headers' : { 
            'TID'          : 'ID',
            'BatchType'    : 'Тип партии',
        },
        'batchtypes' : 'TID',
    },
    'configurator-batchinfo' : { 
        'columns' : ('PName', 'PValue', 'PSortIndex', 'PType',),
        'exec'    : '[BankDB].[dbo].[WEB_GetBatchTypeInfo_sp]',
        'headers' : { 
            'PName'        : 'Название параметра',
            'PValue'       : 'Значение',
            'PSortIndex'   : 'Индекс сортировки',
            'PType'        : 'Тип параметра',
        },
    },
    # ==============
    # LOGGER SERVICE
    # ==============
    'orderlog-messages' : { 
        'columns' : ('TID', 'IP', 'Root', 'Module', 'LogFile', 'Code', 'Count', 'Message', 'EventDate',),
        'view'    : '[OrderLog].[dbo].[WEB_OrderMessages_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'FileID'       : 'ID файла',
            'Client'       : 'КЛИЕНТ',
            'FileName'     : 'ФАЙЛ',
            'BatchID'      : 'ID партии',
            'Code'         : 'Результат',
            'Count'        : 'Всего сообщений',
            'Message'      : 'СООБЩЕНИЕ',
            'IsError'      : 'Ошибка',
            'IsWarning'    : 'Предупреждение',
            'IsOk'         : 'OK',
            'EventDate'    : 'Дата/Время',
        },
        'export'  : ('TID', 'SourceID', 'ModuleID', 'LogID', 'FileID', 'FileName', 'BatchID', 'Client', 'Code', 'Count', 'Message', 'IsError', 'IsWarning', 'IsInfo', 'SystemType', 'IP', 'Root', 'Module', 'LogFile', 'EventDate', 'RD'),
    },
    'orderlog-check-source' : { 
        'params'  : "0,'%(root)s','%(ip)s','%(ctype)s',null",
        'args'    : '0,%s,%s,%s,null',
        'exec'    : '[OrderLog].[dbo].[CHECK_Source_sp]',
    },
    'orderlog-check-module' : { 
        'params'  : "0,%(source_id)s,'%(cname)s','%(cpath)s',null",
        'args'    : '0,%d,%s,%s,null',
        'exec'    : '[OrderLog].[dbo].[CHECK_Module_sp]',
    },
    'orderlog-check-log' : { 
        'params'  : "0,%(source_id)s,%(module_id)s,'%(cname)s',null",
        'args'    : '0,%d,%d,%s,null',
        'exec'    : '[OrderLog].[dbo].[CHECK_Log_sp]',
    },
    'orderlog-register-log-message' : { 
        'params'  : "0,%(source_id)s,%(module_id)s,%(log_id)s,'%(source_info)s','%(module_info)s','%(log_info)s',%(fileid)s,%(batchid)s,'%(client)s','%(filename)s','%(code)s',%(count)s,'%(message)s','%(event_date)s','%(rd)s',null",
        'args'    : '0,%d,%d,%d,%s,%s,%s,%d,%d,%s,%s,%s,%d,%s,%s,%s,null',
        'exec'    : '[OrderLog].[dbo].[REGISTER_LogMessage_sp]',
    },
    # =======================
    # PERSOSTATION BATCH TIME
    # =======================
    'persostation-actions' : { 
        'columns' : ('OrderID', 'BP_FileID', 'Client', 'FName', 'FQty', 'RegisterDate',),
        'view'    : '[BatchTime].[dbo].[WEB_Actions_vw]',
        'headers' : { 
            'TID'          : ('ID',                 ''),
            'OrderID'      : ('ID',                 ''),
            'BP_ClientID'  : ('BP-ID клиента',      ''),
            'BP_FileID'    : ('BP-ID файла',        ''),
            'BP_BatchID'   : ('BP-ID партии',       ''),
            'Client'       : ('КЛИЕНТ',             'nowrap'),
            'FName'        : ('ФАЙЛ',               'nowrap'),
            'FQty'         : ('Кол-во в файле',     ''),
            'BatchName'    : ('ПАРТИЯ',             ''),
            'BatchTypeID'  : ('Тип партии',         ''),
            'BatchNo'      : ('Кол-во в файле',     ''),
            'TZ'           : ('ТЗ',                 ''),
            'ElementQty'   : ('Кол-во в партии',    ''),
            'Operator'     : ('Оператор',           ''),
            'RegisterDate' : ('Дата файла',         ''),
            'RD'           : ('Дата регистрации',   ''),
        },
        'export'  : ('TID', 'ClientID', 'OrderID', 'BatchID', 'BP_ClientID', 'BP_FileID', 'BP_BatchID', 'Client', 'FName', 'FQty', 'RegisterDate', 'BatchName', 'BatchTypeID', 'BatchNo', 'TZ', 'ElementQty', 'Operator', 'RD',),
    },
    'persostation-clients' : { 
        'columns' : ('TID', 'Client',),
        'view'    : '[BatchTime].[dbo].[WEB_Clients_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Client'       : 'КЛИЕНТ',
        },
    },
    'persostation-orders' : { 
        'columns' : ('TID', 'BP_FileID', 'Client', 'FName', 'FQty', 'RegisterDate',),
        'view'    : '[BatchTime].[dbo].[WEB_Orders_vw]',
        'headers' : { 
            'TID'          : ('ID',                 ''),
            'ClientID'     : ('ID клиента',         ''),
            'BP_ClientID'  : ('BP-ID клиента',      ''), 
            'BP_FileID'    : ('BP-ID файла',        ''),
            'BP_BatchID'   : ('BP-ID партии',       ''),
            'Client'       : ('КЛИЕНТ',             'nowrap',),
            'FName'        : ('ФАЙЛ',               'nowrap',),
            'FQty'         : ('Кол-во в файле',     ''),
            'RegisterDate' : ('Дата файла',         ''),
        },
        'export'  : ('TID', 'ClientID', 'BP_ClientID', 'BP_FileID', 'Client', 'FName', 'FQty', 'RegisterDate',),
    },
    'persostation-batches' : { 
        'columns' : ('BatchID', 'BP_BatchID', 'BatchName', 'BatchTypeID', 'BatchNo', 'TZ', 'ElementQty',),
        'view'    : '[BatchTime].[dbo].[WEB_Batches_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'BatchID'      : 'ID',
            'BP_FileID'    : 'BP-ID файла',
            'BP_BatchID'   : 'BP-ID партии',
            'Client'       : 'КЛИЕНТ',
            'FName'        : 'ФАЙЛ',
            'FQty'         : 'Кол-во в файле',
            'RegisterDate' : 'Дата файла',
            'BatchName'    : 'ПАРТИЯ',
            'BatchTypeID'  : 'Тип партии',
            'BatchNo'      : '№ партии',
            'TZ'           : 'ТЗ',
            'ElementQty'   : 'Кол-во в партии',
        },
        'export'  : ('TID', 'BP_FileID', 'BP_BatchID', 'FName', 'FQty', 'BatchName', 'BatchTypeID', 'BatchNo', 'TZ', 'ElementQty',),
    },
    'persostation-batchtypes' : { 
        'columns' : ('BatchTypeID', 'BatchName',),
        'view'    : '[BatchTime].[dbo].[WEB_Batches_vw]',
        'headers' : { 
            'BatchTypeID'  : 'Тип партии',
            'BatchName'    : 'ПАРТИЯ',
        },
    },
    'persostation-operators' : { 
        'columns' : ('Login', 'Name', 'FullName',),
        'view'    : '[BatchTime].[dbo].[Operators_tb]',
        'headers' : { 
            'Login'        : 'Оператор',
            'Name'         : 'Имя',
            'FullName'     : 'Полное имя',
        },
    },
    'persostation-check-client' : { 
        'params'  : "0,%(bp_client_id)s,'%(name)s',null",
        'args'    : '0,%d,%s,null',
        'exec'    : '[BatchTime].[dbo].[CHECK_Client_sp]',
    },
    'persostation-check-order' : { 
        'params'  : "0,%(client_id)s,%(bp_file_id)s,'%(fname)s',%(fqty)s,'%(register_date)s',null",
        'args'    : '0,%d,%d,%s,%d,%s,null',
        'exec'    : '[BatchTime].[dbo].[CHECK_Order_sp]',
    },
    'persostation-check-batch' : { 
        'params'  : "0,%(order_id)s,%(bp_batch_id)s,'%(batchname)s',%(batchtype_id)s,%(batchno)s,%(pers_tz)s,%(element_qty)s,null",
        'args'    : '0,%d,%d,%s,%d,%d,%d,%d,%s,null',
        'exec'    : '[BatchTime].[dbo].[CHECK_Order_sp]',
    },
    'persostation-register-action' : { 
        'params'  : "0,%(bp_client_id)s,%(bp_file_id)s,%(bp_batch_id)s,'%(client)s','%(fname)s',%(fqty)s,'%(register_date)s','%(batchname)s',%(batchtype_id)s,%(batchno)s,%(pers_tz)s,%(element_qty)s,'%(login)s','%(fullname)s',%(add)s,%(delete)s,null",
        'args'    : '0,%d,%d,%d,%s,%s,%d,%s,%s,%d,%d,%d,%d,%s,%s,%d,%d,null',
        'exec'    : '[BatchTime].[dbo].[REGISTER_Action_sp]',
    },
    'persostation-search-actions' : { 
        'params'  : "0,'%(ids)s'",
        'args'    : '0,%s,null',
        'exec'    : '[BatchTime].[dbo].[SearchActions_sp]',
    },
    # =====================
    # PROVISION ORDERS LIST
    # =====================
    'provision-orders' : { 
        'columns' : ['TID', 'Article', 'Qty', 'Subdivision', 'Price', 'Currency', 'Total', 'Condition', 'Seller', 'RD',],
        'noprice' : ['TID', 'Article', 'Qty', 'Subdivision', 'Purpose', 'RD',],
        'view'    : '[ProvisionDB].[dbo].[WEB_Orders_vw]',
        'headers' : { 
            'TID'          : ('№ заявки',            'npp',          ''),
            'Article'      : ('НАИМЕНОВАНИЕ ТОВАРА', 'article',      ''),
            'Author'       : ('Автор заявки',        '',             ''),
            'Qty'          : ('Кол-во, шт.',         'qty',          ''),
            'Category'     : ('Категория',           '',             ''),
            'Purpose'      : ('ОБОСНОВАНИЕ',         '',             ''),
            'Price'        : ('Цена за единицу',     'money price',  ''),
            'Currency'     : ('Валюта платежа',      'currency',     ''),
            'Total'        : ('СУММА',               'money _total', ''),
            'Tax'          : ('НДС',                 'money tax',    ''),
            'Subdivision'  : ('ПОТРЕБИТЕЛЬ',         'office',       ''),
            'Condition'    : ('Условия оплаты',      '',             ''),
            'Equipment'    : ('Описание',            '',             ''),
            'Account'      : ('Номер счета',         '',             ''),
            'Seller'       : ('ПОСТАВЩИК',           'seller',       ''),
            'Status'       : ('Статус заявки',       '',             ''),
            'ReviewStatus' : ('Статус заказа',       '',             ''),
            'RD'           : ('Дата',                'rd',           ''),
        },
        'export'  : ('TID', 'Subdivision', 'Article', 'Qty', 'Price', 'Total', 'Seller', 'SellerTitle', 'SellerAddress', 'Status', 'RD', 'ReviewStatus', 'Author', 'Purpose', 'Currency', 'Tax', 'Condition', 'Equipment', 'EquipmentName', 'Category', 'Account', 'EditedBy', 'SubdivisionCode', 'SubdivisionID', 'ConditionID', 'EquipmentID', 'SellerID', 'CategoryID', 'RowSpan', 'UnreadByLogin',),
        'status'  : ('Qty', 'Price',),
        'updated' : ('Author', 'Article', 'Qty', 'Purpose', 'Price', 'Currency', 'EditedBy', 'SubdivisionID', 'ConditionID', 'EquipmentID', 'SellerID', 'CategoryID',),
        'sorted'  : ('TID', 'Subdivision', 'Article', 'Qty', 'Price', 'Total', 'Seller', 'Status', 'RD',),
    },
    'provision-order-dates' : { 
        'columns' : ('TID', 'Created', 'Approved', 'Paid', 'Delivered', 'ReviewDueDate', 'WithMail',),
        'view'    : '[ProvisionDB].[dbo].[OrderDates_tb]',
    },
    'provision-order-unreads' : { 
        'columns' : ('Login',),
        'view'    : '[ProvisionDB].[dbo].[OrderUnreads_tb]',
    },
    'provision-order-reviewers' : { 
        'columns' : ('ID', 'OrderID', 'Login',),
        'view'    : '[ProvisionDB].[dbo].[Reviewers_tb]',
    },
    'provision-order-authors' : { 
        'columns' : ('Author',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Authors_vw]',
    },
    'provision-order-changes' : { 
        'columns' : ('TID', 'Login', 'Name', 'Value', 'RD',),
        'view'    : '[ProvisionDB].[dbo].[WEB_OrderChanges_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Login'        : 'Автор',
            'Name'         : 'Наименование реквизита',
            'Value'        : 'Значение',
            'RD'           : 'Дата изменения',
        },
        'export'  : ('TID', 'Login', 'Name', 'Value', 'RD',),
    },
    'provision-reviews' : { 
        'columns' : ('TID', 'StatusDate', 'Reviewer', 'Status', 'Note',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Reviews_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'OrderID'      : '№ заявки',
            'RegistryDate' : 'Дата заявки',
            'Reviewer'     : 'ФИО должностного лица',
            'Status'       : 'Статус',
            'Note'         : 'Рецензия',
            'StatusDate'   : 'Дата',
        },
        'export'  : ('TID', 'OrderID', 'Login', 'Reviewer', 'Status', 'Note', 'RegistryDate', 'StatusDate',),
    },
    'provision-subdivisions' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Subdivisions_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Отдел',
            'Code'         : 'Код',
            'Manager'      : 'Руководитель',
            'FullName'     : 'Полное наименование подразделения',
        },
        'export'  : ('TID', 'Name', 'Code', 'Manager', 'FullName',),
    },
    'provision-categories' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Categories_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Категория',
        },
        'export'  : ('TID', 'Name',),
    },
    'provision-sellers' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Sellers_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Поставщик',
            'Title'        : 'Наименование',
            'Address'      : 'Адрес организации',
        },
        'export'  : ('TID', 'Name', 'Title', 'Address',),
    },
    'provision-conditions' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Conditions_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Условие оплаты',
        },
        'export'  : ('TID', 'Name',),
    },
    'provision-equipments' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Equipments_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Title'        : 'Категория',
            'Name'         : 'Наименование',
        },
        'export'  : ('TID', 'Title', 'Name',),
    },
    'provision-params' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Params_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Наименование',
        },
        'export' : ('TID', 'Name',),
    },
    'provision-order-params' : { 
        'columns' : ('TID', 'Login', 'Name', 'Value',),
        'view'    : '[ProvisionDB].[dbo].[WEB_OrderParams_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'ParamID'      : 'ID параметра',
            'Login'        : 'Автор',
            'Name'         : 'Параметр',
            'Value'        : 'Значение',
        },
        'export'  : ('TID', 'ParamID', 'Login', 'Name', 'Value', 'RD',),
    },
    'provision-order-items' : { 
        'columns' : ('TID', 'Login', 'Name', 'Qty', 'Units', 'Total', 'Tax', 'Account'),
        'view'    : '[ProvisionDB].[dbo].[WEB_OrderItems_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Login'        : 'Автор',
            'Name'         : 'Наименование',
            'Qty'          : 'Кол-во',
            'Units'        : 'Ед/изм.',
            'Total'        : 'Сумма',
            'Account'      : 'Номер в 1С (расход)',
            'Tax'          : 'НДС',
        },
        'export'  : ('TID', 'Login', 'Name', 'Qty', 'Units', 'Total', 'Tax', 'Account', 'RD',),
    },
    'provision-payments' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Payments_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Наименование',
        },
        'export' : ('TID', 'Name',),
    },
    'provision-order-payments' : { 
        'columns' : ('TID', 'Login', 'Purpose', 'PaymentDate', 'Total', 'Tax', 'Status',),
        'view'    : '[ProvisionDB].[dbo].[WEB_OrderPayments_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'PaymentID'    : 'ID параметра',
            'Login'        : 'Автор',
            'Purpose'      : 'Назначение платежа',
            'PaymentDate'  : 'Дата платежа',
            'Total'        : 'Сумма',
            'Tax'          : 'НДС',
            'Status'       : 'Статус',
        },
        'export'  : ('TID', 'PaymentID', 'Login', 'Purpose', 'PaymentDate', 'Total', 'Tax', 'Status', 'RD',),
    },
    'provision-comments' : { 
        'columns' : ('TID', 'Name',),
        'view'    : '[ProvisionDB].[dbo].[WEB_Comments_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'Name'         : 'Наименование',
        },
        'export' : ('TID', 'Name',),
    },
    'provision-order-comments' : { 
        'columns' : ('TID', 'Login', 'Author', 'Note',),
        'view'    : '[ProvisionDB].[dbo].[WEB_OrderComments_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'CommentID'    : 'ID параметра',
            'Login'        : 'Автор',
            'Author'       : 'Автор комментария',
            'Note'         : 'Комментарий',
        },
        'export'  : ('TID', 'CommentID', 'Login', 'Author', 'Note', 'RD',),
    },
    'provision-order-documents' : { 
        'columns' : ('TID', 'Login', 'FileName', 'Note', 'FileSize',),
        'view'    : '[ProvisionDB].[dbo].[WEB_OrderDocuments_vw]',
        'headers' : { 
            'TID'          : 'ID',
            'OrderID'      : '№ заявки',
            'Login'        : 'Автор',
            'FileName'     : 'Документ',
            'FileSize'     : 'Размер файла',
            'ContentType'  : 'Тип',
            'Note'         : 'Содержание',
            'UID'          : 'UID',
            'RD'           : 'Дата',
        },
        'export'  : ('TID', 'OrderID', 'Login', 'FileName', 'FileSize', 'ContentType', 'Note', 'IsExist', 'UID', 'RD',),
    },
    'provision-register-order' : { 
        'params'  : "0,'%(login)s','%(article)s',%(qty)s,'%(purpose)s',%(price).5f,'%(currency)s',%(total).2f,%(tax).2f,'%(subdivision)s','%(category)s','%(equipment)s','%(seller)s','%(condition)s','%(account)s','%(duedate)s','%(author)s',%(status)s,%(is_no_price)s,0,null",
        'args'    : "%d,'%s','%s',%d,'%s',%.2f,'%s',%.2f,%.2f,'%s','%s','%s','%s','%s','%s','%s','%s',%s,%d,%d,null",
        'exec'    : '[ProvisionDB].[dbo].[REGISTER_Order_sp]',
    },
    'provision-refresh-order' : { 
        'params'  : "0,%(id)d,'%(login)s','%(article)s',%(qty)s,'%(purpose)s',%(price).5f,'%(currency)s',%(total).2f,%(tax).2f,'%(subdivision)s','%(category)s','%(equipment)s','%(seller)s','%(condition)s','%(duedate)s','%(author)s',%(is_no_price)s,null",
        'exec'    : '[ProvisionDB].[dbo].[UPDATE_Order_sp]',
    },
    'provision-remove-order' : { 
        'params'  : "0,%(id)d,'%(login)s',null",
        'exec'    : '[ProvisionDB].[dbo].[DELETE_Order_sp]',
    },
    'provision-register-review' : { 
        'params'  : "0,%(order_id)d,'%(login)s','%(reviewer)s',%(status)d,'%(note)s','%(review_duedate)s',%(with_mail)d,null",
        'args'    : '0,%d,%s,%s,%d,%s,%s,%d,null',
        'exec'    : '[ProvisionDB].[dbo].[REGISTER_Review_sp]',
    },
    'provision-set-unread' : { 
        'params'  : "0,%(order_id)d,'%(logins)s',null",
        'args'    : '0,%d,%s,null',
        'exec'    : '[ProvisionDB].[dbo].[SET_Unread_sp]',
    },
    'provision-set-read' : { 
        'params'  : "0,%(order_id)s,'%(logins)s',null",
        'args'    : '0,%d,%s,null',
        'exec'    : '[ProvisionDB].[dbo].[SET_Read_sp]',
    },
    'provision-add-param-order' : { 
        'params'  : "0,%(order_id)d,%(id)d,%(param_id)d,'%(login)s','%(new_param)s','%(value)s',null",
        'args'    : "%d,%d,%d,%d,'%s','%s','%s',null",
        'exec'    : '[ProvisionDB].[dbo].[ADD_Param_sp]',
    },
    'provision-add-item-order' : { 
        'params'  : "0,%(order_id)d,%(id)d,'%(login)s','%(item)s',%(qty)d,'%(units)s',%(total).2f,%(tax).2f,'%(account)s',null",
        'args'    : "%d,%d,%d,'%s','%s',%d,'%s',%.2f,%.2f,'%s',null",
        'exec'    : '[ProvisionDB].[dbo].[ADD_Item_sp]',
    },
    'provision-add-payment-order' : { 
        'params'  : "0,%(order_id)d,%(id)d,%(payment_id)d,'%(login)s','%(new_payment)s','%(date)s',%(total).2f,%(tax).2f,%(status)s,null",
        'args'    : "%d,%d,%d,%d,'%s','%s','%s',%.2f,%.2f,%d,null",
        'exec'    : '[ProvisionDB].[dbo].[ADD_Payment_sp]',
    },
    'provision-add-document-order' : { 
        'params'  : "0,'%(uid)s',%(order_id)d,'%(login)s','%(filename)s',%(filesize)s,%(content_type)s,'%(note)s','%(image)s',null",
        'args'    : "%d,%s,%d,%s,%s,%d,%s,%s,%s,null",
        'exec'    : '[ProvisionDB].[dbo].[ADD_Comment_sp]',
    },
    'provision-add-comment-order' : { 
        'params'  : "0,%(order_id)d,%(id)d,%(comment_id)d,'%(login)s','%(new_comment)s','%(note)s',null",
        'args'    : "%d,%d,%d,%d,%s,%s,%s,null",
        'exec'    : '[ProvisionDB].[dbo].[ADD_Comment_sp]',
    },
    'provision-del-param-order' : { 
        'params'  : "0,%(order_id)d,%(id)d,%(param_id)d,'%(login)s',null",
        'args'    : "%d,%d,%d,%d,'%s',null",
        'exec'    : '[ProvisionDB].[dbo].[DEL_Param_sp]',
    },
    'provision-del-item-order' : { 
        'params'  : "0,%(order_id)d,%(id)d,'%(login)s',null",
        'args'    : "%d,%d,%d,'%s',null",
        'exec'    : '[ProvisionDB].[dbo].[DEL_Item_sp]',
    },
    'provision-del-payment-order' : { 
        'params'  : "0,%(order_id)d,%(id)d,%(payment_id)d,'%(login)s',null",
        'args'    : "%d,%d,%d,%d,'%s',null",
        'exec'    : '[ProvisionDB].[dbo].[DEL_Payment_sp]',
    },
    'provision-del-comment-order' : { 
        'params'  : "0,%(order_id)d,%(id)d,%(comment_id)d,'%(login)s',null",
        'args'    : "%d,%d,%d,%d,'%s',null",
        'exec'    : '[ProvisionDB].[dbo].[DEL_Comment_sp]',
    },
    'provision-del-document-order' : { 
        'params'  : "0,%(order_id)d,%(id)d,'%(login)s',null",
        'args'    : "%d,%d,%d,'%s',null",
        'exec'    : '[ProvisionDB].[dbo].[DEL_Document_sp]',
    },
    'provision-del-seller-order' : { 
        'params'  : "0,%(id)d,'%(login)s',null",
        'args'    : "%d,%d,'%s',null",
        'exec'    : '[ProvisionDB].[dbo].[DEL_Seller_sp]',
    },
    'provision-set-status-order' : { 
        'params'  : "0,%(order_id)d,'%(login)s',%(status)s,null",
        'exec'    : '[ProvisionDB].[dbo].[SET_Status_sp]',
    },
    'provision-download-image' : { 
        'columns' : ('FileName', 'FileSize', 'ContentType', 'Image',),
        'view'    : '[ProvisionDB].[dbo].[OrderDocuments_tb]',
    },
}

## -------------------------------
## Inheritance inside `config` XXX
## -------------------------------

for item in database_config:
    if not ':' in item:
        continue
    parent = item.split(':')[0]
    if not parent in database_config:
        continue
    for key in ('columns', 'headers', 'export',):
        if database_config[item][key] == 'self':
            database_config[item][key] = database_config[parent][key]

## ----------
## References
## ----------

def _reference_header(show, title, style, key=None, link=None, reference=None, alias=None, value=None, tag=None):
    """
        Header attributes:
            show      -- Bool, flag show on the screen: 1|0
            title     -- String, column title
            style     -- String, css style name
            key       -- String, field key
            link      -- Int, FK type [{1|2}]: 1-editable, 2-frozen
            reference -- String, FK reference view name
            alias     -- String, view field name
            value     -- String, table field name (as selected value)
            tag       -- String, HTML-tag template
    """
    return {
        'show'      : show and show.isdigit() and int(show) and True or False,
        'title'     : title,
        'style'     : style,
        'key'       : key or key.lower(),
        'link'      : link,
        'reference' : reference,
        'alias'     : alias,
        'value'     : value,
        'tag'       : tag or 'input',
    }

def _reference_field(stype, selector=None, order=None, encoding=None):
    """
        Field attributes:
            type      -- String, field SQL-type
            selector  -- String, SQL search query operator
            order     -- String, order type [{asc|desc}]
            encoding  -- Int, encoding flag [1]
    """
    return {
        'type'      : stype,
        'selector'  : selector,
        'order'     : order,
        'encoding'  : encoding and True or False,
    }

_references = {
    'reference.clients' : {
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_Clients_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'CName'             : '1:Наименование::name',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'CName'             : "varchar:CName like '%%%s%%':asc:1",
        },
    },
    'reference.file-status' : {
        'columns' : ('TID', 'StatusTypeID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_FileStatus_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'StatusTypeID'      : '1:Тип статуса::fk',
            'CName'             : '1:Наименование::name',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'StatusTypeID'      : 'int:StatusTypeID=%s',
            'CName'             : "varchar:CName like '%%%s%%':asc:1",
        },
    },
    'reference.file-type' : {
        'columns' : ('TID', 'ClientID', 'CName', 'ReportPrefix',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'ClientID'          : '1:Клиент::fk',
            'CName'             : '1:Наименование::name',
            'ReportPrefix'      : '1:Признак отчета::report',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'ClientID'          : 'int:ClientID=%s',
            'CName'             : "varchar:CName like '%%%s%%':asc:1",
            'ReportPrefix'      : "varchar:ReportPrefix like '%%%s%%'::1",
        },
    },
    'reference.batch-create-type' : {
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_BatchCreateType_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'CName'             : '1:Наименование::name',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'CName'             : "varchar:CName like '%%%s%%':asc:1",
        },
    },
    'reference.batch-result-type' : {
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_BatchResultType_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'CName'             : '1:Наименование::name',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'CName'             : "varchar:CName like '%%%s%%':asc:1",
        },
    },
    'reference.batch-status' : {
        'columns' : ('TID', 'CName'),
        'view'    : '[BankDB].[dbo].[DIC_BatchStatus_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'CName'             : '1:Наименование::name',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'CName'             : "varchar:CName like '%%%s%%':asc:1",
        },
    },
    'reference.batch-type' : {
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_BatchType_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'CName'             : '1:Наименование::name',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'CName'             : "varchar:CName like '%%%s%%':asc:1",
        },
    },
    'reference.oper-list' : {
        'columns' : ('TID', 'TypeID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_OperList_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'TypeID'            : '1:Тип операции::fk',
            'CName'             : '1:Наименование::name',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'TypeID'            : 'int:TypeID=%s',
            'CName'             : "varchar:CName like '%%%s%%':asc:1",
        },
    },
    'reference.oper-type' : {
        'columns' : ('TID', 'CName', 'SName',),
        'view'    : '[BankDB].[dbo].[DIC_OperType_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'CName'             : '1:Тип операции::type',
            'SName'             : '1:Наименование::name',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'CName'             : "varchar:CName like '%%%s%%'::",
            'SName'             : "varchar:SName like '%%%s%%':asc:1",
        },
    },
    'reference.tag-params' : {
        'columns' : ('TID', 'PName', 'Comment',),
        'view'    : '[BankDB].[dbo].[DIC_TagParams_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'PName'             : '1:Наименование::name',
            'Comment'           : '1:Примечание::comment',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'PName'             : "varchar:PName like '%%%s%%':asc:1",
            'Comment'           : "varchar:Comment like '%%%s%%'::1",
        },
    },
    'reference.ftb-post' : {
        'columns' : ('TID', 'FBLinkID', 'TagParamID', 'PValue', 'PSortIndex', 'Comment',),
        'view'    : '[BankDB].[dbo].[DIC_FTB_POST_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'FBLinkID'          : '1:Тип партии::batch',
            'TagParamID'        : '1:Параметр::tag',
            'PValue'            : '1:Значение параметра::value',
            'PSortIndex'        : '1:Индекс сортировки::sort',
            'Comment'           : '1:Примечание::comment',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'FBLinkID'          : 'int:FBLinkID=%s',
            'TagParamID'        : 'int:TagParamID=%s',
            'PValue'            : "varchar:PValue like '%%%s%%':asc:1",
            'PSortIndex'        : 'int:PSortIndex=%s:asc:',
            'Comment'           : "varchar:Comment like '%%%s%%'::1",
        },
    },
    'reference.ftv-oper-params' : {
        'columns' : ('TID', 'FTV_OPER_ID', 'PName', 'PValue',),
        'view'    : '[BankDB].[dbo].[DIC_FTV_OPER_PARAMS_tb]',
        'headers' : {
            'TID'               : '1:PK::id',
            'FTV_OPER_ID'       : '1:Тип операции::fk',
            'PName'             : '1:Наименование::name',
            'PValue'            : '1:Значение::value',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'FTV_OPER_ID'       : 'int:FTV_OPER_ID=%s',
            'PName'             : "varchar:PName like '%%%s%%':asc:1",
            'PValue'            : "varchar:PValue like '%%%s%%'",
        },
    },
    # ----------------
    # LINKED REFERENCE
    # ----------------
    'reference.linked-batches' : {
        'columns' : ('TID', 'FileTypeID', 'BatchTypeID', 'FileType', 'BatchType',),
        'view'    : '[BankDB].[dbo].[WEB_BatchTypes_vw]',
        'headers' : {
            'TID'               : '1:ID партии::id',
            'FileTypeID'        : '0:ID типа файла::fk1',
            'BatchTypeID'       : '0:ID типа партии::fk2',
            'FileType'          : '1:Тип файла::filetype',
            'BatchType'         : '1:Тип партии::name',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'FileTypeID'        : 'int:FileTypeID=%s',
            'BatchTypeID'       : 'int:BatchTypeID=%s',
            'FileType'          : "varchar:FileType like '%%%s%%':asc:",
            'BatchType'         : "varchar:BatchType like '%%%s%%':asc:1",
        },
    },
    'reference.linked-opers' : {
        'columns' : ('TID', 'FBLinkID', 'FileTypeID', 'BatchTypeID', 'OperID', 'FileType', 'BatchType', 'OperTypeName', 'OperType', 'OperSortIndex',),
        'view'    : '[BankDB].[dbo].[WEB_FileOpers_vw]',
        'headers' : {
            'TID'               : '1:ID операции::id',
            'FBLinkID'          : '0:Тип партии::batch',
            'FileTypeID'        : '0:ID типа файла::fk1',
            'BatchTypeID'       : '0:ID типа партии::fk2',
            'OperID'            : '0:ID типа операции::fk3',
            'FileType'          : '0:Тип файла::filetype',
            'BatchType'         : '0:Тип партии::batchtype',
            'OperTypeName'      : '1:Тип операции::opertype',
            'OperType'          : '1:Операция::name',
            'OperSortIndex'     : '1:Индекс сортировки::sort',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'FBLinkID'          : 'int:FBLinkID=%s',
            'FileTypeID'        : 'int:FileTypeID=%s',
            'BatchTypeID'       : 'int:BatchTypeID=%s',
            'FileType'          : "varchar:FileType like '%%%s%%'::",
            'BatchType'         : "varchar:BatchType like '%%%s%%':2-asc:1",
            'OperTypeName'      : "varchar:OperTypeName like '%%%s%%'::",
            'OperType'          : "varchar:OperType like '%%%s%%'::1",
            'OperSortIndex'     : 'int:OperSortIndex=%s:1-asc:',
        },
    },
    'reference.linked-tags' : {
        'columns' : ('TID', 'FileTypeID', 'FileType', 'TName', 'TMemo',),
        'view'    : '[BankDB].[dbo].[WEB_FileTags_vw]',
        'headers' : {
            'TID'               : '1:ID тега::id',
            'FileTypeID'        : '0:ID типа файла::fk1',
            'FileType'          : '1:Тип файла::filetype',
            'TName'             : '1:Тег::name',
            'TMemo'             : '1:Примечание:text:memo:::::textarea',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'FileTypeID'        : 'int:FileTypeID=%s',
            'FileType'          : "varchar:FileType like '%%%s%%'::",
            'TName'             : "varchar:TName like '%%%s%%':asc:1",
            'TMemo'             : "varchar:TMemo like '%%%s%%'::1",
        },
    },
    'reference.linked-tagvalues' : {
        'columns' : ('TID', 'FTLinkID', 'FileTypeID', 'FileType', 'TName', 'TValue', 'TagValue',),
        'view'    : '[BankDB].[dbo].[WEB_FileTagValues_vw]',
        'headers' : {
            'TID'               : '1:ID значения::id',
            'FTLinkID'          : '0:ID тега::tag',
            'FileTypeID'        : '0:ID типа файла::fk1',
            'FileType'          : '0:Тип файла::filetype',
            'TName'             : '1:Тег::name',
            'TValue'            : '1:Значение::v1',
            'TagValue'          : '0:Значение параметра::value',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'FTLinkID'          : 'int:FTLinkID=%s',
            'FileTypeID'        : 'int:FileTypeID=%s',
            'FileType'          : "varchar:FileType like '%%%s%%'::",
            'TName'             : "varchar:TName like '%%%s%%':asc:1",
            'TValue'            : "varchar:TValue like '%%%s%%'::1",
            'TagValue'          : 'varchar:::1',
        },
    },
    'reference.linked-tagopers' : {
        'columns' : ('TID', 'FTVLinkID', 'FileTypeID', 'TagParamID', 'OperTypeID', 'FileType', 'TName', 'TValue', 'TagValue', 'OperType', 'Oper', 'PName', 'PValue', 'Comment', 'OperSortIndex',),
        'view'    : '[BankDB].[dbo].[WEB_FileTagOpers_vw]',
        'headers' : {
            'TID'               : '1:ID параметра::id',
            'FTVLinkID'         : '0:ID тега::tag',
            'FileTypeID'        : '0:ID типа файла::fk1',
            'TagParamID'        : '0:ID типа файла::fk2',
            'OperTypeID'        : '0:ID типа операции::fk3',
            'FileType'          : '0:Тип файла::filetype',
            'TName'             : '0:Тег::v1',
            'TValue'            : '0:Значение::v2',
            'TagValue'          : '1:Тег::tagvalue',
            'OperType'          : '0:Тип операции::v3',
            'Oper'              : '0:Операция::v4',
            'PName'             : '1:Параметр::name',
            'PValue'            : '1:Операция::value',
            'Comment'           : '1:Примечание::comment',
            'OperSortIndex'     : '0:Индекс сортировки::sort',
        },
        'fields'  : {
            'TID'               : 'int:TID=%s',
            'FTVLinkID'         : 'int:FTVLinkID=%s',
            'FileTypeID'        : 'int:FileTypeID=%s',
            'TagParamID'        : 'int:TagParamID=%s',
            'OperTypeID'        : 'int:OperTypeID=%s',
            'FileType'          : "varchar:FileType like '%%%s%%'::",
            'TName'             : "varchar:TName like '%%%s%%':asc:1",
            'TValue'            : "varchar:TValue like '%%%s%%':asc:1",
            'TagValue'          : 'varchar:#',
            'OperType'          : "varchar:OperType like '%%%s%%'::",
            'Oper'              : "varchar:Oper like '%%%s%%'::1",
            'OperTypeValue'     : "varchar:OperTypeValue like '%%%s%%'::1",
            'PName'             : "varchar:PName like '%%%s%%':asc:1",
            'PValue'            : "varchar:PValue like '%%%s%%':asc:1",
            'Comment'           : "varchar:Comment like '%%%s%%'::1",
            'OperSortIndex'     : 'int:#'
        },
    },
    # -------------------------
    # BANKPERSO CONFIG SETTINGS
    # -------------------------
    'reference.file-type-batch-type' : {
        'columns' : ('TID', 'FileTypeID', 'BatchTypeID', 'BatchCreateTypeID', 'BatchResultTypeID', 'BatchMaxQty', 'IsErpBatch', 'CreateBatchSortIndex', 'CreateBatchGroupIndex',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_BatchType_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FileTypeID'              : '1:Тип файла::fk1:2:reference.file-type:FileType:CName',
            'BatchTypeID'             : '1:Тип партии::fk2:1:reference.batch-type:BatchType:CName',
            'BatchCreateTypeID'       : '1:Признак создания партии::fk3:1:reference.batch-create-type:BatchCreateType:CName',
            'BatchResultTypeID'       : '1:Признак создания файла результата партии::fk4:1:reference.batch-result-type:BatchResultType:CName',
            'BatchMaxQty'             : '1:Предельное число карт партии::maxqty',
            'IsErpBatch'              : '1:Признак использования ERP::iserp',
            'CreateBatchSortIndex'    : '1:Индекс сортировки::sort',
            'CreateBatchGroupIndex'   : '1:Индекс группировки::group',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FileTypeID'              : 'int:FileTypeID=%s',
            'BatchTypeID'             : 'int:BatchTypeID=%s',
            'BatchCreateTypeID'       : 'int:BatchCreateTypeID=%s',
            'BatchResultTypeID'       : 'int:BatchResultTypeID=%s',
            'BatchMaxQty'             : 'int:BatchMaxQty=%s',
            'IsErpBatch'              : 'int:IsErpBatch=%s',
            'CreateBatchSortIndex'    : 'int:CreateBatchSortIndex=%s',
            'CreateBatchGroupIndex'   : 'int:CreateBatchGroupIndex=%s',
            'FileType'                : 'varchar:#',
            'BatchType'               : 'varchar:#',
            'BatchCreateType'         : 'varchar:#',
            'BatchResultType'         : 'varchar:#',
        },
    },
    'reference.order-file-process' : {
        'columns' : ('TID', 'LinkID', 'CurrFileStatusID', 'NextFileStatusID', 'CloseFileStatusID', 'Memo', 'ActivateBatchStatus', 'ARMBatchStatus',),
        'view'    : '[BankDB].[dbo].[DIC_OrderFileProcess_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'LinkID'                  : '1:Тип партии::fk1:1:reference.linked-batches:BatchType:BatchType',
            'CurrFileStatusID'        : '1:Текущий статус файла::fk2:1:reference.file-status:CurrFileStatus:CName',
            'NextFileStatusID'        : '1:Следующий статус файла::fk3:1:reference.file-status:NextFileStatus:CName',
            'CloseFileStatusID'       : '1:Конечный статус файла::fk4:1:reference.file-status:CloseFileStatus:CName',
            'Memo'                    : '1:Примечание:text:memo:::::textarea',
            'ActivateBatchStatus'     : '1:Статус активации партии:varchar:fk5:1:reference.batch-status:ActivateBatchStatus_:CName',
            'ARMBatchStatus'          : '1:Статус партии в АРМ:varchar:fk6:1:reference.batch-status:ARMBatchStatus_:CName',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'LinkID'                  : 'int:LinkID=%s',
            'CurrFileStatusID'        : 'int:CurrFileStatusID=%s',
            'NextFileStatusID'        : 'int:NextFileStatusID=%s',
            'CloseFileStatusID'       : 'int:CloseFileStatusID=%s',
            'Memo'                    : "varchar:Memo like '%%%s%%'::1",
            'ActivateBatchStatus'     : 'int:ActivateBatchStatus=%s',
            'ARMBatchStatus'          : 'int:ARMBatchStatus=%s',
            'BatchType'               : 'varchar:#',
            'CurrFileStatus'          : 'varchar:#',
            'NextFileStatus'          : 'varchar:#',
            'CloseFileStatus'         : 'varchar:#',
            'ActivateBatchStatus_'    : 'varchar:#',
            'ARMBatchStatus_'         : 'varchar:#',
        },
    },
    'reference.file-type-batch-type-opers' : {
        'columns' : ('TID', 'FBLinkID', 'OperID', 'OperSortIndex',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_BatchType_OperList_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FBLinkID'                : '1:Тип партии::fk1:1:reference.linked-batches:BatchType:BatchType',
            'OperID'                  : '1:Операция::fk2:1:reference.oper-list:OperType:OperType',
            'OperSortIndex'           : '1:Индекс сортировки::sort',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FBLinkID'                : 'int:FBLinkID=%s',
            'OperID'                  : 'int:OperID=%s',
            'OperSortIndex'           : 'int:OperSortIndex=%s',
            'BatchType'               : 'varchar:#',
            'OperType'                : 'varchar:#',
        },
    },
    'reference.file-type-batch-type-operparams' : {
        'columns' : ('TID', 'FBLinkID', 'FBOLinkID', 'PName', 'PValue', 'Comment',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_BatchType_OperList_Params_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FBLinkID'                : '1:Тип партии::fk1:1:reference.linked-batches:BatchType:BatchType',
            'FBOLinkID'               : '1:Операция::fk2:1:reference.linked-opers:OperType:OperType',
            'PName'                   : '1:Параметр::name',
            'PValue'                  : '1:Значение параметра::value', #longvarchar
            'Comment'                 : '1:Примечание:text:memo:::::textarea',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FBLinkID'                : 'int:FBLinkID=%s',
            'FBOLinkID'               : 'int:FBOLinkID=%s',
            'PName'                   : "varchar:PName like '%%%s%%':asc:1",
            'PValue'                  : "varchar:PValue like '%%%s%%'",
            'Comment'                 : "varchar:Comment like '%%%s%%'::1",
            'BatchType'               : 'varchar:#',
            'OperType'                : 'varchar:#',
        },
    },
    'reference.file-type-tags' : {
        'columns' : ('TID', 'FileTypeID', 'TName', 'TMemo',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_TagList_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FileTypeID'              : '1:Тип файла::fk1:2:reference.file-type:FileType:CName',
            'TName'                   : '1:Тег::name',
            'TMemo'                   : '1:Примечание:text:memo:::::textarea',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FileTypeID'              : 'int:FileTypeID=%s',
            'TName'                   : "varchar:TName like '%%%s%%':asc:1",
            'TMemo'                   : "varchar:TMemo like '%%%s%%'::1",
            'FileType'                : 'varchar:#',
        },
    },
    'reference.file-type-tagvalues' : {
        'columns' : ('TID', 'FTLinkID', 'TValue',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_TagList_TagValues_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FTLinkID'                : '1:Тег::fk1:1:reference.linked-tags:TName:TName',
            'TValue'                  : '1:Значение::value',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FTLinkID'                : 'int:FTLinkID=%s',
            'TName'                   : "varchar:TName like '%%%s%%':asc:1",
            'TValue'                  : "varchar:TValue like '%%%s%%'::1",
        },
    },
    'reference.file-type-batch-type-filters' : {
        'columns' : ('FileTypeID', 'FBLinkID', 'FTLinkID', 'CriticalValues', 'TID',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_BatchType_FilterShema_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FileTypeID'              : '1:Тип файла::fk1:2:reference.file-type:FileType:CName',
            'FBLinkID'                : '1:Тип партии::fk2:1:reference.linked-batches:BatchType:BatchType',
            'FTLinkID'                : '1:Тег::fk3:1:reference.linked-tags:TName:TName',
            'CriticalValues'          : '1:Критическое значение::value',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FileTypeID'              : 'int:FileTypeID=%s',
            'BatchTypeID'             : 'int:BatchTypeID=%s',
            'FBLinkID'                : 'int:FBLinkID=%s',
            'FTLinkID'                : 'int:FTLinkID=%s',
            'CriticalValues'          : "varchar:CriticalValues like '%%%s%%'::1",
            'TName'                   : "varchar:#",
            'FileType'                : 'varchar:#',
            'BatchType'               : 'varchar:#',
        },
    },
    'reference.file-type-tzs' : {
        'columns' : ('TID', 'FTVLinkID', 'TagParamID', 'PValue', 'Comment', 'PSortIndex',),
        'view'    : '[BankDB].[dbo].[DIC_FTV_TZ_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FileTypeID'              : '0:Тип файла::fk1:2:reference.file-type:FileType:CName',
            'FTVLinkID'               : '1:Тег::fk2:1:reference.linked-tagvalues:TagValue:TagValue',
            'TagParamID'              : '1:Параметр ТЗ::fk3:1:reference.tag-params:PName:PName',
            'PValue'                  : '1:Значение параметра ТЗ:hightext:value:::::textarea',
            'Comment'                 : '1:Примечание:text:memo:::::textarea',
            'PSortIndex'              : '1:Индекс сортировки::sort',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FileTypeID'              : 'int:FileTypeID=%s',
            'FTVLinkID'               : 'int:FTVLinkID=%s',
            'TagParamID'              : 'int:TagParamID=%s',
            'PValue'                  : "varchar:PValue like '%%%s%%':2-asc:1",
            'Comment'                 : "varchar:Comment like '%%%s%%'::1",
            'PSortIndex'              : 'int:PSortIndex=%s:1-asc:',
            'FileType'                : 'varchar:#',
            'TagValue'                : 'varchar:#',
            'PName'                   : "varchar:#",
        },
    },
    'reference.file-type-erpcodes' : {
        'columns' : ('FTVLinkID', 'ERP_CODE', 'BatchTypeID', 'AdditionalInfo', 'TID',),
        'view'    : '[BankDB].[dbo].[DIC_FTV_ERPCODE_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FileTypeID'              : '0:Тип файла::fk1:2:reference.file-type:FileType:CName',
            #'BatchTypeID'             : '1:Тип партии::fk2:1:reference.linked-batches:BatchType:BatchType',
            'BatchTypeID'             : '1:Тип партии::fk2:1:reference.batch-type:BatchType:CName',
            'FTVLinkID'               : '1:Тег::fk3:1:reference.linked-tagvalues:TagValue:TagValue',
            'ERP_CODE'                : '1:Код ЕРП::value',
            'AdditionalInfo'          : '1:Дополнительная информация::info',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FileTypeID'              : 'int:FileTypeID=%s',
            'BatchTypeID'             : 'int:BatchTypeID=%s',
            'FTVLinkID'               : 'int:FTVLinkID=%s',
            'ERP_CODE'                : "varchar:ERP_CODE like '%%%s%%'::",
            'AdditionalInfo'          : "varchar:AdditionalInfo like '%%%s%%'::1",
            'FileType'                : 'varchar:#',
            'BatchType'               : 'varchar:#',
            'TagValue'                : 'varchar:#:1-asc:',
            'PName'                   : "varchar:#",
        },
    },
    'reference.file-type-materials' : {
        'columns' : ('TID', 'FTVLinkID', 'TagParamID', 'BatchTypeID', 'MMin', 'MBadPercent', 'QtyMode',),
        'view'    : '[BankDB].[dbo].[DIC_FTV_MATERIAL_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FileTypeID'              : '0:Тип файла::fk1:2:reference.file-type:FileType:CName',
            'BatchTypeID'             : '1:Тип партии::fk2:1:reference.batch-type:BatchType:CName',
            'FTVLinkID'               : '1:Тег::fk3:1:reference.linked-tagvalues:TagValue:TagValue',
            'TagParamID'              : '1:Параметр ТЗ::fk4:1:reference.tag-params:PName:PName',
            'MMin'                    : '1:Минимум::min',
            'MBadPercent'             : '1:Брак, %::bad:',
            'QtyMode'                 : '1:Количество::qty:',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FileTypeID'              : 'int:FileTypeID=%s',
            'BatchTypeID'             : 'int:BatchTypeID=%s',
            'FTVLinkID'               : 'int:FTVLinkID=%s',
            'TagParamID'              : 'int:TagParamID=%s',
            'MMin'                    : "int:MMin=%s",
            'MBadPercent'             : "int:MBadPercent=%s",
            'QtyMode'                 : "int:QtyMode=%s'",
            'FileType'                : 'varchar:#',
            'BatchType'               : 'varchar:#',
            'TagValue'                : 'varchar:#:1-asc:',
            'PName'                   : "varchar:#",
        },
    },
    'reference.file-type-posts' : {
        'columns' : ('TID', 'FTVLinkID', 'TagParamID', 'PValue', 'Comment',),
        'view'    : '[BankDB].[dbo].[DIC_FTV_POST_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FileTypeID'              : '0:Тип файла::fk1:2:reference.file-type:FileType:CName',
            'FTVLinkID'               : '1:Тег::fk2:1:reference.linked-tagvalues:TagValue:TagValue',
            'TagParamID'              : '1:Параметр ТЗ::fk3:1:reference.tag-params:PName:PName',
            'PValue'                  : '1:Значение параметра::value',
            'Comment'                 : '1:Примечание:text:memo:::::textarea',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FileTypeID'              : 'int:FileTypeID=%s',
            'FTVLinkID'               : 'int:FTVLinkID=%s',
            'TagParamID'              : 'int:TagParamID=%s',
            'PValue'                  : "varchar:PValue like '%%%s%%'",
            'Comment'                 : "varchar:Comment like '%%%s%%'::1",
            'FileType'                : 'varchar:#',
            'TagValue'                : 'varchar:#:1-asc:',
            'PName'                   : "varchar:#",
        },
    },
    'reference.file-type-tagopers' : {
        'columns' : ('TID', 'FTVLinkID', 'TagParamID', 'OperTypeID', 'PValue', 'Comment', 'OperSortIndex',),
        'view'    : '[BankDB].[dbo].[DIC_FTV_OPER_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FileTypeID'              : '0:Тип файла::fk1:2:reference.file-type:FileType:CName',
            'FTVLinkID'               : '1:Тег::fk2:1:reference.linked-tagvalues:TagValue:TagValue',
            'TagParamID'              : '1:Параметр тега::fk3:1:reference.tag-params:PName:PName',
            'OperTypeID'              : '1:Операция::fk4:1:reference.oper-type:Oper:CName',
            'PValue'                  : '1:Значение::value',
            'Comment'                 : '1:Примечание:text:memo:::::textarea',
            'OperSortIndex'           : '1:Индекс сортировки::sort',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FileTypeID'              : 'int:FileTypeID=%s',
            'FTVLinkID'               : 'int:FTVLinkID=%s',
            'TagParamID'              : 'int:TagParamID=%s',
            'OperTypeID'              : 'int:OperTypeID=%s',
            'PValue'                  : "varchar:PValue like '%%%s%%'::1",
            'Comment'                 : "varchar:Comment like '%%%s%%'::1",
            'OperSortIndex'           : 'int:OperSortIndex=%s:1-asc:',
            'FileType'                : 'varchar:#',
            'TagValue'                : 'varchar:#',
            'OperType'                : 'varchar:#',
            'Oper'                    : 'varchar:#',
            'PName'                   : "varchar:#",
        },
    },
    'reference.file-type-tagoperparams' : {
        'columns' : ('TID', 'FTV_OPER_ID', 'PName', 'PValue',),
        'view'    : '[BankDB].[dbo].[DIC_FTV_OPER_PARAMS_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FTV_OPER_ID'             : '1:Операция::fk1:1:reference.linked-tagopers:OperValue:PValue',
            'PName'                   : '1:Параметр операции::name',
            'PValue'                  : '1:Значение::value',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FTV_OPER_ID'             : 'int:FTV_OPER_ID=%s',
            'PName'                   : "varchar:PName like '%%%s%%':asc:1",
            'PValue'                  : "varchar:PValue like '%%%s%%'::1",
            'OperValue'               : 'varchar:#',
        },
    },
    'reference.file-type-processparams' : {
        'columns' : ('TID', 'FTVLinkID', 'TagParamID', 'PValue', 'Comment', 'PSortIndex',),
        'view'    : '[BankDB].[dbo].[DIC_FTV_PROCESS_tb]',
        'headers' : {
            'TID'                     : '1:PK::id:2',
            'FileTypeID'              : '0:Тип файла::fk1:2:reference.file-type:FileType:CName',
            'FTVLinkID'               : '1:Тег::fk2:1:reference.linked-tagvalues:TagValue:TagValue',
            'TagParamID'              : '1:Параметр ТЗ::fk3:1:reference.tag-params:PName:PName',
            'PValue'                  : '1:Значение параметра::value',
            'Comment'                 : '1:Примечание:text:memo:::::textarea',
            'PSortIndex'              : '1:Индекс сортировки::sort',
        },
        'fields'  : {
            'TID'                     : 'int:TID=%s',
            'FileTypeID'              : 'int:FileTypeID=%s',
            'FTVLinkID'               : 'int:FTVLinkID=%s',
            'TagParamID'              : 'int:TagParamID=%s',
            'PValue'                  : "varchar:PValue like '%%%s%%'::1",
            'Comment'                 : "varchar:Comment like '%%%s%%'::1",
            'PSortIndex'              : 'int:PSortIndex=%s:1-asc',
            'FileType'                : 'varchar:#',
            'TagValue'                : 'varchar:#',
            'PName'                   : "varchar:#",
        },
    },
}

def getReferenceConfig(view):
    item = deepcopy(_references.get(view))
    for key in item['headers']:
        item['headers'][key] = _reference_header(*(item['headers'][key].split(':')))
    for key in item['fields']:
        item['fields'][key] = _reference_field(*(item['fields'][key].split(':')))
    return item


class BankPersoEngine():
    
    def __init__(self, name=None, user=None, connection=None):
        self.name = name or 'default'
        self.connection = connection or default_connection
        self.engine = create_engine('mssql+pymssql://%(user)s:%(password)s@%(server)s' % self.connection)
        self.conn = self.engine.connect()
        self.engine_error = False
        self.user = user

        if IsDeepDebug:
            print('>>> open connection[%s]' % self.name)

    @property
    def database(self):
        return self.connection.get('database')

    @property
    def is_error(self):
        return self.engine_error

    def getReferenceID(self, name, key, value, tid='TID'):
        id = None
        
        if isinstance(value, str):
            where = "%s='%s'" % (key, value)
        else:
            where = '%s=%s' % (key, value)
            
        cursor = self.runQuery(name, top=1, columns=(tid,), where=where, distinct=True)
        if cursor:
            id = cursor[0][0]
        
        return id

    def _get_params(self, config, **kw):
        return 'exec_params' in kw and (config['params'] % kw['exec_params']) or kw.get('params') or ''

    def runProcedure(self, name, args=None, no_cursor=False, with_log=False, **kw):
        """
            Executes database stored procedure.
            Could be returned cursor.

            Parameter `with_error` can check error message/severity from SQL Server (raiserror).
        """
        if self.engine_error:
            return

        config = kw.get('config') or database_config[name]

        if args:
            sql = 'EXEC %(sql)s %(args)s' % { 
                'sql'    : config['exec'],
                'args'   : config['args'],
            }
        else:
            sql = 'EXEC %(sql)s %(params)s' % { 
                'sql'    : config['exec'],
                'params' : config['params'] % kw,
            }

        if IsDeepDebug:
            print('>>> runProcedure: %s' % out(sql))

        if with_log:
            print_to(None, '>>> runProcedure: %s' % sql, encoding=default_encoding)

        with_error = kw.get('with_error') and True or False

        return self.run(sql, args=args, no_cursor=no_cursor, with_error=with_error)

    def runQuery(self, name, top=None, offset=None, columns=None, where=None, order=None, distinct=False, as_dict=False, with_log=False, **kw):
        """
            Executes as database query so a stored procedure.
            Returns cursor.
        """
        if self.engine_error:
            return []

        config = kw.get('config') or database_config[name]

        query_columns = columns or config.get('columns')

        if 'clients' in config and self.user is not None:
            profile_clients = self.user.get_profile_clients(True)
            if profile_clients:
                clients = '%s in (%s)' % (
                    config['clients'],
                    ','.join([str(x) for x in profile_clients])
                )

                if where:
                    where = '%s and %s' % (where, clients)
                else:
                    where = clients

        _view = kw.get('view') or 'view'

        if _view in config and config[_view]:
            is_union = isIterable(where)
            union = is_union and where or [(offset, top, where)]

            items, params, sql = [], {}, ''

            params = { 
                'distinct' : distinct and 'DISTINCT' or '',
                'columns'  : ','.join(query_columns),
                'view'     : config[_view],
            }

            for o, t, w in union:
                params.update({
                    'where' : (where and 'WHERE %s' % w) or '',
                    'top'   : (t and 'TOP %s' % str(t)) or '',
                })

                if o is not None:
                    params.update({
                        'order'  : (order and 'ORDER BY %s' % order) or '',
                        'offset' : o or 0,
                    })

                    sql = ('SELECT %(distinct)s %(top)s %(columns)s FROM (select *, ROW_NUMBER() over (%(order)s) as rows ' + 
                          'from %(view)s %(where)s) x where rows > %(offset)s') % params
                else:
                    sql = 'SELECT %(distinct)s %(top)s %(columns)s FROM %(view)s %(where)s' % params

                if kw.get('as_subquery') and 'sql' in kw:
                    sql = kw['sql'] % sql

                if kw.get('with_updlock'):
                    x = sql.split('WHERE')
                    sql = '%s WITH (UPDLOCK)%s' % (x[0].strip(), len(x) > 1 and (' WHERE %s' % x[1].strip()) or '')

                items.append(sql)

            if is_union:
                sql = ' UNION '.join(items)
            else:
                sql = items[0]

            sql += (order and ' ORDER BY %s' % order) or ''

        else:
            params = { 
                'sql'      : config['exec'],
                'params'   : self._get_params(config, **kw),
            }
            sql = 'EXEC %(sql)s %(params)s' % params

        if IsDeepDebug:
            print('>>> runQuery: %s' % out(sql))

        if with_log:
            print_to(None, '>>> runQuery: %s' % sql, encoding=default_encoding)

        rows = []

        encode_columns = kw.get('encode_columns') or []
        worder_columns = kw.get('worder_columns') or []

        mapping = kw.get('mapping')

        cursor = self.execute(sql, no_traceback=kw.get('no_traceback'))

        if cursor is not None and not cursor.closed:
            if IsDeepDebug:
                print('--> in_transaction:%s' % cursor.connection.in_transaction())

            for n, line in enumerate(cursor):
                if as_dict and query_columns:
                    row = dict(zip(query_columns, line))
                else:
                    row = [x for x in line]

                line = None
                del line

                for column in encode_columns:
                    if column in row or isinstance(column, int):
                        row[column] = row[column] and row[column].encode(default_iso).decode(default_encoding) or ''
                for column in worder_columns:
                    row[column] = splitter(row[column], length=None, comma=':')
                if mapping:
                    row = dict([(key, row.get(name)) for key, name in mapping])
                rows.append(row)

            cursor.close()

        return rows

    def runCommand(self, sql, **kw):
        """
            Run sql-command with transaction.
            Could be returned cursor.
        """
        if self.engine_error:
            return

        if IsDeepDebug:
            print('>>> runCommand: %s' % sql)

        if kw.get('no_cursor') is None:
            no_cursor = True
        else:
            no_cursor = kw['no_cursor'] and True or False

        with_error = kw.get('with_error') and True or False

        return self.run(sql, no_cursor=no_cursor, with_error=with_error)

    def run(self, sql, args=None, no_cursor=False, with_error=False):
        if self.conn is None or self.conn.closed:
            if with_error:
                return [], ''
            else:
                return None

        rows = []
        error_msg = ''

        with self.conn.begin() as trans:
            try:
                if args:
                    cursor = self.conn.execute(sql, args)
                else:
                    cursor = self.conn.execute(sql)

                if IsDeepDebug:
                    print('--> in_transaction:%s' % cursor.connection.in_transaction())

                if not no_cursor and cursor:
                    rows = [row for row in cursor if row]

                trans.commit()

            except Exception as err:
                try:
                    trans.rollback()
                except:
                    pass

                if not no_cursor:
                    rows = []

                if err is not None and hasattr(err, 'orig') and (
                        isinstance(err.orig, pymssql.OperationalError) or 
                        isinstance(err.orig, pymssql.IntegrityError) or
                        isinstance(err.orig, pymssql.ProgrammingError)
                    ):
                    msg = len(err.orig.args) > 1 and err.orig.args[1] or ''
                    error_msg = msg and msg.decode().split('\n')[0] or 'unexpected error'
                    
                    if 'DB-Lib' in error_msg:
                        error_msg = re.sub(r'(,\s)', r':', re.sub(r'(DB-Lib)', r':\1', error_msg))
                else:
                    error_msg = 'database error'

                self.engine_error = True

                print_to(None, 'NO SQL QUERY: %s ERROR: %s' % (sql, error_msg))

                if IsPrintExceptions:
                    print_exception()

        if with_error:
            return rows, error_msg

        return rows

    def execute(self, sql, no_traceback=None, raise_error=None):
        try:
            return self.engine.execute(sql)
        except:
            if not no_traceback:
                print_to(None, 'NO SQL EXEC: %s' % sql)
                print_exception(1)

            self.engine_error = True

            if raise_error:
                raise

            return None

    def dispose(self):
        self.engine.dispose()

        if IsDeepDebug:
            print('>>> dispose')

    def close(self):
        if self.conn is None or self.conn.closed:
            return

        self.conn.close()

        if IsDeepDebug:
            print('>>> close connection[%s]' % self.name)

        self.dispose()


class Base:

    def __init__(self, requested_object, *args, **kwargs):
        if IsTrace:
            print_to(None, 'Base.init')

        super().__init__(*args, **kwargs)

        self.requested_object = requested_object

        self._id = None

    @property
    def id(self):
        return self._id


class Connection(Base):
    
    def __init__(self, connection, *args, **kwargs):
        if IsTrace:
            print_to(None, 'Connection.init')

        super().__init__(*args, **kwargs)

        self._connection = connection

        self.conn = None
        self.cursor = None
        self.is_error = False

    def open(self, autocommit=None):
        if IsTrace:
            print_to(None, 'Connection.open, autocommit:%s, connection:%s' % (autocommit, self._connection))

        server = self._connection['server']
        user = self._connection['user']
        password = self._connection['password']
        database = self._connection['database']
        timeout = int(self._connection.get('timeout') or 0)
        login_timeout = int(self._connection.get('login_timeout') or 60)

        self.conn, self.is_error = pymssql.connect(server, user, password, database, timeout, login_timeout), False

        if IsTrace:
            print_to(None, 'Connection.open, done')

        if autocommit is None:
            return

        self.conn.autocommit(autocommit and True or False)
        self.cursor = self.conn.cursor()

    def begin(self):
        pass

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        if self.is_error is not None:
            if self.is_error:
                self.rollback()
            else:
                self.commit()

        self.conn.close()

    def connect(self, sql, params, **kw):
        """
            Parameterized query.

            Arguments:
                sql     -- String, SQL query with params scheme
                params  -- List, query parameters

            Keyword arguments:
                with_commit -- Boolean, use transaction or not
                with_result -- Boolean, should be returned recodset
                callproc    -- Boolean, run stored procedure

            Returns:
                cursor      -- List, cursor or query results recordset
        """
        if IsTrace:
            print_to(None, 'Connection.connect, sql:%s' % sql)

        if kw.get('check_error') and self.is_error:
            return None

        _with_commit = kw.get('with_commit')
        _with_result = kw.get('with_result')
        _callproc = kw.get('callproc')

        _is_error = False

        if not hasattr(self, 'conn') or self.conn is None:
            self.open()

        conn = self.conn

        # ------------------
        # Check `autocommit`
        # ------------------

        if _with_commit is not None:
            if _with_commit: # and conn.autocommit_state:
                conn.autocommit(False)
            else:
                conn.autocommit(True)

        cursor = self.cursor

        if IsDeepDebug:
            print_to(None, 'with_commit: %s' % _with_commit)
            print_to(None, 'sql: %s' % sql)

        res = None

        try:
            p = params is not None and tuple(params) or ()

            if IsTrace:
                print_to(None, 'connect:execute, sql:%s, params:%s' % (sql, len(p)))

            if _callproc:
                res = cursor.callproc(sql, p)
            else:
                cursor.execute(sql, p)

            if IsTrace:
                print_to(None, 'connect:done')
        except:
            if IsPrintExceptions:
                print_exception()

            print_to(None, 'SQL:[%s]' % sql)

            if IsDeepDebug:
                print_to(None, 'params:%s' % repr(params))
        
            _is_error = True

        # ------------------------------------------------
        # Manage transaction if `autocommit` is turned off
        # ------------------------------------------------

        if _with_commit is not None:
            if _with_commit and not conn.autocommit_state:
                if _is_error:
                    conn.rollback()
                else:
                    conn.commit()

        self.conn, self.is_error = conn, _is_error

        if _with_result:
            if _callproc:
                return res
            else:
                res = list(cursor.fetchall())
                return self.encode_columns(res, kw.get('encode_columns'))

        return cursor

    @staticmethod
    def encode_columns(cursor, columns):
        if not (cursor and columns):
            return cursor
        rows = []
        for n, line in enumerate(cursor):
            row = [x for x in line]
            for column in columns:
                if column in row or isinstance(column, int):
                    row[column] = row[column] and row[column].encode(default_iso).decode(default_encoding) or ''
            rows.append(row)        
        return rows

    @staticmethod
    def get_value(x):
        return x and len(x) > 0 and x[0][0] or None


class DBEngine():
    
    def __init__(self, connection=None):
        self.connection = connection
        self.engine = create_engine('mssql+pymssql://%(user)s:%(password)s@%(server)s' % self.connection)
        self.conn = self.engine.connect()
        self.engine_error = False

        self.transaction = None

    def begin(self):
        self.transaction = self.conn.begin()

    def commit(self):
        self.transaction.commit()

    def rollback(self):
        self.transaction.rollback()

    def close(self):
        if self.engine_error:
            self.rollback()
        else:
            self.commit()

        self.conn.close()
        del self.conn

    def run(self, sp, params, raise_error=None):
        sql = 'EXEC %s' % (sp % params)

        cursor = None

        try:
            cursor = self.conn.execute(sql)
        except Exception as err:
            self.engine_error = True

            if IsPrintExceptions:
                print_exception()

            print_to(None, 'SQL:[%s]' % sql)
            
            if raise_error:
                raise
        
        rows = []

        if cursor is not None:
            for n, line in enumerate(cursor):
                row = []
                for x in line:
                    if x and isinstance(x, str):
                        row.append(x.encode(default_iso).decode(default_encoding))
                    else:
                        row.append(x)
                rows.append(row)

        return rows
