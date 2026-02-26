# backend/api/progress_sse.py
from flask import Blueprint, Response, stream_with_context, jsonify
import json
import time
import redis

progress_sse_bp = Blueprint('progress_sse', __name__)


def get_progress_from_redis(job_id):
    """从Redis获取进度信息"""
    try:
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

        if not redis_client.exists(f"table:job:{job_id}"):
            return None

        status = redis_client.hget(f"table:job:{job_id}", "status") or "unknown"
        progress = redis_client.hget(f"table:job:{job_id}", "progress") or "0"
        message = redis_client.hget(f"table:job:{job_id}", "message") or ""
        total_images = redis_client.hget(f"table:job:{job_id}", "total_images") or "0"
        processed_images = redis_client.hget(f"table:job:{job_id}", "processed_images") or "0"

        # ✅ 添加 skipped_images 的读取
        skipped_images = redis_client.hget(f"table:job:{job_id}", "skipped_images") or "0"

        result =  {
            "job_id": job_id,
            "status": status,
            "progress": int(progress) if progress.isdigit() else 0,
            "message": message,
            "total_images": int(total_images) if total_images.isdigit() else 0,
            "processed_images": int(processed_images) if processed_images.isdigit() else 0,
            "skipped_images": int(skipped_images) if skipped_images.isdigit() else 0  # ✅ 新增字段
        }
        print(">>>>>>>>>>>>>>>>result-->:", result)
        return result
    except Exception as e:
        print(f"❌ 查询Redis进度失败: {e}")
        return None


@progress_sse_bp.route('/api/table-progress-sse/<job_id>')
def table_progress_sse(job_id):
    """
    SSE进度流端点
    客户端通过EventSource连接此端点获取实时进度
    """

    def generate():
        last_progress = None

        while True:
            try:
                # 从Redis获取当前进度
                current_progress = get_progress_from_redis(job_id)

                if not current_progress:
                    # 任务不存在
                    yield f"data: {json.dumps({'error': '任务不存在'})}\n\n"
                    break

                # 只在进度变化时发送
                if current_progress != last_progress:
                    yield f"data: {json.dumps(current_progress)}\n\n"
                    last_progress = current_progress

                # 任务完成或失败时结束流
                if current_progress['status'] in ['completed', 'failed']:
                    print(f"✅ 任务{job_id}完成，关闭SSE连接")
                    break

                # 等待1秒后继续检查
                time.sleep(1)

            except Exception as e:
                print(f"❌ SSE流生成异常: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@progress_sse_bp.route('/api/all-tasks-progress')
def all_tasks_progress_sse():
    """
    SSE推送所有表格处理任务的实时进度
    用于前端进度监控弹窗
    """

    def generate():
        import json
        import time

        while True:
            try:
                # 获取所有任务
                redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True
                )

                # 1. 获取所有表格任务
                tasks = []
                task_keys = redis_client.keys("table:job:*")

                for key in task_keys[:50]:  # 限制数量防止性能问题
                    try:
                        job_id = key.replace("table:job:", "")
                        task_data = redis_client.hgetall(key)

                        if task_data:
                            task_data['job_id'] = job_id
                            task_data['timestamp'] = time.time()
                            tasks.append(task_data)

                    except Exception as e:
                        print(f"⚠️ 处理任务键 {key} 失败: {e}")

                # 2. 获取PDF级状态
                pdf_tasks = []
                pdf_keys = redis_client.keys("pdf:*:current_status")

                for key in pdf_keys[:20]:
                    try:
                        pdf_folder = key.replace("pdf:", "").replace(":current_status", "")
                        pdf_data = redis_client.hgetall(key)

                        if pdf_data:
                            pdf_data['pdf_folder'] = pdf_folder
                            pdf_data['status_type'] = 'pdf_level'
                            pdf_data['timestamp'] = time.time()
                            pdf_tasks.append(pdf_data)

                    except Exception as e:
                        print(f"⚠️ 处理PDF键 {key} 失败: {e}")

                # 3. 合并任务列表
                all_tasks = tasks + pdf_tasks

                # 4. 推送数据
                data = {
                    "type": "all_tasks_update",
                    "timestamp": time.time(),
                    "total": len(all_tasks),
                    "tasks": all_tasks
                }

                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            except Exception as e:
                print(f"❌ 生成所有任务进度失败: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            time.sleep(3)  # 3秒推送一次

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@progress_sse_bp.route('/api/active-tasks')
def get_active_tasks():
    """
    获取所有活跃任务的快照（非SSE）
    用于前端打开弹窗时一次性获取
    """
    try:
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

        # 获取所有任务
        tasks = []
        task_keys = redis_client.keys("table:job:*")

        for key in task_keys[:100]:  # 限制100个任务
            try:
                job_id = key.replace("table:job:", "")
                task_data = redis_client.hgetall(key)

                if task_data:
                    task_data['job_id'] = job_id
                    tasks.append(task_data)

            except Exception as e:
                print(f"⚠️ 处理任务键 {key} 失败: {e}")

        # 按时间排序（最新的在前）
        tasks.sort(key=lambda x: float(x.get('timestamp', 0) or x.get('created_at', 0)), reverse=True)

        # 统计摘要
        summary = {
            "total": len(tasks),
            "processing": 0,
            "queued": 0,
            "completed": 0,
            "failed": 0
        }

        for task in tasks:
            status = task.get('status', 'unknown')
            if status in ['processing', 'running']:
                summary['processing'] += 1
            elif status == 'queued':
                summary['queued'] += 1
            elif status in ['completed', 'success']:
                summary['completed'] += 1
            elif status in ['failed', 'exception']:
                summary['failed'] += 1

        return jsonify({
            "success": True,
            "tasks": tasks,
            "summary": summary,
            "timestamp": time.time()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# 在app_factory.py中注册此蓝图
