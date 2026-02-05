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


def get_db_connection():
    """获取数据库连接"""
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'database.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def check_and_fix_table_structure():
    """检查并修复文件表结构"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 检查表是否存在
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
        table_exists = c.fetchone()

        if not table_exists:
            # 创建新表
            c.execute('''
                CREATE TABLE files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    disk_name TEXT UNIQUE NOT NULL,
                    file_hash TEXT NOT NULL,
                    upload_count INTEGER DEFAULT 1,
                    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER,
                    bank_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ 创建文件表成功")
        else:
            # 检查是否存在 upload_time 列
            c.execute("PRAGMA table_info(files)")
            columns = [column[1] for column in c.fetchall()]
            print(f"🔍 当前表结构: {columns}")

            if 'upload_time' not in columns:
                print("🔄 添加 upload_time 列到文件表")
                c.execute('ALTER TABLE files ADD COLUMN upload_time DATETIME DEFAULT CURRENT_TIMESTAMP')

            if 'file_size' not in columns:
                print("🔄 添加 file_size 列到文件表")
                c.execute('ALTER TABLE files ADD COLUMN file_size INTEGER')

            if 'bank_name' not in columns:
                print("🔄 添加 bank_name 列到文件表")
                c.execute('ALTER TABLE files ADD COLUMN bank_name TEXT')

            if 'created_at' not in columns:
                print("🔄 添加 created_at 列到文件表")
                c.execute('ALTER TABLE files ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP')

        conn.commit()
        conn.close()
        print("✅ 数据库表结构检查完成")

    except Exception as e:
        print(f"❌ 检查表结构失败: {e}")


from backend.service.file_upload_service import file_upload_service

@upload_bp.route('/api/upload', methods=['POST'])
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



@upload_bp.route('/api/files111', methods=['GET'])
def get_all_files111():
    """获取所有文件列表 - 修复版本"""
    print("🔍🔍 upload_bp - 获取文件列表")
    try:
        conn = sqlite3.connect(DATABASE)
        if not conn:
            return jsonify({"error": "数据库连接失败"}), 500

        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 使用正确的列名：upload_time 而不是 created_at
        c.execute("""
            SELECT filename, raw_filename, file_type, upload_time
            FROM files 
            WHERE deleted = 0 
            ORDER BY upload_time DESC
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
                    "created_at": row['upload_time']  # 使用 upload_time 的值
                }
                files_list.append(file_info)

        conn.close()

        print(f"📊📊 返回文件数量: {len(files_list)}")
        return jsonify(files_list)

    except Exception as e:
        print(f"❌❌ 获取文件列表失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@upload_bp.route('/api/files', methods=['GET'])
def get_all_files():
    """获取所有文件列表 - 简化版本"""
    try:
        print("🔍🔍 获取文件列表请求")

        conn = sqlite3.connect(DATABASE)  # 直接使用 DATABASE 常量
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 只查询最基本肯定存在的字段
        c.execute("""
            SELECT id, filename, raw_filename, file_type, created_at
            FROM files 
            WHERE deleted = 0 
            ORDER BY created_at DESC
        """)

        rows = c.fetchall()
        files = []

        for row in rows:
            file_info = {
                "id": row["id"],
                "filename": row["raw_filename"] or row["filename"],  # 显示名
                "disk_name": row["filename"],  # 磁盘文件名
                "file_type": row["file_type"],
                "created_at": row["created_at"]
            }
            files.append(file_info)

        conn.close()

        print(f"✅ 返回 {len(files)} 个文件")
        return jsonify({
            "success": True,
            "files": files
        })

    except Exception as e:
        print(f"❌❌ 获取文件列表失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": True,  # 即使出错也返回成功，但文件列表为空
            "files": []
        })



# 在现有路由后面添加以下路由
@upload_bp.route('/api/files/stats', methods=['GET'])
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


@upload_bp.route('/api/files/duplicates', methods=['GET'])
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


@upload_bp.route('/api/files/<file_id>', methods=['GET'])
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


@upload_bp.route('/api/files/orphaned', methods=['GET'])
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


@upload_bp.route('/api/files/cleanup/<int:file_id>', methods=['DELETE'])
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


@upload_bp.route('/api/files/search', methods=['GET'])
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


@upload_bp.route('/api/files/recent', methods=['GET'])
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

