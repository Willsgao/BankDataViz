# -*- coding:utf-8 -*-
"""
安全数据库管理器 - 不会清空已有数据
"""

import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from backend.configs.config import config


class SafeDatabaseManager:
    """安全的数据库管理器 - 不会覆盖已有数据"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为配置中的路径
        """
        # self.db_path = db_path or getattr(config, 'DATABASE_PATH', 'data/database.db')
        self.db_path = db_path or config.DATABASE_PATH  # ✅

        # 确保数据库目录存在
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        print(f"[SafeDatabaseManager] 数据库路径: {self.db_path}")
        print(f"[SafeDatabaseManager] 数据库存在: {os.path.exists(self.db_path)}")

        self.conn = None
        self.cursor = None

    def _connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def _close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def init_database(self) -> bool:
        """
        安全初始化数据库

        Returns:
            bool: 是否创建了新数据库
        """
        database_existed = os.path.exists(self.db_path)

        if not database_existed:
            print(f"[SafeDatabaseManager] 🆕 创建新数据库: {self.db_path}")
            self._create_all_tables()
            return True
        else:
            print(f"[SafeDatabaseManager] ✅ 使用现有数据库: {self.db_path}")
            print(f"[SafeDatabaseManager] 🔍 检查表结构完整性...")
            self._check_and_update_tables()
            return False

    def _create_all_tables(self):
        """创建所有表（仅用于新数据库）"""
        try:
            self._connect()

            # 创建files表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    raw_filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    file_size INTEGER,
                    page_count INTEGER,
                    processed INTEGER DEFAULT 0
                )
            ''')

            # 创建file_mappings表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_id)
                )
            ''')

            # 创建ocr_results表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS ocr_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    result_json TEXT,
                    cost_usd REAL DEFAULT 0,
                    processing_time INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建indexes
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(deleted)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_mappings_file_id ON file_mappings(file_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_ocr_results_image_hash ON ocr_results(image_hash)")

            self.conn.commit()
            print(f"[SafeDatabaseManager] ✅ 所有表创建完成")

        except Exception as e:
            print(f"[SafeDatabaseManager] ❌ 创建表失败: {e}")
            raise
        finally:
            self._close()

    def _check_and_update_tables(self):
        """
        检查并更新表结构（不删除数据）
        只添加缺失的表和列
        """
        try:
            self._connect()

            # 检查files表是否存在
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
            if not self.cursor.fetchone():
                print(f"[SafeDatabaseManager] ⚠️ files表不存在，创建...")
                self.cursor.execute('''
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        raw_filename TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        deleted INTEGER DEFAULT 0,
                        file_size INTEGER,
                        page_count INTEGER,
                        processed INTEGER DEFAULT 0
                    )
                ''')

            # 检查file_mappings表是否存在
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_mappings'")
            if not self.cursor.fetchone():
                print(f"[SafeDatabaseManager] ⚠️ file_mappings表不存在，创建...")
                self.cursor.execute('''
                    CREATE TABLE file_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id TEXT NOT NULL,
                        display_name TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(file_id)
                    )
                ''')

            # 检查每个表的列结构
            self._add_missing_columns('files', [
                ('file_size', 'INTEGER'),
                ('page_count', 'INTEGER'),
                ('processed', 'INTEGER DEFAULT 0')
            ])

            self._add_missing_columns('file_mappings', [
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ])

            # 创建索引（如果不存在）
            self._create_index_if_not_exists('idx_files_filename', 'files(filename)')
            self._create_index_if_not_exists('idx_files_deleted', 'files(deleted)')
            self._create_index_if_not_exists('idx_file_mappings_file_id', 'file_mappings(file_id)')

            self.conn.commit()
            print(f"[SafeDatabaseManager] ✅ 表结构检查完成")

        except Exception as e:
            print(f"[SafeDatabaseManager] ❌ 表结构检查失败: {e}")
        finally:
            self._close()

    def _add_missing_columns(self, table_name: str, columns: List[tuple]):
        """
        为表添加缺失的列

        Args:
            table_name: 表名
            columns: 列列表，格式为 [(列名, 类型定义), ...]
        """
        try:
            # 获取现有列
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [row[1] for row in self.cursor.fetchall()]

            for column_name, column_type in columns:
                if column_name not in existing_columns:
                    print(f"[SafeDatabaseManager] ➕ 为{table_name}表添加列: {column_name}")
                    self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

        except Exception as e:
            print(f"[SafeDatabaseManager] ❌ 添加列失败: {e}")

    def _create_index_if_not_exists(self, index_name: str, index_def: str):
        """创建索引（如果不存在）"""
        try:
            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'")
            if not self.cursor.fetchone():
                print(f"[SafeDatabaseManager] 📊 创建索引: {index_name}")
                self.cursor.execute(f"CREATE INDEX {index_name} ON {index_def}")
        except Exception as e:
            print(f"[SafeDatabaseManager] ❌ 创建索引失败: {e}")

    def backup_database(self, backup_dir: str = "data/backups") -> str:
        """
        备份数据库

        Args:
            backup_dir: 备份目录

        Returns:
            str: 备份文件路径
        """
        try:
            # 创建备份目录
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)

            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"database_backup_{timestamp}.db"

            # 复制数据库文件
            import shutil
            shutil.copy2(self.db_path, backup_file)

            print(f"[SafeDatabaseManager] 💾 数据库已备份到: {backup_file}")
            return str(backup_file)

        except Exception as e:
            print(f"[SafeDatabaseManager] ❌ 数据库备份失败: {e}")
            return ""

    def get_database_info(self) -> Dict[str, Any]:
        """
        获取数据库信息

        Returns:
            Dict: 数据库信息
        """
        try:
            self._connect()

            info = {
                "path": self.db_path,
                "size_bytes": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0,
                "tables": [],
                "row_counts": {}
            }

            # 获取所有表
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in self.cursor.fetchall()]
            info["tables"] = tables

            # 获取每个表的行数
            for table in tables:
                if table.startswith('sqlite_'):  # 跳过系统表
                    continue
                self.cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = self.cursor.fetchone()[0]
                info["row_counts"][table] = count

            self._close()
            return info

        except Exception as e:
            print(f"[SafeDatabaseManager] ❌ 获取数据库信息失败: {e}")
            return {}