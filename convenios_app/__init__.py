from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from convenios_app.config import Config
from flask_jsglue import JSGlue
from flask_bcrypt import Bcrypt
#from flask_ckeditor import CKEditor, CKEditorField

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
jsglue = JSGlue()
login_manager.login_view = 'users.ingresar'
login_manager.login_message_category = 'info'
#ckeditor = CKEditor()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    db.app = app

    jsglue.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    #ckeditor.init_app(app)

    from convenios_app.main.routes import main
    from convenios_app.users.routes import users
    from convenios_app.bitacoras.routes import bitacoras
    from convenios_app.informes.routes import informes
    #from convenios_app.errors.handlers import errors

    app.register_blueprint(main)
    app.register_blueprint(users)
    app.register_blueprint(bitacoras)
    app.register_blueprint(informes)
    #app.register_blueprint(errors)

    return app