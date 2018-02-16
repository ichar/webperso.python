# -*- coding: utf-8 -*-

"""

mails.py
========

This module provides an easy way to send email with docx-attachment.
"""

__all__ = ['SendMail', 'send_materials_order']

import io
import smtplib

from email import encoders
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header

try:
    from config import (
        IsDebug, IsPrintExceptions, errorlog, print_to, print_exception,
        default_unicode, default_encoding,
        smtphost
    )
except:
    IsDebug = 1
    IsPrintExceptions = 0
    print_exception = None
    """
    default_unicode = 'utf-8'
    default_encoding = 'cp1251'
    
    smtphost = {'host':'mail2.rosan.ru', 'port':25}
    """

cr = '\n'

## ============================== ##

class SendMail(object):

    def __init__(self, subject, **kw):
        self._subject = subject
        self._from = kw.get('addr_from')
        self._to = kw.get('addr_to')

        self._msg = None

    def create_message(self, html):
        msg = MIMEMultipart()
        msg['Subject'] = self._subject
        msg['From'] = self._from
        msg['To'] = self._to

        if html:
            msg.attach(MIMEText(html, 'html'))

        self._msg = msg

    def attach_docx(self, document, filename):
        if not self._msg:
            return

        fp = io.BytesIO()
        document.save(fp)

        ctype = 'application/msword' #octet-stream vnd.ms-excel application/pdf vnd.ms-powerpoint image/png
        
        maintype, subtype = ctype.split('/', 1)
        base = MIMEBase(maintype, subtype)
        fp.seek(0)
        base.set_payload(fp.read())
        encoders.encode_base64(base)

        header = Header('%s.doc' % filename, charset=default_unicode)
        base.add_header('Content-Disposition', 'attachment', filename='%s' % header.encode())
        
        self._msg.attach(base)

        fp.close()

    def send(self):
        if smtphost is None or not smtphost.get('host'):
            return 0

        smtp = smtplib.SMTP(smtphost['host'], smtphost['port'])
        smtp.send_message(self._msg)
        smtp.quit()

        return 1


def send_test(subject, document, filename, html, **kw):
    if subject:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = kw.get('addr_from')
        msg['To'] = kw.get('addr_to')

        if html:
            msg.attach(MIMEText(html, 'html'))
    
        fp = io.BytesIO()
        document.save(fp)

        ctype = 'application/msword' #octet-stream vnd.ms-excel application/pdf vnd.ms-powerpoint image/png

        maintype, subtype = ctype.split('/', 1)
        base = MIMEBase(maintype, subtype)
        fp.seek(0)
        base.set_payload(fp.read())
        encoders.encode_base64(base)

        header = Header('%s.doc' % filename, charset=default_unicode)
        base.add_header('Content-Disposition', 'attachment', filename='%s' % header.encode())

        msg.attach(base)

        smtp = smtplib.SMTP(smtphost['host'], smtphost['port'])
        smtp.send_message(msg)
        smtp.quit()

        fp.close()

    return 1


def send_materials_order(subject, props, document, filename, **kw):
    """
        Materials order mail request.
    """
    html = '''
        <html>
        <head>
          <style type="text/css">
            h1 { font-size:18px; padding:0; margin:0 0 10px 0; }
            td { font-size:16px; font-weight:bold; line-height:24px; padding:0; color:#468; margin-left:0px; }
            div.line { border-top:1px dotted #888; width:100%%; height:1px; margin:10px 0 10px 0; }
            div.line hr { display:none; }
          </style>
        </head>
        <body>
          <h1 class="center">Файл заказа:</h1>
          <table>
          <tr><td class="value">%(ClientName)s</td><tr>
          <tr><td class="value">%(FileName)s</td></tr></table>
          <div class="line"><hr></div>
        </body>
        </html>
    ''' % props

    #return send_test(subject, document, filename, html, **kw)

    mail = SendMail(subject, **kw)

    mail.create_message(html)
    mail.attach_docx(document, filename)
    
    return mail.send()
    

if __name__ == "__main__":
    argv = sys.argv
