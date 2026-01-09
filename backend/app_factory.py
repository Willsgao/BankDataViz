# -*- coding:utf-8 -*-

from flask import Flask
from flask_cors import CORS
from backend.api.upload import upload_bp
from backend.api.file import file_bp
from backend.api.convert_apis import convert_bp
from backend.models.safe_unified_db import SafeDatabaseManager  # 使用安全的数据库管理器


def create_app() -> Flask:
    """
    创建Flask应用（安全版本）
    """
    app = Flask(__name__)

    # 配置CORS
    CORS(app)

    print("=" * 60)
    print("🚀 启动DocuVista应用（安全模式）")
    print("=" * 60)

    # 安全初始化数据库（不会清空数据）
    db_mgr = SafeDatabaseManager()

    # 备份数据库（如果是第一次启动或手动触发）
    if app.config.get('ENV') == 'production':
        db_mgr.backup_database()

    # 安全初始化（只创建缺失的表，不删除数据）
    is_new_db = db_mgr.init_database()

    if is_new_db:
        print("📊 新数据库已创建")
    else:
        # 显示数据库信息
        db_info = db_mgr.get_database_info()
        if db_info:
            print("📊 现有数据库信息:")
            for table, count in db_info.get('row_counts', {}).items():
                print(f"   {table}: {count} 行数据")

    print("=" * 60)

    # 注册蓝图
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(file_bp, url_prefix='/api')
    app.register_blueprint(convert_bp, url_prefix='/api')

    # app.register_blueprint(upload_bp)
    # app.register_blueprint(file_bp)
    # app.register_blueprint(convert_bp)

    return app