# -*- coding:utf-8 -*-
"""
Excel 文件管理 API
用于管理用户上传的 Excel 文件（独立于 PDF 处理流程）
"""

import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response, send_file

from backend.utils.constants import DATABASE_PATH, MAIN_ROOT, UPLOAD_DIR
from backend.models.unified_db import UnifiedDatabaseManager

excel_bp = Blueprint('excel', __name__)

# 初始化数据库管理器
db_mgr = UnifiedDatabaseManager()

# Excel 文件存储目录 - 统一到 uploads/excel/
EXCEL_UPLOAD_DIR = os.path.join(MAIN_ROOT, 'data', 'backend', 'static', 'uploads', 'excel')
os.makedirs(EXCEL_UPLOAD_DIR, exist_ok=True)

# 允许的文件扩展名（成品文件支持：Excel、Word、PDF）
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'docx', 'doc', 'pdf'}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_mime_type(filename):
    """根据扩展名获取 MIME 类型"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    mime_types = {
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'pdf': 'application/pdf'
    }
    return mime_types.get(ext, 'application/octet-stream')


def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


@excel_bp.route('/api/excel/upload', methods=['POST'])
def upload_excel():
    """
    上传成品文件（Excel/Word/PDF）
    POST /api/excel/upload
    Form Data: file (文件), description (可选描述)
    """
    # 1. 检查请求
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "没有找到文件字段"}), 400

    file = request.files['file']
    description = request.form.get('description', '')

    # 2. 基础验证
    if file.filename == '':
        return jsonify({"success": False, "error": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "只支持 Excel、Word、PDF 格式"}), 400

    # 3. 检查文件名是否重复
    original_filename = file.filename
    exists, existing_file = db_mgr.check_excel_filename_exists(original_filename)
    
    if exists:
        # 文件名重复，返回警告信息让前端显示确认对话框
        return jsonify({
            "success": False,
            "error": "文件名已存在",
            "duplicate": True,
            "existing_file": {
                "id": existing_file['id'],
                "filename": existing_file['filename'],
                "file_size": existing_file['file_size'],
                "file_size_display": format_file_size(existing_file['file_size']),
                "uploader_name": existing_file['uploader_name'],
                "created_at": existing_file['created_at']
            }
        }), 409  # 使用 409 Conflict 状态码

    # 4. 保存文件
    try:
        file_size = len(file.read())  # 获取文件大小
        file.seek(0)  # 重置文件指针

        # 生成唯一文件名
        ext = original_filename.rsplit('.', 1)[1].lower()
        disk_name = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(EXCEL_UPLOAD_DIR, disk_name)

        # 保存文件
        file.save(file_path)

        # 5. 保存数据库记录
        # 获取上传者信息（从请求头或表单）
        uploader_id = request.form.get('uploader_id') or request.form.get('user_id')
        uploader_name = request.form.get('uploader_name') or request.form.get('username') or '未知'

        file_info = {
            'filename': original_filename,
            'disk_name': disk_name,
            'file_path': file_path,
            'file_size': file_size,
            'uploader_id': uploader_id,
            'uploader_name': uploader_name,
            'description': description
        }

        success, result = db_mgr.save_excel_file(file_info)

        if success:
            return jsonify({
                "success": True,
                "message": "文件上传成功",
                "data": {
                    "id": result,
                    "filename": original_filename,
                    "disk_name": disk_name,
                    "file_size": file_size,
                    "file_size_display": format_file_size(file_size),
                    "file_path": file_path,
                    "uploader_name": uploader_name,
                    "description": description,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        else:
            # 回滚：删除已保存的文件
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"success": False, "error": f"数据库保存失败: {result}"}), 500

    except Exception as e:
        print(f"❌ 文件上传失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@excel_bp.route('/api/excel/upload/confirm', methods=['POST'])
def confirm_upload():
    """
    确认覆盖上传（文件名重复时）
    POST /api/excel/upload/confirm
    Body: { filename, file (二进制), description }
    """
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "没有找到文件字段"}), 400

    file = request.files['file']
    data = request.form
    description = data.get('description', '')

    if file.filename == '':
        return jsonify({"success": False, "error": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "只支持 Excel、Word、PDF 格式"}), 400

    try:
        original_filename = file.filename
        file_size = len(file.read())
        file.seek(0)

        # 生成新文件名
        ext = original_filename.rsplit('.', 1)[1].lower()
        disk_name = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(EXCEL_UPLOAD_DIR, disk_name)

        # 保存文件
        file.save(file_path)

        # 获取上传者信息
        uploader_id = data.get('uploader_id') or data.get('user_id')
        uploader_name = data.get('uploader_name') or data.get('username') or '未知'

        file_info = {
            'filename': original_filename,
            'disk_name': disk_name,
            'file_path': file_path,
            'file_size': file_size,
            'uploader_id': uploader_id,
            'uploader_name': uploader_name,
            'description': description
        }

        success, result = db_mgr.save_excel_file(file_info)

        if success:
            return jsonify({
                "success": True,
                "message": "文件上传成功（已覆盖同名文件）",
                "data": {
                    "id": result,
                    "filename": original_filename,
                    "disk_name": disk_name,
                    "file_size": file_size,
                    "file_size_display": format_file_size(file_size),
                    "file_path": file_path,
                    "uploader_name": uploader_name,
                    "description": description,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        else:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"success": False, "error": f"数据库保存失败: {result}"}), 500

    except Exception as e:
        print(f"❌ 确认上传失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@excel_bp.route('/api/excel/list', methods=['GET'])
def list_excel_files():
    """
    获取 Excel 文件列表（支持筛选和分页）
    GET /api/excel/list
    Query Params:
        - filename: 文件名搜索关键字
        - uploader_name: 上传人搜索关键字
        - start_date: 开始日期 (YYYY-MM-DD)
        - end_date: 结束日期 (YYYY-MM-DD)
        - page: 页码 (默认 1)
        - page_size: 每页数量 (默认 20)
    """
    try:
        # 获取查询参数
        filename = request.args.get('filename', '')
        uploader_name = request.args.get('uploader_name', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        # 构建筛选条件
        filters = {}
        if filename:
            filters['filename'] = filename
        if uploader_name:
            filters['uploader_name'] = uploader_name
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date

        # 查询数据
        success, result = db_mgr.get_excel_files(filters=filters, page=page, page_size=page_size)

        if success:
            # 格式化文件大小
            for file in result['files']:
                file['file_size_display'] = format_file_size(file.get('file_size', 0))

            return jsonify({
                "success": True,
                "data": result
            })
        else:
            return jsonify({"success": False, "error": str(result)}), 500

    except Exception as e:
        print(f"❌ 获取 Excel 文件列表失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@excel_bp.route('/api/excel/<int:file_id>', methods=['GET'])
def get_excel_file(file_id):
    """
    获取单个 Excel 文件信息
    GET /api/excel/:id
    """
    try:
        success, result = db_mgr.get_excel_file_by_id(file_id)

        if success:
            result['file_size_display'] = format_file_size(result.get('file_size', 0))
            return jsonify({
                "success": True,
                "data": result
            })
        else:
            return jsonify({"success": False, "error": result}), 404

    except Exception as e:
        print(f"❌ 获取 Excel 文件失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@excel_bp.route('/api/excel/download/<int:file_id>', methods=['GET'])
def download_excel(file_id):
    """
    下载 Excel 文件
    GET /api/excel/download/:id
    """
    try:
        success, result = db_mgr.get_excel_file_by_id(file_id)

        if not success:
            return jsonify({"success": False, "error": "文件不存在"}), 404

        file_path = result.get('file_path')
        filename = result.get('filename')

        if not file_path or not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件物理路径不存在"}), 404

        # 返回文件下载
        return send_file(
            file_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if filename.endswith('.xlsx') else 'application/vnd.ms-excel',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"❌ 下载 Excel 文件失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@excel_bp.route('/api/excel/<int:file_id>', methods=['DELETE'])
def delete_excel_file(file_id):
    """
    删除 Excel 文件
    DELETE /api/excel/:id
    """
    try:
        success, message = db_mgr.delete_excel_file(file_id)

        if success:
            return jsonify({
                "success": True,
                "message": message
            })
        else:
            return jsonify({"success": False, "error": message}), 404

    except Exception as e:
        print(f"❌ 删除 Excel 文件失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@excel_bp.route('/api/excel/<int:file_id>', methods=['PATCH'])
def update_excel_file(file_id):
    """
    更新 Excel 文件信息（如描述）
    PATCH /api/excel/:id
    Body: { description: "新的描述" }
    """
    try:
        data = request.get_json()
        description = data.get('description', '')

        success, message = db_mgr.update_excel_file_description(file_id, description)

        if success:
            return jsonify({
                "success": True,
                "message": message
            })
        else:
            return jsonify({"success": False, "error": message}), 400

    except Exception as e:
        print(f"❌ 更新 Excel 文件失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
