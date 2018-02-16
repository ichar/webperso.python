#!flask/bin/python
from app import app
#from config import setup_console, default_encoding, default_unicode, default_print_encoding
#setup_console(default_print_encoding)
app.run(host='0.0.0.0', port=8000, debug=True)
#app.run(debug=True)
