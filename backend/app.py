#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
DocuVista 主入口
"""

from flask import Flask, send_from_directory
from flask_cors import CORS
from backend.api.upload import upload_bp
from backend.api.file import file_bp
from backend.api.convert import convert_bp
from backend.api.text import text_bp
from backend.api.llm_routes import llm_bp

# 在 app.py 中添加（如果使用Flask）
from backend.api.visualization_api import visualization_bp
from backend.init_file_mapping import init_existing_files_mapping



# ⭐⭐⭐ 新增：导入WebSocket模块 ⭐⭐⭐
from backend.api.websocket_routes import websocket_bp, init_websocket
from backend.models.database_manager import DatabaseManager

# ----------- 初始化 Flask -----------
app = Flask(__name__)

# ----------- 初始化数据库 -----------
db_mgr = DatabaseManager()
db_mgr.init_database()

# ⭐⭐⭐ 新增：初始化WebSocket ⭐⭐⭐
init_websocket(app)

# 全局处理器实例
_table_processor_instance = None
_non_financial_table_service = None

# ----------- CORS配置 -----------
CORS(
    app,
    origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    supports_credentials=True,
    allow_headers=["*"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
)

# ----------- 静态文件服务路由 -----------
@app.route('/static/excel_data/<path:filename>')
def serve_excel_file(filename):
    """提供Excel文件访问"""
    return send_from_directory('static/excel_data', filename)

# ----------- 注册蓝图 -----------
app.register_blueprint(llm_bp, url_prefix='/api')
app.register_blueprint(upload_bp)
app.register_blueprint(file_bp)
app.register_blueprint(convert_bp, url_prefix='/api')
app.register_blueprint(text_bp)
app.register_blueprint(visualization_bp)


# ⭐⭐⭐ 新增：注册WebSocket蓝图 ⭐⭐⭐
app.register_blueprint(websocket_bp)



# 在 app.py 的启动部分调用
if __name__ == '__main__':
    # 初始化文件映射
    init_existing_files_mapping()
    app.run(debug=True, host='0.0.0.0', port=5000)
