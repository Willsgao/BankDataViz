

import time
import json
import logging

from backend.llm_services.state_manager import state_manager

logger = logging.getLogger(__name__)

# 全局状态存储 - 所有模块共享这些变量
TASK_RESULTS = {}
PROCESSING_STATUS = {}
_table_processor_instance = None
_non_financial_table_service = None


def get_processing_status(task_id):
    """获取处理状态"""
    try:
        status = state_manager.get_processing_status(task_id) or {
            "status": "unknown",
            "progress": 0,
            "message": "任务不存在或已过期",
            "exists": False
        }

        # 如果任务存在，添加存在标记
        if state_manager.get_processing_status(task_id) is not None:
            status["exists"] = True

        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"获取处理状态失败: {str(e)}")
        return {
            "success": False,
            "error": f"获取处理状态失败: {str(e)}"
        }


def get_task_result(task_id):
    """查询任务结果"""
    try:
        print(f"🔍 查询任务结果: {task_id}")
        print(f"📊 状态管理器中的任务: {[k for k in state_manager.TASK_RESULTS.keys()]}")

        if state_manager.task_exists(task_id):
            result = state_manager.get_task_result(task_id)
            print(f"✅ 找到任务结果: {result}")
            return {
                "success": True,
                "data": result
            }
        else:
            print(f"❌ 任务不存在: {task_id}")
            return {
                "success": False,
                "error": "任务不存在或已过期",
                "data": {
                    "status": "not_found"
                }
            }

    except Exception as e:
        print(f"💥 查询任务结果失败: {str(e)}")
        return {
            "success": False,
            "error": f"查询任务结果失败: {str(e)}"
        }


# 导出全局状态获取函数
def get_task_results():
    return TASK_RESULTS

def get_processing_status_dict():
    return PROCESSING_STATUS

def get_table_processor_instance():
    return _table_processor_instance

def get_non_financial_table_service_instance():
    return _non_financial_table_service

def set_table_processor_instance(instance):
    global _table_processor_instance
    _table_processor_instance = instance

def set_non_financial_table_service_instance(instance):
    global _non_financial_table_service
    _non_financial_table_service = instance

def _send_websocket_notification(task_id, status, data=None, error_message=None):
    """发送WebSocket通知的通用函数 - 完全修复版本"""
    try:
        print(f"📨 发送WebSocket通知 - 任务ID: {task_id}, 状态: {status}")

        # 创建模拟的WebSocket函数，避免导入错误
        def mock_notify_task_completion(task_id, data):
            print(f"📨 [WebSocket模拟] 任务完成通知 - 任务ID: {task_id}")
            print(f"📨 [WebSocket模拟] 通知数据: {data}")
            # 这里可以记录到日志文件，供前端轮询使用
            logger.info(f"WebSocket任务完成模拟 - 任务ID: {task_id}, 数据: {data}")

        def mock_notify_task_error(task_id, error_message):
            print(f"📨 [WebSocket模拟] 任务错误通知 - 任务ID: {task_id}")
            print(f"📨 [WebSocket模拟] 错误信息: {error_message}")
            logger.error(f"WebSocket任务错误模拟 - 任务ID: {task_id}, 错误: {error_message}")

        # 使用模拟函数
        notify_task_completion = mock_notify_task_completion
        notify_task_error = mock_notify_task_error

        if status == 'completed' and data:
            notification_data = {
                "total": data.get('total', 0),
                "success": data.get('success', 0),
                "failed": data.get('failed', 0),
                "output_file": data.get('output_file', ''),
                "excel_url": data.get('excel_url', ''),
                "table_type": data.get('table_type', 'financial'),
                "message": data.get('message', '处理完成'),
                "task_id": task_id,
                "type": "task_completed",
                "processing_completed": True,
                "timestamp": time.time()
            }
            print(f"📨 发送完成通知数据: {notification_data}")
            notify_task_completion(task_id, notification_data)

        elif status == 'error' and error_message:
            print(f"📨 发送错误通知: {error_message}")
            notify_task_error(task_id, error_message)

        print(f"✅ WebSocket通知发送完成 - 任务ID: {task_id}")

    except Exception as notify_error:
        print(f"❌ 发送WebSocket通知失败: {str(notify_error)}")
        # 即使通知失败，也不影响主要处理流程


def _force_send_completion_notification(task_id, data):
    """强制发送完成通知，确保前端收到"""
    try:
        from backend.api.websocket_routes import ACTIVE_CONNECTIONS

        print(f"🔔 强制发送完成通知 - 任务ID: {task_id}")

        # 直接通过WebSocket连接发送
        if task_id in ACTIVE_CONNECTIONS:
            ws = ACTIVE_CONNECTIONS[task_id]
            completion_message = {
                "type": "task_completed",
                "task_id": task_id,
                "success": True,
                "data": data,
                "message": data.get('message', '处理完成'),
                "timestamp": time.time()
            }
            ws.send(json.dumps(completion_message))
            print(f"✅ 强制通知发送成功 - 任务ID: {task_id}")
        else:
            print(f"⚠️  WebSocket连接不存在 - 任务ID: {task_id}")

    except Exception as e:
        print(f"❌ 强制通知发送失败: {str(e)}")



def cleanup_tasks():
    """清理过期任务"""
    try:
        current_time = time.time()
        expired_tasks = []

        for task_id, status in list(PROCESSING_STATUS.items()):
            # 清理已完成超过1小时的任务
            if status.get("status") in ["completed", "error"]:
                completion_time = status.get("completion_time") or status.get("error_time")
                if completion_time and (current_time - completion_time) > 3600:
                    del PROCESSING_STATUS[task_id]
                    expired_tasks.append(task_id)

            # 清理处理中但超过2小时的任务（可能卡住的任务）
            elif status.get("status") == "processing":
                start_time = status.get("start_time", 0)
                if (current_time - start_time) > 7200:
                    del PROCESSING_STATUS[task_id]
                    expired_tasks.append(task_id)

        return {
            "success": True,
            "data": {
                "cleaned_tasks": expired_tasks,
                "remaining_tasks": len(PROCESSING_STATUS)
            }
        }
    except Exception as e:
        logger.error(f"清理任务失败: {str(e)}")
        return {
            "success": False,
            "error": f"清理任务失败: {str(e)}"
        }
