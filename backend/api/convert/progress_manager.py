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

    def update_table_job_old(self, job_id, updates):
        """更新表格处理任务状态"""
        if job_id in self.TABLE_PROCESSING_JOBS:
            self.TABLE_PROCESSING_JOBS[job_id].update(updates)
            # 自动保存到数据库
            self.save_table_job_to_db(job_id)
            return True
        return False

    # 在 progress_manager.py 的 update_table_job 方法中修改
    def update_table_job(self, job_id, updates):
        """更新表格处理任务状态 - 同步到Redis"""
        if job_id in self.TABLE_PROCESSING_JOBS:
            # 1. 更新内存中的任务状态
            self.TABLE_PROCESSING_JOBS[job_id].update(updates)

            # 2. 保存到数据库
            db_success = self.save_table_job_to_db(job_id)

            # 3. ✅ 新增：同步到Redis
            redis_success = self.save_table_job_to_redis(job_id)

            if db_success and redis_success:
                return True
            else:
                print(f"⚠️ 进度更新部分失败: 数据库={db_success}, Redis={redis_success}")
                return False
        return False

    def save_table_job_to_redis(self, job_id):
        """保存任务状态到Redis"""
        if job_id not in self.TABLE_PROCESSING_JOBS:
            return False

        try:
            from backend.utils.redis_util import redis_hset_compatible, get_redis_client

            # 获取Redis客户端
            redis_client = get_redis_client()
            if not redis_client:
                print("⚠️ Redis客户端获取失败")
                return False

            # 获取任务信息
            job_info = self.TABLE_PROCESSING_JOBS[job_id]

            # 准备Redis更新数据
            redis_updates = {
                "status": job_info.get("status", "unknown"),
                "progress": str(job_info.get("progress", 0)),
                "message": job_info.get("message", ""),
                "stage": job_info.get("stage", "unknown"),
                "total_images": str(job_info.get("total_images", 0)),
                "processed_images": str(job_info.get("processed_images", 0)),
                "updated_at": datetime.now().isoformat()
            }

            # 添加可选字段
            if "current_image" in job_info:
                redis_updates["current_image"] = job_info["current_image"]

            if "bank_name" in job_info:
                redis_updates["bank_name"] = job_info["bank_name"]

            if "error" in job_info and job_info["error"]:
                redis_updates["error"] = job_info["error"]

            # 更新到Redis
            success = redis_hset_compatible(
                redis_client,
                f"table:job:{job_id}",
                redis_updates
            )

            if success:
                # 设置过期时间（24小时）
                redis_client.expire(f"table:job:{job_id}", 24 * 60 * 60)
                return True
            else:
                return False

        except Exception as e:
            print(f"❌ 保存任务到Redis失败: {e}")
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