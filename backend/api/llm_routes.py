# -*- coding:utf-8 -*-
"""
LLM 表格识别 API 路由 - 重构后主文件
"""

import time
import uuid
import asyncio
import logging
from flask import Blueprint, request, jsonify, send_from_directory


# 创建蓝图
llm_bp = Blueprint('llm', __name__)
logger = logging.getLogger(__name__)


from backend.llm_services.connection_service import (
    _test_connection_internal,
    get_available_models,
    health_check_internal,
    check_llm_config
)

from backend.llm_services.config_service import (
    configure_llm,
    get_processor_status
)

from backend.llm_services.single_table_service import (
    _process_single_image,
    _process_non_financial_table,
    _process_single_non_financial_table,
    recognize_table_internal
)

from backend.llm_services.batch_processing_service import (
    _batch_process_images_sync,
    _batch_process_images,
    _handle_batch_process
)

from backend.llm_services.excel_service import (
    check_excel_internal,
    get_excel_data_internal,
    get_excel_content_internal,
    serve_excel_data
)

from backend.llm_services.task_management_service import (
    _send_websocket_notification,
    _force_send_completion_notification,
    get_processing_status,
    cleanup_tasks,
    get_task_result,
    TASK_RESULTS,
    PROCESSING_STATUS
)

from backend.llm_services.utils import (
    validate_required_params,
    convert_to_excel_url
)


# 路由定义部分保持不变，只是函数实现移到服务模块
@llm_bp.route('/llm/test-connection', methods=['POST'])
def test_connection():
    """测试LLM连接"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "请求体不能为空"}), 400

        result = asyncio.run(_test_connection_internal(data))
        return jsonify(result)
    except Exception as e:
        logger.error(f"测试连接错误: {str(e)}")
        return jsonify({"success": False, "error": f"测试连接错误: {str(e)}"}), 500

# ... 其他路由定义保持不变，只是调用对应的服务函数 ...
# 连接相关路由
@llm_bp.route('/llm/available-models', methods=['GET'])
def get_available_models_route():
    """获取可用的模型列表"""
    result = get_available_models()
    return jsonify(result)

@llm_bp.route('/llm/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    result = health_check_internal()
    return jsonify(result)

# 配置相关路由
@llm_bp.route('/llm/configure', methods=['POST'])
def configure_llm_route():
    """配置LLM参数"""
    data = request.get_json()
    result = configure_llm(data)
    return jsonify(result)

@llm_bp.route('/llm/status', methods=['GET'])
def get_processor_status_route():
    """获取处理器状态"""
    result = get_processor_status()
    return jsonify(result)

# 表格处理路由
@llm_bp.route('/llm/recognize-table', methods=['POST'])
def recognize_table():
    """识别表格并保存到指定路径"""
    return recognize_table_internal()


# Excel相关路由
@llm_bp.route('/llm/check-excel', methods=['GET'])
def check_excel():
    """检查Excel文件是否存在"""
    file_path = request.args.get('path')
    result = check_excel_internal(file_path)
    return jsonify(result)

@llm_bp.route('/llm/get-excel-data', methods=['GET'])
def get_excel_data():
    """读取Excel文件内容并返回给前端"""
    excel_url = request.args.get('url')
    result = get_excel_data_internal(excel_url)
    return jsonify(result)

@llm_bp.route('/excel-data/<path:excel_path>')
def serve_excel_data_route(excel_path):
    """提供Excel文件数据访问"""
    return serve_excel_data(excel_path)

@llm_bp.route('/llm/get-excel-content', methods=['GET'])
def get_excel_content():
    """读取Excel文件内容并返回结构化数据"""
    excel_url = request.args.get('excel_url')
    result = get_excel_content_internal(excel_url)
    return jsonify(result)

# 任务管理路由
@llm_bp.route('/llm/processing-status/<task_id>', methods=['GET'])
def get_processing_status_route(task_id):
    """获取处理状态"""
    result = get_processing_status(task_id)
    return jsonify(result)

@llm_bp.route('/llm/cleanup-tasks', methods=['POST'])
def cleanup_tasks_route():
    """清理过期任务"""
    result = cleanup_tasks()
    return jsonify(result)

@llm_bp.route('/llm/task-result/<task_id>', methods=['GET'])
def get_task_result_route(task_id):
    """查询任务结果"""
    result = get_task_result(task_id)
    return jsonify(result)


# 配置检查路由
@llm_bp.route('/llm/check-config', methods=['GET'])
def check_llm_config_route():
    """检查LLM配置状态"""
    result = check_llm_config()
    return jsonify(result)


# 表格处理路由
@llm_bp.route('/llm/process-image', methods=['POST'])
def process_table_image():
    """处理单张表格图片"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
                "message": "请求体不能为空"
            }), 400

        # 调用对应的服务函数
        print("单张图片:", )
        result = asyncio.run(_process_single_image(data))
        print("单张图片result:", result)
        return jsonify(result)
    except Exception as e:
        logger.error(f"处理表格图片错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"处理表格图片错误: {str(e)}",
            "message": f"处理异常: {str(e)}"
        }), 500

@llm_bp.route('/llm/process-non-financial-table', methods=['POST'])
def process_non_financial_table():
    """处理普通表格"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
                "message": "请求体不能为空"
            }), 400

        # 调用对应的服务函数
        result = asyncio.run(_process_non_financial_table(data))
        return jsonify(result)
    except Exception as e:
        logger.error(f"处理普通表格错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"处理普通表格错误: {str(e)}",
            "message": f"处理异常: {str(e)}"
        }), 500

# 批量处理路由
@llm_bp.route('/llm/batch-process', methods=['POST'])
def batch_process_images_route():
    """批量处理图片 - 立即返回任务ID"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        # 强制设置表格类型
        data['table_type'] = 'financial'
        print(f"🔄 金融表格批量处理 - 图片数量: {len(data.get('image_paths', []))}")

        # 立即生成任务ID并返回
        task_id = str(uuid.uuid4())

        # 启动异步处理（不阻塞当前请求）
        import threading
        def run_async():
            try:
                _batch_process_images_sync(data, task_id)
            except Exception as e:
                logger.error(f"异步处理异常: {str(e)}")

        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()

        print(f"🎯 立即返回任务ID: {task_id}")

        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "批量处理任务已开始，请等待WebSocket通知",
            "status": "started"
        })

    except Exception as e:
        logger.error(f"批量处理错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"批量处理错误: {str(e)}"
        }), 500

@llm_bp.route('/llm/batch-process-non-financial', methods=['POST'])
def batch_process_non_financial_images_route():
    """批量处理普通表格 - 同步处理"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        # 强制设置表格类型
        data['table_type'] = 'non_financial'
        print(f"🔄 普通表格批量处理 - 图片数量: {len(data.get('image_paths', []))}")

        # 立即生成任务ID并返回
        task_id = str(uuid.uuid4())

        # ⭐⭐⭐ 同步调用 ⭐⭐⭐
        _batch_process_images_sync(data, task_id)

        print(f"🎯 同步处理完成，任务ID: {task_id}")

        # 返回处理结果状态
        status = PROCESSING_STATUS.get(task_id, {})
        if status.get('status') == 'completed':
            return jsonify({
                "success": True,
                "task_id": task_id,
                "data": {
                    "total": status.get('total', 0),
                    "success": status.get('success_count', 0),
                    "failed": status.get('failed_count', 0),
                    "excel_url": status.get('excel_url'),
                    "table_type": 'non_financial'
                },
                "message": "批量处理完成",
                "status": "completed"
            })
        else:
            return jsonify({
                "success": False,
                "task_id": task_id,
                "error": status.get('message', '处理失败'),
                "status": "error"
            })

    except Exception as e:
        logger.error(f"普通表格批量处理错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"普通表格批量处理错误: {str(e)}"
        }), 500

@llm_bp.route('/llm/batch-process', methods=['POST'], endpoint='batch_process_financial')
def batch_process_financial_images_route():
    """批量处理金融表格"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        data['table_type'] = 'financial'
        image_count = len(data.get('image_paths', []))
        print(f"🔵 金融表格批量处理 - 图片数量: {image_count}")

        # ⭐⭐⭐ 只创建一个任务ID ⭐⭐⭐
        task_id = str(uuid.uuid4())
        print(f"🎯 创建任务ID: {task_id}")

        # 在后台线程中处理，避免阻塞请求
        import threading
        def process_in_background():
            try:
                # ⭐⭐⭐ 传递相同的任务ID ⭐⭐⭐
                _batch_process_images_sync(data, task_id)
                print(f"✅ 后台处理完成 - 任务ID: {task_id}")
            except Exception as e:
                print(f"❌ 后台处理异常: {str(e)}")
                # 即使异常也要更新状态
                TASK_RESULTS[task_id] = {
                    "status": "error",
                    "error": f"处理异常: {str(e)}",
                    "completed_at": time.time()
                }

        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()

        # 立即返回响应，不等待处理完成
        print(f"🎯 立即返回响应，任务ID: {task_id}")

        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "批量处理任务已开始",
            "status": "started",
            "image_count": image_count,
            "processing_started": True
        })

    except Exception as e:
        logger.error(f"金融表格批量处理错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"金融表格批量处理错误: {str(e)}"
        }), 500