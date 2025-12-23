#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
数据库维护脚本
用于检查、备份、修复数据库
"""

import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.models.safe_unified_db import SafeDatabaseManager


def backup_database():
    """备份数据库"""
    print("🔧 执行数据库备份...")

    db_mgr = SafeDatabaseManager()
    backup_file = db_mgr.backup_database()

    if backup_file:
        print(f"✅ 数据库已备份到: {backup_file}")

        # 显示备份信息
        import shutil
        backup_size = os.path.getsize(backup_file)
        print(f"   备份大小: {backup_size / 1024:.2f} KB")
    else:
        print("❌ 数据库备份失败")


def check_database():
    """检查数据库状态"""
    print("🔍 检查数据库状态...")

    db_mgr = SafeDatabaseManager()
    db_info = db_mgr.get_database_info()

    if not db_info:
        print("❌ 无法获取数据库信息")
        return

    print(f"📁 数据库路径: {db_info['path']}")
    print(f"📊 数据库大小: {db_info['size_bytes'] / 1024:.2f} KB")
    print("📈 数据表统计:")

    total_rows = 0
    for table, count in db_info.get('row_counts', {}).items():
        print(f"   {table}: {count} 行")
        total_rows += count

    print(f"📊 总计: {total_rows} 行数据")

    # 检查文件映射完整性
    if 'files' in db_info.get('row_counts', {}):
        files_count = db_info['row_counts']['files']
        file_mappings_count = db_info['row_counts'].get('file_mappings', 0)

        if files_count > 0 and file_mappings_count < files_count:
            print(f"⚠️  警告: {files_count - file_mappings_count} 个文件可能缺少映射")
        else:
            print("✅ 文件映射完整性检查通过")


def repair_database():
    """修复数据库（重建索引等）"""
    print("🔧 修复数据库...")

    db_mgr = SafeDatabaseManager()

    # 安全初始化（会检查和修复表结构）
    db_mgr.init_database()

    print("✅ 数据库修复完成")


def export_database():
    """导出数据库为SQL文件"""
    import sqlite3
    import datetime

    db_mgr = SafeDatabaseManager()

    if not os.path.exists(db_mgr.db_path):
        print("❌ 数据库文件不存在")
        return

    # 创建导出目录
    export_dir = Path("data/exports")
    export_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    export_file = export_dir / f"database_export_{timestamp}.sql"

    print(f"📤 导出数据库到: {export_file}")

    try:
        conn = sqlite3.connect(db_mgr.db_path)

        with open(export_file, 'w', encoding='utf-8') as f:
            # 导出表结构
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")

            for row in cursor.fetchall():
                f.write(f"{row[0]};\n\n")

            # 导出数据
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")

            for table_row in cursor.fetchall():
                table_name = table_row[0]
                f.write(f"\n-- 数据表: {table_name}\n")

                cursor2 = conn.cursor()
                cursor2.execute(f"SELECT * FROM {table_name}")
                columns = [desc[0] for desc in cursor2.description]

                for data_row in cursor2.fetchall():
                    # 转义特殊字符
                    values = []
                    for value in data_row:
                        if value is None:
                            values.append('NULL')
                        elif isinstance(value, (int, float)):
                            values.append(str(value))
                        else:
                            escaped = str(value).replace("'", "''")
                            values.append(f"'{escaped}'")

                    insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});\n"
                    f.write(insert_sql)

        conn.close()
        print(f"✅ 数据库已导出到: {export_file}")

    except Exception as e:
        print(f"❌ 数据库导出失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库维护工具")
    parser.add_argument('action', choices=['backup', 'check', 'repair', 'export', 'all'],
                        help='执行的操作')

    args = parser.parse_args()

    print("=" * 60)
    print("🔧 DocuVista 数据库维护工具")
    print("=" * 60)

    if args.action == 'backup':
        backup_database()
    elif args.action == 'check':
        check_database()
    elif args.action == 'repair':
        repair_database()
    elif args.action == 'export':
        export_database()
    elif args.action == 'all':
        check_database()
        print("-" * 40)
        backup_database()
        print("-" * 40)
        repair_database()

    print("=" * 60)
    print("✅ 操作完成")
    print("=" * 60)


if __name__ == '__main__':
    main()