#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
数据库表结构管理器 - 完整可移植版本
功能：在任何服务器上安全创建或补充数据库表结构
特点：100%兼容现有结构，不会删除或修改任何现有数据
"""

import sqlite3
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional


class UniversalDatabaseSchemaManager:
    """
    通用数据库表结构管理器
    可在任何服务器上安全运行，自动检测并创建完整的表结构
    """

    def __init__(self, db_path: str = None, project_root: str = None):
        # 如果提供了项目根目录，直接使用
        if project_root:
            self.project_root = Path(project_root)
        else:
            # 直接使用固定层级计算
            current_file = Path(__file__).resolve()
            self.project_root = current_file.parent.parent.parent
            print(f"✅ 修正后的项目根目录: {self.project_root}")

        # 设置数据库路径
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self._detect_database_path()

        print(f"🚀🚀 通用数据库表结构管理器初始化")
        print(f"📁📁 项目根目录: {self.project_root}")
        print(f"🗃🗃️ 数据库路径: {self.db_path}")

        # 确保所有必要目录存在
        self._ensure_directories()


    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        # 方法1: 从当前文件向上查找
        current_file = Path(__file__).resolve()
        for parent in [current_file] + list(current_file.parents):
            if (parent / 'backend').exists() and (parent / 'data').exists():
                return parent
            if (parent / 'requirements.txt').exists():
                return parent

        # 方法2: 从当前工作目录查找
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            if (parent / 'backend').exists() and (parent / 'data').exists():
                return parent
            if (parent / 'requirements.txt').exists():
                return parent

        # 方法3: 使用当前目录
        print("⚠️ 无法自动检测项目根目录，使用当前目录")
        return Path.cwd()

    def _ensure_directories(self):
        """确保所有必要目录存在"""
        directories = [
            self.db_path.parent,
            self.project_root / 'data',
            self.project_root / 'data' / 'backups',
            self.project_root / 'data' / 'backend',
            self.project_root / 'data' / 'backend' / 'static',
            self.project_root / 'data' / 'backend' / 'static' / 'uploads'
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                print(f"✅ 确保目录存在: {directory}")
            except Exception as e:
                print(f"❌❌ 创建目录失败 {directory}: {e}")

    def connect(self) -> sqlite3.Connection:
        """连接数据库"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌❌ 数据库连接失败: {e}")
            raise

    def check_database_exists(self) -> bool:
        """检查数据库文件是否存在"""
        return self.db_path.exists()

    def get_all_tables(self) -> List[str]:
        """获取数据库中所有用户表"""
        if not self.check_database_exists():
            return []

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        return table_name in self.get_all_tables()

    def get_table_structure(self, table_name: str) -> List[Dict[str, Any]]:
        """获取指定表的结构信息"""
        if not self.check_database_exists() or not self.check_table_exists(table_name):
            return []

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'cid': row[0],
                    'name': row[1],
                    'type': row[2],
                    'notnull': bool(row[3]),
                    'dflt_value': row[4],
                    'pk': bool(row[5])
                })
            return columns
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def create_complete_table_structure(self) -> bool:
        """
        创建完整的5个表结构
        这个方法是核心：如果表不存在就创建，如果存在就跳过
        """
        conn = self.connect()
        try:
            cursor = conn.cursor()

            print("📋📋 开始创建完整的数据库表结构...")

            # 1. texts表 - 存储富文本内容（全新表）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS texts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ 检查/创建 texts 表")

            # 2. files表 - 文件信息表（修复版）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL UNIQUE,  -- 添加UNIQUE约束
                    file_type TEXT NOT NULL,
                    raw_filename TEXT,
                    -- 线上已有字段（完全保留）
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    file_size INTEGER,
                    page_count INTEGER,
                    processed INTEGER DEFAULT 0,
                    file_hash TEXT,
                    upload_count INTEGER DEFAULT 1,
                    last_uploaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bank_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- 安全新增字段
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_path TEXT
                )
            ''')
            print("✅ 检查/创建 files 表（100%兼容）")

            # 3. file_mappings表 - 文件映射表（兼容线上现有结构）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    mapping_data TEXT,
                    UNIQUE(file_id)
                )
            ''')
            print("✅ 检查/创建 file_mappings 表")

            # 4. table_processing_records表 - 表格处理记录表（全新表）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS table_processing_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    pdf_folder TEXT,
                    bank_name TEXT,
                    status TEXT,
                    stage TEXT,
                    progress INTEGER,
                    total_images INTEGER,
                    processed_images INTEGER,
                    success_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    excel_files TEXT,
                    start_time DATETIME,
                    end_time DATETIME,
                    error_message TEXT,
                    raw_result TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ 检查/创建 table_processing_records 表")

            # 5. api_call_log表 - API调用日志表（修复版）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_call_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    -- API基本信息
                    api_endpoint TEXT NOT NULL,
                    http_method TEXT NOT NULL,
                    request_headers TEXT,
                    request_body TEXT,
                    query_params TEXT,
                    -- 响应信息
                    response_status INTEGER,
                    response_headers TEXT,
                    response_body TEXT,
                    response_size INTEGER,
                    -- 性能监控
                    processing_time_ms INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    -- 客户端信息
                    client_ip TEXT,
                    user_agent TEXT,
                    referer TEXT,
                    -- 错误信息
                    error_message TEXT,
                    stack_trace TEXT,
                    -- 业务上下文
                    user_id INTEGER,
                    session_id TEXT,
                    correlation_id TEXT,
                    -- 缓存网关需要的列（新增）
                    md5 CHAR(32),
                    provider VARCHAR(50),
                    model_id VARCHAR(100),
                    cost_usd REAL DEFAULT 0,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    s3_key TEXT,
                    status VARCHAR(10) DEFAULT 'succ',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ 检查/创建 api_call_log 表")

            # 创建性能优化索引
            self._create_indexes(cursor)

            conn.commit()
            print("🎉🎉 完整的5个表结构检查/创建完成")
            return True

        except Exception as e:
            conn.rollback()
            print(f"❌❌ 创建表结构失败: {e}")
            return False
        finally:
            conn.close()

    def _create_indexes(self, cursor):
        """创建性能优化索引"""
        indexes = [
            ('idx_files_filename', 'files(filename)'),
            ('idx_files_deleted', 'files(deleted)'),
            ('idx_api_log_timestamp', 'api_call_log(timestamp)'),
            ('idx_api_log_endpoint', 'api_call_log(api_endpoint)'),
            ('idx_api_log_status', 'api_call_log(response_status)'),
            ('idx_processing_job_id', 'table_processing_records(job_id)'),
            ('idx_processing_status', 'table_processing_records(status)')
        ]

        for index_name, index_def in indexes:
            try:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}')
                print(f"✅ 创建索引: {index_name}")
            except Exception as e:
                print(f"⚠️ 创建索引失败 {index_name}: {e}")

    def add_missing_columns_safely(self) -> bool:
        """
        安全地添加缺失的列（不修改现有列）
        重点修复：添加 api_call_log 表缺失的缓存网关列
        """
        conn = self.connect()
        try:
            cursor = conn.cursor()

            # 定义每个表应该有的完整列结构
            table_columns = {
                'files': [
                    ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                    ('file_path', 'TEXT')
                ],
                'file_mappings': [
                    ('mapping_data', 'TEXT')
                ],
                'texts': [
                    # 全新表，通常不需要额外列
                ],
                'table_processing_records': [
                    # 全新表，通常不需要额外列
                ],
                'api_call_log': [
                    # 缓存网关需要的列（新增）
                    ('md5', 'CHAR(32)'),
                    ('provider', 'VARCHAR(50)'),
                    ('model_id', 'VARCHAR(100)'),
                    ('cost_usd', 'REAL DEFAULT 0'),
                    ('prompt_tokens', 'INTEGER DEFAULT 0'),
                    ('completion_tokens', 'INTEGER DEFAULT 0'),
                    ('s3_key', 'TEXT'),
                    ('status', 'VARCHAR(10) DEFAULT "succ"')
                ]
            }

            added_count = 0

            for table_name, expected_columns in table_columns.items():
                if not self.check_table_exists(table_name):
                    print(f"ℹℹ️ 表 {table_name} 不存在，跳过列检查")
                    continue

                # 获取现有列
                existing_columns = [col['name'] for col in self.get_table_structure(table_name)]
                print(f"🔍🔍 检查表 {table_name}，现有列: {existing_columns}")

                for column_name, column_type in expected_columns:
                    if column_name not in existing_columns:
                        try:
                            cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}')
                            print(f"✅ 为表 {table_name} 添加列: {column_name} {column_type}")
                            added_count += 1
                        except Exception as e:
                            print(f"❌❌ 为表 {table_name} 添加列 {column_name} 失败: {e}")
                    else:
                        print(f"ℹ️ 表 {table_name} 列 {column_name} 已存在，跳过")

            conn.commit()

            if added_count > 0:
                print(f"✅ 成功添加 {added_count} 个缺失的列")
            else:
                print("ℹℹ️ 没有需要添加的列")

            return True

        except Exception as e:
            conn.rollback()
            print(f"❌❌ 添加缺失列失败: {e}")
            return False
        finally:
            conn.close()

    def initialize_complete_database(self) -> bool:
        """
        初始化完整的数据库结构
        这是主要的入口方法
        """
        print("=" * 70)
        print("🚀🚀 开始初始化完整的数据库结构")
        print("=" * 70)

        # 检查当前状态
        db_exists = self.check_database_exists()
        existing_tables = self.get_all_tables()

        print(f"📊📊 当前状态:")
        print(f"   数据库文件: {'✅ 存在' if db_exists else '❌❌ 不存在'}")
        print(f"   现有表数量: {len(existing_tables)} 个")
        if existing_tables:
            print(f"   现有表: {', '.join(existing_tables)}")

        # 创建完整的表结构
        print("\n📋📋 步骤1: 创建完整的表结构")
        success = self.create_complete_table_structure()

        if not success:
            print("❌❌ 表结构创建失败")
            return False

        # 安全添加缺失列
        print("\n📋📋 步骤2: 检查并添加缺失的列")
        self.add_missing_columns_safely()

        # 验证最终结果
        print("\n📋📋 步骤3: 验证最终结构")
        final_tables = self.get_all_tables()

        print(f"🎉🎉 初始化完成!")
        print(f"📊📊 最终表数量: {len(final_tables)} 个")
        print(f"📋📋 包含以下表:")
        expected_tables = ['texts', 'files', 'file_mappings', 'table_processing_records', 'api_call_log']

        for table in expected_tables:
            status = "✅" if table in final_tables else "❌❌"
            columns = self.get_table_structure(table)
            column_count = len(columns) if columns else 0
            print(f"   {status} {table}: {column_count} 列")

        return True

    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库详细信息"""
        info = {
            'database_path': str(self.db_path),
            'database_exists': self.check_database_exists(),
            'database_size': self.db_path.stat().st_size if self.db_path.exists() else 0,
            'tables': {}
        }

        if not info['database_exists']:
            return info

        tables = self.get_all_tables()
        info['table_count'] = len(tables)

        for table in tables:
            columns = self.get_table_structure(table)
            info['tables'][table] = {
                'column_count': len(columns),
                'columns': [col['name'] for col in columns]
            }

        return info

    def print_detailed_report(self):
        """打印详细的数据报告"""
        info = self.get_database_info()

        print("\n" + "=" * 80)
        print("📊📊 数据库详细报告")
        print("=" * 80)

        print(f"📁📁 数据库文件: {info['database_path']}")
        print(f"📏📏 文件大小: {info['database_size'] / 1024 / 1024:.2f} MB" if info['database_exists'] else '文件不存在')
        print(f"📊📊 表数量: {info['table_count']}")

        if info['table_count'] > 0:
            print("\n📋📋 表结构详情:")
            for table_name, table_info in info['tables'].items():
                print(f"\n📊📊 表: {table_name}")
                print(f"   列数: {table_info['column_count']}")
                print(f"   列名: {', '.join(table_info['columns'])}")

    def _detect_database_path(self) -> Path:
        """自动检测数据库路径"""
        print(f"🔍🔍🔍🔍🔍🔍 调试信息 - 项目根目录: {self.project_root}")

        try:
            from backend.configs.config import config
            db_path_config = getattr(config, 'DATABASE_PATH', 'data/database.db')
            print(f"🔍🔍🔍🔍🔍🔍 调试信息 - config.DATABASE_PATH: {db_path_config}")

            # 确保返回正确的路径
            final_path = self.project_root / db_path_config
            print(f"🔍🔍🔍🔍🔍🔍 调试信息 - 最终路径: {final_path}")
            return final_path

        except ImportError as e:
            print(f"🔍🔍🔍🔍🔍🔍 调试信息 - 导入config失败: {e}")
            default_path = self.project_root / 'data' / 'database.db'
            print(f"🔍🔍🔍🔍🔍🔍 调试信息 - 使用默认路径: {default_path}")
            return default_path



def main():
    """主函数 - 提供交互式界面"""
    import argparse

    parser = argparse.ArgumentParser(description='数据库表结构管理器')
    parser.add_argument('--db-path', help='数据库文件路径')
    parser.add_argument('--project-root', help='项目根目录路径')
    parser.add_argument('--auto', action='store_true', help='自动模式（非交互式）')

    args = parser.parse_args()

    # 创建管理器实例
    manager = UniversalDatabaseSchemaManager(
        db_path=args.db_path,
        project_root=args.project_root
    )

    if args.auto:
        # 自动模式 - 直接执行初始化
        print("🤖🤖 自动模式启动")
        success = manager.initialize_complete_database()
        if success:
            print("🎉🎉 自动初始化完成!")
            manager.print_detailed_report()
        else:
            print("❌❌ 自动初始化失败")
            sys.exit(1)
    else:
        # 交互式模式
        interactive_mode(manager)


def interactive_mode(manager):
    """交互式模式"""
    while True:
        print("\n" + "=" * 60)
        print("🗃🗃️ 通用数据库表结构管理器")
        print("=" * 60)
        print("1. 🔄🔄 初始化完整数据库结构（推荐）")
        print("2. 🔍🔍 查看数据库状态")
        print("3. 📊📊 查看详细报告")
        print("4. 📋📋 查看现有表")
        print("5. ❌❌ 退出")

        choice = input("\n请选择操作 (1-5): ").strip()

        if choice == "1":
            print("\n🚀🚀 开始初始化完整数据库结构...")
            success = manager.initialize_complete_database()
            if success:
                print("\n🎉🎉 初始化成功！")
            else:
                print("\n❌❌ 初始化失败")

        elif choice == "2":
            info = manager.get_database_info()
            print(f"\n📊📊 数据库状态:")
            print(f"   路径: {info['database_path']}")
            print(f"   存在: {'✅' if info['database_exists'] else '❌❌'}")
            print(f"   表数量: {info['table_count']}")

        elif choice == "3":
            manager.print_detailed_report()

        elif choice == "4":
            tables = manager.get_all_tables()
            if tables:
                print(f"\n📋📋 现有表 ({len(tables)} 个):")
                for table in sorted(tables):
                    columns = manager.get_table_structure(table)
                    print(f"   📊📊 {table} ({len(columns)} 列)")
            else:
                print("ℹℹ️ 数据库中没有用户表")

        elif choice == "5":
            print("👋👋 再见！")
            break

        else:
            print("❌❌ 无效选择")

        input("\n按回车键继续...")


# 简单的一键执行函数
def setup_database(db_path: str = None, project_root: str = None) -> bool:
    """
    一键设置数据库（用于其他脚本调用）

    Args:
        db_path: 数据库路径
        project_root: 项目根目录

    Returns:
        bool: 是否成功
    """
    manager = UniversalDatabaseSchemaManager(db_path, project_root)
    return manager.initialize_complete_database()


if __name__ == "__main__":
    # 可以直接运行，也可以被其他模块导入
    if len(sys.argv) > 1:
        main()
    else:
        # 默认行为：自动模式
        manager = UniversalDatabaseSchemaManager()
        success = manager.initialize_complete_database()

        if success:
            print("\n🎉🎉 数据库表结构初始化完成！")
            print("💡💡 您现在可以：")
            print("   1. 重启后端服务")
            print("   2. 验证所有功能正常")
            print("   3. 检查API调用日志")
        else:
            print("\n❌❌ 初始化失败，请检查错误信息")
            sys.exit(1)