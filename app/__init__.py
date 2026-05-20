from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

from .config import config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()


def create_app(config_name='default'):
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    from .blueprints.auth import auth_bp
    from .blueprints.catalogue import catalogue_bp
    from .blueprints.commandes import commandes_bp
    from .blueprints.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(catalogue_bp, url_prefix='/')
    app.register_blueprint(commandes_bp, url_prefix='/commandes')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.errorhandler(404)
    def page_introuvable(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def acces_interdit(e):
        from flask import render_template
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def erreur_serveur(e):
        from flask import render_template
        return render_template('errors/500.html'), 500

    return app