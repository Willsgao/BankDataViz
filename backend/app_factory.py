# -*- coding:utf-8 -*-

from flask import Flask
from flask_cors import CORS
from backend.api.upload import upload_bp
from backend.api.file import file_bp
from backend.api.convert_apis import convert_bp
# from backend.models.database_manager import OldDatabaseManager
from backend.models.unified_db import DatabaseManager as OldDatabaseManager

def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    db_mgr = OldDatabaseManager()
    db_mgr.init_database()

    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(file_bp, url_prefix='/api')
    app.register_blueprint(convert_bp, url_prefix='/api')

    return app