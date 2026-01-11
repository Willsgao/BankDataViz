"""
数据库模块导出文件 - 安全的方法，不修改原有文件
"""

# 导入基础配置
from . import (
    get_db_connection,
    get_database_path,
    get_upload_folder,
    get_main_root
)

# 导入新功能
try:
    from .unified_manager import UnifiedDatabaseManager, unified_db_manager
    from .adapters import OldDatabaseManagerAdapter, NewDatabaseManagerAdapter
    from .service_adapters import FileUploadServiceAdapter, FileManagementServiceAdapter

    # 导出所有功能
    __all__ = [
        'get_db_connection',
        'get_database_path',
        'get_upload_folder',
        'get_main_root',
        'UnifiedDatabaseManager',
        'unified_db_manager',
        'OldDatabaseManagerAdapter',
        'NewDatabaseManagerAdapter',
        'FileUploadServiceAdapter',
        'FileManagementServiceAdapter'
    ]

    print("✅ 数据库模块完整导出")

except ImportError as e:
    # 如果新功能导入失败，只导出基础功能
    __all__ = [
        'get_db_connection',
        'get_database_path',
        'get_upload_folder',
        'get_main_root'
    ]

    print(f"⚠️ 新功能导入失败，只导出基础功能: {e}")
    