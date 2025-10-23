#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
DocuVista 主入口
只负责：注册蓝图 + 启动
"""

from flask import Flask
from flask_cors import CORS
from backend.api.upload import upload_bp
from backend.api.file import file_bp
from backend.api.convert import convert_bp
from backend.api.text import text_bp   # 新增

from backend.models.database_manager import DatabaseManager

# ----------- 初始化 Flask -----------
app = Flask(__name__)



# 关键修改：扩大CORS覆盖范围，确保包含所有接口路径
CORS(
    app,
    resources={
        r"/api/*": {  # 覆盖所有/api开头的接口（包括你的batch-cut-table）
            "origins": "http://localhost:8080",  # 前端实际地址，必须精确匹配
            "supports_credentials": True,
            "allow_headers": "*",
            "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"]  # 显式允许OPTIONS方法
        },
        # 如果还有其他非/api开头的接口需要跨域，补充规则
        r"/*": {  # 可选：覆盖所有路径（谨慎使用，生产环境建议精确匹配）
            "origins": "http://localhost:8080",
            "supports_credentials": True,
            "allow_headers": "*",
            "methods": ["GET", "POST", "OPTIONS"]
        }
    }
)

# ----------- 初始化数据库 -----------
db_mgr = DatabaseManager()
db_mgr.init_database()

# ----------- 注册蓝图 -----------
app.register_blueprint(upload_bp)
app.register_blueprint(file_bp)
app.register_blueprint(convert_bp, url_prefix='/api')  # 该蓝图的接口以 /api 开头
app.register_blueprint(text_bp)
# app.register_blueprint(pipeline_bp, url_prefix='/api')  # 可选

# ----------- 启动 -----------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)