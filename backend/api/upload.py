# -*- coding:utf-8 -*-

from flask import Blueprint, request, jsonify, make_response
from backend.utils.constants import UPLOAD_FOLDER, DATABASE, MAIN_ROOT
import uuid, os, hashlib
from pathlib import Path
import sqlite3
from datetime import datetime

from backend.utils.constants import ALLOWED_EXTENSIONS

# 新增导入
from backend.service.file_mapping_service import file_mapping_service

upload_bp = Blueprint('upload', __name__)


def allowed_file(filename):
    """
    辅助函数
    :param filename: 目标文件名
    :return: 格式化后的文件名
    """
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_file_hash(file_content):
    """
    计算文件的MD5哈希值
    :param file_content: 文件字节内容
    :return: 32位十六进制哈希字符串
    """
    return hashlib.md5(file_content).hexdigest()



from backend.service.file_upload_service import file_upload_service

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """文件上传接口 - 使用服务类"""

    # 1. 检查请求
    if 'file' not in request.files:
        print("❌ 错误: 没有找到file字段")
        return make_response(jsonify({"error": "No file part"}), 400)

    file = request.files['file']
    raw_filename = file.filename

    # 2. 基础验证
    if raw_filename == '':
        print("❌ 错误: 文件名为空")
        return make_response(jsonify({"error": "No selected file"}), 400)

    # 3. 使用服务类处理上传
    result = file_upload_service.process_upload(file, raw_filename)

    # 4. 根据结果返回响应
    if result["success"]:
        return jsonify(result)
    else:
        return make_response(
            jsonify({"error": result.get("error", "上传失败")}),
            result.get("status_code", 500)
        )


# 在 upload.py 中添加以下导入
from backend.service.file_management_service import file_management_service



@upload_bp.route('/files', methods=['GET'])
def get_all_files():
    """获取所有文件列表 - 简化版本"""
    print("🔍 upload_bp - 获取文件列表")
    try:
        conn = sqlite3.connect(DATABASE)
        if not conn:
            return jsonify({"error": "数据库连接失败"}), 500

        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 先只查询基本字段，避免列不存在错误
        c.execute("""
            SELECT filename, raw_filename, file_type, created_at
            FROM files 
            WHERE deleted = 0 
            ORDER BY created_at DESC
        """)

        rows = c.fetchall()
        files_list = []

        upload_dir = Path(MAIN_ROOT) / UPLOAD_FOLDER

        for row in rows:
            file_path = upload_dir / row['filename']

            if file_path.exists():
                file_info = {
                    "filename": row['raw_filename'] or row['filename'],
                    "disk_name": row['filename'],
                    "file_id": row['filename'].split('.')[0],
                    "file_type": row['file_type'],
                    "created_at": row['created_at']
                }
                files_list.append(file_info)

        conn.close()

        print(f"📊 返回文件数量: {len(files_list)}")
        return jsonify(files_list)

    except Exception as e:
        print(f"❌ 获取文件列表失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# 在现有路由后面添加以下路由
@upload_bp.route('/files/stats', methods=['GET'])
def get_file_stats():
    """获取文件统计信息"""
    try:
        stats = file_management_service.get_file_stats()
        if stats:
            return jsonify({
                "success": True,
                "data": stats
            })
        else:
            return jsonify({
                "success": False,
                "error": "获取统计信息失败"
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@upload_bp.route('/files/duplicates', methods=['GET'])
def list_duplicates():
    """列出重复文件"""
    try:
        limit = request.args.get('limit', 20, type=int)
        duplicates = file_management_service.find_duplicates(limit)

        return jsonify({
            "success": True,
            "data": {
                "duplicates": duplicates,
                "count": len(duplicates),
                "potential_saving_total": sum(d['potential_saving_mb'] for d in duplicates)
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@upload_bp.route('/files/<file_id>', methods=['GET'])
def get_file_details(file_id):
    """获取文件详细信息"""
    try:
        file_info = file_management_service.get_file_info(file_id)
        if file_info:
            return jsonify({
                "success": True,
                "data": file_info
            })
        else:
            return jsonify({
                "success": False,
                "error": "文件不存在"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@upload_bp.route('/files/orphaned', methods=['GET'])
def list_orphaned_files():
    """列出孤立文件"""
    try:
        days = request.args.get('days', 30, type=int)
        result = file_management_service.find_orphaned_files(days)

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@upload_bp.route('/files/cleanup/<int:file_id>', methods=['DELETE'])
def cleanup_file(file_id):
    """清理文件"""
    try:
        delete_physical = request.args.get('physical', 'false').lower() == 'true'
        result = file_management_service.cleanup_file(file_id, delete_physical)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@upload_bp.route('/files/search', methods=['GET'])
def search_files():
    """搜索文件"""
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 50, type=int)

        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        if query:
            c.execute("""
                SELECT id, raw_filename, filename, file_type, file_size, 
                       created_at, upload_count, file_hash
                FROM files 
                WHERE deleted = 0 
                  AND (raw_filename LIKE ? OR file_hash LIKE ?)
                ORDER BY created_at DESC
                LIMIT ?
            """, (f'%{query}%', f'%{query}%', limit))
        else:
            c.execute("""
                SELECT id, raw_filename, filename, file_type, file_size, 
                       created_at, upload_count, file_hash
                FROM files 
                WHERE deleted = 0 
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        files = [dict(row) for row in c.fetchall()]
        conn.close()

        return jsonify({
            "success": True,
            "data": {
                "files": files,
                "count": len(files),
                "query": query
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@upload_bp.route('/files/recent', methods=['GET'])
def get_recent_files():
    """获取最近上传的文件"""
    try:
        limit = request.args.get('limit', 10, type=int)

        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("""
            SELECT id, raw_filename, filename, file_type, file_size, 
                   created_at, upload_count, file_hash
            FROM files 
            WHERE deleted = 0 
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        files = [dict(row) for row in c.fetchall()]
        conn.close()

        return jsonify({
            "success": True,
            "data": {
                "files": files,
                "count": len(files)
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

