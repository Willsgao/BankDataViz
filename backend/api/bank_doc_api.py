# -*- coding:utf-8 -*-
"""
银行数据文档管理 API

独立的银行数据文档上传接口，专门用于"数据看板-文档"页面的文件上传。
与待处理文件(PDF)和成品文件(excel_api)完全分离。

接口列表：
- POST   /api/bank-doc/upload              - 上传银行数据文档
- POST   /api/bank-doc/upload/confirm      - 确认覆盖上传
- GET    /api/bank-doc/list                - 获取文档列表
- GET    /api/bank-doc/<id>                - 获取单个文档详情
- GET    /api/bank-doc/download/<id>       - 下载文档
- DELETE /api/bank-doc/<id>                - 删除文档
- PATCH  /api/bank-doc/<id>               - 更新文档信息
- GET    /api/bank-doc/stats               - 获取统计信息
"""

import os
import uuid
import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file

from backend.configs.config import config

# 创建蓝图
bank_doc_bp = Blueprint('bank_doc', __name__, url_prefix='/api/bank-doc')

# 数据库路径
DATABASE_PATH = config.DATABASE_PATH

# 银行数据文档存储根目录
BANK_DOC_UPLOAD_DIR = os.path.join(
    config.MAIN_ROOT, 'data', 'backend', 'static', 'uploads', 'bank_documents'
)
os.makedirs(BANK_DOC_UPLOAD_DIR, exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'docx', 'doc', 'pdf', 'pptx', 'ppt', 'txt', 'csv'}


def get_file_save_path():
    """根据当前年份生成存储目录路径：bank_documents/{year}/"""
    year = str(datetime.now().year)
    target_dir = os.path.join(BANK_DOC_UPLOAD_DIR, year)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_bank_doc_table():
    """初始化银行数据文档表"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 创建银行数据文档表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                disk_name TEXT UNIQUE NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                file_type TEXT,
                category TEXT DEFAULT 'general',
                description TEXT,
                uploader_id TEXT,
                uploader_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0
            )
        ''')

        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bank_documents_filename 
            ON bank_documents(filename)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bank_documents_category 
            ON bank_documents(category)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bank_documents_deleted 
            ON bank_documents(deleted)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bank_documents_created_at 
            ON bank_documents(created_at)
        ''')

        conn.commit()
        print("[bank_doc_api] 银行数据文档表初始化完成")
        return True

    except Exception as e:
        print(f"[bank_doc_api] 表初始化失败: {e}")
        return False
    finally:
        conn.close()


# 在模块加载时初始化表
init_bank_doc_table()


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename):
    """获取文件扩展名"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def check_filename_exists(filename):
    """检查文件名是否已存在"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, filename, file_size, uploader_name, created_at 
            FROM bank_documents 
            WHERE filename = ? AND deleted = 0
        ''', (filename,))
        row = cursor.fetchone()
        return (True, dict(row)) if row else (False, None)
    finally:
        conn.close()


def save_document(file_info):
    """保存文档记录"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bank_documents 
            (filename, disk_name, file_path, file_size, file_type, category, description, uploader_id, uploader_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file_info['filename'],
            file_info['disk_name'],
            file_info['file_path'],
            file_info['file_size'],
            file_info.get('file_type', ''),
            file_info.get('category', 'general'),
            file_info.get('description', ''),
            file_info.get('uploader_id'),
            file_info.get('uploader_name', '未知')
        ))
        conn.commit()
        return (True, cursor.lastrowid)
    except Exception as e:
        conn.rollback()
        return (False, str(e))
    finally:
        conn.close()


def get_document_by_id(doc_id):
    """根据ID获取文档"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM bank_documents 
            WHERE id = ? AND deleted = 0
        ''', (doc_id,))
        row = cursor.fetchone()
        return (True, dict(row)) if row else (False, "文档不存在")
    finally:
        conn.close()


def get_documents(filters=None, page=1, page_size=20):
    """获取文档列表"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        where_clauses = ["deleted = 0"]
        params = []

        if filters:
            if filters.get('filename'):
                where_clauses.append("filename LIKE ?")
                params.append(f"%{filters['filename']}%")
            if filters.get('category'):
                # 支持多分类，用 LIKE 匹配（category 字段存储为 "industry,report" 格式）
                where_clauses.append("category LIKE ?")
                params.append(f"%{filters['category']}%")
            if filters.get('uploader_name'):
                where_clauses.append("uploader_name LIKE ?")
                params.append(f"%{filters['uploader_name']}%")
            if filters.get('start_date'):
                where_clauses.append("created_at >= ?")
                params.append(filters['start_date'])
            if filters.get('end_date'):
                where_clauses.append("created_at <= ?")
                params.append(filters['end_date'])

        where_sql = " AND ".join(where_clauses)

        # 获取总数
        count_sql = f"SELECT COUNT(*) FROM bank_documents WHERE {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]

        # 获取分页数据
        offset = (page - 1) * page_size
        data_sql = f'''
            SELECT * FROM bank_documents 
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        '''
        cursor.execute(data_sql, params + [page_size, offset])
        rows = cursor.fetchall()

        files = [dict(row) for row in rows]

        return (True, {
            'files': files,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })
    except Exception as e:
        return (False, str(e))
    finally:
        conn.close()


def _cleanup_empty_dirs(dir_path):
    """清理空的年份目录（不超过 BANK_DOC_UPLOAD_DIR）"""
    try:
        # 只清理年份级别的一层目录
        if (dir_path != BANK_DOC_UPLOAD_DIR 
            and os.path.isdir(dir_path) 
            and not os.listdir(dir_path)):
            os.rmdir(dir_path)
    except Exception as e:
        print(f"[bank_doc_api] 清理空目录失败: {e}")


def _do_delete_document(doc_id):
    """删除文档（软删除）- 内部函数"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 检查文档是否存在
        cursor.execute('SELECT file_path FROM bank_documents WHERE id = ? AND deleted = 0', (doc_id,))
        row = cursor.fetchone()
        if not row:
            return (False, "文档不存在")

        # 软删除
        cursor.execute('UPDATE bank_documents SET deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (doc_id,))
        conn.commit()

        # 删除物理文件
        file_path = row[0]
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                # 尝试清理空的年份/分类子目录
                _cleanup_empty_dirs(os.path.dirname(file_path))
            except Exception as e:
                print(f"[bank_doc_api] 删除物理文件失败: {e}")

        return (True, "文档已删除")
    except Exception as e:
        conn.rollback()
        return (False, str(e))
    finally:
        conn.close()


def _do_update_document(doc_id, data):
    """更新文档信息 - 内部函数"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        updates = []
        params = []

        if 'description' in data:
            updates.append("description = ?")
            params.append(data['description'])
        if 'categories' in data:
            # 支持多分类，用逗号分隔存储
            categories = ','.join(data['categories']) if isinstance(data['categories'], list) else str(data['categories'])
            updates.append("category = ?")
            params.append(categories)

        if not updates:
            return (False, "没有要更新的字段")

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(doc_id)

        sql = f"UPDATE bank_documents SET {', '.join(updates)} WHERE id = ? AND deleted = 0"
        cursor.execute(sql, params)
        conn.commit()

        if cursor.rowcount == 0:
            return (False, "文档不存在")

        return (True, "文档更新成功")
    except Exception as e:
        conn.rollback()
        return (False, str(e))
    finally:
        conn.close()


# ============================================================
# API 路由
# ============================================================

@bank_doc_bp.route('/upload', methods=['POST'])
def upload_document():
    """
    上传银行数据文档
    POST /api/bank-doc/upload
    Form Data: 
        - file: 文件
        - category: 分类 (industry/single_bank/report/general)
        - description: 描述
        - uploader_id: 上传者ID
        - uploader_name: 上传者名称
    """
    # 1. 检查请求
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "没有找到文件字段"}), 400

    file = request.files['file']
    category = request.form.get('category', 'general')
    description = request.form.get('description', '')
    overwrite = request.form.get('overwrite', 'false').lower() == 'true'

    # 2. 基础验证
    if file.filename == '':
        return jsonify({"success": False, "error": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "success": False, 
            "error": f"不支持的文件格式，只支持: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    # 3. 检查文件名是否重复
    original_filename = file.filename
    exists, existing_file = check_filename_exists(original_filename)

    if exists:
        if overwrite:
            # 覆盖模式：删除旧文件，更新记录
            try:
                # 删除旧物理文件
                if os.path.exists(existing_file['file_path']):
                    os.remove(existing_file['file_path'])
                
                # 软删除旧记录（这样新上传会有新ID）
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE bank_documents SET deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (existing_file['id'],))
                conn.commit()
                conn.close()
            except Exception as e:
                return jsonify({"success": False, "error": f"删除旧文件失败: {str(e)}"}), 500
        else:
            # 非覆盖模式：返回重复提示
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
            }), 409

    # 4. 保存文件（按年份目录）
    try:
        file_size = len(file.read())
        file.seek(0)

        # 生成唯一文件名
        ext = get_file_extension(original_filename)
        disk_name = f"{uuid.uuid4().hex}.{ext}"
        save_dir = get_file_save_path()
        file_path = os.path.join(save_dir, disk_name)

        # 保存文件
        file.save(file_path)

        # 5. 保存数据库记录
        uploader_id = request.form.get('uploader_id') or request.form.get('user_id')
        uploader_name = request.form.get('uploader_name') or request.form.get('username') or '未知'

        file_info = {
            'filename': original_filename,
            'disk_name': disk_name,
            'file_path': file_path,
            'file_size': file_size,
            'file_type': ext,
            'category': category,
            'description': description,
            'uploader_id': uploader_id,
            'uploader_name': uploader_name
        }

        success, result = save_document(file_info)

        if success:
            return jsonify({
                "success": True,
                "message": "文档上传成功",
                "data": {
                    "id": result,
                    "filename": original_filename,
                    "disk_name": disk_name,
                    "file_size": file_size,
                    "file_size_display": format_file_size(file_size),
                    "file_path": file_path,
                    "file_type": ext,
                    "category": category,
                    "uploader_name": uploader_name,
                    "description": description,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        else:
            # 回滚
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"success": False, "error": f"数据库保存失败: {result}"}), 500

    except Exception as e:
        print(f"[bank_doc_api] 文件上传失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bank_doc_bp.route('/upload/confirm', methods=['POST'])
def confirm_upload():
    """
    确认覆盖上传（文件名重复时）
    POST /api/bank-doc/upload/confirm
    """
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "没有找到文件字段"}), 400

    file = request.files['file']
    category = request.form.get('category', 'general')
    description = request.form.get('description', '')

    if file.filename == '':
        return jsonify({"success": False, "error": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "不支持的文件格式"}), 400

    try:
        original_filename = file.filename
        file_size = len(file.read())
        file.seek(0)

        ext = get_file_extension(original_filename)
        disk_name = f"{uuid.uuid4().hex}.{ext}"
        save_dir = get_file_save_path()
        file_path = os.path.join(save_dir, disk_name)

        file.save(file_path)

        uploader_id = request.form.get('uploader_id') or request.form.get('user_id')
        uploader_name = request.form.get('uploader_name') or request.form.get('username') or '未知'

        file_info = {
            'filename': original_filename,
            'disk_name': disk_name,
            'file_path': file_path,
            'file_size': file_size,
            'file_type': ext,
            'category': category,
            'description': description,
            'uploader_id': uploader_id,
            'uploader_name': uploader_name
        }

        success, result = save_document(file_info)

        if success:
            return jsonify({
                "success": True,
                "message": "文档上传成功",
                "data": {
                    "id": result,
                    "filename": original_filename,
                    "disk_name": disk_name,
                    "file_size": file_size,
                    "file_size_display": format_file_size(file_size),
                    "file_path": file_path,
                    "file_type": ext,
                    "category": category,
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
        print(f"[bank_doc_api] 确认上传失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bank_doc_bp.route('/list', methods=['GET'])
def list_documents():
    """
    获取文档列表
    GET /api/bank-doc/list
    Query Params:
        - category: 分类筛选 (industry/single_bank/report/general)
        - filename: 文件名搜索
        - uploader_name: 上传人搜索
        - start_date: 开始日期
        - end_date: 结束日期
        - page: 页码
        - page_size: 每页数量
    """
    try:
        category = request.args.get('category')
        filename = request.args.get('filename', '')
        uploader_name = request.args.get('uploader_name', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        filters = {}
        if category:
            filters['category'] = category
        if filename:
            filters['filename'] = filename
        if uploader_name:
            filters['uploader_name'] = uploader_name
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date

        success, result = get_documents(filters=filters, page=page, page_size=page_size)

        if success:
            # 格式化文件大小
            for doc in result['files']:
                doc['file_size_display'] = format_file_size(doc.get('file_size', 0))

            return jsonify({
                "success": True,
                "data": result
            })
        else:
            return jsonify({"success": False, "error": str(result)}), 500

    except Exception as e:
        print(f"[bank_doc_api] 获取文档列表失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bank_doc_bp.route('/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """
    获取单个文档详情
    GET /api/bank-doc/<id>
    """
    try:
        success, result = get_document_by_id(doc_id)

        if success:
            result['file_size_display'] = format_file_size(result.get('file_size', 0))
            return jsonify({
                "success": True,
                "data": result
            })
        else:
            return jsonify({"success": False, "error": result}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bank_doc_bp.route('/download/<int:doc_id>', methods=['GET'])
def download_document(doc_id):
    """
    下载文档
    GET /api/bank-doc/download/<id>
    """
    try:
        success, result = get_document_by_id(doc_id)

        if not success:
            return jsonify({"success": False, "error": "文档不存在"}), 404

        file_path = result.get('file_path')
        filename = result.get('filename')
        file_type = result.get('file_type', '')

        if not file_path or not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件物理路径不存在"}), 404

        # 根据文件类型设置MIME
        mime_types = {
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xls': 'application/vnd.ms-excel',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'pdf': 'application/pdf',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'ppt': 'application/vnd.ms-powerpoint',
            'txt': 'text/plain',
            'csv': 'text/csv'
        }
        mimetype = mime_types.get(file_type, 'application/octet-stream')

        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"[bank_doc_api] 下载文档失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bank_doc_bp.route('/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """
    删除文档
    DELETE /api/bank-doc/<id>
    """
    try:
        success, message = _do_delete_document(doc_id)

        if success:
            return jsonify({
                "success": True,
                "message": message
            })
        else:
            return jsonify({"success": False, "error": message}), 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bank_doc_bp.route('/<int:doc_id>', methods=['PATCH'])
def update_document(doc_id):
    """
    更新文档信息
    PATCH /api/bank-doc/<id>
    Body: { description?: string, category?: string }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "请求体不能为空"}), 400

        success, message = _do_update_document(doc_id, data)

        if success:
            return jsonify({
                "success": True,
                "message": message
            })
        else:
            return jsonify({"success": False, "error": message}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bank_doc_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    获取统计信息
    GET /api/bank-doc/stats
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 总文件数
        cursor.execute('SELECT COUNT(*) FROM bank_documents WHERE deleted = 0')
        total_count = cursor.fetchone()[0]

        # 总大小
        cursor.execute('SELECT COALESCE(SUM(file_size), 0) FROM bank_documents WHERE deleted = 0')
        total_size = cursor.fetchone()[0]

        # 各分类统计
        cursor.execute('''
            SELECT category, COUNT(*) as count, COALESCE(SUM(file_size), 0) as size 
            FROM bank_documents 
            WHERE deleted = 0 
            GROUP BY category
        ''')
        category_stats = [dict(row) for row in cursor.fetchall()]

        # 最近上传
        cursor.execute('''
            SELECT COUNT(*) 
            FROM bank_documents 
            WHERE deleted = 0 
            AND created_at >= datetime('now', '-7 days')
        ''')
        recent_count = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            "success": True,
            "data": {
                "total_count": total_count,
                "total_size": total_size,
                "total_size_display": format_file_size(total_size),
                "category_stats": category_stats,
                "recent_count": recent_count
            }
        })

    except Exception as e:
        print(f"[bank_doc_api] 获取统计信息失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bank_doc_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    获取文档分类列表
    GET /api/bank-doc/categories
    """
    categories = [
        {"value": "industry", "label": "行业板块"},
        {"value": "single_bank", "label": "单家银行"},
        {"value": "report", "label": "行业报告"},
        {"value": "general", "label": "综合文档"}
    ]
    return jsonify({
        "success": True,
        "data": categories
    })
