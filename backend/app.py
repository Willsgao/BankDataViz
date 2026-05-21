#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
DocuVista 应用构建入口

职责：
  1. 创建 Flask 实例并完成所有初始化（CORS、数据库、WebSocket、蓝图、静态路由）
  2. 暴露顶层 `app` 对象供外部使用
  3. 直接执行时作为开发服务器入口（python backend/app.py）

启动说明：
  开发环境：python backend_run.py（推荐，与生产保持一致）
  生产环境：start_server.sh 中 nohup python3 backend_run.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # 加载项目根目录的 .env  → LLM_API_KEY 等环境变量

from flask import Flask, request, send_from_directory
from flask_cors import CORS

# ----------- 导入蓝图 -----------
from backend.api.upload import upload_bp
from backend.api.file import file_bp
from backend.api.convert_apis import convert_bp
from backend.api.text import text_bp
from backend.api.llm_routes import llm_bp
from backend.api.baidu_ocr_routes import baidu_ocr_bp
from backend.api.visualization_api import visualization_bp
from backend.api.websocket_routes import websocket_bp, init_websocket
from backend.api.excel_api import excel_bp
from backend.api.bank_data_api import bank_data_bp
from backend.api.bank_doc_api import bank_doc_bp
from backend.api.progress_sse import progress_sse_bp
from backend.api.audit import audit_bp
from backend.api.smart_recognize import smart_recognize_bp
from backend.api.rag_api import rag_bp
from backend.api.harness_routes import harness_bp

# ----------- 导入工具 -----------
from backend.models.safe_unified_db import SafeDatabaseManager
from backend.utils.constants import MAIN_ROOT, PNG_OUTPUT_ROOT, DATABASE_PATH as DB_PATH

# =============================================================================
# 创建 Flask 实例
# =============================================================================
app = Flask(__name__)

print("=" * 60)
print("🚀 DocuVista 服务启动中...")
print("=" * 60)

# =============================================================================
# CORS 配置
# =============================================================================
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://172.17.0.1:8080",
                "http://192.168.10.111:8080",
                "http://122.51.196.65:8080",
                "http://122.51.196.65:5000",
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
            "expose_headers": ["Content-Type", "Content-Disposition"],
            "supports_credentials": True,
            "max_age": 86400,
        }
    },
)

# 兜底：确保所有响应（含预检和错误响应）都带 CORS 头
# 注意：用直接赋值而非 setdefault，因为 Flask-CORS 可能已把
# Access-Control-Allow-Credentials 设为空字符串，setdefault 不会覆盖已有键
@app.after_request
def add_cors_headers(response):
    origin = response.headers.get('Access-Control-Allow-Origin')
    if not origin:
        # Flask-CORS 未设置时，动态回显请求的 Origin（支持任意局域网 IP）
        request_origin = request.headers.get('Origin', '')
        response.headers['Access-Control-Allow-Origin'] = request_origin or 'http://localhost:8080'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
    return response

# 显式处理所有 /api/* 的 OPTIONS 预检请求
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_preflight(path):
    resp = app.make_default_options_response()
    # 动态回显请求 Origin，支持任意局域网 IP 访问
    request_origin = request.headers.get('Origin', '')
    resp.headers['Access-Control-Allow-Origin'] = request_origin or 'http://localhost:8080'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
    resp.headers['Access-Control-Max-Age'] = '86400'
    return resp

# =============================================================================
# 数据库初始化
# =============================================================================
print(f"📊 统一数据库路径: {DB_PATH}")
print(f"📊 数据库文件存在: {os.path.exists(DB_PATH)}")

db_mgr = SafeDatabaseManager()

# 生产环境自动备份
if app.config.get("ENV") == "production":
    backup_file = db_mgr.backup_database()
    if backup_file:
        print(f"💾 生产环境数据库已备份: {backup_file}")

# 安全初始化（不删除现有数据）
is_new_db = db_mgr.init_database()
if is_new_db:
    print("📊 新数据库已创建")
else:
    db_info = db_mgr.get_database_info()
    total_rows = sum(db_info.get("row_counts", {}).values())
    print(f"📊 加载现有数据库，共 {total_rows} 行数据")

print("=" * 60)

# =============================================================================
# WebSocket 初始化
# =============================================================================
init_websocket(app)

# 全局处理器实例（供各蓝图延迟初始化使用）
_table_processor_instance = None
_non_financial_table_service = None

# =============================================================================
# 注册蓝图
# =============================================================================
app.register_blueprint(llm_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(file_bp)
app.register_blueprint(convert_bp)
app.register_blueprint(text_bp)
app.register_blueprint(visualization_bp)
app.register_blueprint(baidu_ocr_bp)
app.register_blueprint(websocket_bp)
app.register_blueprint(excel_bp)
app.register_blueprint(bank_data_bp)
app.register_blueprint(bank_doc_bp)
app.register_blueprint(progress_sse_bp)
app.register_blueprint(audit_bp)
app.register_blueprint(smart_recognize_bp)
app.register_blueprint(rag_bp)
app.register_blueprint(harness_bp)

# =============================================================================
# 静态文件路由
# =============================================================================
app.add_url_rule(
    "/static/converted/<path:filename>",
    "converted_png",
    lambda filename: send_from_directory(Path(MAIN_ROOT) / PNG_OUTPUT_ROOT, filename),
)

app.add_url_rule(
    "/static/excel_data/<path:filename>",
    "serve_excel_file",
    lambda filename: send_from_directory(
        Path(MAIN_ROOT) / "data" / "backend" / "static" / "excel_data", filename
    ),
)

app.add_url_rule(
    "/static/excel_output/<path:filename>",
    "serve_excel_output",
    lambda filename: send_from_directory(
        Path(MAIN_ROOT) / "data" / "backend" / "static" / "excel_output", filename
    ),
)

app.add_url_rule(
    "/static/joined_tables/<path:filename>",
    "joined_tables",
    lambda filename: send_from_directory(
        Path(MAIN_ROOT) / "data" / "backend" / "static" / "joined_tables", filename
    ),
)

print("✅ 所有蓝图和路由注册完成")
print("=" * 60)


# =============================================================================
# 预热 RAG Embedding 模型（后台线程，避免阻塞启动）
# bge-large-zh 约 1.3GB，首次加载需 40-60s，提前加载可避免首次查询卡顿
# =============================================================================
def _preload_rag_embedding():
    """后台预热 RAG Embedding 模型"""
    import threading
    def _load():
        try:
            from backend.services.rag_service import get_rag_pipeline
            get_rag_pipeline()
            print("🧠 RAG Embedding 模型预热完成")
        except Exception as e:
            print(f"⚠️ RAG 模型预热跳过（不影响服务）: {e}")
    t = threading.Thread(target=_load, daemon=True)
    t.start()


_preload_rag_embedding()


# =============================================================================
# 文件映射初始化（首次启动时建立文件与数据库记录的映射）
# =============================================================================
def init_existing_files():
    """安全初始化文件映射（不会清空已有数据）"""
    try:
        from backend.init_file_mapping import init_existing_files_mapping
        init_existing_files_mapping()
        print("📁 文件映射初始化完成")
    except Exception as e:
        print(f"⚠️ 文件映射初始化失败: {e}")


# =============================================================================
# 开发服务器入口（直接运行本文件时使用）
# =============================================================================
if __name__ == "__main__":
    init_existing_files()
    print("🌐 启动开发服务器...")
    print("📡 访问地址: http://0.0.0.0:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
