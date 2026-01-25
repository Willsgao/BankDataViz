"""
进度管理模块
"""
from datetime import datetime

# 保存到数据库
from backend.utils.constants import DATABASE_PATH
# from backend.models.new_database import NewDatabaseManager
from backend.models.unified_db import NewDatabaseManager


class ProgressManager:
    """进度管理器"""

    def __init__(self):
        self.PROGRESS = {}
        self.TABLE_PROCESSING_JOBS = {}
        self.TABLE_PROCESSING_STAGES = {
            'pending': '等待处理',
            'ocr': 'OCR识别中',
            'llm': 'LLM分析中',
            'reconstruction': '表格重构中',
            'exporting': '导出Excel中',
            'completed': '处理完成',
            'failed': '处理失败'
        }

    def init_job(self, job_id):
        """初始化任务进度"""
        self.PROGRESS[job_id] = {"total": 0, "finished": 0, "percent": 0}

    def init_table_job(self, job_id, job_info):
        """初始化表格处理任务"""
        job_info.update({
            "status": "pending",
            "stage": "pending",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "processed_images": 0,
            "results": [],
            "error": None
        })
        self.TABLE_PROCESSING_JOBS[job_id] = job_info

    def update_table_job(self, job_id, updates):
        """更新表格处理任务状态"""
        if job_id in self.TABLE_PROCESSING_JOBS:
            self.TABLE_PROCESSING_JOBS[job_id].update(updates)
            # 自动保存到数据库
            self.save_table_job_to_db(job_id)
            return True
        return False

    def save_table_job_to_db(self, job_id):
        """保存任务状态到数据库"""
        if job_id not in self.TABLE_PROCESSING_JOBS:
            return False

        job_info = self.TABLE_PROCESSING_JOBS[job_id].copy()
        job_info['job_id'] = job_id

        try:
            db_handler = NewDatabaseManager(DATABASE_PATH)
            db_handler.save_table_processing_record(job_info)
            return True
        except Exception as e:
            print(f"⚠️ 保存任务到数据库失败: {e}")
            return False

    def get_folder_tasks(self, pdf_folder):
        """获取文件夹的所有任务"""
        folder_tasks = []
        for job_id, job_info in self.TABLE_PROCESSING_JOBS.items():
            if job_info.get("pdf_folder") == pdf_folder:
                folder_tasks.append({
                    "job_id": job_id,
                    "status": job_info.get("status", "unknown"),
                    "stage": job_info.get("stage", "unknown"),
                    "progress": job_info.get("progress", 0),
                    "start_time": job_info.get("start_time"),
                    "end_time": job_info.get("end_time"),
                    "total_images": job_info.get("total_images", 0),
                    "processed_images": job_info.get("processed_images", 0),
                    "bank_name": job_info.get("bank_name", ""),
                    "summary": job_info.get("summary", {})
                })
        return folder_tasks

    def get_progress(self, job_id):
        """获取任务进度 - 返回数据，不返回响应"""

        # ✅ 改为返回数据
        return self.PROGRESS.get(job_id, {"state": "unknown", "percent": 0})

    def get_table_progress(self, job_id):
        """查询表格处理任务状态 - 返回数据，不返回响应"""
        if job_id not in self.TABLE_PROCESSING_JOBS:
            # ✅ 改为返回字典或None
            return None  # 或者 raise Exception("任务不存在")

        job_info = self.TABLE_PROCESSING_JOBS[job_id]
        progress = job_info.get("progress", 0)
        if job_info["status"] == "completed":
            progress = 100
        elif job_info["status"] == "failed":
            progress = 0

        # ✅ 返回纯数据字典
        return {
            "success": True,
            "job_id": job_id,
            "status": job_info["status"],
            "stage": job_info["stage"],
            "progress": progress,
            "data": {
                "pdf_folder": job_info.get("pdf_folder"),
                "total_images": job_info.get("total_images", 0),
                "processed_images": job_info.get("processed_images", 0),
                "bank_name": job_info.get("bank_name", ""),
                "start_time": job_info.get("start_time"),
                "end_time": job_info.get("end_time"),
                "error": job_info.get("error")
            }
        }

    def cleanup_old_jobs(self):
        """清理表格处理任务 - 返回数据，不返回响应"""
        try:
            now = datetime.now()
            jobs_to_remove = []

            for job_id, job_info in self.TABLE_PROCESSING_JOBS.items():
                if job_info.get("status") in ["completed", "failed"]:
                    end_time_str = job_info.get("end_time")
                    if end_time_str:
                        try:
                            end_time = datetime.fromisoformat(end_time_str)
                            if (now - end_time).total_seconds() > 3600:
                                jobs_to_remove.append(job_id)
                        except:
                            jobs_to_remove.append(job_id)

            for job_id in jobs_to_remove:
                del self.TABLE_PROCESSING_JOBS[job_id]

            # ✅ 返回数据字典
            return {
                "success": True,
                "message": f"清理了 {len(jobs_to_remove)} 个旧任务",
                "remaining_jobs": len(self.TABLE_PROCESSING_JOBS)
            }

        except Exception as e:
            # ✅ 返回错误数据
            return {
                "success": False,
                "error": f"清理失败: {str(e)}"
            }

    # ✅ 添加：获取单个任务信息（纯数据）
    def get_table_job_info(self, job_id):
        """获取表格任务信息（纯数据）"""
        if job_id not in self.TABLE_PROCESSING_JOBS:
            return None

        return self.TABLE_PROCESSING_JOBS[job_id]