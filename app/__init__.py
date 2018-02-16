from flask import Flask
from flask.ext.bootstrap import Bootstrap
from flask.ext.mail import Mail
#from flask.ext.moment import Moment
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
#from flask.ext.pagedown import PageDown
from config import config

bootstrap = Bootstrap()
babel = Babel()
mail = Mail()
#moment = Moment()
db = SQLAlchemy()
#pagedown = PageDown()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    babel.init_app(app)
    mail.init_app(app)
    #moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    #pagedown.init_app(app)

    #if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
    #    from flask.ext.sslify import SSLify
    #    sslify = SSLify(app)

    from .bankperso import bankperso as bankperso_blueprint
    app.register_blueprint(bankperso_blueprint)

    from .cards import cards as cards_blueprint
    app.register_blueprint(cards_blueprint)

    from .configurator import configurator as configurator_blueprint
    app.register_blueprint(configurator_blueprint)
    """
    from .stock import stock as stock_blueprint
    app.register_blueprint(stock_blueprint)

    from .preload import preload as preload_blueprint
    app.register_blueprint(preload_blueprint)

    from .orderstate import orderstate as orderstate_blueprint
    app.register_blueprint(orderstate_blueprint)
    """
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from .semaphore import semaphore as semaphore_blueprint
    app.register_blueprint(semaphore_blueprint, url_prefix='/semaphore')

    from .profile import profile as profile_blueprint
    app.register_blueprint(profile_blueprint, url_prefix='/profile')

    #from .api import api as api_blueprint
    #app.register_blueprint(api_blueprint, url_prefix='/api')

    return app
