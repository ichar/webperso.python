# -*- coding: utf-8 -*-

import re
from sqlalchemy import create_engine
from copy import deepcopy
import pymssql

from config import (
     CONNECTION, IsDebug, IsDeepDebug,
     default_unicode, default_encoding, default_iso,
     print_to, print_exception
     )

from .utils import splitter, worder, getMaskedPAN

default_connection = CONNECTION['bankperso']

database_config = { \
    # =========
    # BANKPERSO
    # =========
    'orders' : { \
        'columns' : ('FileID', 'FName', 'FQty', 'BankName', 'FileType', 'StatusDate', 'FileStatus', 'RegisterDate', 'ReadyDate',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersStatus_vw]',
        'headers' : { \
            'FileID'       : ('ID файла',                   '',),
            'FName'        : ('ФАЙЛ',                       'nowrap',),
            'FQty'         : ('Кол-во',                     '',),
            'BankName'     : ('КЛИЕНТ',                     'nowrap',),
            'FileType'     : ('Тип файла',                  '',),
            'StatusDate'   : ('Дата статуса',               '',),
            'FileStatus'   : ('СТАТУС',                     'breakable',),
            'RegisterDate' : ('Дата регистрации',           '',),
            'ReadyDate'    : ('Ожидаемая дата готовности',  '',),
        },
        'clients' : 'ClientID',
        'export'  : ('FileID', 'FileTypeID', 'ClientID', 'FileStatusID', 'FName', 'FQty', 'BankName', 'FileType', 'StatusDate', 'FileStatus', 'RegisterDate', 'ReadyDate',),
    },
    'batches' : { \
        'columns' : ('TZ', 'TID', 'BatchType', 'BatchNo', 'ElementQty', 'Status', 'StatusDate',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersBatchList_vw]',
        'headers' : { \
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
    'batches.preview' : { \
        'columns' : ('TID',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersBatchPreview_vw]',
        'export'  : ('TID', 'IsPrintMaterialOrder', 'BatchStatusID', 'FileStatusID', 'RegisterDate',),
    },
    'logs' : { \
        'columns' : ('LID', 'ModDate', 'FileStatusID', 'Status', 'Oper', 'HostName', 'ApplName', 'UserName',), # 'LID', 'TID',
        'view'    : '[BankDB].[dbo].[WEB_OrdersLog_vw]',
        'headers' : { \
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
    'banks' : { \
        'columns' : ('ClientID', 'BankName',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersStatus_vw]',
        'headers' : { \
            'BankName'     : 'Клиент',
        },
        'clients' : 'ClientID',
    },
    'clients' : { \
        'columns' : ('TID', 'CName'),
        'view'    : '[BankDB].[dbo].[DIC_Clients_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'CName'        : 'Наименование',
        },
        'clients' : 'TID',
    },
    'types' : { \
        'columns' : ('TID', 'CName', 'ClientID',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'ClientID'     : 'ID клиента',
            'CName'        : 'Тип файла',
        },
        'clients' : 'ClientID',
    },
    'statuses' : { \
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_FileStatus_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'Status'       : 'Статус файла',
        },
    },
    'filestatuses' : { \
        'columns' : ('FileID', 'FileStatusID',),
        'view'    : '[BankDB].[dbo].[OrderFilesBody_tb]',
        'headers' : { \
            'Status'       : 'Статус файла',
        },
    },
    'filestatuslist' : { \
        'columns' : ('TID', 'StatusTypeID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_FileStatus_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'StatusTypeID' : 'Тип cтатуса',
            'CName'        : 'Наименование',
        },
    },
    'batchstatuslist' : { \
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_BatchStatus_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'CName'        : 'Наименование',
        },
    },
    'batchtypelist' : { \
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_BatchType_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'CName'        : 'Наименование',
        },
    },
    'params' : { \
        'columns' : ('TID', 'PName', 'PValue', 'PSortIndex', 'TName', 'TValue', 'FTVLinkID', 'TagParamID', 'FileTypeID', 'FileID', 'BatchID', 'PERS_TZ', 'BatchTypeID', 'ElementQty',),
        'exec'    : '[BankDB].[dbo].[WEB_GetBatchParamValues_sp]',
        'headers' : { \
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
    'image': { \
        'columns' : ('FileID', 'FBody',),
        'exec'    : '[BankDB].[dbo].[WEB_GetOrderFileBodyImage_sp]',
        'headers' : { \
            'FileID'       : 'ID файла',
            'FBody'        : 'Контент заказа',
        },
    },
    'body': { \
        'columns' : ('FileID', 'FileStatusID', 'IBody',),
        'exec'    : '[BankDB].[dbo].[WEB_GetOrderFileBody_sp]',
        'headers' : { \
            'FileID'       : 'ID файла',
            'FileStatusID' : 'ID статуса файла',
            'IBody'        : 'Контент заказа',
        },
    },
    'TZ' : { \
        'columns' : ('PName', 'PValue', 'PSortIndex', 'PType', 'ElementQty',),
        'exec'    : '[BankDB].[dbo].[WEB_GetBatchParamValues_sp]',
        'headers' : { \
            'PName'        : 'Название параметра',
            'PValue'       : 'Значение',
            'ElementQty'   : 'Количество элементов в партии',
            'PSortIndex'   : 'Индекс сортировки',
            'PType'        : 'Тип параметра',
        },
        'exclude' : ('CLIENTID', 'DeliveryType', 'PackageCode',),
        'rename'  : { \
            'PlasticType'  : ('', 25),
        },
    },
    'materials.order' : { \
        'columns' : ('BatchType', 'ERP_TZ', 'MName', 'BatchQty', 'Qty',),
        'params'  : "%(file_id)s,%(show)s",
        'exec'    : '[BankDB].[dbo].[WEB_MaterialForFile_sp]',
        'headers' : { \
            'BatchType'    : 'Тип партии',
            'ERP_TZ'       : 'ЕРП ТЗ',
            'MName'        : 'Наименование материала',
            'BatchQty'     : 'Количество элементов в партии',
            'Qty'          : 'Зарезервировать на складе',
        },
    },
    'materials.approval' : { \
        'params'  : "%(file_id)s,'%(file_status_ids)s',0",
        'exec'    : '[BankDB].[dbo].[WEB_ApprovalMaterialOrder_sp]',
    },
    'materials.check' : { \
        'params'  : "%(file_id)s,'%(file_status_ids)s',%(check)s",
        'exec'    : '[BankDB].[dbo].[WEB_ApprovalMaterialOrder_sp]',
    },
    'persolog': { \
        'columns' : ('Date', 'Code', 'Message',),
        'headers' : { \
            'Date'         : 'Дата Время',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
        'export'  : ('Date', 'Code', 'Message',),
    },
    'infoexchangelog': { \
        'columns' : ('Date', 'Code', 'Message',),
        'headers' : { \
            'Date'         : 'Дата Время',
            'Time'         : 'Время',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
        'export' : ('Date', 'Code', 'Message',), # , 'Time'
    },
    'sdclog': { \
        'columns' : ('Date', 'Code', 'Message',),
        'headers' : { \
            'Date'         : 'Дата Время',
            'Time'         : 'Время',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
        'export'  : ('Date', 'Time', 'Code', 'Message',),
    },
    'exchangelog': { \
        'columns' : ('Date', 'Module', 'Code', 'Message',),
        'headers' : { \
            'Date'         : 'Дата Время',
            'Time'         : 'Время',
            'Module'       : 'Модуль',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
        'export'  : ('Date', 'Time', 'Module', 'Code', 'Message',),
    },
    'bankperso.semaphore': { \
        'columns' : ('LID', 'Status', 'Oper',),
        'params'  : "%(mode)s,%(oid)s,%(bid)s,null,''",
        'exec'    : '[BankDB].[dbo].[WEB_SemaphoreEvents_sp]',
    },
    # --------------------------------
    # Представления на контенте заказа
    # --------------------------------
    'cardholders' : { \
        'root'    : 'FileBody_Record',
        'tags'    : ( \
            ('FileRecNo',),
            ('PAN', 'PANWIDE',),
            ('EMBNAME1', 'FIO', 'ClientName', 'CardholderName', 'EMBNAME', ('FIRSTNAME', 'SECONDNAME', 'LASTNAME'), 
                ('LSTN', 'FRSN'), ('FirstName', 'SurName', 'SecondName'), 'EmbName', 'TRACK1NAME',),
            ('ExpireDate', 'EDATE', 'EDATE_YYMM', 'EXPDATE', 'EDATE_YYYYMM',),
            ('PLASTIC_CODE', 'PlasticType', 'PLASTIC_TYPE', 'PlasticID',),
            ('CardType', 'CLIENT_ID', 'CHIP_ID',),
            ('KIND',),
            ('FactAddress', 'BRANCH_NAME', 'DEST_NAME',)
        ),
        'columns' : ('FileRecNo', 'PAN', 'Cardholder', 'ExpireDate', 'PLASTIC_CODE', 'CardType', 'KIND', 'FactAddress',),
        'headers' : { \
            'FileRecNo'    : '#',
            'PAN'          : 'PAN',
            'Cardholder'   : 'ФИО клиента',
            'ExpireDate'   : 'Дата истечения',
            'PLASTIC_CODE' : 'Код пластика',
            'CardType'     : 'Тип карты',
            'KIND'         : 'Вид',
            'FactAddress'  : 'Фактический адрес',
        },
        'func'    : {'PAN' : getMaskedPAN },
    },
    # ---------------
    # Операции BankDB
    # ---------------
    'activate' : { \
        'params'  : '%(batch_id)s',
        'exec'    : '[BankDB].[dbo].[WEB_BatchActivate_sp]',
    },
    'changefilestatus' : { \
        'params'  : "null,null,0,%(file_id)s,%(check_file_status)s,%(new_file_status)s,null,null,null,1,0,0,0",
        'exec'    : '[BankDB].[dbo].[WEB_ChangeOrderState_sp]',
    },
    'changebatchstatus' : { \
        'params'  : "null,null,0,%(file_id)s,null,null,%(batch_id)s,null,%(new_batch_status)s,0,1,0,0",
        'exec'    : '[BankDB].[dbo].[WEB_ChangeOrderState_sp]',
    },
    'deletefile' : { \
        'params'  : "null,null,0,%(file_id)s,null,0,null,null,0,1,1,1,1",
        'exec'    : '[BankDB].[dbo].[WEB_ChangeOrderState_sp]',
    },
    'createfile'  : { \
        'params'  : "null,null,0,%(file_id)s,1,1,null,null,0,1,1,1,0",
        'exec'    : '[BankDB].[dbo].[WEB_ChangeOrderState_sp]',
    },
    'dostowin' : { \
        'params'  : "0,'%s'",
        'exec'    : '[BankDB].[dbo].[WEB_DecodeCyrillic_sp]',
    },
    'wintodos' : { \
        'params'  : "1,'%s'",
        'exec'    : '[BankDB].[dbo].[WEB_DecodeCyrillic_sp]',
    },
    # ==================
    # CARDS PERSOSTATION
    # ==================
    'cards.batches' : { \
        'columns' : ('TID', 'Client', 'FName', 'TZ', 'BQty', 'PQty', 'PersType', 'PersStatus', 'Status',), # 'StatusDate', 'BatchID'
        'view'    : '[Cards].[dbo].[WEB_Batches_vw]',
        'headers' : { \
            'TID'          : ('ID партии',       '',),
            'BatchID'      : ('ID ТЗ',           '',),
            'Client'       : ('КЛИЕНТ',          '',),
            'FName'        : ('ФАЙЛ ЗАКАЗА',     'breakable',),
            'TZ'           : ('№ ТЗ',            '',),
            'BQty'         : ('Кол-во в ТЗ',     '',),
            'PQty'         : ('Кол-во в партии', '',),
            'PersType'     : ('Тип партии',      '',),
            'Status'       : ('Статус ТЗ',       'nowrap',),
            'PersStatus'   : ('Статус партии',   'nowrap',),
            'StatusDate'   : ('Дата статуса',    '',),
        },
        'export'  : ('TID', 'BatchID', 'Client', 'FName', 'TZ', 'BQty', 'PQty', 'PersType', 'Status', 'PersStatus', 'StatusDate', 'StatusID', 'PersTypeID',),
    },
    'cards.batches-log' : { \
        'columns' : ('LID', 'Status', 'StatusID', 'StatusDate', 'Oper', 'HostName', 'ApplName', 'UserName', 'ModDate'),
        'view'    : '[Cards].[dbo].[WEB_BatchesLog_vw]',
        'headers' : { \
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
    'cards.batch-opers' : { \
        'columns' : ('TID', 'CName', 'Status', 'StatusDate',),
        'view'    : '[Cards].[dbo].[WEB_BatchOpers_vw]',
        'headers' : { \
            'TID'          : 'ID операции',
            'CName'        : 'Тип операции',
            'Status'       : 'Статус операции',
            'StatusDate'   : 'Дата статуса',
        },
        'export'  : ('TID', 'CName', 'Status', 'StatusDate', 'BatchID', 'StatusID', 'PersOperTypeID',),
    },
    'cards.batch-opers-log' : { \
        'columns' : ('LID', 'PersOperType', 'Status', 'StatusID', 'StatusDate', 'Oper', 'HostName', 'ApplName', 'UserName', 'ModDate'),
        'view'    : '[Cards].[dbo].[WEB_PersBatchOpersLog_vw]',
        'headers' : { \
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
    'cards.batch-params' : { \
        'columns' : ('TID', 'PType', 'PName', 'PValue',),
        'view'    : '[Cards].[dbo].[WEB_BatchParams_vw]',
        'headers' : { \
            'TID'          : 'ID параметра',
            'PType'        : 'Тип параметра',
            'PName'        : 'Наименование параметра',
            'PValue'       : 'Значение',
        },
        'export'  : ('TID', 'BatchID', 'TZ', 'PType', 'PName', 'PValue',),
    },
    'cards.pers-batch-opers' : { \
        'columns' : ('TID', 'Oper', 'Status', 'StatusDate',),
        'view'    : '[Cards].[dbo].[WEB_PersBatchOpers_vw]',
        'headers' : { \
            'TID'          : 'ID операции',
            'Oper'         : 'Тип операции',
            'Status'       : 'Статус операции',
            'StatusDate'   : 'Дата статуса',
        },
        'export'  : ('TID', 'Oper', 'Status', 'StatusDate', 'PersBatchID', 'PersOperTypeID', 'PersBatchOperStatusID',),
    },
    'cards.batch-oper-params' : { \
        'columns' : ('TID', 'PName', 'PValue',),
        'view'    : '[Cards].[dbo].[WEB_BatchOperParams_vw]',
        'headers' : { \
            'TID'          : 'ID параметра',
            'PName'        : 'Наименование параметра',
            'PValue'       : 'Значение',
        },
        'export'  : ('TID', 'PName', 'PValue', 'BatchID', 'PersBatchID', 'BatchOperID', 'BatchOperTypeID',),
    },
    'cards.batch-units' : { \
        'columns' : ('TID', 'FileRecNo', 'PAN', 'Status', 'StatusDate',), #, 'BatchStatus'
        'view'    : '[Cards].[dbo].[WEB_BatchUnits_vw]',
        'headers' : { \
            'TID'          : 'ID карты',
            'FileRecNo'    : 'Номер записи',
            'PAN'          : 'PAN',
            'Status'       : 'Наименование статуса',
            'BatchStatus'  : 'Статус партии',
            'StatusDate'   : 'Дата статуса',
        },
        'export'  : ('TID', 'FileRecNo', 'PAN', 'Status', 'BatchStatus', 'StatusDate', 'BatchID', 'StatusID'),
    },
    'cards.clients' : { \
        'columns' : ('Client',),
        'view'    : '[Cards].[dbo].[WEB_Clients_vw]',
    },
    'cards.files' : { \
        'columns' : ('Client', 'FileName',),
        'view'    : '[Cards].[dbo].[WEB_Files_vw]',
    },
    'cards.perstypes' : { \
        'columns' : ('TID', 'CName',),
        'view'    : '[Cards].[dbo].[WEB_PersTypes_vw]',
    },
    'cards.statuses' : { \
        'columns' : ('TID', 'CName',),
        'view'    : '[Cards].[dbo].[WEB_Statuses_vw]',
    },
    'cards.persstatuses' : { \
        'columns' : ('CName',),
        'view'    : '[Cards].[dbo].[WEB_GetPersBatchStatuses_fn]()',
    },
    'cards.semaphore': { \
        'columns' : ('LID', 'Status', 'Oper',),
        'params'  : "%(mode)s,%(oid)s,%(bid)s,null,''",
        'exec'    : '[Cards].[dbo].[WEB_SemaphoreEvents_sp]',
    },
    # --------------
    # Операции Cards
    # --------------
    'cards.activate' : { \
        'params'  : "%(pers_id)s",
        'exec'    : '[Cards].[dbo].[WEB_PersBatch_Activate_sp]',
    },
    'cards.reject' : { \
        'params'  : "%(pers_id)s",
        'exec'    : '[Cards].[dbo].[WEB_PersBatch_Reject_sp]',
    },
    # -------------------------------
    # Параметры партий персонализации
    # -------------------------------
    'cards.plastic-params' : { \
        'exec'    : '[Cards].[dbo].[WEB_BatchFreeParams_For_PlasticOrder_sp]',
        'params'  : "'%(pers_ids)s'",
        'fields'  : { \
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
        'TZ' : { \
            'Column1'      : 'Клиент',
            'Column2'      : 'Тип карт',
            'Column3'      : 'Тип пластика',
            'Column4'      : 'ERP ТЗ',
        },
    },
    'cards.plastic-params-new' : { \
        'exec'    : '[Cards].[dbo].[WEB_BatchFreeParams_For_PlasticOrderNew_sp]',
        'params'  : "'%(pers_ids)s'",
        'fields'  : { \
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
        'TZ' : { \
            'Column1'      : 'Клиент',
            'Column2'      : 'Тип карт',
            'Column3'      : 'Тип пластика',
            'Column4'      : 'ERP ТЗ',
        },
    },
    'cards.plastic-params-info' : { \
        'exec'    : '[Cards].[dbo].[W_GetClientIDStr_fn]',
        'params'  : "%(pers_id)s",
        'fields'  : { \
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
    'preloads' : { \
        'columns' : ('PreloadID', 'FName', 'FQty', 'BankName', 'StartedDate', 'FinishedDate', 'ErrorCode', 'OrderNum', 'FinalMessage', 'RegisterDate',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersPreload_vw]',
        'headers' : { \
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
    'articles' : { \
        'columns' : ('[#]', 'Article', 'BIN', 'V', 'Q', 'unavailable',),
        'view'    : '[BankDB].[dbo].[WEB_OrdersPreloadArticleList_vw]',
        'headers' : { \
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
    'orderstate-orders' : { \
        'columns' : ('TID', 'Client', 'BP_FileID', 'PackageName', 'Qty', 'Host', 'BaseFolder', 'ArchiveFolder', 'RD',),
        'view'    : '[OrderState].[dbo].[SHOW_Orders_vw]',
        'headers' : { \
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
    'orderstate-orders:by-type' : { \
        'columns' : 'self',
        'params'  : "%(client_id)s,%(config_id)s,%(action_id)s,'%(type)s','%(date_from)s','%(date_to)s',%(sort)s,''",
        'exec'    : '[OrderState].[dbo].[WEB_GetOrdersByConfigType_sp]',
        'headers' : 'self',
        'clients' : 'ClientID',
        'export'  : 'self',
    },
    'orderstate-events' : { \
        'columns' : ('TID', 'Action', 'Type', 'ToFolder', 'Result',), #, 'Started', 'Finished', 'Duration', 'Weight', 'RD',
        'view'    : '[OrderState].[dbo].[SHOW_vw]',
        'headers' : { \
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
    'orderstate-files' : { \
        'columns' : ('TID', 'Address', 'Name', 'IsError'), #, 'ConfigID', 'OrderID'
        'view'    : '[OrderState].[dbo].[SHOW_Files_vw]',
        'headers' : { \
            'TID'          : 'ID файла',
            'ConfigID'     : 'ID сценария',
            'OrderID'      : 'ID заказа',
            'Address'      : 'Событие',
            'Name'         : 'ИМЯ ФАЙЛА', 
            'IsError'      : 'Ошибка',
        },
        'export'  : ('TID', 'ConfigID', 'OrderID', 'Address', 'Name', 'IsError'),
    },
    'orderstate-errors' : { \
        'columns' : ('SourceFileID', 'OrderID', 'Address', 'Started', 'Finished', 'Result', 'ErrorMessage', 'RD',),
        'view'    : '[OrderState].[dbo].[SHOW_Errors_vw]',
        'headers' : { \
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
    'orderstate-certificates' : { \
        'columns' : ('Event', 'Info', 'RD',),
        'view'    : '[OrderState].[dbo].[SHOW_OrderCertificates_vw]',
        'headers' : { \
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
    'orderstate-aliases' : { \
        'columns' : ('TID', 'Name', 'Title', 'Aliases',),
        'view'    : '[OrderState].[dbo].[SHOW_Aliases_vw]',
        'headers' : { \
            'TID'          : 'ID клиента',
            'Name'         : 'Клиент', 
            'Title'        : 'Полное наименование',
            'Aliases'      : 'Алиасы',
        },
        'export'  : ('TID', 'Name', 'Title', 'Aliases',),
    },
    'orderstate-actions' : { \
        'columns' : ('TID', 'Name',),
        'view'    : '[OrderState].[dbo].[DIC_Actions_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'Name'         : 'Операция',
        },
        'clients' : 'TID',
    },
    'orderstate-clients' : { \
        'columns' : ('TID', 'Name',),
        'view'    : '[OrderState].[dbo].[DIC_Clients_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'Name'         : 'Клиент',
        },
        'clients' : 'TID',
    },
    'orderstate-configs' : { \
        'columns' : ('TID', 'Name',),
        'view'    : '[OrderState].[dbo].[DIC_Configs_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'Name'         : 'Сценарий',
        },
        'clients' : 'TID',
    },
    'orderstate-types' : { \
        'columns' : ('Type',),
        'view'    : '[OrderState].[dbo].[DIC_Configs_tb]',
    },
    'orderstate-eventinfo' : { \
        'columns' : ('PName', 'PValue', 'PSortIndex', 'PType',),
        'exec'    : '[OrderState].[dbo].[WEB_GetEventInfo_sp]',
        'headers' : { \
            'PName'        : 'Название параметра',
            'PValue'       : 'Значение',
            'PSortIndex'   : 'Индекс сортировки',
            'PType'        : 'Тип параметра',
        },
    },
    'orderstate-log': { \
        'columns' : ('Date', 'Code', 'Message',),
        'headers' : { \
            'Date'         : 'Дата Время',
            'Code'         : 'Результат',
            'Message'      : 'Текст сообщения',
        },
    },
    # ======================
    # BANKPERSO CONFIGURATOR
    # ======================
    'configurator-files' : { \
        'columns' : ('TID', 'ClientID', 'Client', 'FileType', 'ReportPrefix',),
        'view'    : '[BankDB].[dbo].[WEB_FileTypes_vw]',
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
    'configurator-batches' : { \
        'columns'   : ('TID', 'BatchTypeID', 'BatchType', 'BatchMaxQty', 'IsErpBatch', 'CreateBatchSortIndex', 'CreateBatchGroupIndex',), #, 'BatchCreateType', 'BatchResultType'
        'view'      : '[BankDB].[dbo].[WEB_BatchTypes_vw]',
        'headers'   : { \
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
    'configurator-processes' : { \
        'columns' : ('TID', 'FileType', 'BatchType', 'CurrFileStatus', 'NextFileStatus', 'CloseFileStatus', 'ActivateBatchStatus_', 'ARMBatchStatus_', 'Memo'),
        'view'    : '[BankDB].[dbo].[WEB_FileProcesses_vw]',
        'headers' : { \
            'TID'                 : 'ID сценария',
            'FileType'            : 'Тип файла', 
            'BatchType'           : 'Тип партии',
            'CurrFileStatus'      : 'Текущий статус партии', 
            'NextFileStatus'      : 'Следующий статус партии', 
            'CloseFileStatus'     : 'Конечный статус партии', 
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
    'configurator-opers' : { \
        'columns' : ('TID', 'FileType', 'BatchType', 'OperTypeName', 'OperType', 'OperSortIndex',),
        'view'    : '[BankDB].[dbo].[WEB_FileOpers_vw]',
        'headers' : { \
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
    'configurator-operparams' : { \
        'columns' : ('TID', 'FileType', 'BatchType', 'OperTypeName', 'OperType', 'PName', 'PValue', 'Comment',),
        'view'    : '[BankDB].[dbo].[WEB_FileOperParams_vw]',
        'headers' : { \
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
    'configurator-filters' : { \
        'columns' : ('TID', 'FileType', 'BatchType', 'TName', 'CriticalValues',),
        'view'    : '[BankDB].[dbo].[WEB_FileFilters_vw]',
        'headers' : { \
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
    'configurator-tags' : { \
        'columns' : ('TID', 'FileType', 'TName', 'TMemo',),
        'view'    : '[BankDB].[dbo].[WEB_FileTags_vw]',
        'headers' : { \
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
    'configurator-tagvalues' : { \
        'columns' : ('TID', 'FileType', 'TName', 'TValue',),
        'view'    : '[BankDB].[dbo].[WEB_FileTagValues_vw]',
        'headers' : { \
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
    'configurator-tzs' : { \
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'PName', 'PValue', 'PSortIndex', 'Comment',),
        'view'    : '[BankDB].[dbo].[WEB_FileTZs_vw]',
        'headers' : { \
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
    'configurator-erpcodes' : { \
        'columns' : ('TID', 'FileType', 'BatchType', 'TName', 'TValue', 'ERP_CODE', 'AdditionalInfo',),
        'view'    : '[BankDB].[dbo].[WEB_FileERPCodes_vw]',
        'headers' : { \
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
    'configurator-materials' : { \
        'columns' : ('TID', 'FileType', 'BatchType', 'TName', 'TValue', 'PName', 'QtyMode', 'MMin', 'MBadPercent',),
        'view'    : '[BankDB].[dbo].[WEB_FileMaterials_vw]',
        'headers' : { \
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
    'configurator-posts' : { \
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'PName', 'PValue', 'Comment',),
        'view'    : '[BankDB].[dbo].[WEB_FilePosts_vw]',
        'headers' : { \
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
    'configurator-tagopers' : { \
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'OperType', 'Oper', 'PName', 'PValue', 'OperSortIndex', 'Comment',),
        'view'    : '[BankDB].[dbo].[WEB_FileTagOpers_vw]',
        'headers' : { \
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
    'configurator-tagoperparams' : { \
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'OperTypeValue', 'OperValue', 'PName', 'PValue',),
        'view'    : '[BankDB].[dbo].[WEB_FileTagOperParams_vw]',
        'headers' : { \
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
    'configurator-processparams' : { \
        'columns' : ('TID', 'FileType', 'TName', 'TValue', 'PName', 'PValue', 'Comment', 'PSortIndex',),
        'view'    : '[BankDB].[dbo].[WEB_FileProcessParams_vw]',
        'headers' : { \
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
    'configurator-clients' : { \
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_Clients_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'CName'        : 'Клиент',
        },
        'clients' : 'TID',
    },
    'configurator-filetypes' : { \
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_FileType_vw]',
        'headers' : { \
            'TID'          : 'ID',
            'CName'        : 'Тип файла',
        },
        'filetypes' : 'TID',
    },
    'configurator-batchtypes' : { \
        'columns' : ('TID', 'CName',),
        'view'    : '[BankDB].[dbo].[DIC_BatchType_tb]',
        'headers' : { \
            'TID'          : 'ID',
            'BatchType'    : 'Тип партии',
        },
        'batchtypes' : 'TID',
    },
    'configurator-batchinfo' : { \
        'columns' : ('PName', 'PValue', 'PSortIndex', 'PType',),
        'exec'    : '[BankDB].[dbo].[WEB_GetBatchTypeInfo_sp]',
        'headers' : { \
            'PName'        : 'Название параметра',
            'PValue'       : 'Значение',
            'PSortIndex'   : 'Индекс сортировки',
            'PType'        : 'Тип параметра',
        },
    },
    # ==============
    # LOGGER SERVICE
    # ==============
    'orderlog-messages' : { \
        'columns' : ('TID', 'IP', 'Root', 'Module', 'LogFile', 'Code', 'Count', 'Message', 'EventDate',),
        'view'    : '[OrderLog].[dbo].[WEB_OrderMessages_vw]',
        'headers' : { \
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
    'orderlog-check-source' : { \
        'params'  : "0,'%(root)s','%(ip)s','%(ctype)s',null",
        'args'    : '0,%s,%s,%s,null',
        'exec'    : '[OrderLog].[dbo].[CHECK_Source_sp]',
    },
    'orderlog-check-module' : { \
        'params'  : "0,%(source_id)s,'%(cname)s','%(cpath)s',null",
        'args'    : '0,%d,%s,%s,null',
        'exec'    : '[OrderLog].[dbo].[CHECK_Module_sp]',
    },
    'orderlog-check-log' : { \
        'params'  : "0,%(source_id)s,%(module_id)s,'%(cname)s',null",
        'args'    : '0,%d,%d,%s,null',
        'exec'    : '[OrderLog].[dbo].[CHECK_Log_sp]',
    },
    'orderlog-register-log-message' : { \
        'params'  : "0,%(source_id)s,%(module_id)s,%(log_id)s,'%(source_info)s','%(module_info)s','%(log_info)s',%(fileid)s,%(batchid)s,'%(client)s','%(filename)s','%(code)s',%(count)s,'%(message)s','%(event_date)s','%(rd)s',null",
        'args'    : '0,%d,%d,%d,%s,%s,%s,%d,%d,%s,%s,%s,%d,%s,%s,%s,null',
        'exec'    : '[OrderLog].[dbo].[REGISTER_LogMessage_sp]',
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
            'PValue'                  : '1:Значение параметра ТЗ::value',
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
    
    def __init__(self, user=None, connection=None):
        self.connection = connection or default_connection
        self.engine = create_engine('mssql+pymssql://%(user)s:%(password)s@%(server)s' % self.connection)
        self.conn = self.engine.connect()
        self.engine_error = False
        self.user = user

        if IsDeepDebug:
            print('>>> open connection')

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

    def runProcedure(self, name, args=None, no_cursor=False, **kw):
        """
            Executes database stored procedure.
            Could be returned cursor.

            Parameter `with_error` can check error message/severity from SQL Server (raiserror).
        """
        if self.engine_error:
            return

        config = kw.get('config') or database_config[name]

        if args:
            sql = 'EXEC %(sql)s %(args)s' % { \
                'sql'    : config['exec'],
                'args'   : config['args'],
            }
        else:
            sql = 'EXEC %(sql)s %(params)s' % { \
                'sql'    : config['exec'],
                'params' : config['params'] % kw,
            }

        if IsDeepDebug:
            print('>>> runProcedure: %s' % sql)

        with_error = kw.get('with_error') and True or False

        return self.run(sql, args=args, no_cursor=no_cursor, with_error=with_error)

    def runQuery(self, name, top=None, columns=None, where=None, order=None, distinct=False, as_dict=False, **kw):
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
                clients = '%s in (%s)' % ( \
                    config['clients'],
                    ','.join([str(x) for x in profile_clients])
                )

                if where:
                    where = '%s and %s' % (where, clients)
                else:
                    where = clients

        if 'view' in config and config['view']:
            params = { \
                'distinct' : distinct and 'DISTINCT' or '',
                'top'      : (top and 'TOP %s' % str(top)) or '',
                'columns'  : ','.join(query_columns),
                'view'     : config['view'],
                'where'    : (where and 'WHERE %s' % where) or '',
                'order'    : (order and 'ORDER BY %s' % order) or '',
            }
            sql = 'SELECT %(distinct)s %(top)s %(columns)s FROM %(view)s %(where)s %(order)s' % params
        else:
            params = { \
                'sql'      : config['exec'],
                'params'   : self._get_params(config, **kw),
            }
            sql = 'EXEC %(sql)s %(params)s' % params

        if IsDeepDebug:
            print('>>> runQuery: %s' % sql)

        rows = []

        encode_columns = kw.get('encode_columns') or []
        worder_columns = kw.get('worder_columns') or []

        mapping = kw.get('mapping')

        cursor = self.execute(sql)

        if cursor is not None and not cursor.closed:
            if IsDeepDebug:
                print('--> in_transaction:%s' % cursor.connection.in_transaction())

            for n, line in enumerate(cursor):
                if as_dict and query_columns:
                    row = dict(zip(query_columns, line))
                else:
                    row = [x for x in line]
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

                if not no_cursor:
                    rows = [row for row in cursor if cursor]

                trans.commit()

            except Exception as err:
                trans.rollback()

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
                print_exception()

        if with_error:
            return rows, error_msg

        return rows

    def execute(self, sql):
        try:
            return self.engine.execute(sql)
        except:
            print_to(None, 'NO SQL EXEC: %s' % sql)
            print_exception()

            self.engine_error = True

            return None

    def dispose(self):
        self.engine.dispose()

        if IsDeepDebug:
            print('>>> dispose')

    def close(self):
        self.conn.close()

        if IsDeepDebug:
            print('>>> close connection')

        self.dispose()
