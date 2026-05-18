#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
DocuVista 服务启动入口

职责：仅负责启动服务，所有应用构建逻辑（蓝图注册、CORS、数据库初始化）
均在 backend/app.py 中完成。

用法：
  开发环境：python backend_run.py
  生产环境：nohup python3 backend_run.py > logs/app.log 2>&1 &
"""

from dotenv import load_dotenv

load_dotenv()  # 加载项目根目录的 .env 文件

from backend.app import app
from backend.app import init_existing_files

if __name__ == "__main__":
    init_existing_files()
    print("🌐 启动服务...")
    print("📡 访问地址: http://0.0.0.0:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
