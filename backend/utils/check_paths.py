#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
检查所有路径配置是否一致
"""
import os
import sys


def check_all_paths():
    """检查所有路径配置"""
    print("=" * 60)
    print("🔍 路径配置检查")
    print("=" * 60)

    # 从 constants 导入
    try:
        from constants import DATABASE, UPLOAD_FOLDER, PNG_OUTPUT_ROOT, EXCEL_OUTPUT_ROOT
        print("[constants.py]")
        print(f"  DATABASE: {DATABASE}")
        print(f"  UPLOAD_FOLDER: {UPLOAD_FOLDER}")
        print(f"  数据库存在: {os.path.exists(DATABASE)}")
    except ImportError as e:
        print(f"❌ 无法导入 constants: {e}")

    print("-" * 40)

    # 从 config 导入
    try:
        from config import config
        print("[config.py]")
        print(f"  DATABASE_PATH: {config.DATABASE_PATH}")
        print(f"  UPLOAD_FOLDER: {config.UPLOAD_FOLDER}")
        print(f"  数据库存在: {os.path.exists(config.DATABASE_PATH)}")
    except ImportError as e:
        print(f"❌ 无法导入 config: {e}")

    print("=" * 60)

    # 检查路径一致性
    try:
        from constants import DATABASE as const_db
        from config import config as cfg

        if os.path.abspath(const_db) == os.path.abspath(cfg.DATABASE_PATH):
            print("✅ 数据库路径一致")
        else:
            print("❌ 数据库路径不一致！")
            print(f"  constants: {const_db}")
            print(f"  config: {cfg.DATABASE_PATH}")

    except Exception as e:
        print(f"❌ 检查失败: {e}")

    print("=" * 60)


if __name__ == "__main__":
    # 添加当前目录到路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    check_all_paths()