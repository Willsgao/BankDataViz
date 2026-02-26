"""
统一数据库管理器 - 第四步：创建主管理器类
整合所有数据库相关功能，提供单一入口点
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime


# 导入适配器和配置
from . import get_db_connection, get_database_path, get_upload_folder, get_main_root
from .adapters import OldDatabaseManagerAdapter, NewDatabaseManagerAdapter
from .service_adapters import FileUploadServiceAdapter, FileManagementServiceAdapter


class UnifiedDatabaseManager:
    """
    统一数据库管理器
    整合所有数据库相关功能，提供单一入口点
    """

    def __init__(self):
        self.db_path = get_database_path()
        self.uploads_dir = get_upload_folder()
        self.main_root = get_main_root()

        # 初始化各个适配器
        self.old_adapter = OldDatabaseManagerAdapter()
        self.new_adapter = NewDatabaseManagerAdapter()
        self.upload_service = FileUploadServiceAdapter()
        self.management_service = FileManagementServiceAdapter()

        print(f"🎯 UnifiedDatabaseManager 初始化完成")
        print(f"   数据库路径: {self.db_path}")
        print(f"   上传目录: {self.uploads_dir}")

    def connect(self):
        """统一的数据库连接方法"""
        return sqlite3.connect(self.db_path)

    # ============ 数据库初始化相关方法 ============

    def init_all_tables(self):
        """一次性初始化所有数据库表"""
        print("🔄 开始初始化所有数据库表...")

        success_count = 0
        total_count = 0

        # 初始化文档相关表
        total_count += 1
        if self.old_adapter.init_database():
            success_count += 1
            print("✅ 文档表初始化成功")
        else:
            print("❌ 文档表初始化失败")

        # 初始化表格处理表
        total_count += 1
        if self.new_adapter.init_table_processing_db():
            success_count += 1
            print("✅ 表格处理表初始化成功")
        else:
            print("❌ 表格处理表初始化失败")

        print(f"🎯 数据库表初始化完成: {success_count}/{total_count} 成功")
        return success_count == total_count

    def check_database_health(self):
        """检查数据库健康状态"""
        print("🔍 检查数据库健康状态...")

        health_info = {
            "database_file": {
                "exists": os.path.exists(self.db_path),
                "size_bytes": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0,
                "path": self.db_path
            },
            "upload_directory": {
                "exists": os.path.exists(self.uploads_dir),
                "file_count": len(os.listdir(self.uploads_dir)) if os.path.exists(self.uploads_dir) else 0,
                "path": self.uploads_dir
            },
            "tables": {}
        }

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # 获取所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]

                for table_name in tables:
                    if table_name.startswith('sqlite_'):
                        continue

                    # 获取表行数
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    row_count = cursor.fetchone()[0]

                    # 获取表结构
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [{"name": col[1], "type": col[2]} for col in cursor.fetchall()]

                    health_info["tables"][table_name] = {
                        "row_count": row_count,
                        "columns": columns,
                        "health": "✅ 正常" if row_count >= 0 else "⚠️ 异常"
                    }

                print("✅ 数据库健康检查完成")
                return health_info

        except Exception as e:
            print(f"❌ 数据库健康检查失败: {e}")
            health_info["error"] = str(e)
            return health_info

    # ============ 文件操作相关方法 ============

    def process_file_upload(self, file, raw_filename):
        """处理文件上传"""
        return self.upload_service.process_upload(file, raw_filename)

    def get_file_statistics(self):
        """获取文件统计信息"""
        return self.management_service.get_file_stats()

    def find_duplicate_files(self, limit=20):
        """查找重复文件"""
        return self.management_service.find_duplicates(limit)

    # ============ 表格处理相关方法 ============

    def save_table_processing_record(self, job_info):
        """保存表格处理记录"""
        return self.new_adapter.save_table_processing_record(job_info)

    def load_table_processing_records(self, pdf_folder=None, limit=100):
        """加载表格处理记录"""
        return self.new_adapter.load_table_processing_records(pdf_folder, limit)

    def get_task_detail(self, job_id):
        """获取任务详情"""
        return self.new_adapter.get_task_detail(job_id)

    # ============ 数据库维护相关方法 ============

    def backup_database(self, backup_dir="data/backups"):
        """备份数据库"""
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"database_backup_{timestamp}.db"

            import shutil
            shutil.copy2(self.db_path, backup_file)

            print(f"💾 数据库已备份到: {backup_file}")
            return {
                "success": True,
                "backup_path": str(backup_file),
                "backup_size": os.path.getsize(backup_file),
                "timestamp": timestamp
            }

        except Exception as e:
            print(f"❌ 数据库备份失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def vacuum_database(self):
        """优化数据库"""
        try:
            with get_db_connection() as conn:
                conn.execute("VACUUM")
                print("✅ 数据库已优化")
                return True
        except Exception as e:
            print(f"❌ 优化数据库失败: {e}")
            return False

    def get_database_info(self):
        """获取数据库详细信息"""
        info = {
            "path": self.db_path,
            "size_bytes": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0,
            "tables": [],
            "row_counts": {},
            "health_status": "unknown"
        }

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # 获取所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                info["tables"] = tables

                # 获取每个表的行数
                for table in tables:
                    if table.startswith('sqlite_'):
                        continue
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cursor.fetchone()[0]
                    info["row_counts"][table] = count

                info["health_status"] = "healthy"
                return info

        except Exception as e:
            print(f"❌ 获取数据库信息失败: {e}")
            info["error"] = str(e)
            info["health_status"] = "error"
            return info

    # ============ 兼容性方法 ============

    def get_old_manager(self):
        """获取旧版数据库管理器（兼容性方法）"""
        return self.old_adapter

    def get_new_manager(self):
        """获取新版数据库管理器（兼容性方法）"""
        return self.new_adapter

    def get_upload_service(self):
        """获取文件上传服务（兼容性方法）"""
        return self.upload_service

    def get_management_service(self):
        """获取文件管理服务（兼容性方法）"""
        return self.management_service


# 创建全局实例
unified_db_manager = UnifiedDatabaseManager()

print("✅ 第四步完成：创建了统一的数据库管理器")