"""
统一数据库配置和连接管理
第一步：创建基础连接管理器，不影响现有代码
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

# 尝试导入配置，如果失败使用安全回退
try:
    from backend.configs.config import config

    DATABASE_PATH = getattr(config, 'DATABASE_PATH', 'data/database.db')
    UPLOAD_FOLDER = getattr(config, 'UPLOAD_FOLDER', 'data/backend/static/uploads')
    MAIN_ROOT = getattr(config, 'MAIN_ROOT', '.')
except ImportError as e:
    print(f"⚠️ 配置导入失败，使用默认值: {e}")
    DATABASE_PATH = 'data/database.db'
    UPLOAD_FOLDER = 'data/backend/static/uploads'
    MAIN_ROOT = '.'


@contextmanager
def get_db_connection():
    """
    统一的数据库连接上下文管理器
    使用此方法可以确保连接正确关闭
    """
    # 确保数据库目录存在
    db_dir = Path(DATABASE_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 启用行工厂，返回字典式结果
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        print(f"❌ 数据库操作失败: {e}")
        raise
    finally:
        conn.close()


def get_database_path():
    """获取统一的数据库路径"""
    return DATABASE_PATH


def get_upload_folder():
    """获取统一的上传文件夹路径"""
    return UPLOAD_FOLDER


def get_main_root():
    """获取统一的主根目录"""
    return MAIN_ROOT


# 第一步完成标记
print("✅ 第一步完成：创建了统一的数据库配置管理器")