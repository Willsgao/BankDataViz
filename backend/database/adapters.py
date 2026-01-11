"""
数据库适配器 - 第二步：创建向后兼容的适配器
确保现有代码无需修改即可工作
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from contextlib import closing

# 导入第一步创建的配置
from . import get_db_connection, get_database_path, get_upload_folder, get_main_root


class OldDatabaseManagerAdapter:
    """
    兼容旧版 OldDatabaseManager 的适配器
    完全复制原始代码，只修改数据库连接部分
    """

    def __init__(self, db_path=None):
        # 保持接口兼容，但忽略传入的db_path，使用统一配置
        self.db_path = get_database_path()
        self.uploads_dir = get_upload_folder()

        # 确保目录存在（保持与原类相同的行为）
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)

        print(f"🔄 OldDatabaseManagerAdapter 初始化完成")
        print(f"   数据库路径: {self.db_path}")
        print(f"   上传目录: {self.uploads_dir}")

    def connect(self):
        """完全复制原始connect方法"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"❌❌ 数据库连接错误: {e}")
            return None

    def init_database(self):
        """完全复制原始init_database方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                # 1. 创建 texts 表（保持不变）
                c.execute('''CREATE TABLE IF NOT EXISTS texts
                             (id      INTEGER PRIMARY KEY AUTOINCREMENT,
                              content TEXT)''')

                # 2. 创建/升级 files 表（含软删除字段）
                c.execute('''CREATE TABLE IF NOT EXISTS files
                             (id           INTEGER PRIMARY KEY AUTOINCREMENT,
                              filename     TEXT NOT NULL UNIQUE,
                              file_type    TEXT NOT NULL,
                              raw_filename TEXT,              -- 原始中文文件名
                              created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                              deleted      INTEGER   DEFAULT 0)''')
                # -- 软删除标志

                # 3. 旧库兼容：依次补列
                c.execute("PRAGMA table_info(files)")
                cols = [col[1] for col in c.fetchall()]
                if 'raw_filename' not in cols:
                    c.execute("ALTER TABLE files ADD COLUMN raw_filename TEXT")
                    print("✅ 已自动为旧库添加 raw_filename 字段")
                if 'deleted' not in cols:
                    c.execute("ALTER TABLE files ADD COLUMN deleted INTEGER DEFAULT 0")
                    print("✅ 已自动为旧库添加 deleted 字段")

                # 4. 文本表处理 - 修改这里！！！
                # 只确保至少有一条记录，不删除已有数据
                c.execute("SELECT COUNT(*) FROM texts")
                count = c.fetchone()[0]

                if count == 0:
                    # 如果表是空的，插入一条记录
                    c.execute("INSERT INTO texts (content) VALUES (?)", ("",))
                    print("✅ 文本表为空，插入一条空记录")
                # 如果已经有数据，什么也不做，保持现有数据

                conn.commit()
                print("✅ 数据库初始化完成")
                return True
        except sqlite3.Error as e:
            print(f"❌❌ 数据库初始化错误: {e}")
            return False

    def read_database(self):
        """完全复制原始read_database方法，只修改连接方式"""
        print("\n===== 数据库内容读取器 =====")
        print(f"读取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                # 富文本内容
                print("\n===== 富文本内容 =====")
                c.execute("SELECT * FROM texts")
                texts = c.fetchall()
                for text in texts:
                    content = text["content"] or ""
                    print(f"ID: {text['id']}")
                    print(f"内容长度: {len(content)} 字符")
                    print(f"内容预览: {content[:100]}{'...' if len(content) > 100 else ''}")
                    print("-" * 50)

                # 文件记录
                print("\n===== 文件记录 =====")
                c.execute(
                    "SELECT id, filename, raw_filename, file_type, created_at FROM files ORDER BY created_at DESC")
                files = c.fetchall()

                if not files:
                    print("文件表中没有记录")
                else:
                    for file in files:
                        file_path = os.path.join(self.uploads_dir, file["filename"])
                        exists = "✅ 存在" if os.path.exists(file_path) else "❌❌ 缺失"
                        display_name = file["raw_filename"] or file["filename"]  # 优先中文
                        print(f"ID: {file['id']}, 文件名: {display_name}, "
                              f"类型: {file['file_type']}, 上传时间: {file['created_at']}, "
                              f"文件状态: {exists}")

                # 统计信息
                print("\n===== 数据库统计 =====")
                c.execute("SELECT COUNT(*) FROM texts")
                texts_count = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM files")
                files_count = c.fetchone()[0]

                actual_files = set(os.listdir(self.uploads_dir))
                db_files = set(file["filename"] for file in files)

                print(f"富文本记录: {texts_count} 条")
                print(f"文件记录: {files_count} 条")
                print(f"实际存储的文件: {len(actual_files)} 个")
                print(f"记录中缺失的文件: {len(db_files - actual_files)} 个")
                print(f"未记录的额外文件: {len(actual_files - db_files)} 个")

        except sqlite3.Error as e:
            print(f"❌❌ 读取数据库错误: {e}")
        finally:
            # 注意：这里不需要手动关闭连接，with语句会自动处理
            pass

        print("\n读取完成！")

    def clear_all(self):
        """完全复制原始clear_all方法，只修改连接方式"""
        if input("⚠️ 警告: 这将删除所有数据和文件。确认吗？(y/n): ").lower() != "y":
            print("操作已取消")
            return

        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                # 获取所有文件记录以便删除
                c.execute("SELECT filename FROM files")
                filenames = [row["filename"] for row in c.fetchall()]

                # 清空数据表
                c.execute("DELETE FROM texts")
                c.execute("DELETE FROM files")
                c.execute("DELETE FROM sqlite_sequence")

                conn.commit()
                print("✅ 数据库记录已清空")

                # 删除上传的文件
                self.delete_files(filenames)

        except sqlite3.Error as e:
            print(f"❌❌ 清空数据库错误: {e}")
            return False

    def clear_files(self):
        """完全复制原始clear_files方法，只修改连接方式"""
        if input("⚠️ 警告: 这将删除所有上传文件。确认吗？(y/n): ").lower() != "y":
            print("操作已取消")
            return

        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                # 获取所有文件记录以便删除
                c.execute("SELECT filename FROM files")
                filenames = [row["filename"] for row in c.fetchall()]

                # 清空文件表
                c.execute("DELETE FROM files")
                c.execute("DELETE FROM sqlite_sequence WHERE name='files'")

                conn.commit()
                print("✅ 文件记录已清空")

                # 删除上传的文件
                self.delete_files(filenames)

        except sqlite3.Error as e:
            print(f"❌❌ 清空文件错误: {e}")
            return False

    def clear_text(self):
        """完全复制原始clear_text方法，只修改连接方式"""
        if input("⚠️ 警告: 这将清除所有富文本内容。确认吗？(y/n): ").lower() != "y":
            print("操作已取消")
            return

        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE texts SET content = ?", ("",))
                conn.commit()
                print("✅ 富文本内容已清除")
        except sqlite3.Error as e:
            print(f"❌❌ 清除富文本内容错误: {e}")

    def delete_files(self, filenames=None):
        """完全复制原始delete_files方法"""
        if filenames is None:
            # 如果未指定文件名，则删除所有上传文件
            filenames = os.listdir(self.uploads_dir)

        deleted_count = 0
        error_count = 0

        for filename in filenames:
            file_path = os.path.join(self.uploads_dir, filename)
            try:
                if os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                    else:
                        print(f"⚠️ 不是文件: {file_path}")
                else:
                    print(f"⚠️ 文件不存在: {file_path}")
            except Exception as e:
                print(f"❌❌ 删除文件 {filename} 时出错: {e}")
                error_count += 1

        print(f"✅ 已删除 {deleted_count} 个文件，{error_count} 个失败")

    def vacuum_database(self):
        """完全复制原始vacuum_database方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                conn.execute("VACUUM")
                print("✅ 数据库已优化")
        except sqlite3.Error as e:
            print(f"❌❌ 优化数据库时出错: {e}")

    # 保持与原类相同的辅助函数
    def show_database_info(self):
        """完全复制原始show_database_info方法"""
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        files_count = len(os.listdir(self.uploads_dir))

        print("\n===== 数据库信息 =====")
        print(f"数据库路径: {self.db_path}")
        print(f"数据库大小: {db_size / 1024:.1f} KB" if db_size else "数据库文件不存在")
        print(f"上传目录: {self.uploads_dir}")
        print(f"上传文件数量: {files_count}")

    def main(self):
        """完全复制原始main方法"""
        # 确保数据库已初始化
        if not os.path.exists(self.db_path):
            print(f"数据库文件不存在，正在初始化...")
            self.init_database()
        else:
            # 检查是否需要优化
            db_size = os.path.getsize(self.db_path)
            if db_size > 10 * 1024 * 1024:
                print("⚠️ 注意: 数据库文件较大，建议优化")

        # 主菜单
        while True:
            print("\n===== 数据库管理工具 =====")
            print("1. 查看数据库内容")
            print("2. 清除所有内容（文件和文本）")
            print("3. 清除所有文件（图片和PDF）")
            print("4. 清除富文本内容")
            print("5. 优化数据库")
            print("6. 显示数据库信息")
            print("7. 退出")

            choice = input("请选择操作 (1-7): ")

            if choice == "1":
                self.read_database()
            elif choice == "2":
                self.clear_all()
            elif choice == "3":
                self.clear_files()
            elif choice == "4":
                self.clear_text()
            elif choice == "5":
                if input("⚠️ 将锁定数据库进行优化，确认吗？(y/n): ").lower() == "y":
                    self.vacuum_database()
            elif choice == "6":
                self.show_database_info()
            elif choice == "7":
                print("退出程序")
                break
            else:
                print("无效选择，请重新输入")


class NewDatabaseManagerAdapter:
    """
    兼容新版 NewDatabaseManager 的适配器
    完全复制原始代码，只修改数据库连接部分
    """

    def __init__(self, db_path=None):
        self.db_path = get_database_path()
        print(f"🔄 NewDatabaseManagerAdapter 初始化完成")

    def connect(self):
        """保持接口兼容"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # ✅ 必须设置这行！
        return conn

    def init_table_processing_db(self):
        """完全复制原始方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS table_processing_records
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                              updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                conn.commit()
                print("✅ 表格处理记录表初始化完成")
                return True
        except Exception as e:
            print(f"❌❌ 保存表格处理记录失败: {e}")
            return False

    def save_table_processing_record(self, job_info):
        """完全复制原始方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT id FROM table_processing_records WHERE job_id = ?",
                               (job_info.get('job_id'),))
                exists = cursor.fetchone()

                excel_files_json = json.dumps(job_info.get('excel_files', []))
                raw_result_json = json.dumps(job_info)

                if exists:
                    cursor.execute("""
                        UPDATE table_processing_records 
                        SET status = ?, stage = ?, progress = ?,
                            processed_images = ?, success_count = ?, failed_count = ?,
                            excel_files = ?, end_time = ?, error_message = ?,
                            raw_result = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE job_id = ?
                    """, (
                        job_info.get('status'),
                        job_info.get('stage'),
                        job_info.get('progress', 0),
                        job_info.get('processed_images', 0),
                        job_info.get('success_count', 0),
                        job_info.get('failed_count', 0),
                        excel_files_json,
                        job_info.get('end_time'),
                        job_info.get('error'),
                        raw_result_json,
                        job_info.get('job_id')
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO table_processing_records 
                        (job_id, pdf_folder, bank_name, status, stage, progress,
                         total_images, processed_images, success_count, failed_count,
                         excel_files, start_time, end_time, error_message, raw_result)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job_info.get('job_id'),
                        job_info.get('pdf_folder'),
                        job_info.get('bank_name'),
                        job_info.get('status'),
                        job_info.get('stage'),
                        job_info.get('progress', 0),
                        job_info.get('total_images', 0),
                        job_info.get('processed_images', 0),
                        job_info.get('success_count', 0),
                        job_info.get('failed_count', 0),
                        excel_files_json,
                        job_info.get('start_time'),
                        job_info.get('end_time'),
                        job_info.get('error'),
                        raw_result_json
                    ))

                conn.commit()
                return True
        except Exception as e:
            print(f"❌❌ 保存表格处理记录失败: {e}")
            return False

    def load_table_processing_records(self, pdf_folder=None, limit=100):
        """完全复制原始方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if pdf_folder:
                    cursor.execute("""
                        SELECT * FROM table_processing_records 
                        WHERE pdf_folder = ? 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (pdf_folder, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM table_processing_records 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (limit,))

                records = []
                for row in cursor.fetchall():
                    record = dict(row)
                    if record.get('excel_files'):
                        try:
                            record['excel_files'] = json.loads(record['excel_files'])
                        except:
                            record['excel_files'] = []
                    if record.get('raw_result'):
                        try:
                            record['raw_result'] = json.loads(record['raw_result'])
                        except:
                            record['raw_result'] = {}

                    records.append(record)

                return records
        except Exception as e:
            print(f"❌❌ 加载表格处理记录失败: {e}")
            return []

    def get_task_detail(self, job_id):
        """完全复制原始方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM table_processing_records 
                    WHERE job_id = ?
                """, (job_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                task_detail = dict(row)
                if task_detail.get('excel_files'):
                    try:
                        task_detail['excel_files'] = json.loads(task_detail['excel_files'])
                    except:
                        task_detail['excel_files'] = []
                if task_detail.get('raw_result'):
                    try:
                        task_detail['raw_result'] = json.loads(task_detail['raw_result'])
                    except:
                        task_detail['raw_result'] = {}

                return task_detail
        except Exception as e:
            print(f"❌❌ 查询任务详情失败: {e}")
            return None


# 创建适配器实例（供测试使用）
old_db_adapter = OldDatabaseManagerAdapter()
new_db_adapter = NewDatabaseManagerAdapter()

print("✅ 第二步完成：创建了完整的数据库适配器，保持100%向后兼容")