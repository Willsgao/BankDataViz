"""
进度管理模块
"""
from datetime import datetime
from flask import jsonify


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

    def get_progress(self, job_id):
        """获取任务进度"""
        return jsonify(self.PROGRESS.get(job_id, {"state": "unknown", "percent": 0}))

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

    def get_table_progress(self, job_id):
        """查询表格处理任务状态"""
        if job_id not in self.TABLE_PROCESSING_JOBS:
            return jsonify({
                "success": False,
                "error": "任务不存在或已过期",
                "job_id": job_id
            }), 404

        job_info = self.TABLE_PROCESSING_JOBS[job_id]
        progress = job_info.get("progress", 0)
        if job_info["status"] == "completed":
            progress = 100
        elif job_info["status"] == "failed":
            progress = 0

        return jsonify({
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
        })

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

    def cleanup_old_jobs(self):
        """清理表格处理任务（仅用于开发调试）"""
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

            return jsonify({
                "success": True,
                "message": f"清理了 {len(jobs_to_remove)} 个旧任务",
                "remaining_jobs": len(self.TABLE_PROCESSING_JOBS)
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"清理失败: {str(e)}"
            }), 500