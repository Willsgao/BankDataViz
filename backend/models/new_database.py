
import json
import sqlite3
from contextlib import closing
from pathlib import Path

# 表格处理记录表结构
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


class NewDatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path=None):
        from backend.configs.config import config
        self.db_path = db_path or config.DATABASE_PATH

    def connect(self):
        """连接数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # ✅ 必须设置这行！
        return conn

    def init_table_processing_db(self):
        """初始化表格处理数据库表"""
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(TABLE_PROCESSING_RECORDS_TABLE)
            conn.commit()
            print("✅ 表格处理记录表初始化完成")
            return True

    def save_table_processing_record(self, job_info):
        """保存表格处理记录到数据库"""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
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
