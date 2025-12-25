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


@upload_bp.route('/upload11', methods=['POST'])
def upload_file11():
    print("=" * 50)
    print("🔄 开始处理文件上传...")
    print("=" * 50)

    print(f"📁 UPLOAD - 数据库路径: {DATABASE}")

    # 检查请求内容
    if 'file' not in request.files:
        print("❌ 错误: 没有找到file字段")
        return make_response(jsonify({"error": "No file part"}), 400)

    file = request.files['file']

    # 检查文件内容
    file_content = file.read()
    file.seek(0)  # 重置文件指针
    file_size = len(file_content)
    print(f"📄 文件大小: {file_size} bytes")

    if file.filename == '':
        print("❌ 错误: 文件名为空")
        return make_response(jsonify({"error": "No selected file"}), 400)

    if not (file and allowed_file(file.filename)):
        print(f"❌ 文件类型不允许: {file.filename}")
        return make_response(jsonify({"error": "File type not allowed"}), 400)

    ext = os.path.splitext(file.filename)[1].lower()
    raw_name = file.filename
    print(f"✅ 文件验证通过")
    print(f"📝 原始文件名: {raw_name}")
    print(f"📝 文件扩展名: {ext}")

    # =================== 1. 计算文件哈希 ===================
    file_hash = calculate_file_hash(file_content)
    print(f"🔢 文件哈希: {file_hash}")

    # =================== 2. 检查是否重复 ===================
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # 检查表结构，添加需要的列
        c.execute("PRAGMA table_info(files)")
        columns = c.fetchall()
        existing_cols = {col[1] for col in columns}

        # 需要添加的列（只对新文件）
        new_columns = {
            'file_hash': 'TEXT',  # 新增：文件哈希
            'file_size': 'INTEGER',  # 新增：文件大小
            'upload_count': 'INTEGER DEFAULT 1',  # 新增：上传次数
            'last_uploaded': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'  # 新增：最后上传时间
        }

        for col_name, col_type in new_columns.items():
            if col_name not in existing_cols:
                print(f"🔧 添加缺失列: {col_name} {col_type}")
                try:
                    c.execute(f"ALTER TABLE files ADD COLUMN {col_name} {col_type}")
                    conn.commit()
                    print(f"✅ 列 {col_name} 添加成功")
                except Exception as e:
                    print(f"⚠️ 添加列 {col_name} 失败: {e}")
                    # 继续执行，不影响主要逻辑

        # 检查是否已有相同内容的文件（只检查有哈希值的）
        c.execute("""
            SELECT id, filename, raw_filename, upload_count, created_at 
            FROM files 
            WHERE file_hash = ? AND deleted = 0 AND file_hash IS NOT NULL
            LIMIT 1
        """, (file_hash,))

        existing_file = c.fetchone()

        # 在重复文件处理部分（if existing_file: 内部）
        if existing_file:
            # 文件已存在，更新上传次数
            file_id = existing_file[0]  # 数据库中的id
            disk_name = existing_file[1]
            raw_name_in_db = existing_file[2]
            upload_count = existing_file[3] + 1
            created_at = existing_file[4]

            # 从disk_name中提取file_id（去掉扩展名）
            existing_file_id = disk_name.split('.')[0] if '.' in disk_name else disk_name

            print(f"🔄 发现重复文件，内容完全相同")
            print(f"   文件ID: {file_id}")
            print(f"   磁盘文件名: {disk_name}")
            print(f"   文件ID(提取): {existing_file_id}")
            print(f"   原始文件名: {raw_name_in_db}")
            print(f"   上传次数: {upload_count}")

            # =================== 关键修复：添加映射 ===================
            print("🗂️ 添加到文件映射（重复文件）...")
            try:
                # 即使文件重复，也要为当前请求建立映射
                # 使用提取的existing_file_id，而不是新生成的
                # 注意：这里使用当前请求的原始文件名raw_name，而不是数据库中的raw_name_in_db
                file_mapping_service.add_mapping(existing_file_id, raw_name, ext[1:].lower())
                print(f"✅ 重复文件映射添加成功")
            except Exception as e:
                print(f"⚠️ 重复文件映射添加失败: {e}")
            # =========================================================

            # 更新上传次数和最后上传时间
            c.execute("""
                UPDATE files 
                SET upload_count = ?, last_uploaded = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (upload_count, file_id))
            conn.commit()

            # 返回已存在的文件信息
            response_data = {
                "success": True,
                "id": file_id,
                "filename": raw_name,  # 注意：这里应该返回当前上传的文件名，不是数据库中的
                "file_type": ext[1:] if ext.startswith('.') else ext,
                "disk_name": disk_name,
                "file_id": existing_file_id,  # 使用已有的file_id
                "message": "文件已存在（内容相同），直接使用现有文件",
                "duplicate": True,
                "upload_count": upload_count,
                "created_at": created_at,
                "file_size": file_size
            }

            print(f"✅ 返回重复文件信息")
            print("=" * 50)

            return jsonify(response_data)

    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("🔒 数据库连接已关闭（去重检查）")

    # =================== 3. 新文件处理 ===================
    # 3.1 生成唯一ID作为存储文件名（只有新文件才需要）
    file_id = str(uuid.uuid4())
    real_name = f"{file_id}{ext}"
    path = Path(MAIN_ROOT) / UPLOAD_FOLDER / real_name

    print(f"🆔 生成新文件ID: {file_id}")
    print(f"📁 存储文件名: {real_name}")

    # 3.2 确保上传目录存在
    upload_dir = Path(MAIN_ROOT) / UPLOAD_FOLDER
    if not upload_dir.exists():
        print(f"📁 创建上传目录: {upload_dir}")
        upload_dir.mkdir(parents=True, exist_ok=True)

    # 3.3 保存文件内容
    print("💾 保存新文件...")
    try:
        # 注意：file.read() 已经在前面调用过，需要重置指针
        file.seek(0)
        content = file.read()

        path.write_bytes(content)
        print(f"💾 文件已保存到: {path}")

        if not path.exists():
            print("❌ 物理文件创建失败")
            return make_response(jsonify({"error": "文件保存失败"}), 500)

    except Exception as e:
        print(f"❌ 文件保存异常: {e}")
        return make_response(jsonify({"error": f"文件保存异常: {str(e)}"}), 500)

    # 3.4 添加到文件映射
    print("🗂️ 添加到文件映射...")
    try:
        file_mapping_service.add_mapping(file_id, raw_name, ext[1:].lower())
        print(f"✅ 文件映射添加成功")
    except Exception as e:
        print(f"⚠️ 文件映射添加失败: {e}")

    # 3.5 写入数据库
    print("💾 写入数据库记录...")
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # 插入新文件记录
        file_type = ext[1:] if ext.startswith('.') else ext
        print(f"📝 插入新文件记录")
        print(f"   文件名: {real_name}")
        print(f"   类型: {file_type}")
        print(f"   原始名: {raw_name}")
        print(f"   文件哈希: {file_hash}")
        print(f"   文件大小: {file_size}")

        c.execute(
            """INSERT INTO files 
               (filename, file_type, raw_filename, deleted, file_hash, file_size, upload_count) 
               VALUES (?, ?, ?, 0, ?, ?, 1)""",
            (real_name, file_type, raw_name, file_hash, file_size)
        )
        new_id = c.lastrowid
        conn.commit()

        print(f"✅ 数据库插入成功 - 新记录ID: {new_id}")

    except Exception as e:
        print(f"❌ 数据库操作异常: {e}")
        if conn:
            conn.rollback()
        return make_response(jsonify({"error": f"数据库操作失败: {str(e)}"}), 500)
    finally:
        if conn:
            conn.close()
            print("🔒 数据库连接已关闭（插入记录）")

    # 3.6 返回成功响应
    print("📤 返回成功响应...")
    response_data = {
        "success": True,
        "id": new_id,
        "filename": raw_name,
        "file_type": file_type,
        "disk_name": real_name,
        "file_id": file_id,
        "file_hash": file_hash[:12],  # 返回哈希前12位用于调试
        "file_size": file_size,
        "upload_count": 1,
        "message": "新文件上传成功",
        "duplicate": False
    }

    print(f"✅ 新文件上传完成")
    print("=" * 50)

    return jsonify(response_data)

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

