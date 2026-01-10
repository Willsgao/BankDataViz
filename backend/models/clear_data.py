#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
数据库清理工具 - 专门用于清空数据库内容
适配根目录数据库文件路径
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
import json

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

# 现在可以导入backend模块
try:
    from backend.configs.config import config
except ImportError:
    # 如果直接导入失败，尝试动态导入
    import importlib.util
    config_path = project_root / "backend" / "configs" / "config.py"
    spec = importlib.util.spec_from_file_location("config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    config = config_module.config


class DatabaseCleaner:
    """数据库清理工具 - 适配根目录数据库路径"""

    def __init__(self, db_path=None, uploads_dir=None):
        """
        初始化清理工具

        Args:
            db_path: 数据库文件路径，默认为根目录下的 database.db
            uploads_dir: 上传目录路径，默认为 backend/static/uploads
        """
        # 计算根目录路径
        self.project_root = Path(__file__).parent.parent.parent

        print("self.project_root:", self.project_root)

        # 设置默认路径
        self.db_path = db_path or config.DATABASE_PATH
        self.uploads_dir = uploads_dir or str(self.project_root / "data" /  "backend" / "static")
        self.backup_dir = str(self.project_root / "data" / "backups")

        # 修改：缓存路径下所有的JSON文件
        self.mapping_files_path = Path(self.project_root) / "data" / "backend"  # 修改这一行
        print("self.mapping_files_path:", self.mapping_files_path)

        print(f"🔍🔍 项目根目录: {self.project_root}")
        print(f"🗃🗃️ 数据库路径: {self.db_path}")
        print(f"📁📁 上传目录: {self.uploads_dir}")
        print(f"💾💾 备份目录: {self.backup_dir}")
        print(f"🗂🗂🗂🗂 映射文件: {self.mapping_files_path}")  # 新增这一行

        # 确保备份目录存在
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)

        # 检查数据库文件是否存在
        if not os.path.exists(self.db_path):
            print(f"⚠️ 数据库文件不存在: {self.db_path}")

    def connect(self):
        """连接数据库"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_backup(self) -> str:
        """
        创建数据库备份

        Returns:
            str: 备份文件路径
        """
        if not os.path.exists(self.db_path):
            print("❌❌ 数据库文件不存在，无法备份")
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = Path(self.backup_dir) / f"database_clean_backup_{timestamp}.db"

        try:
            import shutil
            shutil.copy2(self.db_path, backup_file)
            print(f"✅ 数据库已备份到: {backup_file}")
            return str(backup_file)
        except Exception as e:
            print(f"❌❌❌❌ 备份失败: {e}")
            return ""

    def _get_mapping_files(self):
        """
        获取缓存路径下所有的JSON文件（不包含子文件夹）

        Returns:
            list: JSON文件路径列表
        """
        if not self.mapping_files_path.exists():
            return []

        json_files = []
        for file_path in self.mapping_files_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.json':
                json_files.append(file_path)

        return sorted(json_files)

    def clear_file_mapping_cache(self, confirm: bool = False) -> bool:
        """
        清空文件映射缓存（删除所有JSON文件）

        Args:
            confirm: 是否需要确认

        Returns:
            bool: 是否成功
        """
        json_files = self._get_mapping_files()

        if not json_files:
            print(f"ℹℹℹℹ️ 缓存路径中没有JSON文件: {self.mapping_files_path}")
            return True

        if not confirm:
            print(f"⚠️⚠️⚠️ 警告：这将删除缓存路径中的所有JSON文件！")
            print(f"⚠️⚠️⚠️ 路径: {self.mapping_files_path}")
            print(f"⚠️⚠️⚠️ 将删除以下 {len(json_files)} 个文件:")
            for file_path in json_files:
                print(f"  - {file_path.name}")
            response = input("请输入 'DELETE_MAPPING' 确认操作: ")
            if response != "DELETE_MAPPING":
                print("操作已取消")
                return False

        try:
            deleted_count = 0
            error_count = 0

            for file_path in json_files:
                try:
                    # 备份文件
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_file = Path(self.backup_dir) / f"{file_path.stem}_backup_{timestamp}.json"
                    import shutil
                    shutil.copy2(file_path, backup_file)
                    print(f"💾 已备份: {file_path.name} -> {backup_file.name}")

                    # 删除文件
                    file_path.unlink()
                    deleted_count += 1
                    print(f"🗑🗑🗑🗑️ 已删除: {file_path.name}")
                except Exception as e:
                    print(f"❌❌❌❌ 删除文件失败 {file_path.name}: {e}")
                    error_count += 1

            print(f"✅ 文件映射缓存清理完成！删除了 {deleted_count} 个文件，{error_count} 个失败")
            return error_count == 0

        except Exception as e:
            print(f"❌❌❌❌❌❌❌❌ 清空文件映射缓存失败: {e}")
            return False

    def reset_file_mapping_cache(self, confirm: bool = False) -> bool:
        """
        重置文件映射缓存（清空所有JSON文件内容但保留文件）

        Args:
            confirm: 是否需要确认

        Returns:
            bool: 是否成功
        """
        json_files = self._get_mapping_files()

        if not json_files:
            print(f"ℹℹℹℹ️ 缓存路径中没有JSON文件: {self.mapping_files_path}")
            return True

        if not confirm:
            print(f"⚠️⚠️⚠️ 警告：这将重置缓存路径中的所有JSON文件内容！")
            print(f"⚠️⚠️⚠️ 路径: {self.mapping_files_path}")
            print(f"⚠️⚠️⚠️ 将重置以下 {len(json_files)} 个文件:")
            for file_path in json_files:
                print(f"  - {file_path.name}")
            response = input("请输入 'RESET_MAPPING' 确认操作: ")
            if response != "RESET_MAPPING":
                print("操作已取消")
                return False

        try:
            reset_count = 0
            error_count = 0
            total_records = 0

            for file_path in json_files:
                try:
                    # 备份文件
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_file = Path(self.backup_dir) / f"{file_path.stem}_backup_{timestamp}.json"
                    import shutil
                    shutil.copy2(file_path, backup_file)
                    print(f"💾 已备份: {file_path.name} -> {backup_file.name}")

                    # 读取现有内容以获取记录数
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            try:
                                mapping_data = json.load(f)
                                if isinstance(mapping_data, dict):
                                    file_records = len(mapping_data)
                                else:
                                    file_records = 1  # 如果不是字典，至少有一条记录
                            except:
                                file_records = 0
                    else:
                        file_records = 0

                    total_records += file_records

                    # 重置为空内容
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({}, f, ensure_ascii=False, indent=2)

                    reset_count += 1
                    print(f"🔄 已重置: {file_path.name} (原 {file_records} 条记录)")

                except Exception as e:
                    print(f"❌❌❌❌ 重置文件失败 {file_path.name}: {e}")
                    error_count += 1

            print(
                f"✅ 文件映射缓存重置完成！重置了 {reset_count} 个文件，清空了 {total_records} 条记录，{error_count} 个失败")
            return error_count == 0

        except Exception as e:
            print(f"❌❌❌❌❌❌❌❌ 重置文件映射缓存失败: {e}")
            return False

    def get_file_mapping_stats(self) -> dict:
        """
        获取文件映射缓存统计信息

        Returns:
            dict: 映射文件统计信息
        """
        json_files = self._get_mapping_files()

        if not json_files:
            return {
                "exists": False,
                "file_path": str(self.mapping_files_path),
                "file_count": 0,
                "total_records": 0,
                "total_size": 0,
                "files": []
            }

        try:
            files_info = []
            total_records = 0
            total_size = 0

            for file_path in json_files:
                file_info = {
                    "name": file_path.name,
                    "size": os.path.getsize(file_path),
                    "records": 0,
                    "error": None
                }

                total_size += file_info["size"]

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        mapping_data = json.load(f)
                        if isinstance(mapping_data, dict):
                            file_info["records"] = len(mapping_data)
                        else:
                            file_info["records"] = 1
                    total_records += file_info["records"]
                except Exception as e:
                    file_info["error"] = str(e)
                    file_info["records"] = 0

                files_info.append(file_info)

            return {
                "exists": True,
                "file_path": str(self.mapping_files_path),
                "file_count": len(json_files),
                "total_records": total_records,
                "total_size": total_size,
                "files": files_info
            }

        except Exception as e:
            return {
                "exists": True,
                "file_path": str(self.mapping_files_path),
                "error": f"读取失败: {e}",
                "file_count": len(json_files),
                "total_size": sum(os.path.getsize(f) for f in json_files)
            }


    def get_database_stats(self) -> dict:
        """
        获取数据库统计信息

        Returns:
            dict: 数据库统计信息
        """
        if not os.path.exists(self.db_path):
            return {"error": "数据库文件不存在"}

        stats = {
            "database_path": self.db_path,
            "database_size": os.path.getsize(self.db_path),
            "tables": {},
            "total_records": 0,
            "exists": True
        }

        conn = self.connect()
        try:
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]

            # 获取每个表的记录数
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()[0]
                stats["tables"][table] = count
                stats["total_records"] += count

            return stats

        except Exception as e:
            return {"error": f"获取统计信息失败: {e}"}
        finally:
            conn.close()

    def view_all_data(self, table_limit: int = 10, row_limit: int = 50):
        """
        查看数据库所有数据

        Args:
            table_limit: 最多显示的表数量
            row_limit: 每个表最多显示的行数
        """
        if not os.path.exists(self.db_path):
            print("❌❌ 数据库文件不存在")
            return

        conn = self.connect()
        try:
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]

            if not tables:
                print("ℹℹ️ 数据库中没有用户表")
                return

            print(f"\n📋📋 数据库所有数据 (共 {len(tables)} 个表)")
            print("=" * 80)

            for i, table in enumerate(tables):
                if i >= table_limit:
                    print(f"\n⚠️⚠️ 已显示前 {table_limit} 个表，其余表被省略...")
                    break

                print(f"\n📊📊 表: {table}")
                print("-" * 60)

                # 获取表结构信息
                cursor.execute(f"PRAGMA table_info({table})")
                columns_info = cursor.fetchall()
                column_names = [col[1] for col in columns_info]

                # 显示列名
                print("字段名: " + " | ".join(column_names))

                # 获取数据
                cursor.execute(f"SELECT * FROM {table} LIMIT {row_limit}")
                rows = cursor.fetchall()

                if not rows:
                    print("  (空表)")
                    continue

                # 显示数据
                for j, row in enumerate(rows):
                    if j >= row_limit:
                        print(f"  ... (只显示前 {row_limit} 条记录)")
                        break

                    # 格式化每行数据
                    row_data = []
                    for value in row:
                        if value is None:
                            row_data.append("NULL")
                        elif isinstance(value, str) and len(value) > 20:
                            row_data.append(value[:20] + "...")
                        else:
                            row_data.append(str(value))

                    print(f"  {j + 1:2d}. " + " | ".join(row_data))

                # 显示总记录数
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                total_count = cursor.fetchone()[0]
                if total_count > row_limit:
                    print(f"  ... 共 {total_count} 条记录 (只显示前 {row_limit} 条)")

        except Exception as e:
            print(f"❌❌❌❌ 查看数据失败: {e}")
        finally:
            conn.close()

    def view_table_data(self, table_name: str, row_limit: int = 100):
        """
        查看指定表的详细数据

        Args:
            table_name: 表名
            row_limit: 最多显示的行数
        """
        if not os.path.exists(self.db_path):
            print("❌❌ 数据库文件不存在")
            return

        conn = self.connect()
        try:
            cursor = conn.cursor()

            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                print(f"❌❌ 表 '{table_name}' 不存在")
                return

            # 获取表结构信息
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()

            print(f"\n📊📊 表 '{table_name}' 的详细数据")
            print("=" * 80)

            # 显示表结构
            print("表结构:")
            for col in columns_info:
                col_id, col_name, col_type, not_null, default_val, is_pk = col
                pk_str = " PRIMARY KEY" if is_pk else ""
                null_str = " NOT NULL" if not_null else ""
                default_str = f" DEFAULT {default_val}" if default_val else ""
                print(f"  {col_name:15} {col_type:10}{null_str}{default_str}{pk_str}")

            # 获取总记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_count = cursor.fetchone()[0]
            print(f"\n总记录数: {total_count}")

            if total_count == 0:
                print("表为空")
                return

            # 获取数据
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {row_limit}")
            rows = cursor.fetchall()
            column_names = [col[1] for col in columns_info]

            print(f"\n数据内容 (显示前 {min(row_limit, total_count)} 条):")
            print("-" * 80)

            # 显示列名标题
            header = " | ".join([f"{name:<15}" for name in column_names])
            print(f"  ID  | {header}")
            print("  " + "-" * (len(header) + 10))

            # 显示数据行
            for i, row in enumerate(rows):
                row_data = []
                for value in row:
                    if value is None:
                        row_data.append("NULL".ljust(15))
                    elif isinstance(value, str) and len(value) > 15:
                        row_data.append((value[:12] + "...").ljust(15))
                    else:
                        row_data.append(str(value).ljust(15)[:15])

                print(f"  {i + 1:3d} | " + " | ".join(row_data))

            if total_count > row_limit:
                print(f"\n⚠️⚠️ 只显示前 {row_limit} 条记录，共 {total_count} 条记录")

        except Exception as e:
            print(f"❌❌❌❌ 查看表数据失败: {e}")
        finally:
            conn.close()

    def clear_all_tables(self, confirm: bool = False) -> bool:
        """
        清空所有表（危险操作！）

        Args:
            confirm: 是否需要确认

        Returns:
            bool: 是否成功
        """
        if not os.path.exists(self.db_path):
            print("❌❌ 数据库文件不存在")
            return False

        if not confirm:
            print("⚠️⚠️⚠️ 警告：这将删除所有数据！")
            print("⚠️⚠️⚠️ 此操作不可逆！")
            response = input("请输入 'DELETE_ALL' 确认操作: ")
            if response != "DELETE_ALL":
                print("操作已取消")
                return False

        # 创建备份
        backup_file = self.create_backup()
        if not backup_file:
            print("❌❌ 备份失败，操作中止")
            return False

        conn = self.connect()
        try:
            cursor = conn.cursor()

            # 获取所有用户表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]

            if not tables:
                print("ℹℹ️ 数据库中没有用户表")
                return True

            print(f"🔍🔍 找到 {len(tables)} 个表: {', '.join(tables)}")

            # 清空每个表
            total_deleted = 0
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
                deleted = cursor.rowcount
                total_deleted += deleted
                print(f"✅ 清空表 {table}: 删除了 {deleted} 条记录")

            # 重置自增ID
            cursor.execute("DELETE FROM sqlite_sequence")

            conn.commit()

            print(f"✅ 数据库清空完成！总共删除了 {total_deleted} 条记录")
            print(f"💾💾 备份文件: {backup_file}")

            return True

        except Exception as e:
            conn.rollback()
            print(f"❌❌❌❌ 清空数据库失败: {e}")
            return False
        finally:
            conn.close()

    def clear_specific_table(self, table_name: str, confirm: bool = False) -> bool:
        """
        清空指定表

        Args:
            table_name: 表名
            confirm: 是否需要确认

        Returns:
            bool: 是否成功
        """
        if not os.path.exists(self.db_path):
            print("❌❌ 数据库文件不存在")
            return False

        if not confirm:
            print(f"⚠️⚠️⚠️ 警告：这将清空表 '{table_name}' 的所有数据！")
            response = input("请输入 'DELETE_TABLE' 确认操作: ")
            if response != "DELETE_TABLE":
                print("操作已取消")
                return False

        conn = self.connect()
        try:
            cursor = conn.cursor()

            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                print(f"❌❌ 表 '{table_name}' 不存在")
                return False

            # 获取记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count_before = cursor.fetchone()[0]

            if count_before == 0:
                print(f"ℹℹ️ 表 '{table_name}' 已经是空的")
                return True

            # 清空表
            cursor.execute(f"DELETE FROM {table_name}")

            # 如果是自增表，重置自增ID
            cursor.execute("SELECT name FROM sqlite_sequence WHERE name=?", (table_name,))
            if cursor.fetchone():
                cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table_name,))

            conn.commit()

            print(f"✅ 表 '{table_name}' 清空完成！删除了 {count_before} 条记录")
            return True

        except Exception as e:
            conn.rollback()
            print(f"❌❌❌❌ 清空表 '{table_name}' 失败: {e}")
            return False
        finally:
            conn.close()

    def clear_uploaded_files(self, confirm: bool = False) -> bool:
        """
        清空上传的文件

        Args:
            confirm: 是否需要确认

        Returns:
            bool: 是否成功
        """
        if not os.path.exists(self.uploads_dir):
            print(f"❌❌ 上传目录不存在: {self.uploads_dir}")
            return False

        if not confirm:
            print(f"⚠️⚠️⚠️ 警告：这将删除目录 '{self.uploads_dir}' 中的所有文件！")
            response = input("请输入 'DELETE_FILES' 确认操作: ")
            if response != "DELETE_FILES":
                print("操作已取消")
                return False


        try:
            print("self.uploads_dir:", self.uploads_dir)
            # 获取文件列表
            files = []
            for root, dirs, filenames in os.walk(self.uploads_dir):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if os.path.isfile(file_path):
                        files.append(file_path)


            print("filesfiles:", files)

            if not files:
                print("ℹℹ️ 上传目录已经是空的")
                return True


            print(f"🔍🔍 找到 {len(files)} 个文件")

            # 删除文件
            deleted_count = 0
            error_count = 0

            for file_path in files:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"🗑🗑️ 已删除: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"❌❌ 删除文件失败 {file_path}: {e}")
                    error_count += 1

            print(f"✅ 文件清理完成！删除了 {deleted_count} 个文件，{error_count} 个失败")
            return error_count == 0

        except Exception as e:
            print(f"❌❌❌❌ 清空上传文件失败: {e}")
            return False

    def vacuum_database(self) -> bool:
        """
        优化数据库（清理空闲空间）

        Returns:
            bool: 是否成功
        """
        if not os.path.exists(self.db_path):
            print("❌❌ 数据库文件不存在")
            return False

        conn = self.connect()
        try:
            print("🔄🔄 正在优化数据库...")
            conn.execute("VACUUM")
            conn.commit()
            print("✅ 数据库优化完成")
            return True
        except Exception as e:
            print(f"❌❌❌❌ 数据库优化失败: {e}")
            return False
        finally:
            conn.close()

    def show_database_structure(self):
        """显示数据库表结构"""
        if not os.path.exists(self.db_path):
            print("❌❌ 数据库文件不存在")
            return

        conn = self.connect()
        try:
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]

            print(f"\n📋📋 数据库表结构 ({len(tables)} 个表):")
            print("=" * 60)

            for table in tables:
                print(f"\n📊📊 表: {table}")
                print("-" * 40)

                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()

                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    not_null = "NOT NULL" if col[3] else "NULL"
                    default = f"DEFAULT {col[4]}" if col[4] else ""
                    pk = "PRIMARY KEY" if col[5] else ""

                    print(f"  {col_name:15} {col_type:10} {not_null:10} {default:15} {pk}")

                # 获取记录数
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  记录数: {count}")

        except Exception as e:
            print(f"❌❌❌❌ 获取表结构失败: {e}")
        finally:
            conn.close()

    def clear_data_comprehensive(self, confirm: bool = False) -> bool:
        """
        一键完成综合清理：清空所有表 + 清空上传文件 + 重置文件映射缓存

        Args:
            confirm: 是否需要确认

        Returns:
            bool: 是否成功
        """
        if not confirm:
            print("⚠️⚠️⚠️ 警告：这将执行综合清理操作！")
            print("⚠️⚠️⚠️ 包含以下三个步骤：")
            print("  1. 清空所有数据库表（危险操作！）")
            print("  3. 清空上传文件")
            print("  5. 重置文件映射缓存（清空所有JSON文件内容）")
            print("⚠️⚠️⚠️ 此操作不可逆！")

            response = input("请输入 'CLEAR_ALL' 确认执行综合清理: ")
            if response != "CLEAR_ALL":
                print("操作已取消")
                return False

        print("🚀🚀🚀🚀 开始执行综合清理...")

        # 步骤1：创建备份
        print("\n📋 步骤1: 创建数据库备份")
        backup_file = self.create_backup()
        if not backup_file:
            print("❌ 备份失败，操作中止")
            return False

        # 步骤2：清空所有表
        print("\n📋 步骤2: 清空所有数据库表")
        table_result = self.clear_all_tables(confirm=True)  # 直接调用现有的方法

        if not table_result:
            return False

        # 步骤3：清空上传文件 - 使用您原有的清理逻辑
        print("\n📋 步骤3: 清空上传文件")
        upload_result = self.clear_uploaded_files(confirm=True)  # 直接调用现有的方法

        # 步骤4：重置文件映射缓存
        print("\n📋 步骤4: 重置文件映射缓存")
        mapping_result = self.reset_file_mapping_cache(confirm=True)  # 直接调用现有的方法

        # 汇总结果
        print("\n" + "=" * 60)
        print("📊 综合清理完成汇总:")
        print("=" * 60)
        print(f"✅ 数据库备份: {backup_file}")
        print(f"✅ 清空数据库表: {'成功' if table_result else '失败'}")
        print(f"✅ 清空上传文件: {'成功' if upload_result else '失败'}")
        print(f"✅ 重置文件映射缓存: {'成功' if mapping_result else '失败'}")

        overall_success = table_result and upload_result and mapping_result
        if overall_success:
            print("🎉 综合清理完成！所有步骤均成功执行")
        else:
            print("⚠️ 综合清理完成，但部分步骤失败")

        return overall_success



def main():
    """主函数 - 交互式清理工具"""
    print("🧹🧹🧹🧹 数据库清理工具 - 根目录数据库版本")
    print("=" * 60)

    # 自动检测路径
    cleaner = DatabaseCleaner()

    while True:
        print("\n" + "=" * 50)
        print("🧹🧹🧹🧹 数据库清理工具")
        print("=" * 50)

        # 显示文件映射缓存状态
        mapping_stats = cleaner.get_file_mapping_stats()
        print(f"\n🗂🗂🗂🗂🗂🗂🗂🗂 文件映射缓存:")
        print(f"  路径: {mapping_stats['file_path']}")

        if mapping_stats["exists"]:
            if "error" in mapping_stats:
                print(f"  ❌❌ {mapping_stats['error']}")
            else:
                print(f"  📊📊 文件数量: {mapping_stats['file_count']} 个")
                print(f"  📊📊 总记录数: {mapping_stats['total_records']} 条")
                print(f"  📏📏 总大小: {mapping_stats['total_size']} 字节")

        # 菜单选项
        print("\n🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠️ 操作选项:")
        print("1. 清空所有表（危险！）")
        print("2. 清空指定表")
        print("3. 清空上传文件")
        print("4. 清空文件映射缓存（删除所有JSON文件）")
        print("5. 重置文件映射缓存（清空所有JSON文件内容）")
        print("6. 🚀 一键综合清理（1+3+5步骤）")  # 新增选项
        print("7. 优化数据库")
        print("8. 显示表结构")
        print("9. 查看所有数据")
        print("10. 查看指定表数据")
        print("11. 创建备份")
        print("12. 退出")

        choice = input("\n请选择操作 (1-12): ").strip()

        if choice == "1":
            cleaner.clear_all_tables()
        elif choice == "2":
            table_name = input("请输入要清空的表名: ").strip()
            if table_name:
                cleaner.clear_specific_table(table_name)
        elif choice == "3":
            cleaner.clear_uploaded_files()
        elif choice == "4":
            cleaner.clear_file_mapping_cache()
        elif choice == "5":
            cleaner.reset_file_mapping_cache()
        elif choice == "6":  # 新增的一键综合清理
            cleaner.clear_data_comprehensive()
        elif choice == "7":
            cleaner.vacuum_database()
        elif choice == "8":
            cleaner.show_database_structure()
        elif choice == "9":
            cleaner.view_all_data()
        elif choice == "10":
            table_name = input("请输入要查看的表名: ").strip()
            if table_name:
                row_limit = input("请输入显示行数限制 (默认100): ").strip()
                row_limit = int(row_limit) if row_limit.isdigit() else 100
                cleaner.view_table_data(table_name, row_limit)
        elif choice == "11":
            cleaner.create_backup()
        elif choice == "12":
            print("👋👋👋👋👋👋👋👋 再见！")
            break
        else:
            print("❌❌❌❌❌❌❌❌ 无效选择")

        input("\n按回车键继续...")


def quick_clean():
    """快速清理方法（用于集成到其他代码）"""
    cleaner = DatabaseCleaner()

    # 显示当前状态
    stats = cleaner.get_database_stats()
    if "error" in stats:
        print(f"❌❌❌❌❌❌❌❌ {stats['error']}")
        return

    # 显示文件映射缓存状态
    mapping_stats = cleaner.get_file_mapping_stats()
    print(f"📊📊📊📊📊📊📊📊 当前数据库状态: {stats['total_records']} 条记录")
    if mapping_stats["exists"] and not "error" in mapping_stats:
        print(f"🗂🗂🗂🗂🗂🗂🗂🗂 文件映射缓存: {mapping_stats['file_count']} 个文件, {mapping_stats['total_records']} 条记录")

    # 确认清理
    confirm = input("是否执行一键综合清理？(y/N): ").strip().lower()
    if confirm == 'y':
        # 使用新的综合清理方法
        cleaner.clear_data_comprehensive(confirm=True)
        print("✅ 一键综合清理完成！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋👋 程序被用户中断")