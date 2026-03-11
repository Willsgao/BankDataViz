# -*- coding:utf-8 -*-
# backend/api/baidu_ocr_routes.py

import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from backend.excel_service.baidu_table_ocr_llm import TableOCRService
from backend.excel_service.baidu_table_processor import BaiduTableProcessor
from backend.utils.constants import MAIN_ROOT

# 创建蓝图
baidu_ocr_bp = Blueprint('baidu_ocr', __name__, url_prefix='/api/baidu-ocr')

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp'}

# 演示用的固定Excel文件名
DEMO_EXCEL_FILENAME = "baidu_ocr_demo.xlsx"


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_directories():
    """确保必要的目录存在"""
    upload_dir = os.path.join(MAIN_ROOT, 'backend', 'static', 'upload_images')
    output_dir = os.path.join(MAIN_ROOT, 'backend', 'static', 'excel_output')

    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    return upload_dir, output_dir


@baidu_ocr_bp.route('/recognize-table', methods=['POST'])
def recognize_table():
    """
    百度OCR表格识别接口
    接收图片文件，进行表格识别并返回Excel文件
    """
    try:
        # 检查文件是否存在
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '未找到文件，请选择要上传的图片文件'
            }), 400

        file = request.files['file']

        # 检查文件名
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400

        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'不支持的文件类型。允许的类型: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # 确保目录存在
        upload_dir, output_dir = ensure_directories()

        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        upload_path = os.path.join(upload_dir, unique_filename)

        # 保存上传的文件
        file.save(upload_path)

        # 初始化OCR服务
        ocr_service = TableOCRService()

        try:
            # 进行表格识别
            current_app.logger.info(f"开始识别表格: {upload_path}")
            ocr_result = ocr_service.recognize_table_from_file(upload_path)

            # 检查识别结果
            if 'error_code' in ocr_result:
                error_msg = ocr_result.get('error_msg', '未知错误')
                return jsonify({
                    'success': False,
                    'error': f'OCR识别失败: {error_msg}',
                    'error_code': ocr_result['error_code']
                }), 500

            # 保存OCR原始结果（可选）
            json_filename = f"{uuid.uuid4().hex}.json"
            json_path = os.path.join(output_dir, json_filename)
            ocr_service.save_result_to_json(ocr_result, json_path)

            # 处理表格数据并生成Excel
            processor = BaiduTableProcessor()

            # 使用固定文件名用于演示
            excel_filename = DEMO_EXCEL_FILENAME
            excel_path = os.path.join(output_dir, excel_filename)

            excel_file = processor.process_baidu_table(ocr_result, excel_path)

            # 构建返回的URL
            excel_url = f"/static/excel_output/{excel_filename}"

            # 返回成功结果
            return jsonify({
                'success': True,
                'message': '表格识别成功',
                'data': {
                    'excel_url': excel_url,
                    'excel_filename': excel_filename,
                    'original_filename': file.filename,
                    'tables_count': len(ocr_result.get('tables_result', [])),
                    'words_count': len(ocr_result.get('words_result', [])),
                    'ocr_result_available': 'words_result' in ocr_result
                }
            })

        except Exception as e:
            current_app.logger.error(f"表格识别处理失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'表格识别处理失败: {str(e)}'
            }), 500

        finally:
            # 关闭OCR服务
            ocr_service.close()

    except Exception as e:
        current_app.logger.error(f"接口处理异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500


@baidu_ocr_bp.route('/batch-recognize', methods=['POST'])
def batch_recognize_tables():
    """
    批量表格识别接口
    支持多张图片同时识别
    """
    try:
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': '未找到文件'
            }), 400

        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400

        # 过滤有效文件
        valid_files = []
        for file in files:
            if file and allowed_file(file.filename):
                valid_files.append(file)

        if not valid_files:
            return jsonify({
                'success': False,
                'error': '没有有效的图片文件'
            }), 400

        # 确保目录存在
        upload_dir, output_dir = ensure_directories()

        results = []
        ocr_service = TableOCRService()

        try:
            # 使用固定Excel文件名
            excel_filename = DEMO_EXCEL_FILENAME
            excel_path = os.path.join(output_dir, excel_filename)
            processor = BaiduTableProcessor()

            for file in valid_files:
                try:
                    # 生成唯一文件名
                    file_extension = os.path.splitext(file.filename)[1]
                    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
                    upload_path = os.path.join(upload_dir, unique_filename)

                    # 保存文件
                    file.save(upload_path)

                    # 识别表格
                    ocr_result = ocr_service.recognize_table_from_file(upload_path)

                    if 'error_code' in ocr_result:
                        results.append({
                            'success': False,
                            'filename': file.filename,
                            'error': ocr_result.get('error_msg', '识别失败')
                        })
                        continue

                    # 处理表格数据并生成Excel（使用固定文件名）
                    excel_file = processor.process_baidu_table(ocr_result, excel_path)

                    results.append({
                        'success': True,
                        'filename': file.filename,
                        'excel_url': f"/static/excel_output/{excel_filename}",
                        'excel_filename': excel_filename,
                        'tables_count': len(ocr_result.get('tables_result', []))
                    })

                except Exception as e:
                    results.append({
                        'success': False,
                        'filename': file.filename,
                        'error': str(e)
                    })

            # 统计结果
            success_count = sum(1 for r in results if r['success'])

            return jsonify({
                'success': True,
                'message': f'批量处理完成，成功: {success_count}/{len(valid_files)}',
                'data': {
                    'results': results,
                    'total_files': len(valid_files),
                    'success_count': success_count,
                    'failed_count': len(valid_files) - success_count
                }
            })

        finally:
            ocr_service.close()

    except Exception as e:
        current_app.logger.error(f"批量识别接口异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500


@baidu_ocr_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    try:
        # 简单的健康检查，验证OCR服务是否可用
        ocr_service = TableOCRService()
        token = ocr_service.get_access_token()
        ocr_service.close()

        return jsonify({
            'success': True,
            'message': '百度OCR服务正常',
            'data': {
                'services': 'baidu_ocr',
                'status': 'healthy',
                'has_token': bool(token)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'OCR服务异常: {str(e)}'
        }), 500