#!flask/bin/python

import os
from app import create_app, db
from flask.ext.script import Server, Manager, Shell
from config import setup_console, isIterable #, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO
from sqlalchemy import func, asc, desc, and_, or_

from app.models import (
     Pagination, User, ClientProfile, Setting, UserProfile,
     StringSettingValue, IntSettingValue, FloatSettingValue, BooleanSettingValue, DateTimeSettingValue,
     admin_view_users,
     setup, updateSettings
     )

app = create_app(os.getenv('APP_CONFIG') or 'default')

manager = Manager(app)

def make_shell_context():
    return dict( \
            app=app, db=db,
            Pagination=Pagination, func=func, asc=asc, desc=desc, and_=and_, or_=or_,
            User=User, ClientProfile=ClientProfile, Setting=Setting, UserProfile=UserProfile,
            StringSettingValue=StringSettingValue, 
            IntSettingValue=IntSettingValue, 
            FloatSettingValue=FloatSettingValue, 
            BooleanSettingValue=BooleanSettingValue, 
            DateTimeSettingValue=DateTimeSettingValue,
            admin_view_users=admin_view_users,
            isIterable=isIterable,
            setup=setup,
            updateSettings=updateSettings,
        )

manager.add_command("shell", Shell(make_context=make_shell_context))
#manager.add_command("start", Server(host='0.0.0.0', port=5000))

@manager.command
def test(coverage=False):
    """Run the unit tests."""
    pass

@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    #from werkzeug.contrib.profiler import ProfilerMiddleware
    #app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length], profile_dir=profile_dir)
    #app.run()
    pass

@manager.command
def deploy():
    """Run deployment tasks."""
    #from flask.ext.migrate import upgrade
    # migrate database to latest revision
    #upgrade()
    pass

@manager.command
def start():
    """Run server."""
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    manager.run()
