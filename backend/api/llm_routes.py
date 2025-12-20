# -*- coding:utf-8 -*-
"""
LLM 表格识别 API 路由 - 重构后主文件
"""

import time
import uuid
import asyncio
import logging
from pathlib import Path
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
    recognize_table_internal
)

from backend.llm_services.batch_processing_service import (
    _batch_process_images_sync,
)

from backend.llm_services.excel_service import (
    check_excel_internal,
    get_excel_data_internal,
    get_excel_content_internal
)

from backend.llm_services.task_management_service import (
    get_processing_status,
    cleanup_tasks,
    get_task_result,
)


from backend.utils.constants import EXCEL_DATA_DIR, STATIC_DIR

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




# 批量处理路由
@llm_bp.route('/llm/batch-process1', methods=['POST'])
def batch_process_images_route1():
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


import threading
@llm_bp.route('/llm/batch-process', methods=['POST'])
def batch_process_financial():
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    data['table_type'] = 'financial'
    task_id = str(uuid.uuid4())

    threading.Thread(target=_batch_process_images_sync, args=(data, task_id), daemon=True).start()
    print("🔍 后端返回任务ID:", task_id)
    return jsonify({"task_id": task_id}), 200


@llm_bp.route('/llm/batch-process-non-financial', methods=['POST'])
def batch_process_non_financial():
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    data['table_type'] = 'non_financial'
    task_id = str(uuid.uuid4())

    # 同步跑完（里面已 set_task_result）
    _batch_process_images_sync(data, task_id)

    # 立即拿结果
    result = get_task_result(task_id)
    if result["success"]:
        inner_data = result["data"]["data"]
        return_data = {
            "excel_url": inner_data.get("excel_url", ""),
            "from_cache": inner_data.get("from_cache", False),
            "table_type": "non_financial"
        }
        print(f"🚀 实际 return 结构: {return_data}")  # ← 新增
        return jsonify(return_data), 200

    else:
        return jsonify({"error": result.get("error", "处理失败")}), 500




# 修改单张图片处理函数
@llm_bp.route('/llm/process-image', methods=['POST'])
def process_table_image():
    """处理单张表格图片 - 添加Excel存在性检查"""
    print("处理金融表格1212123")
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
                "message": "请求体不能为空"
            }), 400

        # 提取参数
        image_path = data.get('image_path')
        output_path = data.get('output_path')
        sheet_name = data.get('sheet_name', 'Sheet1')
        bank_name = data.get('bank_name', '未知银行')

        # 检查Excel是否已存在
        excel_exists, final_excel_path = _check_excel_exists(image_path, output_path)

        if excel_exists:
            logger.info(f"Excel文件已存在，直接返回: {final_excel_path}")
            # 构建可访问的URL
            excel_url = f"/static/excel_data/{Path(final_excel_path).name}"

            return jsonify({
                "success": True,
                "from_cache": True,
                "excel_url": excel_url,
                "message": "已加载现有Excel文件",
                "file_path": final_excel_path
            })

        # 如果不存在，继续正常处理
        print("单张图片处理请求:", data)
        result = asyncio.run(_process_single_image(data))
        print("单张图片处理结果:", result)

        # 确保结果中包含from_cache字段
        if "from_cache" not in result:
            result["from_cache"] = False

        return jsonify(result)

    except Exception as e:
        logger.error(f"处理表格图片错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"处理表格图片错误: {str(e)}",
            "message": f"处理异常: {str(e)}"
        }), 500


# 修改普通表格处理函数
@llm_bp.route('/llm/process-non-financial-table', methods=['POST', 'OPTIONS'])
def process_non_financial_table():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    """处理普通表格 - 添加Excel存在性检查"""
    print("处理普通表格1212123")
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
                "message": "请求体不能为空"
            }), 400

        # 提取参数
        image_path = data.get('image_path')
        output_path = data.get('output_path')
        sheet_name = data.get('sheet_name', 'Sheet1')
        bank_name = data.get('bank_name', '未知机构')

        # 检查Excel是否已存在
        excel_exists, final_excel_path = _check_excel_exists(image_path, output_path)

        if excel_exists:
            logger.info(f"普通表格Excel文件已存在，直接返回: {final_excel_path}")
            # 构建可访问的URL
            excel_url = f"/static/excel_data/{Path(final_excel_path).name}"

            return jsonify({
                "success": True,
                "from_cache": True,
                "excel_url": excel_url,
                "message": "已加载现有Excel文件",
                "file_path": final_excel_path
            })

        # 如果不存在，继续正常处理
        result = asyncio.run(_process_non_financial_table(data))

        # 确保结果中包含from_cache字段
        if "from_cache" not in result:
            result["from_cache"] = False

        return jsonify(result)

    except Exception as e:
        logger.error(f"处理普通表格错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"处理普通表格错误: {str(e)}",
            "message": f"处理异常: {str(e)}"
        }), 500


@llm_bp.route('/excel-data/<path:excel_path>')
def serve_excel_data_route(excel_path):
    """提供Excel文件数据访问"""
    # ⭐⭐⭐ 修复：使用常量路径 ⭐⭐⭐
    from backend.utils.constants import EXCEL_DATA_DIR
    excel_file_path = EXCEL_DATA_DIR / excel_path

    if excel_file_path.exists():
        return send_from_directory(EXCEL_DATA_DIR, excel_path)
    else:
        return jsonify({"error": "Excel文件不存在"}), 404


def _check_excel_exists(image_path: str, output_path: str) -> tuple[bool, str]:
    """
    检查Excel文件是否已存在
    返回: (是否存在, Excel文件路径)
    """
    try:
        # ⭐⭐⭐ 修复：使用常量路径 ⭐⭐⭐
        excel_path = Path(output_path)

        # 如果输出路径是相对路径，转换为绝对路径
        if not excel_path.is_absolute():
            # 使用常量EXCEL_DATA_DIR作为基础路径
            excel_path = EXCEL_DATA_DIR / output_path

        # 确保路径存在
        excel_path.parent.mkdir(parents=True, exist_ok=True)

        # 检查文件是否存在
        if excel_path.exists():
            # 返回相对路径用于URL访问
            try:
                relative_path = str(excel_path.relative_to(EXCEL_DATA_DIR))
            except ValueError:
                # 如果不在EXCEL_DATA_DIR下，返回绝对路径
                relative_path = str(excel_path)
            return True, str(excel_path)

        return False, str(excel_path)

    except Exception as e:
        logger.error(f"检查Excel文件存在性失败: {e}")
        return False, output_path