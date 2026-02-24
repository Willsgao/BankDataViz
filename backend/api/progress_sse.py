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

        return {
            "job_id": job_id,
            "status": status,
            "progress": int(progress) if progress.isdigit() else 0,
            "message": message,
            "total_images": int(total_images) if total_images.isdigit() else 0,
            "processed_images": int(processed_images) if processed_images.isdigit() else 0
        }
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

# 在app_factory.py中注册此蓝图
