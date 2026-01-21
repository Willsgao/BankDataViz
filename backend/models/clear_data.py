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

    def __init__00(self, db_path=None, uploads_dir=None):
        """
        初始化清理工具 - 增强路径验证
        """
        # 计算根目录路径
        self.project_root = Path(__file__).parent.parent.parent

        # 设置默认路径
        self.db_path = db_path or config.DATABASE_PATH
        self.uploads_dir = uploads_dir or str(self.project_root / "data" / "backend" / "static" / "uploads")
        self.backup_dir = str(self.project_root / "data" / "backups")

        # 修改：缓存路径下所有的JSON文件
        self.mapping_files_path = Path(self.project_root) / "data" / "backend"

        # 验证并创建必要的目录
        self._validate_and_create_dirs()

        print(f"🔍🔍 项目根目录: {self.project_root}")
        print(f"🗃🗃 数据库路径: {self.db_path}")
        print(f"📁📁 上传目录: {self.uploads_dir}")
        print(f"💾💾 备份目录: {self.backup_dir}")
        print(f"🗂🗂 映射文件路径: {self.mapping_files_path}")

        # 检查数据库文件是否存在
        if not os.path.exists(self.db_path):
            print(f"⚠️⚠️ 数据库文件不存在: {self.db_path}")

    def __init__(self, db_path=None, uploads_dir=None):
        # 计算根目录路径
        self.project_root = Path(__file__).parent.parent.parent

        print(f"🔍🔍🔍 调试信息 - 项目根目录: {self.project_root}")

        # 设置默认路径
        try:
            from backend.configs.config import config
            print(f"🔍🔍🔍 调试信息 - config.DATABASE_PATH: {config.DATABASE_PATH}")
            print(f"🔍🔍🔍 调试信息 - config.DATABASE_PATH类型: {type(config.DATABASE_PATH)}")

            # 检查是否是绝对路径
            db_path_from_config = config.DATABASE_PATH
            is_absolute = Path(db_path_from_config).is_absolute()
            print(f"🔍🔍🔍 调试信息 - 是否是绝对路径: {is_absolute}")

            self.db_path = db_path or config.DATABASE_PATH
            print(f"🔍🔍🔍 调试信息 - 最终db_path: {self.db_path}")

        except ImportError as e:
            print(f"🔍🔍🔍 调试信息 - 导入config失败: {e}")
            self.db_path = db_path or str(self.project_root / "data" / "database.db")
            print(f"🔍🔍🔍 调试信息 - 使用默认路径: {self.db_path}")

        # 其他路径设置...
        self.uploads_dir = uploads_dir or str(self.project_root / "data" / "backend" / "static" / "uploads")
        self.backup_dir = str(self.project_root / "data" / "backups")
        self.mapping_files_path = Path(self.project_root) / "data" / "backend"

        print(f"🔍🔍🔍 调试信息 - 最终数据库路径: {self.db_path}")
        print(f"🔍🔍🔍 调试信息 - 上传目录: {self.uploads_dir}")

    def _validate_and_create_dirs(self):
        """验证并创建必要的目录"""
        # 确保上传目录存在
        if not os.path.exists(self.uploads_dir):
            try:
                os.makedirs(self.uploads_dir, exist_ok=True)
                print(f"✅ 已创建上传目录: {self.uploads_dir}")
            except Exception as e:
                print(f"❌❌ 创建上传目录失败: {e}")

        # 确保备份目录存在
        if not os.path.exists(self.backup_dir):
            try:
                os.makedirs(self.backup_dir, exist_ok=True)
                print(f"✅ 已创建备份目录: {self.backup_dir}")
            except Exception as e:
                print(f"❌❌ 创建备份目录失败: {e}")

        # 确保映射文件路径存在
        if not os.path.exists(self.mapping_files_path):
            try:
                os.makedirs(self.mapping_files_path, exist_ok=True)
                print(f"✅ 已创建映射文件路径: {self.mapping_files_path}")
            except Exception as e:
                print(f"❌❌ 创建映射文件路径失败: {e}")

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

    def clear_uploaded_files00000(self, confirm: bool = False) -> bool:
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

    def clear_uploaded_files(self, confirm: bool = False) -> bool:
        """
        清空上传的文件 - 修复版（支持多级目录清理）

        Args:
            confirm: 是否需要确认

        Returns:
            bool: 是否成功
        """
        # 检查目录是否存在，如果不存在则创建
        if not os.path.exists(self.uploads_dir):
            print(f"⚠️⚠️ 上传目录不存在: {self.uploads_dir}")
            try:
                os.makedirs(self.uploads_dir, exist_ok=True)
                print(f"✅ 已创建上传目录: {self.uploads_dir}")
            except Exception as e:
                print(f"❌❌ 创建上传目录失败: {e}")
                return False

        if not confirm:
            print(f"⚠️⚠️⚠️ 警告：这将删除目录 '{self.uploads_dir}' 中的所有文件和子目录！")
            print(f"⚠️⚠️⚠️ 路径: {self.uploads_dir}")
            response = input("请输入 'DELETE_FILES' 确认操作: ")
            if response != "DELETE_FILES":
                print("操作已取消")
                return False

        try:
            print(f"🔍🔍 开始清理上传目录: {self.uploads_dir}")

            # 获取所有文件和目录
            all_items = []
            files_count = 0
            dirs_count = 0

            for root, dirs, files in os.walk(self.uploads_dir):
                # 统计文件
                for file in files:
                    file_path = os.path.join(root, file)
                    all_items.append(('file', file_path))
                    files_count += 1

                # 统计目录（排除根目录）
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    all_items.append(('dir', dir_path))
                    dirs_count += 1

            print(f"📊📊 找到 {files_count} 个文件, {dirs_count} 个目录")

            if not all_items:
                print("ℹ️ℹ️ 上传目录已经是空的")
                return True

            # 删除文件
            deleted_files = 0
            deleted_dirs = 0
            errors = 0

            # 先删除所有文件
            for item_type, item_path in all_items:
                if item_type == 'file':
                    try:
                        os.remove(item_path)
                        deleted_files += 1
                        relative_path = os.path.relpath(item_path, self.uploads_dir)
                        print(f"🗑️🗑️ 已删除文件: {relative_path}")
                    except Exception as e:
                        print(f"❌❌ 删除文件失败 {item_path}: {e}")
                        errors += 1

            # 然后删除所有空目录（从最深层次开始）
            for root, dirs, files in os.walk(self.uploads_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        # 检查目录是否为空
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                            deleted_dirs += 1
                            relative_path = os.path.relpath(dir_path, self.uploads_dir)
                            print(f"🗑️🗑️ 已删除空目录: {relative_path}")
                        else:
                            print(f"⚠️⚠️ 目录非空，跳过: {os.path.relpath(dir_path, self.uploads_dir)}")
                    except Exception as e:
                        print(f"❌❌ 删除目录失败 {dir_path}: {e}")
                        errors += 1

            # 确保uploads目录本身存在
            if not os.path.exists(self.uploads_dir):
                os.makedirs(self.uploads_dir, exist_ok=True)
                print(f"✅ 重新创建上传目录: {self.uploads_dir}")

            print(f"✅✅ 文件清理完成！")
            print(f"   - 删除文件: {deleted_files}/{files_count}")
            print(f"   - 删除目录: {deleted_dirs}/{dirs_count}")
            print(f"   - 错误数量: {errors}")

            return errors == 0

        except Exception as e:
            print(f"❌❌❌❌ 清空上传文件失败: {e}")
            import traceback
            traceback.print_exc()
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

    def list_pdf_ids(self, limit=50, offset=0, search_filter=None):
        """查询PDF ID列表"""
        print(f"📄 查询PDF ID列表 (限制: {limit}, 偏移: {offset})...")

        conn = self.connect()
        cursor = conn.cursor()

        try:
            # 构建查询条件
            query = "SELECT pdf_id, file_name, created_at, file_size FROM pdf_files WHERE 1=1"
            params = []

            if search_filter:
                query += " AND (pdf_id LIKE ? OR file_name LIKE ?)"
                params.extend([f"%{search_filter}%", f"%{search_filter}%"])

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            pdf_files = cursor.fetchall()

            # 获取总数
            count_query = "SELECT COUNT(*) FROM pdf_files"
            if search_filter:
                count_query += " WHERE pdf_id LIKE ? OR file_name LIKE ?"
                count_params = [f"%{search_filter}%", f"%{search_filter}%"]
                cursor.execute(count_query, count_params)
            else:
                cursor.execute(count_query)

            total_count = cursor.fetchone()[0]

            return pdf_files, total_count

        except Exception as e:
            print(f"❌ 查询PDF ID列表失败: {e}")
            return [], 0
        finally:
            conn.close()

    def clear_data_comprehensive00000(self, confirm: bool = False) -> bool:
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

    def clear_data_comprehensive(self, confirm: bool = False) -> bool:
        """
        一键完成综合清理 - 修复版（确保所有步骤正确执行）

        Args:
            confirm: 是否需要确认

        Returns:
            bool: 是否成功
        """
        if not confirm:
            print("⚠️⚠️⚠️ 警告：这将执行综合清理操作！")
            print("⚠️⚠️⚠️ 包含以下三个步骤：")
            print("  1. 清空所有数据库表（危险操作！）")
            print("  2. 清空上传文件（包括所有PDF和图片文件）")
            print("  3. 重置文件映射缓存（清空所有JSON文件内容）")
            print("⚠️⚠️⚠️ 此操作不可逆！")

            response = input("请输入 'CLEAR_ALL' 确认执行综合清理: ")
            if response != "CLEAR_ALL":
                print("操作已取消")
                return False

        print("🚀🚀🚀🚀 开始执行综合清理...")
        print("=" * 60)

        # 步骤1：创建备份
        print("\n📋📋 步骤1: 创建数据库备份")
        backup_file = self.create_backup()
        if not backup_file:
            print("❌❌ 备份失败，操作中止")
            return False
        print(f"✅ 备份文件: {backup_file}")

        # 步骤2：清空所有表
        print("\n📋📋 步骤2: 清空所有数据库表")
        table_result = False
        try:
            table_result = self.clear_all_tables(confirm=True)
            if table_result:
                print("✅ 数据库表清空成功")
            else:
                print("❌❌ 数据库表清空失败")
        except Exception as e:
            print(f"❌❌ 清空数据库表异常: {e}")
            table_result = False

        # 步骤3：清空上传文件（关键修复）
        print("\n📋📋 步骤3: 清空上传文件")
        upload_result = False
        try:
            # 检查上传目录状态
            print(f"🔍🔍 检查上传目录: {self.uploads_dir}")
            if os.path.exists(self.uploads_dir):
                # 统计目录内容
                file_count = 0
                dir_count = 0
                for root, dirs, files in os.walk(self.uploads_dir):
                    file_count += len(files)
                    dir_count += len(dirs)

                print(f"📊📊 上传目录包含: {file_count} 个文件, {dir_count} 个目录")

                if file_count == 0 and dir_count == 0:
                    print("ℹ️ℹ️ 上传目录已经是空的，跳过清理")
                    upload_result = True
                else:
                    upload_result = self.clear_uploaded_files(confirm=True)
            else:
                print("ℹ️ℹ️ 上传目录不存在，跳过清理")
                upload_result = True

            if upload_result:
                print("✅ 上传文件清理成功")
            else:
                print("❌❌ 上传文件清理失败")

        except Exception as e:
            print(f"❌❌ 清空上传文件异常: {e}")
            upload_result = False

        # 步骤4：重置文件映射缓存
        print("\n📋📋 步骤4: 重置文件映射缓存")
        mapping_result = False
        try:
            mapping_result = self.reset_file_mapping_cache(confirm=True)
            if mapping_result:
                print("✅ 文件映射缓存重置成功")
            else:
                print("❌❌ 文件映射缓存重置失败")
        except Exception as e:
            print(f"❌❌ 重置文件映射缓存异常: {e}")
            mapping_result = False

        # 汇总结果
        print("\n" + "=" * 60)
        print("📊📊 综合清理完成汇总:")
        print("=" * 60)
        print(f"✅ 数据库备份: {backup_file}")
        print(f"✅ 清空数据库表: {'成功' if table_result else '失败'}")
        print(f"✅ 清空上传文件: {'成功' if upload_result else '失败'}")
        print(f"✅ 重置文件映射缓存: {'成功' if mapping_result else '失败'}")

        # 计算总体成功率
        success_steps = sum([table_result, upload_result, mapping_result])
        total_steps = 3
        success_rate = (success_steps / total_steps) * 100

        print(f"📈📈 总体成功率: {success_rate:.1f}% ({success_steps}/{total_steps})")

        if success_steps == total_steps:
            print("🎉🎉 综合清理完成！所有步骤均成功执行")
            return True
        elif success_steps > 0:
            print("⚠️⚠️ 综合清理完成，但部分步骤失败")
            return True  # 即使部分失败，也返回True（因为备份已创建）
        else:
            print("❌❌❌❌ 综合清理失败，所有步骤均失败")
            return False

    def _clear_mapping_by_pdf_id(self, pdf_id: str) -> bool:
        """
        清理JSON文件中与pdf_id相关的映射内容（参考reset_file_mapping_cache但只清理特定内容）

        Args:
            pdf_id: PDF标识符

        Returns:
            bool: 是否成功
        """
        json_files = self._get_mapping_files()

        if not json_files:
            print(f"ℹ️ℹ️ℹ️ℹ️ 缓存路径中没有JSON文件: {self.mapping_files_path}")
            return True

        try:
            cleared_count = 0
            error_count = 0
            total_cleared_records = 0

            for file_path in json_files:
                try:
                    # 备份文件
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_file = Path(self.backup_dir) / f"{file_path.stem}_backup_{timestamp}.json"
                    import shutil
                    shutil.copy2(file_path, backup_file)

                    # 读取现有内容
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            try:
                                mapping_data = json.load(f)
                                if isinstance(mapping_data, dict):
                                    # 删除与pdf_id相关的键
                                    keys_to_remove = []
                                    for key in mapping_data.keys():
                                        if pdf_id in key:  # 键中包含pdf_id
                                            keys_to_remove.append(key)

                                    for key in keys_to_remove:
                                        del mapping_data[key]

                                    cleared_records = len(keys_to_remove)
                                    total_cleared_records += cleared_records

                                    # 写回文件
                                    with open(file_path, 'w', encoding='utf-8') as f_out:
                                        json.dump(mapping_data, f_out, ensure_ascii=False, indent=2)

                                    cleared_count += 1
                                    print(
                                        f"✅ 已清理文件 {file_path.name}: 删除了 {cleared_records} 条与pdf_id '{pdf_id}' 相关的记录")
                                else:
                                    print(f"ℹ️ℹ️ 文件 {file_path.name} 格式不是字典，跳过")
                            except json.JSONDecodeError:
                                print(f"❌❌ 文件 {file_path.name} JSON格式错误，跳过")
                    else:
                        print(f"ℹ️ℹ️ 文件不存在: {file_path.name}")

                except Exception as e:
                    print(f"❌❌ 清理文件失败 {file_path.name}: {e}")
                    error_count += 1

            print(
                f"✅ 映射缓存清理完成！清理了 {cleared_count} 个文件，删除了 {total_cleared_records} 条记录，{error_count} 个失败")
            return error_count == 0

        except Exception as e:
            print(f"❌❌❌❌ 清理映射缓存失败: {e}")
            return False

    def _clear_uploaded_files_by_pdf_id(self, pdf_id: str) -> bool:
        """
        清理static目录下以pdf_id为名的文件夹和对应的PDF文件

        Args:
            pdf_id: PDF标识符

        Returns:
            bool: 是否成功
        """
        if not os.path.exists(self.uploads_dir):
            print(f"❌❌❌❌❌❌❌❌ 上传目录不存在: {self.uploads_dir}")
            return False

        try:
            deleted_count = 0
            error_count = 0

            # 1. 删除以pdf_id命名的文件夹
            target_dir = os.path.join(self.uploads_dir, pdf_id)
            if os.path.exists(target_dir):
                try:
                    import shutil
                    shutil.rmtree(target_dir)
                    deleted_count += 1
                    print(f"✅ 已删除目录: {target_dir}")
                except Exception as e:
                    print(f"❌❌❌❌ 删除目录失败 {target_dir}: {e}")
                    error_count += 1
            else:
                print(f"ℹ️ℹ️ℹ️ℹ️ 目录不存在，无需删除: {target_dir}")

            # 2. 删除对应的PDF文件（在uploads_dir根目录下）
            pdf_patterns = [
                f"{pdf_id}.pdf",
                f"{pdf_id}.PDF",
                f"{pdf_id}.*"  # 匹配任何扩展名
            ]

            for pattern in pdf_patterns:
                pdf_files = list(Path(self.uploads_dir).glob(pattern))
                for pdf_file in pdf_files:
                    if pdf_file.is_file():
                        try:
                            pdf_file.unlink()
                            deleted_count += 1
                            print(f"✅ 已删除PDF文件: {pdf_file.name}")
                        except Exception as e:
                            print(f"❌❌❌❌ 删除PDF文件失败 {pdf_file}: {e}")
                            error_count += 1

            # 3. 递归搜索并删除所有包含pdf_id的文件
            print(f"🔍🔍 搜索包含 '{pdf_id}' 的文件...")
            for root, dirs, files in os.walk(self.uploads_dir):
                for file in files:
                    if pdf_id in file:
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                            print(f"✅ 已删除相关文件: {file}")
                        except Exception as e:
                            print(f"❌❌❌❌ 删除相关文件失败 {file}: {e}")
                            error_count += 1

            # 4. 检查数据库中的文件路径并删除
            conn = self.connect()
            cursor = conn.cursor()
            try:
                # 获取文件在数据库中的路径信息
                cursor.execute("SELECT filename, raw_filename FROM files WHERE filename = ?", (pdf_id,))
                file_record = cursor.fetchone()

                if file_record:
                    filename, raw_filename = file_record
                    # 如果raw_filename存在，尝试删除原始文件
                    if raw_filename:
                        raw_file_path = os.path.join(self.uploads_dir, raw_filename)
                        if os.path.exists(raw_file_path):
                            try:
                                os.remove(raw_file_path)
                                deleted_count += 1
                                print(f"✅ 已删除原始文件: {raw_filename}")
                            except Exception as e:
                                print(f"❌❌❌❌ 删除原始文件失败 {raw_filename}: {e}")
                                error_count += 1
            except Exception as e:
                print(f"❌❌❌❌ 查询数据库文件路径失败: {e}")
            finally:
                conn.close()

            print(f"✅ 文件清理完成！总共删除了 {deleted_count} 个文件/目录，{error_count} 个失败")
            return error_count == 0

        except Exception as e:
            print(f"❌❌❌❌❌❌❌❌ 清理上传文件失败: {e}")
            return False

    def get_pdf_id_list(self, limit: int = 100, offset: int = 0, search_filter: str = None) -> tuple:
        """
        查询PDF ID列表（修正版，使用files表）

        Args:
            limit: 返回记录数限制
            offset: 偏移量
            search_filter: 搜索过滤条件

        Returns:
            tuple: (PDF列表, 总记录数)
        """
        print(f"📄📄 查询PDF ID列表 (限制: {limit}, 偏移: {offset})...")

        conn = self.connect()
        cursor = conn.cursor()

        try:
            # 构建查询条件 - 使用files表
            query = "SELECT id, filename, created_at, file_size, file_type FROM files WHERE 1=1"
            params = []

            if search_filter:
                query += " AND (filename LIKE ? OR file_type LIKE ?)"
                params.extend([f"%{search_filter}%", f"%{search_filter}%"])

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            pdf_files = cursor.fetchall()

            # 获取总数
            count_query = "SELECT COUNT(*) FROM files"
            if search_filter:
                count_query += " WHERE filename LIKE ? OR file_type LIKE ?"
                count_params = [f"%{search_filter}%", f"%{search_filter}%"]
                cursor.execute(count_query, count_params)
            else:
                cursor.execute(count_query)

            total_count = cursor.fetchone()[0]

            return pdf_files, total_count

        except Exception as e:
            print(f"❌❌ 查询PDF ID列表失败: {e}")
            return [], 0
        finally:
            conn.close()

    def get_pdf_details(self, file_id: str) -> tuple:
        """
        获取特定PDF的详细信息（修正版，使用files表）

        Args:
            file_id: 文件ID或文件名

        Returns:
            tuple: (PDF基本信息, 相关文件信息)
        """
        print(f"🔍🔍 查询PDF详情: {file_id}")

        conn = self.connect()
        cursor = conn.cursor()

        try:
            # 获取PDF基本信息 - 使用files表
            cursor.execute("""
                SELECT id, filename, file_type, raw_filename, created_at, 
                       file_size, page_count, processed, file_hash, bank_name
                FROM files WHERE filename = ? OR id = ?
            """, (file_id, file_id))
            file_info = cursor.fetchone()

            if not file_info:
                print(f"❌❌ 未找到文件: {file_id}")
                return None, []

            # 获取相关文件映射信息
            cursor.execute("""
                SELECT file_id, display_name, file_type, created_at 
                FROM file_mappings WHERE file_id = ?
            """, (file_info[0],))
            mappings = cursor.fetchall()

            return file_info, mappings

        except Exception as e:
            print(f"❌❌ 查询PDF详情失败: {e}")
            return None, []
        finally:
            conn.close()

    def _clear_database_by_pdf_id(self, pdf_id: str) -> bool:
        """
        清理数据库中与指定pdf_id相关的记录（修正版，适应实际表结构）

        Args:
            pdf_id: PDF标识符

        Returns:
            bool: 是否成功
        """
        if not os.path.exists(self.db_path):
            print("❌❌❌❌❌❌❌❌ 数据库文件不存在")
            return False

        conn = self.connect()
        try:
            cursor = conn.cursor()

            # 首先检查pdf_id是否存在
            cursor.execute("SELECT id FROM files WHERE filename = ?", (pdf_id,))
            file_record = cursor.fetchone()

            if not file_record:
                print(f"ℹℹ️ℹℹ️ℹℹ️ℹℹ️ 数据库中不存在pdf_id为 '{pdf_id}' 的记录")
                return True

            file_id = file_record[0]
            print(f"🔍🔍🔍🔍 找到pdf_id '{pdf_id}'，对应文件ID: {file_id}")

            total_deleted = 0
            deleted_per_table = {}

            # 根据您的实际表结构进行清理
            # 1. 先清理关联表的数据
            tables_to_clear = [
                "texts",  # 如果有文本内容表
                "file_mappings",  # 文件映射表
                "table_processing_records"  # 处理记录表
            ]

            for table in tables_to_clear:
                try:
                    # 检查表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                    if not cursor.fetchone():
                        print(f"ℹℹ️ℹℹ️ 表 {table} 不存在，跳过")
                        continue

                    # 尝试不同的关联字段进行删除
                    delete_queries = [
                        f"DELETE FROM {table} WHERE file_id = ?",
                        f"DELETE FROM {table} WHERE filename = ?",
                        f"DELETE FROM {table} WHERE pdf_id = ?"
                    ]

                    deleted_count = 0
                    for query in delete_queries:
                        try:
                            cursor.execute(query, (file_id,))
                            deleted_count += cursor.rowcount
                        except:
                            try:
                                cursor.execute(query, (pdf_id,))
                                deleted_count += cursor.rowcount
                            except:
                                continue  # 如果查询失败，继续尝试下一个

                    if deleted_count > 0:
                        deleted_per_table[table] = deleted_count
                        total_deleted += deleted_count
                        print(f"✅ 清理表 {table}: 删除了 {deleted_count} 条记录")

                except Exception as e:
                    print(f"❌❌❌❌ 清理表 {table} 失败: {e}")
                    continue

            # 2. 最后删除files表中的记录
            try:
                cursor.execute("DELETE FROM files WHERE filename = ?", (pdf_id,))
                files_deleted = cursor.rowcount
                if files_deleted > 0:
                    deleted_per_table["files"] = files_deleted
                    total_deleted += files_deleted
                    print(f"✅ 清理表 files: 删除了 {files_deleted} 条记录")
            except Exception as e:
                print(f"❌❌❌❌ 清理表 files 失败: {e}")

            conn.commit()
            print(f"✅ 数据库清理完成！总共删除了 {total_deleted} 条与pdf_id '{pdf_id}' 相关的记录")

            # 显示各表删除统计
            for table, count in deleted_per_table.items():
                print(f"   - {table}: {count} 条")

            return True

        except Exception as e:
            conn.rollback()
            print(f"❌❌❌❌❌❌❌❌ 清理数据库失败: {e}")
            return False
        finally:
            conn.close()

    def clear_data_by_pdf_id(self, pdf_id: str, confirm: bool = False) -> bool:
        """
        根据pdf_id精确清理数据（参考1+3+5步骤，但只清理指定pdf_id的内容）

        Args:
            pdf_id: 要清理的PDF标识符（对应files表中的filename字段）
            confirm: 是否需要确认

        Returns:
            bool: 是否成功
        """
        if not pdf_id or not pdf_id.strip():
            print("❌❌❌❌❌❌❌❌ pdf_id不能为空")
            return False

        pdf_id = pdf_id.strip()

        if not confirm:
            print(f"⚠️⚠️⚠️ 警告：这将清理与pdf_id '{pdf_id}' 相关的所有数据！")
            print("⚠️⚠️⚠️ 包含以下三个步骤：")
            print(f"  1. 删除数据库中与 '{pdf_id}' 相关的记录")
            print(f"  2. 删除static目录下以 '{pdf_id}' 为名的文件夹")
            print(f"  3. 删除JSON文件中与 '{pdf_id}' 相关的映射内容")
            print("⚠️⚠️⚠️ 此操作不可逆！")

            response = input("请输入 'DELETE_PDF_ID' 确认操作: ")
            if response != "DELETE_PDF_ID":
                print("操作已取消")
                return False

        print(f"🚀🚀🚀🚀🚀🚀🚀🚀 开始根据pdf_id '{pdf_id}' 精确清理数据...")

        # 创建备份
        print("\n📋📋📋📋 步骤1: 创建数据库备份")
        backup_file = self.create_backup()
        if not backup_file:
            print("❌❌❌❌ 备份失败，操作中止")
            return False

        overall_success = True

        # 步骤1: 清理数据库表中与pdf_id相关的记录（参考步骤1）
        print(f"\n📋📋📋📋 步骤2: 清理数据库中与 '{pdf_id}' 相关的记录")
        db_result = self._clear_database_by_pdf_id(pdf_id)
        overall_success = overall_success and db_result

        # 步骤2: 清理上传文件中与pdf_id相关的文件夹（参考步骤3）
        print(f"\n📋📋📋📋 步骤3: 清理static目录下以 '{pdf_id}' 为名的文件夹")
        file_result = self._clear_uploaded_files_by_pdf_id(pdf_id)  # 修正方法名
        overall_success = overall_success and file_result

        # 步骤3: 清理JSON文件中与pdf_id相关的映射内容（参考步骤5）
        print(f"\n📋📋📋📋 步骤4: 清理JSON文件中与 '{pdf_id}' 相关的映射内容")
        mapping_result = self._clear_mapping_by_pdf_id(pdf_id)
        overall_success = overall_success and mapping_result

        # 汇总结果
        print("\n" + "=" * 60)
        print(f"📊📊📊📊 根据pdf_id '{pdf_id}' 清理完成汇总:")
        print("=" * 60)
        print(f"✅ 数据库备份: {backup_file}")
        print(f"✅ 清理数据库记录: {'成功' if db_result else '失败'}")
        print(f"✅ 清理上传文件: {'成功' if file_result else '失败'}")
        print(f"✅ 清理映射缓存: {'成功' if mapping_result else '失败'}")

        if overall_success:
            print(f"🎉🎉🎉🎉 根据pdf_id '{pdf_id}' 的精确清理完成！")
        else:
            print("⚠️ 精确清理完成，但部分步骤失败")

        return overall_success


def view_pdf_details(cleaner):
    """查看PDF详细信息"""
    pdf_id = input("请输入要查看的PDF ID: ").strip()
    if not pdf_id:
        print("❌ PDF ID不能为空")
        return

    pdf_info, chunks = cleaner.get_pdf_details(pdf_id)

    if pdf_info:
        pdf_id, file_name, created_at, file_size, file_path, status = pdf_info

        print(f"\n📋 PDF详细信息")
        print("=" * 50)
        print(f"PDF ID: {pdf_id}")
        print(f"文件名: {file_name}")
        print(f"创建时间: {created_at}")
        print(f"文件大小: {file_size / 1024 / 1024:.1f}MB" if file_size else "N/A")
        print(f"文件路径: {file_path}")
        print(f"状态: {status}")
        print(f"文本块数量: {len(chunks)}")
        print("-" * 50)

        if chunks:
            print("文本块预览:")
            for i, (chunk_id, page_num, chunk_idx, content_preview) in enumerate(chunks[:5]):  # 只显示前5个
                preview = content_preview[:100] + "..." if len(content_preview) > 100 else content_preview
                print(f"  {i + 1}. 页面{page_num}-块{chunk_idx}: {preview}")

            if len(chunks) > 5:
                print(f"  ... 还有{len(chunks) - 5}个文本块")

        # 提供删除选项
        delete_choice = input("\n是否删除此PDF? (y/N): ").strip().lower()
        if delete_choice == 'y':
            # 这里可以调用现有的删除功能
            print("⚠️  删除功能需要调用现有的清理方法")
    else:
        print(f"❌ 未找到PDF: {pdf_id}")


def list_pdf_ids_interactive(cleaner):
    """交互式PDF ID列表查询"""
    while True:
        print("\n" + "=" * 60)
        print("📄📄 PDF ID 列表查询")
        print("=" * 60)
        print("1. 查看PDF列表")
        print("2. 搜索PDF文件")
        print("3. 查看PDF详情")
        print("4. 返回主菜单")

        choice = input("请选择操作 (1-4): ").strip()

        if choice == '1':
            show_pdf_list(cleaner)
        elif choice == '2':
            search_pdf_files(cleaner)
        elif choice == '3':
            view_pdf_details(cleaner)
        elif choice == '4':
            break
        else:
            print("❌❌ 无效选择，请重新输入")


def search_pdf_files(cleaner):
    """搜索PDF文件"""
    search_term = input("请输入搜索关键词 (PDF ID或文件名): ").strip()
    if not search_term:
        print("❌❌ 搜索关键词不能为空")
        return

    pdf_files, total_count = cleaner.get_pdf_id_list(
        limit=100,  # 搜索结果显示更多
        search_filter=search_term
    )

    print(f"\n🔍🔍 搜索结果: '{search_term}' (找到{total_count}个文件)")
    print("-" * 80)

    if pdf_files:
        for pdf_id, file_name, created_at, file_size in pdf_files:
            size_str = f"{file_size / 1024 / 1024:.1f}MB" if file_size else "N/A"
            print(f"PDF ID: {pdf_id}")
            print(f"文件名: {file_name}")
            print(f"创建时间: {created_at}")
            print(f"文件大小: {size_str}")
            print("-" * 40)
    else:
        print("❌❌ 未找到匹配的PDF文件")


def show_pdf_list(cleaner, page_size=20):
    """显示PDF列表（修正版）"""
    page = 0
    while True:
        pdf_files, total_count = cleaner.get_pdf_id_list(
            limit=page_size,
            offset=page * page_size
        )

        print(f"\n📋📋 文件列表 (第{page + 1}页，共{total_count}个文件)")
        print("-" * 100)
        print(f"{'ID':<5} {'文件名'} {'文件类型':<15} {'创建时间':<20} {'大小':<10} {'页数':<5}")
        print("-" * 100)

        for i, (file_id, filename, created_at, file_size, file_type) in enumerate(pdf_files):
            size_str = f"{file_size / 1024 / 1024:.1f}MB" if file_size else "N/A"
            # 获取页数信息
            cursor = cleaner.connect().cursor()
            cursor.execute("SELECT page_count FROM files WHERE id = ?", (file_id,))
            page_count_result = cursor.fetchone()
            page_count = page_count_result[0] if page_count_result and page_count_result[0] else "N/A"
            cursor.close()

            print(
                f"{file_id:<5} {filename} {file_type:<15} {created_at[:19]:<20} {size_str:<10} {page_count:<5}")

        print(f"\n第 {page + 1}/{(total_count + page_size - 1) // page_size} 页")
        print(f"显示 {len(pdf_files)} 个文件，总共 {total_count} 个文件")

        if total_count > page_size:
            action = input("\n操作: (n)下一页, (p)上一页, (q)返回: ").strip().lower()
            if action == 'n' and (page + 1) * page_size < total_count:
                page += 1
            elif action == 'p' and page > 0:
                page -= 1
            elif action == 'q':
                break
        else:
            input("\n按回车键返回...")
            break


def view_pdf_details_interactive(cleaner):
    """查看PDF详细信息（修正版）"""
    file_id = input("请输入要查看的文件ID或文件名: ").strip()
    if not file_id:
        print("❌❌ 文件ID或文件名不能为空")
        return

    file_info, mappings = cleaner.get_pdf_details(file_id)

    if file_info:
        (file_id, filename, file_type, raw_filename, created_at,
         file_size, page_count, processed, file_hash, bank_name) = file_info

        print(f"\n📋📋 文件详细信息")
        print("=" * 60)
        print(f"文件ID: {file_id}")
        print(f"文件名: {filename}")
        print(f"原始文件名: {raw_filename or 'N/A'}")
        print(f"文件类型: {file_type}")
        print(f"银行名称: {bank_name or 'N/A'}")
        print(f"创建时间: {created_at}")
        print(f"文件大小: {file_size / 1024 / 1024:.1f}MB" if file_size else "N/A")
        print(f"页数: {page_count or 'N/A'}")
        print(f"处理状态: {'已处理' if processed else '未处理'}")
        print(f"文件哈希: {file_hash or 'N/A'}")
        print("-" * 60)

        if mappings:
            print("文件映射信息:")
            for mapping in mappings:
                file_id, display_name, file_type, created_at = mapping
                print(f"  - 映射ID: {file_id}, 显示名: {display_name}, 类型: {file_type}, 时间: {created_at}")
        else:
            print("无文件映射信息")

        # 提供删除选项
        delete_choice = input("\n是否删除此文件? (y/N): ").strip().lower()
        if delete_choice == 'y':
            confirm = input(f"确认删除文件 '{filename}'? 输入 'DELETE_FILE' 确认: ").strip()
            if confirm == 'DELETE_FILE':
                # 调用清理方法
                cleaner.clear_data_by_pdf_id(filename, confirm=True)
            else:
                print("操作已取消")
    else:
        print(f"❌❌ 未找到文件: {file_id}")


def main():
    """主函数 - 交互式清理工具"""
    print("🧹🧹🧹🧹🧹🧹🧹🧹 数据库清理工具 - 根目录数据库版本")
    print("=" * 60)

    # 自动检测路径
    cleaner = DatabaseCleaner()

    while True:
        print("\n" + "=" * 50)
        print("🧹🧹🧹🧹🧹🧹🧹🧹 数据库清理工具")
        print("=" * 50)

        # 显示文件映射缓存状态
        mapping_stats = cleaner.get_file_mapping_stats()
        print(f"\n🗂🗂🗂🗂🗂🗂🗂🗂🗂🗂🗂🗂🗂🗂🗂🗂 文件映射缓存:")
        print(f"  路径: {mapping_stats['file_path']}")

        if mapping_stats["exists"]:
            if "error" in mapping_stats:
                print(f"  ❌❌❌❌ {mapping_stats['error']}")
            else:
                print(f"  📊📊📊📊 文件数量: {mapping_stats['file_count']} 个")
                print(f"  📊📊📊📊 总记录数: {mapping_stats['total_records']} 条")
                print(f"  📏📏📏📏 总大小: {mapping_stats['total_size']} 字节")

        # 显示数据库状态
        db_stats = cleaner.get_database_stats()
        print(f"\n🗃🗃🗃🗃🗃🗃🗃🗃🗃🗃🗃🗃🗃🗃🗃🗃 数据库状态:")
        if "error" in db_stats:
            print(f"  ❌❌❌❌ {db_stats['error']}")
        else:
            print(f"  📊📊📊📊 总记录数: {db_stats['total_records']} 条")
            print(f"  📁📁📁📁 表数量: {len(db_stats['tables'])} 个")
            for table, count in db_stats['tables'].items():
                print(f"    - {table}: {count} 条记录")

        # 菜单选项
        print("\n🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠🛠️ 操作选项:")
        print("1. 清空所有表（危险！）")
        print("2. 清空指定表")
        print("3. 清空上传文件")
        print("4. 清空文件映射缓存（删除所有JSON文件）")
        print("5. 重置文件映射缓存（清空所有JSON文件内容）")
        print("6. 🚀🚀🚀 一键综合清理（1+3+5步骤）")
        print("7. 🔍🔍🔍 根据pdf_id精确清理（新增功能）")
        print("8. 优化数据库")
        print("9. 显示表结构")
        print("10. 查看所有数据")
        print("11. 查看指定表数据")
        print("12. 创建备份")
        print("13. 退出")
        # 在现有菜单选项后添加
        print("14. 查询PDF ID列表")
        print("15. 查看PDF详情")

        # 在处理用户选择的部分添加对应的处理逻辑


        choice = input("\n请选择操作 (1-13): ").strip()

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
        elif choice == "6":
            cleaner.clear_data_comprehensive()
        elif choice == "7":
            pdf_id = input("请输入要清理的pdf_id: ").strip()
            if pdf_id:
                cleaner.clear_data_by_pdf_id(pdf_id)
            else:
                print("❌❌❌❌ pdf_id不能为空")
        elif choice == "8":
            cleaner.vacuum_database()
        elif choice == "9":
            cleaner.show_database_structure()
        elif choice == "10":
            cleaner.view_all_data()
        elif choice == "11":
            table_name = input("请输入要查看的表名: ").strip()
            if table_name:
                row_limit = input("请输入显示行数限制 (默认100): ").strip()
                row_limit = int(row_limit) if row_limit.isdigit() else 100
                cleaner.view_table_data(table_name, row_limit)
        elif choice == "12":
            cleaner.create_backup()
        elif choice == "13":
            print("👋👋👋👋👋👋👋👋👋👋👋👋👋👋👋👋 再见！")
            break
        elif choice == "14":
            list_pdf_ids_interactive(cleaner)
        elif choice == "15":
            view_pdf_details_interactive(cleaner)
        else:
            print("❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌ 无效选择")

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


    #
# 2     087dfa50-edcb-af39-867f-7568   pdf             2026-01-11 01:50:29  14.9MB     N/A
# 1     731b28f5-2bd0-141b-129f-c2ee   pdf             2026-01-11 01:49:26  0.7MB      N/A
# 2     087dfa50-edcb-af39-867f-7568   pdf             2026-01-11 01:50:29  14.9MB     N/A
# 1     731b28f5-2bd0-141b-129f-c2ee   pdf             2026-01-11 01:49:26  0.7MB      N/A
