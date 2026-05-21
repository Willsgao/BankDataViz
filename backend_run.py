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

import sys
import io
import logging
import os
from logging.handlers import RotatingFileHandler

# 修复 Windows 控制台 GBK 编码导致的 emoji UnicodeEncodeError
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()  # 加载项目根目录的 .env 文件


def _setup_logging():
    """配置统一日志：控制台 + 滚动文件"""
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    # 文件 handler（10MB 滚动，保留 5 个备份）
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)


_setup_logging()
logger = logging.getLogger("run")

from backend.app import app
from backend.app import init_existing_files

if __name__ == "__main__":
    init_existing_files()
    logger.info("启动服务...")
    print("访问地址: http://0.0.0.0:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
