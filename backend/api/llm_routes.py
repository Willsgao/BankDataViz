# -*- coding:utf-8 -*-
"""
LLM 表格识别 API 路由
"""

import time
from flask import Blueprint, request, jsonify
import logging
from backend.service.table_llm_service import get_table_processor
from backend.schemas.table_schemas import ExcelSaveConfig
from backend.utils.constants import MAIN_ROOT

from pprint import pprint

# 创建蓝图
llm_bp = Blueprint('llm', __name__)

# 设置日志
logger = logging.getLogger(__name__)

# llm_routes.py
from flask import Blueprint, request, jsonify, send_from_directory
import asyncio
import logging
from pathlib import Path

llm_bp = Blueprint('llm', __name__)
logger = logging.getLogger(__name__)

# llm_routes.py
from flask import Blueprint, request, jsonify
import asyncio
import logging
from pathlib import Path



@llm_bp.route('/llm/process-image', methods=['POST'])
def process_table_image():
    """处理单张表格图片"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        print("&&&&&&&&&&&& 收到识别请求:", data)

        # 提取参数
        image_path = data.get('image_path')
        output_path = data.get('output_path')
        sheet_name = data.get('sheet_name', '识别结果')
        bank_name = data.get('bank_name', '未知银行')
        file_name = data.get('file_name', 'table_1')

        print(f"🔍 检查Excel文件是否存在: {output_path}")

        # 使用已有的标识创建Excel存储文件夹
        folder_name = Path(image_path).stem.split('_')[0]
        excel_base_dir = Path("static/excel_data")
        excel_dir = excel_base_dir / folder_name
        excel_dir.mkdir(parents=True, exist_ok=True)

        # 重新构建输出路径
        excel_filename = f"single_{Path(image_path).stem}.xlsx"
        new_output_path = excel_dir / excel_filename
        final_output_path = str(new_output_path)

        print(f"最终Excel路径: {final_output_path}")

        # 检查最终路径是否存在
        final_excel_path = Path(final_output_path)
        # 在 process_table_image 函数中
        if final_excel_path.exists():
            print("✅ Excel文件已存在，直接返回路径")

            # 将绝对路径转换为可访问的URL
            # excel_path: F:\wills\codes\DocuVista\backend/static\excel_data\...
            # 转换为: /static/excel_data/...
            relative_path = final_output_path.replace('\\', '/')  # 统一路径分隔符
            if 'static/' in relative_path:
                # 提取 static/ 之后的部分
                static_index = relative_path.find('static/')
                if static_index != -1:
                    excel_url = '/' + relative_path[static_index:]  # 变成 /static/excel_data/...
                else:
                    excel_url = f"/static/excel_data/{folder_name}/{excel_filename}"
            else:
                excel_url = f"/static/excel_data/{folder_name}/{excel_filename}"

            return jsonify({
                "success": True,
                "from_cache": True,
                "message": "已加载现有表格数据",
                "excel_url": excel_url,  # 现在这是正确的URL
                "excel_path": f"{MAIN_ROOT}/{final_output_path}",
                "table_name": sheet_name
            })

        # 如果Excel不存在，进行LLM识别
        print("🔄 Excel文件不存在，开始LLM识别流程")

        # 检查图片文件是否存在
        image_full_path = Path(image_path)
        if not image_full_path.exists():
            static_path = Path("static") / image_path
            if static_path.exists():
                image_full_path = static_path
            else:
                return jsonify({
                    "success": False,
                    "error": f"图片文件不存在: {image_path}"
                }), 404

        # 调用异步处理函数
        process_data = {
            'image_path': str(image_full_path),
            'output_path': final_output_path,
            'sheet_name': sheet_name,
            'bank_name': bank_name,
            'file_name': file_name
        }

        result = asyncio.run(_process_single_image(process_data))
        print("LLM识别结果:", result)

        if result.get('success'):
            excel_url = f"/api/excel-data/{folder_name}/{excel_filename}"

            return jsonify({
                "success": True,
                "from_cache": False,
                "message": "表格识别完成",
                "excel_url": excel_url,
                "excel_path": f"{MAIN_ROOT}/{final_output_path}",  # 保留 MAIN_ROOT
                "table_name": sheet_name,
                "data": result['data']
            })
        else:
            return jsonify(result)

    except Exception as e:
        logger.error(f"异步处理错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"异步处理错误: {str(e)}"
        }), 500


def validate_required_params(data, required_fields):
    """验证必要参数"""
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return False, f"缺少必要参数: {', '.join(missing_fields)}"
    return True, None


async def _process_single_image(data):
    """处理单张图片的异步函数"""
    try:
        # 验证必要参数
        is_valid, error_msg = validate_required_params(
            data, ['image_path', 'output_path']
        )

        print("###################")
        print(is_valid, error_msg)

        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }

        image_path = data.get('image_path')
        output_path = data.get('output_path')
        sheet_name = data.get('sheet_name', '识别结果')
        bank_name = data.get('bank_name', '未知银行')
        file_name = data.get('file_name', Path(image_path).stem)

        print("************image_path****output_path****************")
        print(image_path)
        print(output_path)
        print(sheet_name)
        print(bank_name)
        print(file_name)

        # 检查图片文件是否存在
        if not Path(image_path).exists():
            return {
                "success": False,
                "error": f"图片文件不存在: {image_path}"
            }

        processor = get_table_processor()

        print("****************processor.llm_client******************")
        print(processor.llm_client)

        if not processor.llm_client:
            return {
                "success": False,
                "error": "请先配置LLM客户端"
            }

        # 使用已有的标识创建Excel存储文件夹
        # 从 image_path 提取标识：类似 d0586abf1323dbfd80a926ce1e2d5676
        folder_name = Path(image_path).stem.split('_')[0]  # 取第一个下划线前的部分

        excel_base_dir = Path("static/excel_data")
        excel_dir = excel_base_dir / folder_name
        excel_dir.mkdir(parents=True, exist_ok=True)

        # 重新构建输出路径
        excel_filename = Path(output_path).name
        new_output_path = excel_dir / excel_filename
        output_path = str(new_output_path)

        print(f"Excel文件将保存到: {output_path}")

        # 配置Excel保存参数
        excel_config = ExcelSaveConfig(
            anchor_cell=data.get('anchor_cell', 'R2'),
            width_px=data.get('width_px', 768),
            mode=data.get('mode', 'overwrite')
        )

        # 处理图片 - 使用新的方法名和参数
        result = await processor.process_table_pipeline(
            image_path=image_path,
            out_file=output_path,
            sheet_name=sheet_name,
            bank_name=bank_name,
            file_name=file_name,
            excel_config=excel_config
        )

        logger.info(f"表格识别完成 - 状态: {result.status}, 文件: {output_path}")

        return {
            "success": result.status == "success",
            "data": {
                "status": result.status,
                "complexity": result.complexity,
                "mode": result.mode,
                "table_name": result.table_name,
                "assessment_reason": result.assessment_reason,
                "error_message": result.error_message,
                "output_path": output_path  # 返回实际的输出路径
            }
        }

    except Exception as e:
        logger.error(f"表格识别失败: {str(e)}")
        return {
            "success": False,
            "error": f"处理失败: {str(e)}"
        }


async def _batch_process_images(data):
    """批量处理图片的异步函数"""
    try:
        # 验证必要参数
        is_valid, error_msg = validate_required_params(
            data, ['image_paths', 'output_dir']
        )
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }

        image_paths = data.get('image_paths', [])
        output_dir = data.get('output_dir')
        bank_name = data.get('bank_name', '未知银行')
        output_file = data.get('output_file', 'batch_processing_results.xlsx')

        # 检查图片文件
        missing_images = []
        for img_path in image_paths:
            if not Path(img_path).exists():
                missing_images.append(img_path)

        if missing_images:
            return {
                "success": False,
                "error": f"以下图片文件不存在: {missing_images}"
            }

        processor = get_table_processor()

        if not processor.llm_client:
            return {
                "success": False,
                "error": "请先配置LLM客户端"
            }

        # 使用已有的标识创建Excel存储文件夹
        # 从第一个图片路径提取标识：类似 d0586abf1323dbfd80a926ce1e2d5676
        if image_paths:
            folder_name = Path(image_paths[0]).stem.split('_')[0]  # 取第一个下划线前的部分
        else:
            folder_name = "unknown_batch"

        excel_base_dir = Path("static/excel_data")
        excel_dir = excel_base_dir / folder_name
        excel_dir.mkdir(parents=True, exist_ok=True)

        # 重新构建输出路径
        excel_filename = Path(output_file).name
        new_output_file = excel_dir / excel_filename
        output_file = str(new_output_file)

        print(f"批量处理Excel文件将保存到: {output_file}")

        # 批量处理 - 需要实现批量处理方法
        results = []
        success_count = 0

        for i, image_path in enumerate(image_paths):
            try:
                sheet_name = f"sheet_{i + 1}"
                file_name = Path(image_path).stem

                result = await processor.process_table_pipeline(
                    image_path=image_path,
                    out_file=output_file,  # 所有结果保存到同一个文件
                    sheet_name=sheet_name,
                    bank_name=bank_name,
                    file_name=file_name
                )

                results.append({
                    "image_path": image_path,
                    "status": result.status,
                    "complexity": result.complexity,
                    "table_name": result.table_name,
                    "sheet_name": sheet_name
                })

                if result.status == "success":
                    success_count += 1

            except Exception as e:
                logger.error(f"处理图片失败 {image_path}: {str(e)}")
                results.append({
                    "image_path": image_path,
                    "status": "error",
                    "error": str(e)
                })

        logger.info(f"批量处理完成 - 总数: {len(image_paths)}, 成功: {success_count}")

        return {
            "success": True,
            "data": {
                "total": len(image_paths),
                "success": success_count,
                "failed": len(image_paths) - success_count,
                "results": results,
                "output_file": output_file
            }
        }

    except Exception as e:
        logger.error(f"批量处理失败: {str(e)}")
        return {
            "success": False,
            "error": f"批量处理失败: {str(e)}"
        }

async def _test_connection_internal(data):
    """测试LLM连接的内部异步函数"""
    try:
        # 验证必要参数
        is_valid, error_msg = validate_required_params(
            data, ['base_url', 'api_key', 'model_id']
        )
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }

        base_url = data.get('base_url')
        api_key = data.get('api_key')
        model_id = data.get('model_id')

        # 临时配置处理器进行测试
        from backend.service.table_llm_service import TableLLMService
        temp_processor = TableLLMService()
        # 直接使用构造函数配置，不再需要 configure_client 方法
        temp_processor = TableLLMService(
            llm_client=None,  # 让服务自己创建客户端
            model_id=model_id
        )

        # 测试连接
        try:
            response = await temp_processor.llm_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "Hello, respond with just 'OK'"}],
                max_tokens=10
            )

            return {
                "success": True,
                "message": "LLM连接测试成功",
                "data": {
                    "model_response": bool(response.choices),
                    "response_content": response.choices[0].message.content if response.choices else None
                }
            }

        except Exception as api_error:
            return {
                "success": False,
                "error": f"API调用失败: {str(api_error)}"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"连接测试失败: {str(e)}"
        }



@llm_bp.route('/llm/configure', methods=['POST'])
def configure_llm():
    """配置LLM参数"""
    try:
        data = request.get_json()
        print(f"🔧 收到配置请求: {data}")  # 调试信息

        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        # 验证必要参数
        is_valid, error_msg = validate_required_params(
            data, ['base_url', 'api_key', 'model_id']
        )
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400

        base_url = data.get('base_url')
        api_key = data.get('api_key')
        model_id = data.get('model_id')
        prompts = data.get('prompts', {})

        print(f"🔧 解析配置参数: base_url={base_url}, model_id={model_id}, prompts_keys={list(prompts.keys())}")

        # 获取处理器实例 - 需要修改 get_table_processor 函数来支持配置
        from backend.service.table_llm_service import TableLLMService
        processor = TableLLMService(
            llm_client=None,  # 让服务自己创建
            model_id=model_id
        )

        print(f"🔧 处理器状态: llm_client={processor.llm_client is not None}, model_id={processor.model_id}")

        # 检查客户端是否配置成功
        if not processor.llm_client:
            return jsonify({
                "success": False,
                "error": "LLM客户端配置失败，请检查API密钥和URL是否正确"
            }), 400

        # 更新提示词配置
        if prompts:
            for prompt_type, prompt_content in prompts.items():
                if prompt_type in processor.prompt_registry:
                    processor.prompt_registry[prompt_type] = prompt_content

        logger.info(f"LLM配置成功 - 模型: {model_id}, 基础URL: {base_url}")

        return jsonify({
            "success": True,
            "message": "LLM配置成功",
            "data": {
                "model_id": processor.model_id,
                "base_url": base_url,
                "prompts_configured": list(prompts.keys()) if prompts else [],
                "client_configured": processor.llm_client is not None
            }
        })

    except Exception as e:
        logger.error(f"LLM配置失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"配置失败: {str(e)}"
        }), 500



@llm_bp.route('/llm/batch-process', methods=['POST'])
def batch_process_images():
    """批量处理图片"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        result = asyncio.run(_batch_process_images(data))
        return jsonify(result)
    except Exception as e:
        logger.error(f"异步处理错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"异步处理错误: {str(e)}"
        }), 500


@llm_bp.route('/llm/test-connection', methods=['POST'])
def test_connection():
    """测试LLM连接"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        result = asyncio.run(_test_connection_internal(data))
        return jsonify(result)
    except Exception as e:
        logger.error(f"测试连接错误: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"测试连接错误: {str(e)}"
        }), 500


@llm_bp.route('/llm/available-models', methods=['GET'])
def get_available_models():
    """获取可用的模型列表"""
    models = [
        {
            "id": "doubao-1-5-vision-pro-250328",
            "name": "豆包视觉专业版",
            "description": "支持视觉识别的专业模型",
            "max_tokens": 16000
        },
        {
            "id": "doubao-seed-1-6-vision-250815",
            "name": "豆包视觉种子版",
            "description": "视觉识别基础模型",
            "max_tokens": 16000
        }
    ]

    return jsonify({
        "success": True,
        "data": models
    })




@llm_bp.route('/llm/status', methods=['GET'])
def get_processor_status():
    """获取处理器状态"""
    try:
        processor = get_table_processor()

        # 修复：确保所有值都是可JSON序列化的
        base_url = getattr(processor.llm_client, 'base_url', None)
        if base_url is not None:
            base_url = str(base_url)  # 将URL对象转换为字符串

        status = {
            "client_configured": processor.llm_client is not None,
            "model_id": processor.model_id,
            "base_url": base_url,  # 使用转换后的字符串
            "prompts_configured": {
                prompt_type: bool(content) and len(content.strip()) > 0
                for prompt_type, content in processor.prompt_registry.items()
            }
        }

        return jsonify({
            "success": True,
            "data": status
        })
    except Exception as e:
        logger.error(f"获取状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取状态失败: {str(e)}"
        }), 500


@llm_bp.route('/llm/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        processor = get_table_processor()

        # 修复：确保所有值都是可JSON序列化的
        base_url = getattr(processor.llm_client, 'base_url', None)
        if base_url is not None:
            base_url = str(base_url)

        health_status = {
            "service": "running",
            "llm_configured": processor.llm_client is not None,
            "model_id": processor.model_id,
            "base_url": base_url,  # 使用转换后的字符串
            "timestamp": time.time()  # 使用time.time()而不是asyncio的时间
        }

        return jsonify({
            "success": True,
            "data": health_status
        })
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"健康检查失败: {str(e)}"
        }), 500



@llm_bp.route('/llm/recognize-table', methods=['POST'])
def recognize_table():
    """识别表格并保存到指定路径 - 先检查Excel是否存在"""
    try:
        data = request.get_json()
        print(f"收到识别请求: {data}")

        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        # 验证必要参数
        required_fields = ['imageUrl', 'excelPath']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"缺少必要参数: {', '.join(missing_fields)}"
            }), 400

        image_url = data.get('imageUrl')
        excel_path = data.get('excelPath')
        table_name = data.get('tableName', '识别结果')
        index = data.get('index', 0)

        print(f"识别参数 - imageUrl: {image_url}, excelPath: {excel_path}")

        # 构建完整Excel路径
        excel_full_path = Path(excel_path)
        if not excel_full_path.is_absolute():
            excel_full_path = Path.cwd() / excel_path

        print(f"检查Excel文件是否存在: {excel_full_path}")

        # 1. 首先检查Excel文件是否已经存在
        if excel_full_path.exists():
            print("✅ Excel文件已存在，直接读取数据")
            try:
                import openpyxl
                workbook = openpyxl.load_workbook(excel_full_path)
                sheet_name = workbook.sheetnames[0]
                worksheet = workbook[sheet_name]

                # 转换为JSON数据
                headers = []
                data = []

                # 读取表头（第一行）
                for col in range(1, worksheet.max_column + 1):
                    cell_value = worksheet.cell(row=1, column=col).value
                    headers.append(str(cell_value) if cell_value is not None else f"列{col}")

                # 读取数据行
                for row in range(2, worksheet.max_row + 1):
                    row_data = {}
                    for col, header in enumerate(headers, 1):
                        cell_value = worksheet.cell(row=row, column=col).value
                        row_data[header] = str(cell_value) if cell_value is not None else ""
                    if any(row_data.values()):  # 只添加非空行
                        data.append(row_data)

                return jsonify({
                    "success": True,
                    "recognizedData": {
                        "headers": headers,
                        "data": data,
                        "tableName": table_name,
                        "excelPath": str(excel_full_path)
                    },
                    "message": "已加载现有表格数据",
                    "fromCache": True  # 添加标记表示来自缓存
                })
            except Exception as e:
                logger.error(f"读取现有Excel失败: {str(e)}")
                # 如果读取失败，继续走LLM识别流程
                print("❌ 读取现有Excel失败，继续走LLM识别")

        # 2. 如果Excel不存在，进行LLM识别
        print("🔄 Excel文件不存在，开始LLM识别流程")

        # 从图片URL提取图片路径
        if image_url.startswith('http://127.0.0.1:5000/'):
            image_path = image_url.replace('http://127.0.0.1:5000/', '')
        elif image_url.startswith('http://localhost:5000/'):
            image_path = image_url.replace('http://localhost:5000/', '')
        else:
            image_path = image_url

        # 确保是相对路径
        if image_path.startswith('/'):
            image_path = image_path[1:]

        print(f"处理图片路径: {image_path}")

        # 检查图片文件是否存在
        image_full_path = Path(image_path)
        if not image_full_path.exists():
            # 尝试在static目录下查找
            static_path = Path("static") / image_path
            if static_path.exists():
                image_full_path = static_path
            else:
                return jsonify({
                    "success": False,
                    "error": f"图片文件不存在: {image_path}"
                }), 404

        # 确保Excel目录存在
        excel_full_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Excel保存路径: {excel_full_path}")

        # 调用 _process_single_image 异步函数进行LLM识别
        process_data = {
            'image_path': str(image_full_path),
            'output_path': str(excel_full_path),
            'sheet_name': table_name,
            'bank_name': '未知银行',
            'file_name': f"table_{index + 1}"
        }

        # 使用异步处理
        result = asyncio.run(_process_single_image(process_data))
        print(f"LLM识别结果: {result}")

        if result.get('success'):
            # 读取生成的Excel文件数据返回给前端
            output_path = result['data']['output_path']
            excel_result_path = Path(output_path)

            if excel_result_path.exists():
                try:
                    import openpyxl
                    workbook = openpyxl.load_workbook(excel_result_path)
                    sheet_name = workbook.sheetnames[0]
                    worksheet = workbook[sheet_name]

                    # 转换为JSON数据
                    headers = []
                    data = []

                    # 读取表头（第一行）
                    for col in range(1, worksheet.max_column + 1):
                        cell_value = worksheet.cell(row=1, column=col).value
                        headers.append(str(cell_value) if cell_value is not None else f"列{col}")

                    # 读取数据行
                    for row in range(2, worksheet.max_row + 1):
                        row_data = {}
                        for col, header in enumerate(headers, 1):
                            cell_value = worksheet.cell(row=row, column=col).value
                            row_data[header] = str(cell_value) if cell_value is not None else ""
                        if any(row_data.values()):  # 只添加非空行
                            data.append(row_data)

                    return jsonify({
                        "success": True,
                        "recognizedData": {
                            "headers": headers,
                            "data": data,
                            "tableName": table_name,
                            "excelPath": str(excel_result_path)
                        },
                        "message": "表格识别完成",
                        "fromCache": False  # 添加标记表示来自LLM识别
                    })
                except Exception as e:
                    logger.error(f"读取生成的Excel失败: {str(e)}")
                    # 即使读取失败，也返回成功，因为Excel文件已经生成
                    return jsonify({
                        "success": True,
                        "recognizedData": {
                            "headers": ["识别完成"],
                            "data": [{"状态": "表格识别完成，但读取数据失败"}],
                            "tableName": table_name,
                            "excelPath": str(excel_result_path)
                        },
                        "message": "表格识别完成",
                        "fromCache": False
                    })
            else:
                return jsonify({
                    "success": False,
                    "error": "识别完成但Excel文件未生成"
                }), 500
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', '识别失败')
            }), 500

    except Exception as e:
        logger.error(f"表格识别失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"表格识别失败: {str(e)}"
        }), 500


@llm_bp.route('/llm/check-excel', methods=['GET'])
def check_excel():
    """检查Excel文件是否存在"""
    try:
        file_path = request.args.get('path')
        print(f"🔍 检查Excel文件请求 - path: {file_path}")

        if not file_path:
            return jsonify({
                "success": False,
                "error": "缺少path参数"
            }), 400

        # 构建完整路径
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = Path.cwd() / file_path

        print(f"🔍 检查Excel完整路径: {full_path}")
        print(f"🔍 文件是否存在: {full_path.exists()}")

        if full_path.exists():
            try:
                import openpyxl
                workbook = openpyxl.load_workbook(full_path)
                sheet_name = workbook.sheetnames[0]
                worksheet = workbook[sheet_name]

                # 转换为JSON数据
                data = []
                headers = []

                # 读取表头（第一行）
                for col in range(1, worksheet.max_column + 1):
                    cell_value = worksheet.cell(row=1, column=col).value
                    headers.append(str(cell_value) if cell_value is not None else f"列{col}")

                # 读取数据行
                for row in range(2, worksheet.max_row + 1):
                    row_data = {}
                    for col, header in enumerate(headers, 1):
                        cell_value = worksheet.cell(row=row, column=col).value
                        row_data[header] = str(cell_value) if cell_value is not None else ""
                    if any(row_data.values()):  # 只添加非空行
                        data.append(row_data)

                print(f"🔍 Excel数据读取成功 - 表头: {headers}, 数据行数: {len(data)}")

                return jsonify({
                    "success": True,
                    "exists": True,
                    "excelData": {
                        "headers": headers,
                        "data": data,
                        "sheet_name": sheet_name,
                        "file_path": str(full_path)
                    }
                })
            except Exception as e:
                logger.error(f"读取Excel文件失败: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"读取Excel文件失败: {str(e)}"
                }), 500
        else:
            print(f"🔍 Excel文件不存在: {file_path}")
            return jsonify({
                "success": True,
                "exists": False,
                "message": f"Excel文件不存在: {file_path}"
            })

    except Exception as e:
        logger.error(f"检查Excel失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"检查Excel失败: {str(e)}"
        }), 500



@llm_bp.route('/llm/get-excel-data', methods=['GET'])
def get_excel_data():
    """读取Excel文件内容并返回给前端"""
    try:
        excel_url = request.args.get('url')
        if not excel_url:
            return jsonify({
                "success": False,
                "error": "缺少url参数"
            }), 400

        # 将URL转换为文件路径
        if excel_url.startswith('/static/'):
            file_path = excel_url[1:]  # 去掉开头的斜杠
        else:
            file_path = excel_url

        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = Path.cwd() / file_path

        print(f"读取Excel文件: {full_path}")

        if not full_path.exists():
            return jsonify({
                "success": False,
                "error": f"Excel文件不存在: {file_path}"
            }), 404

        # 读取Excel文件
        import openpyxl
        workbook = openpyxl.load_workbook(full_path)
        sheet_name = workbook.sheetnames[0]
        worksheet = workbook[sheet_name]

        # 转换为JSON数据
        headers = []
        data_rows = []

        # 读取表头（第一行）
        for col in range(1, worksheet.max_column + 1):
            cell_value = worksheet.cell(row=1, column=col).value
            headers.append(str(cell_value) if cell_value is not None else f"列{col}")

        # 读取数据行
        for row in range(2, worksheet.max_row + 1):
            row_data = {}
            for col, header in enumerate(headers, 1):
                cell_value = worksheet.cell(row=row, column=col).value
                row_data[header] = str(cell_value) if cell_value is not None else ""
            if any(row_data.values()):  # 只添加非空行
                data_rows.append(row_data)

        return jsonify({
            "success": True,
            "data": {
                "headers": headers,
                "data": data_rows,
                "tableName": sheet_name,
                "excelPath": str(full_path)
            }
        })

    except Exception as e:
        logger.error(f"读取Excel数据失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"读取Excel数据失败: {str(e)}"
        }), 500




@llm_bp.route('/llm/get-excel-content', methods=['GET'])
def get_excel_content():
    """读取Excel文件内容并返回结构化数据"""
    try:
        excel_url = request.args.get('excel_url')
        print(f"📖 读取Excel内容: {excel_url}")

        if not excel_url:
            return jsonify({
                "success": False,
                "error": "缺少excel_url参数"
            }), 400

        # 从URL提取文件路径
        if excel_url.startswith('/api/excel-data/'):
            file_path = excel_url.replace('/api/excel-data/', 'static/excel_data/')
        else:
            return jsonify({
                "success": False,
                "error": "无效的Excel URL格式"
            }), 400

        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = Path.cwd() / file_path

        print(f"Excel文件完整路径: {full_path}")

        if not full_path.exists():
            return jsonify({
                "success": False,
                "error": f"Excel文件不存在: {file_path}"
            }), 404

        # 读取Excel文件
        import openpyxl
        workbook = openpyxl.load_workbook(full_path)
        sheet_name = workbook.sheetnames[0]
        worksheet = workbook[sheet_name]

        # 转换为JSON数据
        headers = []
        data_rows = []

        # 读取表头（第一行）
        for col in range(1, worksheet.max_column + 1):
            cell_value = worksheet.cell(row=1, column=col).value
            headers.append(str(cell_value) if cell_value is not None else f"列{col}")

        # 读取数据行
        for row in range(2, worksheet.max_row + 1):
            row_data = {}
            for col, header in enumerate(headers, 1):
                cell_value = worksheet.cell(row=row, column=col).value
                row_data[header] = str(cell_value) if cell_value is not None else ""
            if any(row_data.values()):  # 只添加非空行
                data_rows.append(row_data)

        return jsonify({
            "success": True,
            "data": {
                "headers": headers,
                "data": data_rows,
                "tableName": sheet_name,
                "excelPath": str(full_path)
            }
        })

    except Exception as e:
        logger.error(f"读取Excel内容失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"读取Excel内容失败: {str(e)}"
        }), 500

