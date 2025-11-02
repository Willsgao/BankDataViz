

import json
import time
import asyncio
import logging

from flask import jsonify
from pathlib import Path
from flask import Blueprint

from backend.schemas.table_schemas import ExcelSaveConfig
from backend.service.table_llm_service import get_table_processor
from backend.service.non_financial_table_service import NonFinancialTableService

TASK_RESULTS = {}

# 创建蓝图
llm_bp = Blueprint('llm', __name__)

# 设置日志
logger = logging.getLogger(__name__)


# 全局处理器实例
_table_processor_instance = None
_non_financial_table_service = None


# 在文件顶部添加全局状态存储
PROCESSING_STATUS = {}

# 单例实例
_non_financial_table_service = None

def get_non_financial_table_service():
    """获取普通表格服务单例实例"""
    global _non_financial_table_service

    if _non_financial_table_service is None:
        _non_financial_table_service = NonFinancialTableService()

    return _non_financial_table_service


def validate_required_params(data, required_fields):
    """验证必要参数"""
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return False, f"缺少必要参数: {', '.join(missing_fields)}"
    return True, None


# 金融表格处理
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




def _handle_batch_process(data, task_id):
    """统一的批量处理入口"""
    try:
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        # 添加调试信息
        table_type = data.get('table_type', 'unknown')
        print(f"🔄 批量处理入口 - 表格类型: {table_type}")

        result = asyncio.run(_batch_process_images(data, task_id))
        return jsonify(result)
    except Exception as e:
        logger.error(f"批量处理错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"批量处理错误: {str(e)}"
        }), 500


def convert_to_excel_url(file_path):
    """将文件路径转换为Excel URL"""
    file_path = file_path.replace('\\', '/')

    print(f"🔧 转换Excel路径: {file_path}")

    # 处理各种可能的路径格式
    if 'static/excel_data/' in file_path:
        # 提取相对路径部分
        parts = file_path.split('static/excel_data/')
        if len(parts) > 1:
            relative_path = parts[1]
            return f"/api/excel-data/{relative_path}"

    # 如果路径已经是相对路径
    if file_path.startswith('static/excel_data/'):
        relative_path = file_path.replace('static/excel_data/', '')
        return f"/api/excel-data/{relative_path}"

    # 回退方案：从路径中提取文件夹和文件名
    path_obj = Path(file_path)
    if path_obj.parts:
        # 查找 static/excel_data 在路径中的位置
        try:
            excel_data_index = path_obj.parts.index('static') + 1
            if excel_data_index < len(path_obj.parts):
                relative_parts = path_obj.parts[excel_data_index:]
                relative_path = '/'.join(relative_parts)
                return f"/api/excel-data/{relative_path}"
        except ValueError:
            pass

    # 最终回退：直接使用文件名
    file_name = Path(file_path).name
    folder_name = Path(file_path).parent.name
    return f"/api/excel-data/{folder_name}/{file_name}"

# 添加一个工具函数，根据表格类型获取合适的处理器
def get_appropriate_processor(table_type=None):
    """根据表格类型获取合适的处理器"""
    if table_type == 'non_financial' or _non_financial_table_service is not None:
        if _non_financial_table_service is not None:
            return _non_financial_table_service
        else:
            from backend.service.non_financial_table_service import get_non_financial_table_service
            return get_non_financial_table_service()
    else:
        if _table_processor_instance is not None:
            return _table_processor_instance
        else:
            from backend.service.table_llm_service import get_table_processor
            return get_table_processor()

