"""
WebSocket 实时通信路由
"""

import time
import asyncio
import json
import logging
from flask import Blueprint
from flask_sock import Sock

# 创建蓝图和WebSocket扩展
websocket_bp = Blueprint('websocket', __name__)
sock = Sock()

# 存储活跃的WebSocket连接
ACTIVE_CONNECTIONS = {}

logger = logging.getLogger(__name__)


def init_websocket(app):
    """初始化WebSocket"""
    sock.init_app(app)


# 存储等待连接的任务
WAITING_TASKS = {}


def close_websocket_connection(task_id):
    """主动关闭WebSocket连接"""
    try:
        if task_id in ACTIVE_CONNECTIONS:
            ws = ACTIVE_CONNECTIONS[task_id]
            # 发送关闭消息
            ws.send(json.dumps({
                "type": "close_connection",
                "task_id": task_id,
                "message": "任务处理完成，连接关闭"
            }))
            # 实际关闭连接
            ws.close()
            logger.info(f"🔒 主动关闭WebSocket连接 - 任务ID: {task_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"关闭WebSocket连接失败: {str(e)}")
        return False


# 在 websocket_routes.py 中
def notify_task_completion(task_id, data):
    """通知任务完成"""
    try:
        from . import ACTIVE_CONNECTIONS  # 导入全局连接字典

        if task_id in ACTIVE_CONNECTIONS:
            ws = ACTIVE_CONNECTIONS[task_id]
            message = {
                "type": "task_completed",
                "task_id": task_id,
                "success": True,
                "data": data,
                "timestamp": time.time()
            }
            ws.send(json.dumps(message))
            print(f"✅ WebSocket任务完成通知已发送 - 任务ID: {task_id}")
        else:
            print(f"⚠️  WebSocket连接不存在，无法发送完成通知 - 任务ID: {task_id}")
    except Exception as e:
        print(f"❌ 发送WebSocket完成通知失败: {str(e)}")


def notify_task_error(task_id, error_message):
    """通知任务错误"""
    try:
        if task_id in ACTIVE_CONNECTIONS:
            ws = ACTIVE_CONNECTIONS[task_id]
            ws.send(json.dumps({
                "type": "task_error",
                "task_id": task_id,
                "status": "error",
                "error": error_message
            }))
            logger.info(f"📨 已发送任务错误通知 - 任务ID: {task_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"发送任务错误通知失败: {str(e)}")
        return False


@sock.route('/ws/task-status/<task_id>')
def handle_task_status(ws, task_id):
    """处理任务状态WebSocket连接"""
    try:
        # 存储连接
        ACTIVE_CONNECTIONS[task_id] = ws
        logger.info(f"🔗 WebSocket连接建立 - 任务ID: {task_id}")

        # 立即发送连接确认
        try:
            ws.send(json.dumps({
                "type": "connection_established",
                "task_id": task_id,
                "message": "WebSocket连接已建立"
            }))
        except Exception as send_error:
            logger.error(f"发送连接确认失败: {send_error}")
            return

        print(f"**************** WebSocket连接建立成功 - 任务ID: {task_id}")

        # 简化消息处理循环
        while True:
            try:
                message = ws.receive(timeout=10)  # 10秒超时
                if message:
                    try:
                        data = json.loads(message)
                        message_type = data.get('type')

                        if message_type == 'ping':
                            ws.send(json.dumps({"type": "pong"}))
                        elif message_type == 'close':
                            logger.info(f"📨 收到客户端关闭请求 - 任务ID: {task_id}")
                            break
                    except json.JSONDecodeError:
                        logger.warning(f"收到非JSON消息: {message}")
                        continue

            except Exception as e:
                if "timed out" in str(e):
                    continue  # 超时是正常的，继续循环
                else:
                    logger.error(f"WebSocket接收消息异常: {str(e)}")
                    break

        print(f"**==========** WebSocket连接正常结束 - 任务ID: {task_id}")

    except Exception as e:
        logger.error(f"WebSocket处理异常: {str(e)}")
    finally:
        # 清理连接
        if task_id in ACTIVE_CONNECTIONS:
            del ACTIVE_CONNECTIONS[task_id]
        logger.info(f"🔗 WebSocket连接关闭 - 任务ID: {task_id}")






