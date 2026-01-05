"""
数据库处理模块
"""

from datetime import datetime
from flask import jsonify
from backend.utils.constants import DATABASE_PATH
from backend.models.unified_db import NewDatabaseManager


def load_processing_history():
    """查询所有表格处理历史记录"""
    try:
        from backend.utils.constants import DATABASE_PATH
        db_handler = NewDatabaseManager(DATABASE_PATH)
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
            db_handler = NewDatabaseManager(DATABASE_PATH)
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
