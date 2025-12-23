"""
统一的数据库管理器 - 合并 database_manager.py 和 new_database.py
路径使用 utils/config.py 中的配置
"""

import os
import json
import sqlite3
from contextlib import closing
from datetime import datetime

# ============ 导入配置 ============

try:
    from backend.configs.config import (
        PROJECT_ROOT_STR,
        UPLOAD_FOLDER,
        PNG_OUTPUT_ROOT,
        EXCEL_OUTPUT_ROOT,
        DATABASE,  # ✅ 使用 config.py 中的路径
        ALLOWED_EXTENSIONS
    )
except ImportError as e:
    print(f"❌ 无法导入配置: {e}")
    # 回退到默认值（与 config.py 一致）
    PROJECT_ROOT_STR = os.getcwd()
    UPLOAD_FOLDER = 'data/backend/static/uploads'
    PNG_OUTPUT_ROOT = 'data/backend/static/pdf2pngs'
    EXCEL_OUTPUT_ROOT = 'data/backend/static/excel_data'
    DATABASE = 'data/database.db'  # ✅ 统一使用这个路径
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


# 在导入配置后添加
TABLE_PROCESSING_RECORDS_TABLE = """
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
"""

class UnifiedDatabaseManager:
    """统一数据库管理器"""

    def __init__(self):
        """初始化 - 使用 utils/config.py 中的配置"""
        # ✅ 使用从 config.py 导入的 DATABASE
        self.db_path = DATABASE
        # ✅ 使用从 config.py 导入的 UPLOAD_FOLDER
        self.uploads_dir = UPLOAD_FOLDER

        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)

        print(f"✅ 数据库路径: {self.db_path}")
        print(f"✅ 上传目录: {self.uploads_dir}")

    # ============ 来自 database_manager.py 的方法 ============
    def init_database(self):
        """兼容旧方法 - 实际调用 init_all_tables"""
        print("⚠️ init_database() 已过时，请使用 init_all_tables()")
        return self.init_all_tables()

    def read_database(self):
        """
        读取数据库内容
        :return: None
        """
        print("\n===== 数据库内容读取器 =====")
        print(f"读取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        conn = self.connect()
        if conn is None:
            return

        try:
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
            c.execute("SELECT id, filename, raw_filename, file_type, created_at FROM files ORDER BY created_at DESC")
            files = c.fetchall()

            if not files:
                print("文件表中没有记录")
            else:
                for file in files:
                    file_path = os.path.join(self.uploads_dir, file["filename"])
                    exists = "✅ 存在" if os.path.exists(file_path) else "❌ 缺失"
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
            print(f"❌ 读取数据库错误: {e}")
        finally:
            conn.close()

        print("\n读取完成！")

    def clear_all(self):
        """
        清空所有数据库记录并删除文件
        :return: None
        """
        if input("⚠️ 警告: 这将删除所有数据和文件。确认吗？(y/n): ").lower() != "y":
            print("操作已取消")
            return

        conn = self.connect()
        if conn is None:
            return

        try:
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
            print(f"❌ 清空数据库错误: {e}")
            return False
        finally:
            conn.close()

    def clear_files(self):
        """删除所有上传文件并清空文件记录"""
        if input("⚠️ 警告: 这将删除所有上传文件。确认吗？(y/n): ").lower() != "y":
            print("操作已取消")
            return

        conn = self.connect()
        if conn is None:
            return

        try:
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
            print(f"❌ 清空文件错误: {e}")
            return False
        finally:
            conn.close()

    def clear_text(self):
        """清除富文本内容"""
        if input("⚠️ 警告: 这将清除所有富文本内容。确认吗？(y/n): ").lower() != "y":
            print("操作已取消")
            return

        conn = self.connect()
        if conn is None:
            return

        try:
            c = conn.cursor()
            c.execute("UPDATE texts SET content = ?", ("",))
            conn.commit()
            print("✅ 富文本内容已清除")
        except sqlite3.Error as e:
            print(f"❌ 清除富文本内容错误: {e}")
        finally:
            conn.close()

    def delete_files(self, filenames=None):
        """删除指定的文件"""
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
                print(f"❌ 删除文件 {filename} 时出错: {e}")
                error_count += 1

        print(f"✅ 已删除 {deleted_count} 个文件，{error_count} 个失败")

    def vacuum_database(self):
        """优化数据库并减小文件大小"""
        conn = self.connect()
        if conn is None:
            return

        try:
            conn.execute("VACUUM")
            print("✅ 数据库已优化")
        except sqlite3.Error as e:
            print(f"❌ 优化数据库时出错: {e}")
        finally:
            conn.close()

    def show_database_info(self):
        """显示数据库信息"""
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        files_count = len(os.listdir(self.uploads_dir))

        print("\n===== 数据库信息 =====")
        print(f"数据库路径: {self.db_path}")
        print(f"数据库大小: {db_size / 1024:.1f} KB" if db_size else "数据库文件不存在")
        print(f"上传目录: {self.uploads_dir}")
        print(f"上传文件数量: {files_count}")

    # ============ 来自 new_database.py 的方法 ============
    def init_table_processing_db(self):
        """兼容旧方法 - 实际调用 init_all_tables"""
        print("⚠️ init_table_processing_db() 已过时，请使用 init_all_tables()")
        return self.init_all_tables()

    def save_table_processing_record(self, job_info):
        """保存表格处理记录到数据库"""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn = self.connect()  # ✅ 使用统一的 connect() 方法
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
            print(f"❌ 保存表格处理记录失败: {e}")
            return False

    def load_table_processing_records(self, pdf_folder=None, limit=100):
        """从数据库加载表格处理记录"""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
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
            print(f"❌ 加载表格处理记录失败: {e}")
            return []

    def get_task_detail(self, job_id):
        """查询单个任务详情"""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
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
            print(f"❌ 查询任务详情失败: {e}")
            return None


    # ============ 公共方法 ============
    def connect(self):
        """统一的数据库连接方法"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_all_tables(self):
        """一次性初始化所有表"""
        conn = self.connect()
        try:
            cursor = conn.cursor()

            success = True

            # 1. 初始化文档相关表
            if not self._init_document_tables(cursor):
                print("❌ 文档表初始化失败")
                success = False

            # 2. 初始化表格处理表
            if not self._init_table_processing_tables(cursor):
                print("❌ 表格处理表初始化失败")
                success = False

            if success:
                conn.commit()
                print("✅ 所有数据库表初始化完成")
            else:
                conn.rollback()
                print("❌ 数据库表初始化失败，已回滚")

            return success

        except Exception as e:
            conn.rollback()
            print(f"❌ 初始化失败: {e}")
            return False
        finally:
            conn.close()

    def _init_document_tables(self, cursor):
        """
        初始化文档表（原 database_manager 功能）
        创建 texts 表和 files 表，并处理旧库兼容性
        """
        try:
            # 1. 创建 texts 表（保持不变）
            cursor.execute('''CREATE TABLE IF NOT EXISTS texts
                             (id      INTEGER PRIMARY KEY AUTOINCREMENT,
                              content TEXT)''')

            # 2. 创建/升级 files 表（含软删除字段）
            cursor.execute('''CREATE TABLE IF NOT EXISTS files
                             (id           INTEGER PRIMARY KEY AUTOINCREMENT,
                              filename     TEXT NOT NULL UNIQUE,
                              file_type    TEXT NOT NULL,
                              raw_filename TEXT,
                              created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                              deleted      INTEGER   DEFAULT 0)''')

            # 3. 旧库兼容：检查并添加缺失的列
            cursor.execute("PRAGMA table_info(files)")
            existing_cols = [col[1] for col in cursor.fetchall()]

            # 检查并添加 raw_filename 列
            if 'raw_filename' not in existing_cols:
                cursor.execute("ALTER TABLE files ADD COLUMN raw_filename TEXT")
                print("✅ 已为 files 表添加 raw_filename 字段")

            # 检查并添加 deleted 列
            if 'deleted' not in existing_cols:
                cursor.execute("ALTER TABLE files ADD COLUMN deleted INTEGER DEFAULT 0")
                print("✅ 已为 files 表添加 deleted 字段")

            # 4. 确保 texts 表仅保留一条记录
            cursor.execute("SELECT COUNT(*) FROM texts")
            count = cursor.fetchone()[0]

            if count == 0:
                cursor.execute("INSERT INTO texts (content) VALUES (?)", ("",))
            elif count > 1:
                # 保留第一条记录，删除其他
                cursor.execute("SELECT id FROM texts ORDER BY id LIMIT 1")
                first_id = cursor.fetchone()[0]
                cursor.execute("DELETE FROM texts WHERE id != ?", (first_id,))

            print("✅ 文档表初始化完成")
            return True

        except sqlite3.Error as e:
            print(f"❌ 初始化文档表失败: {e}")
            return False

    def _init_table_processing_tables(self, cursor):
        """
        初始化表格处理表（原 new_database 功能）
        创建 table_processing_records 表
        """
        try:
            # 创建表格处理记录表
            cursor.execute('''CREATE TABLE IF NOT EXISTS table_processing_records
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

            # 检查表结构并添加缺失列（如果需要）
            cursor.execute("PRAGMA table_info(table_processing_records)")
            existing_cols = [col[1] for col in cursor.fetchall()]

            # 定义所有预期的列及其类型
            expected_columns = [
                ('job_id', 'TEXT'),
                ('pdf_folder', 'TEXT'),
                ('bank_name', 'TEXT'),
                ('status', 'TEXT'),
                ('stage', 'TEXT'),
                ('progress', 'INTEGER'),
                ('total_images', 'INTEGER'),
                ('processed_images', 'INTEGER'),
                ('success_count', 'INTEGER'),
                ('failed_count', 'INTEGER'),
                ('excel_files', 'TEXT'),
                ('start_time', 'DATETIME'),
                ('end_time', 'DATETIME'),
                ('error_message', 'TEXT'),
                ('raw_result', 'TEXT'),
                ('created_at', 'DATETIME'),
                ('updated_at', 'DATETIME')
            ]

            # 添加缺失的列
            for col_name, col_type in expected_columns:
                if col_name not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE table_processing_records ADD COLUMN {col_name} {col_type}")
                        print(f"✅ 已为 table_processing_records 表添加 {col_name} 字段")
                    except sqlite3.Error as e:
                        print(f"⚠️ 添加列 {col_name} 失败: {e}")

            print("✅ 表格处理表初始化完成")
            return True

        except sqlite3.Error as e:
            print(f"❌ 初始化表格处理表失败: {e}")
            return False


# ============ 兼容层（可选） ============
class DatabaseManager(UnifiedDatabaseManager):
    """兼容原 database_manager.py 的类名"""

    def __init__(self, db_path=None):
        """
        兼容构造函数，接受参数但忽略它们
        注意：现在使用 config.py 中的路径，传入的参数将被忽略
        """
        if db_path is not None:
            print(f"⚠️ 注意：DatabaseManager 现在使用 config.py 中的路径")
            print(f"     传入的路径 '{db_path}' 将被忽略")
            print(f"     实际使用路径: {DATABASE}")

        print("⚠️ DatabaseManager 已弃用，请使用 UnifiedDatabaseManager")
        super().__init__()


class NewDatabaseManager(UnifiedDatabaseManager):
    """兼容原 new_database.py 的类名"""

    def __init__(self, db_path=None):
        print("⚠️ NewDatabaseManager 已弃用，请使用 UnifiedDatabaseManager")
        # 忽略传入的 db_path，使用 config.py 中的路径
        super().__init__()