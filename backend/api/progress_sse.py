# backend/api/progress_sse.py
from flask import Blueprint, Response, stream_with_context, jsonify
import json
import time
import redis

progress_sse_bp = Blueprint('progress_sse', __name__)


def get_progress_from_redis(job_id):
    """从Redis获取进度信息 - 完整版本"""
    try:
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

        redis_key = f"table:job:{job_id}"
        if not redis_client.exists(redis_key):
            return None

        # ✅ 获取所有字段
        all_fields = redis_client.hgetall(redis_key)

        # ✅ 定义需要读取的所有字段
        field_mappings = {
            # 基本字段
            "job_id": job_id,
            "status": all_fields.get("status", "unknown"),
            "progress": all_fields.get("progress", "0"),
            "message": all_fields.get("message", ""),

            # 文件信息字段
            "original_filename": all_fields.get("original_filename", ""),
            "pdf_folder": all_fields.get("pdf_folder", ""),
            "pdf_disk_name": all_fields.get("pdf_disk_name", ""),

            # 时间字段
            "started_at": all_fields.get("started_at", ""),
            "completed_at": all_fields.get("completed_at", ""),
            "timestamp": all_fields.get("timestamp", ""),
            "last_updated": all_fields.get("last_updated", ""),

            # 图片统计字段
            "total_images": all_fields.get("total_images", "0"),
            "processed_images": all_fields.get("processed_images", "0"),
            "skipped_images": all_fields.get("skipped_images", "0"),
            "failed_images": all_fields.get("failed_images", "0"),

            # 其他元数据
            "worker_id": all_fields.get("worker_id", ""),
            "db_filename": all_fields.get("db_filename", ""),
            "db_query_success": all_fields.get("db_query_success", ""),
            "task_start_time": all_fields.get("task_start_time", "")
        }

        # ✅ 转换数字字段
        for field in ["progress", "total_images", "processed_images", "skipped_images", "failed_images"]:
            if field in field_mappings and field_mappings[field].isdigit():
                field_mappings[field] = int(field_mappings[field])

        # ✅ 添加调试
        print(f"🔍 Redis读取结果:")
        print(f"  - job_id: {job_id}")
        print(f"  - original_filename: {field_mappings.get('original_filename')}")
        print(f"  - started_at: {field_mappings.get('started_at')}")
        print(f"  - 总字段数: {len(field_mappings)}")

        return field_mappings

    except Exception as e:
        print(f"❌ 查询Redis进度失败: {e}")
        return None


@progress_sse_bp.route('/api/table-progress-sse/<job_id>')
def table_progress_sse(job_id):
    """
    SSE进度流端点 - 使用Redis Pub/Sub实现实时推送
    客户端通过EventSource连接此端点获取实时进度
    """
    
    channel_name = f"table:progress:{job_id}"
    
    def generate():
        pubsub = None
        redis_client = None
        last_progress_str = ""
        
        try:
            # 创建独立的Redis连接用于Pub/Sub
            redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_keepalive=True,
                socket_timeout=30
            )
            
            # 创建Pub/Sub客户端
            pubsub = redis_client.pubsub()
            
            # 订阅进度频道
            pubsub.subscribe(channel_name)
            print(f"📡 已订阅频道: {channel_name}")
            
            # 首先从Redis Hash获取初始状态
            initial_progress = get_progress_from_redis(job_id)
            if initial_progress:
                # 发送初始状态
                progress_str = json.dumps(initial_progress, ensure_ascii=False)
                yield f"data: {progress_str}\n\n"
                last_progress_str = progress_str
                print(f"📤 发送初始进度: {initial_progress.get('progress', 0)}%")
                
                # 如果已完成，直接退出
                if initial_progress.get('status') in ['completed', 'failed', 'success']:
                    print(f"✅ 任务已完成，直接退出")
                    return
            else:
                # 任务还不存在，发送错误信息并等待
                yield f"data: {json.dumps({'error': '任务不存在或正在创建', 'waiting': True})}\n\n"
            
            # 设置超时时间（秒）
            timeout_seconds = 60
            start_time = time.time()
            last_message_time = time.time()
            
            # 监听Pub/Sub消息
            for message in pubsub.listen():
                try:
                    # 检查超时
                    if time.time() - start_time > timeout_seconds:
                        print(f"⏱️ SSE连接超时 ({timeout_seconds}秒)")
                        yield f"data: {json.dumps({'error': '连接超时', 'timeout': True})}\n\n"
                        break
                    
                    if message['type'] == 'message':
                        # 解析消息
                        data = json.loads(message['data'])
                        print(f"📥 收到Pub/Sub消息: {data}")
                        
                        # 提取进度数据
                        progress_data = data.get('data') if isinstance(data, dict) else data
                        if not progress_data:
                            progress_data = data
                        
                        # 转换为JSON字符串
                        progress_str = json.dumps(progress_data, ensure_ascii=False)
                        
                        # 只有进度变化时才发送（避免重复发送相同数据）
                        if progress_str != last_progress_str:
                            yield f"data: {progress_str}\n\n"
                            last_progress_str = progress_str
                            last_message_time = time.time()
                            
                            # 检查任务是否完成
                            status = progress_data.get('status', '')
                            if status in ['completed', 'failed', 'success']:
                                print(f"✅ 任务{job_id}完成，状态: {status}")
                                break
                    elif message['type'] == 'subscribe':
                        print(f"📡 订阅确认: {message['channel']}")
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ 消息解析失败: {e}")
                except Exception as e:
                    print(f"⚠️ 处理消息异常: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    break
            
            print(f"📴 SSE连接结束")
            
        except Exception as e:
            print(f"❌ SSE流生成异常: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        finally:
            # 清理资源
            try:
                if pubsub:
                    pubsub.unsubscribe()
                    pubsub.close()
                    print(f"🧹 已清理Pub/Sub连接")
                if redis_client:
                    redis_client.close()
            except Exception as e:
                print(f"⚠️ 清理连接异常: {e}")

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
    使用Pub/Sub实现实时推送 - 订阅全局进度频道
    """
    
    def generate():
        pubsub = None
        redis_client = None
        
        try:
            # 创建独立的Redis连接
            redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_keepalive=True,
                socket_timeout=30
            )
            
            # 创建Pub/Sub客户端
            pubsub = redis_client.pubsub()
            
            # 订阅全局进度频道（当有任何任务更新时，会收到通知）
            pubsub.subscribe('table:progress:all')
            print("📡 已订阅全局进度频道: table:progress:all")
            
            # 首先立即发送一次当前所有任务的状态
            try:
                tasks = []
                task_keys = redis_client.keys("table:job:*")
                
                for key in task_keys[:50]:
                    try:
                        job_id = key.replace("table:job:", "")
                        task_data = redis_client.hgetall(key)
                        
                        if task_data:
                            task_data['job_id'] = job_id
                            task_data['timestamp'] = time.time()
                            tasks.append(task_data)
                    except Exception as e:
                        print(f"⚠️ 处理任务键 {key} 失败: {e}")
                
                # 获取PDF级状态
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
                
                all_tasks = tasks + pdf_tasks
                
                # 统计摘要
                summary = {
                    "total": len(all_tasks),
                    "processing": 0,
                    "queued": 0,
                    "completed": 0,
                    "failed": 0
                }
                
                for task in all_tasks:
                    status = task.get('status', 'unknown')
                    if status in ['processing', 'running']:
                        summary['processing'] += 1
                    elif status == 'queued':
                        summary['queued'] += 1
                    elif status in ['completed', 'success']:
                        summary['completed'] += 1
                    elif status in ['failed', 'exception']:
                        summary['failed'] += 1
                    elif status in ['pending', 'starting', 'generating_excel', '']:
                        summary['processing'] += 1
                
                # 发送初始数据
                data = {
                    "type": "all_tasks_update",
                    "timestamp": time.time(),
                    "total": len(all_tasks),
                    "tasks": all_tasks,
                    "summary": summary
                }
                
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                print(f"📤 发送初始任务列表: {len(all_tasks)} 个任务")
                
            except Exception as e:
                print(f"⚠️ 获取初始任务列表失败: {e}")
            
            # 设置超时时间（秒）
            timeout_seconds = 300  # 5分钟超时
            start_time = time.time()
            last_update_time = time.time()
            
            # 监听Pub/Sub消息
            for message in pubsub.listen():
                try:
                    # 检查超时
                    if time.time() - start_time > timeout_seconds:
                        print(f"⏱️ SSE连接超时 ({timeout_seconds}秒)")
                        yield f"data: {json.dumps({'error': '连接超时', 'timeout': True})}\n\n"
                        break
                    
                    if message['type'] == 'message':
                        print(f"📥 收到全局进度更新通知")
                        
                        # 收到通知后，立即获取所有任务数据
                        tasks = []
                        task_keys = redis_client.keys("table:job:*")
                        
                        for key in task_keys[:50]:
                            try:
                                job_id = key.replace("table:job:", "")
                                task_data = redis_client.hgetall(key)
                                
                                if task_data:
                                    task_data['job_id'] = job_id
                                    task_data['timestamp'] = time.time()
                                    tasks.append(task_data)
                            except Exception as e:
                                pass
                        
                        # 获取PDF级状态
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
                                pass
                        
                        all_tasks = tasks + pdf_tasks
                        
                        # 统计摘要
                        summary = {
                            "total": len(all_tasks),
                            "processing": 0,
                            "queued": 0,
                            "completed": 0,
                            "failed": 0
                        }
                        
                        for task in all_tasks:
                            status = task.get('status', 'unknown')
                            if status in ['processing', 'running']:
                                summary['processing'] += 1
                            elif status == 'queued':
                                summary['queued'] += 1
                            elif status in ['completed', 'success']:
                                summary['completed'] += 1
                            elif status in ['failed', 'exception']:
                                summary['failed'] += 1
                            elif status in ['pending', 'starting', 'generating_excel', '']:
                                summary['processing'] += 1
                        
                        # 发送更新数据
                        data = {
                            "type": "all_tasks_update",
                            "timestamp": time.time(),
                            "total": len(all_tasks),
                            "tasks": all_tasks,
                            "summary": summary
                        }
                        
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        print(f"📤 推送任务更新: {len(all_tasks)} 个任务, 统计: {summary}")
                        last_update_time = time.time()
                        
                    elif message['type'] == 'subscribe':
                        print(f"📡 订阅确认: {message['channel']}")
                        
                except Exception as e:
                    print(f"⚠️ 处理消息异常: {e}")
            
            print(f"📴 SSE连接结束")
            
        except Exception as e:
            print(f"❌ SSE流生成异常: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        finally:
            # 清理资源
            try:
                if pubsub:
                    pubsub.unsubscribe()
                    pubsub.close()
                    print(f"🧹 已清理Pub/Sub连接")
                if redis_client:
                    redis_client.close()
            except Exception as e:
                print(f"⚠️ 清理连接异常: {e}")

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
            elif status in ['pending', 'starting', 'generating_excel', '']:
                # 正在处理中，归入处理中统计
                summary['processing'] += 1
            # unknown 或其他状态不统计，避免总数不一致

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
