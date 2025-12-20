"""
数据库处理模块
"""
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from flask import jsonify
from backend.utils.constants import DATABASE_PATH

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


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path):
        self.db_path = db_path

    def connect(self):
        """连接数据库"""
        from sqlite3 import Connection
        return Connection(self.db_path)

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


def load_processing_history():
    """查询所有表格处理历史记录"""
    try:
        from backend.utils.constants import DATABASE_PATH
        db_handler = DatabaseManager(DATABASE_PATH)
        records = db_handler.load_table_processing_records(limit=50)

        formatted_records = []
        for record in records:
            formatted_records.append({
                "job_id": record.get("job_id"),
                "pdf_folder": record.get("pdf_folder"),
                "bank_name": record.get("bank_name"),
                "status": record.get("status"),
                "stage": record.get("stage"),
                "progress": record.get("progress", 0),
                "total_images": record.get("total_images", 0),
                "success_count": record.get("success_count", 0),
                "failed_count": record.get("failed_count", 0),
                "start_time": record.get("start_time"),
                "end_time": record.get("end_time"),
                "duration": _calculate_duration(record.get("start_time"), record.get("end_time")),
                "excel_files": record.get("excel_files", []),
                "error_message": record.get("error_message")
            })

        return jsonify({
            "success": True,
            "data": {
                "records": formatted_records,
                "total": len(formatted_records),
                "stats": {
                    "total_tasks": len(formatted_records),
                    "completed": sum(1 for r in formatted_records if r["status"] == "completed"),
                    "processing": sum(1 for r in formatted_records if r["status"] == "processing"),
                    "failed": sum(1 for r in formatted_records if r["status"] == "failed")
                }
            }
        })
    except Exception as e:
        print(f"❌ 查询历史记录失败: {e}")
        return jsonify({
            "success": False,
            "error": f"查询失败: {str(e)}"
        }), 500


def _calculate_duration(start_time_str, end_time_str):
    """计算处理时长"""
    if not start_time_str or not end_time_str:
        return "未知"

    try:
        start = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        duration = end - start
        return f"{duration.total_seconds():.1f}秒"
    except:
        return "未知"


# 在 database_handler.py 末尾添加
def get_task_detail(job_id, progress_tracker):
    """
    查询单个任务详情
    """
    print(f"📋 查询任务详情 - Job ID: {job_id}")

    try:
        # 先从内存查找
        if job_id in progress_tracker.TABLE_PROCESSING_JOBS:
            task_detail = progress_tracker.TABLE_PROCESSING_JOBS[job_id].copy()
        else:
            # 从数据库查找
            db_handler = DatabaseManager(DATABASE_PATH)
            task_detail = db_handler.get_task_detail(job_id)
            if not task_detail:
                return jsonify({
                    "success": False,
                    "error": "任务不存在"
                }), 404

        # 清理敏感或过大字段
        if 'raw_result' in task_detail:
            # 可以选择性返回部分信息
            del task_detail['raw_result']

        return jsonify({
            "success": True,
            "job_id": job_id,
            "data": task_detail
        })
    except Exception as e:
        print(f"❌ 查询任务详情失败: {e}")
        return jsonify({
            "success": False,
            "error": f"查询失败: {str(e)}"
        }), 500
