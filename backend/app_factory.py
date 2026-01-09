# backend/app_factory.py
# -*- coding:utf-8 -*-

from flask import Flask, send_from_directory
from flask_cors import CORS
from pathlib import Path

# 导入蓝图（完全按照app.py的导入顺序）
from backend.api.upload import upload_bp
from backend.api.file import file_bp
from backend.api.convert_apis import convert_bp
from backend.api.text import text_bp
from backend.api.llm_routes import llm_bp
from backend.api.baidu_ocr_routes import baidu_ocr_bp
from backend.api.visualization_api import visualization_bp
from backend.api.websocket_routes import websocket_bp, init_websocket

# 使用安全的数据库管理器
from backend.models.safe_unified_db import SafeDatabaseManager
from backend.utils.constants import MAIN_ROOT, PNG_OUTPUT_ROOT


def create_app() -> Flask:
    """
    创建Flask应用（完全忠实于原有app.py）
    """
    app = Flask(__name__)

    print("=" * 60)
    print("🚀🚀 DocuVista 服务启动中...")
    print("=" * 60)

    # ----------- 完整的 CORS 配置（完全复制app.py的配置） -----------
    CORS(
        app,
        resources={
            r"/api/*": {  # 对 /api/ 开头的所有路由应用 CORS
                "origins": [
                    "http://localhost:8080",
                    "http://127.0.0.1:8080",
                    "http://172.17.0.1:8080",
                    # "http://101.43.35.52:8080",
                    "http://122.51.196.65:8080",
                    "http://122.51.196.65:5000",
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": ["Content-Type", "Authorization", "Accept"],
                "expose_headers": ["Content-Type", "Content-Disposition"],
                "supports_credentials": True,
                "max_age": 86400
            }
        }
    )

    # ----------- 安全初始化数据库（完全复制app.py的逻辑） -----------
    db_mgr = SafeDatabaseManager()

    # 在 app.py 的数据库初始化前
    import os
    from backend.utils.constants import DATABASE as DB_PATH
    print(f"📊📊 统一数据库路径: {DB_PATH}")
    print(f"📊📊 数据库文件存在: {os.path.exists(DB_PATH)}")

    # 生产环境自动备份
    if app.config.get('ENV') == 'production':
        backup_file = db_mgr.backup_database()
        if backup_file:
            print(f"💾💾 生产环境数据库已备份: {backup_file}")

    # 安全初始化（不删除现有数据）
    is_new_db = db_mgr.init_database()

    if is_new_db:
        print("📊📊 新数据库已创建")
    else:
        # 显示现有数据量
        db_info = db_mgr.get_database_info()
        total_rows = sum(db_info.get('row_counts', {}).values())
        print(f"📊📊 加载现有数据库，共 {total_rows} 行数据")

    print("=" * 60)

    # ----------- 初始化WebSocket -----------
    init_websocket(app)

    # 全局处理器实例（完全复制）
    _table_processor_instance = None
    _non_financial_table_service = None

    # ----------- 注册蓝图（完全按照app.py的顺序和方式） -----------
    # 注释掉的版本（保持注释状态）
    # app.register_blueprint(llm_bp, url_prefix='/api')
    # app.register_blueprint(upload_bp, url_prefix='/api')
    # app.register_blueprint(file_bp, url_prefix='/api')
    # app.register_blueprint(convert_bp, url_prefix='/api')

    # 实际使用的版本（无前缀）
    app.register_blueprint(llm_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(convert_bp)

    # 注释掉的重复注册（保持注释状态）
    # app.register_blueprint(llm_bp)
    # app.register_blueprint(upload_bp)
    # app.register_blueprint(file_bp)
    # app.register_blueprint(convert_bp)

    app.register_blueprint(text_bp)
    app.register_blueprint(visualization_bp)
    app.register_blueprint(baidu_ocr_bp)
    app.register_blueprint(websocket_bp)

    # ----------- 静态文件路由配置（完全复制app.py的配置） -----------
    app.add_url_rule(
        '/static/converted/<path:filename>',
        'converted_png',
        lambda filename: send_from_directory(
            Path(MAIN_ROOT) / PNG_OUTPUT_ROOT,
            filename
        )
    )

    app.add_url_rule(
        '/static/excel_data/<path:filename>',
        'serve_excel_file',
        lambda filename: send_from_directory(
            Path(MAIN_ROOT) / 'backend' / 'static' / 'excel_data',
            filename
        )
    )

    app.add_url_rule(
        '/static/excel_output/<path:filename>',
        'serve_excel_output',
        lambda filename: send_from_directory(
            Path(MAIN_ROOT) / 'backend' / 'static' / 'excel_output',
            filename
        )
    )

    app.add_url_rule(
        '/static/joined_tables/<path:filename>',
        'joined_tables',
        lambda filename: send_from_directory(
            Path(MAIN_ROOT) / 'backend' / 'static' / 'joined_tables',
            filename
        )
    )

    print("✅ 所有蓝图和路由注册完成")
    print("=" * 60)

    return app