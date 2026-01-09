# backend_run.py
# !/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
DocuVista 主入口（安全版本）- 完全忠实于原有app.py
"""

import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from backend.app_factory import create_app


def init_existing_files():
    """安全初始化文件映射（不会清空数据）- 完全复制app.py的函数"""
    try:
        from backend.init_file_mapping import init_existing_files_mapping
        init_existing_files_mapping()
        print("📁📁 文件映射初始化完成")
    except Exception as e:
        print(f"⚠️ 文件映射初始化失败: {e}")


def main():
    """主启动函数 - 完全复制app.py的启动逻辑"""
    # 创建Flask应用
    app = create_app()

    # 初始化文件映射（完全复制app.py的逻辑）
    init_existing_files()

    print("🌐🌐 启动服务...")
    print(f"📡📡 访问地址: http://0.0.0.0:5000")
    print("=" * 60)

    # 启动Flask应用（参数完全一致）
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()