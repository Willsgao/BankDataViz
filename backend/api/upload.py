# -*- coding:utf-8 -*-

from flask import Blueprint, request, jsonify, make_response
from backend.utils.constants import UPLOAD_FOLDER, DATABASE, MAIN_ROOT
from backend.models.database_manager import DatabaseManager
import hashlib, pathlib, uuid, os
from pathlib import Path
import sqlite3

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




@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    print("=" * 50)
    print("🔄 开始处理文件上传...")
    print("=" * 50)

    print(f"📁 UPLOAD - 数据库路径: {DATABASE}")

    # 检查请求内容
    print(f"📦 请求方法: {request.method}")
    print(f"📦 请求Content-Type: {request.content_type}")
    print(f"📦 请求文件字段: {list(request.files.keys())}")

    if 'file' not in request.files:
        print("❌ 错误: 没有找到file字段")
        print(f"📦 可用的文件字段: {list(request.files.keys())}")
        return make_response(jsonify({"error": "No file part"}), 400)

    file = request.files['file']
    print(f"📄 接收到文件对象: {file}")
    print(f"📄 文件名: {file.filename}")
    print(f"📄 文件类型: {file.content_type}")

    # 检查文件内容
    file_content = file.read()
    file.seek(0)  # 重置文件指针
    print(f"📄 文件大小: {len(file_content)} bytes")

    if file.filename == '':
        print("❌ 错误: 文件名为空")
        return make_response(jsonify({"error": "No selected file"}), 400)

    print(f"🔍 检查文件扩展名...")
    if file and allowed_file(file.filename):
        ext = os.path.splitext(file.filename)[1].lower()
        raw_name = file.filename
        print(f"✅ 文件验证通过")
        print(f"📝 原始文件名: {raw_name}")
        print(f"📝 文件扩展名: {ext}")

        # 1. 生成唯一ID作为存储文件名
        file_id = str(uuid.uuid4())
        real_name = f"{file_id}{ext}"
        path = Path(MAIN_ROOT) / UPLOAD_FOLDER / real_name

        print(f"🆔 生成文件ID: {file_id}")
        print(f"📁 存储文件名: {real_name}")
        print(f"📁 完整存储路径: {path}")
        print(f"📁 UPLOAD_FOLDER: {UPLOAD_FOLDER}")
        print(f"📁 MAIN_ROOT: {MAIN_ROOT}")

        # 2. 确保上传目录存在
        upload_dir = Path(MAIN_ROOT) / UPLOAD_FOLDER
        if not upload_dir.exists():
            print(f"📁 创建上传目录: {upload_dir}")
            upload_dir.mkdir(parents=True, exist_ok=True)

        # 3. 读取并保存文件内容
        print("💾 开始保存文件...")
        try:
            content = file.read()
            print(f"💾 读取到文件内容: {len(content)} bytes")

            path.write_bytes(content)
            print(f"💾 文件已保存到: {path}")

            # 验证文件是否真的保存成功
            if path.exists():
                file_size = path.stat().st_size
                print(f"✅ 物理文件创建成功 - 大小: {file_size} bytes")
            else:
                print("❌ 物理文件创建失败 - 文件不存在")
                return make_response(jsonify({"error": "文件保存失败"}), 500)

        except Exception as e:
            print(f"❌ 文件保存异常: {e}")
            return make_response(jsonify({"error": f"文件保存异常: {str(e)}"}), 500)

        # 4. 添加到文件映射
        print("🗂️ 添加到文件映射...")
        try:
            file_mapping_service.add_mapping(file_id, raw_name, ext[1:].lower())
            print(f"✅ 文件映射添加成功")
        except Exception as e:
            print(f"⚠️ 文件映射添加失败: {e}")

        # 5. 写入数据库
        print("💾 开始写入数据库...")
        conn = None
        try:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()

            # 检查表结构
            print("🔍 检查数据库表结构...")
            c.execute("PRAGMA table_info(files)")
            columns = c.fetchall()
            print(f"📋 表结构: {[col[1] for col in columns]}")

            # 自动补列
            need_cols = {'raw_filename': 'TEXT', 'deleted': 'INTEGER DEFAULT 0'}
            exist_cols = {col[1] for col in columns}
            for col, def_type in need_cols.items():
                if col not in exist_cols:
                    print(f"🔧 添加缺失列: {col} {def_type}")
                    c.execute(f"ALTER TABLE files ADD COLUMN {col} {def_type}")
                    conn.commit()

            # 插入文件记录
            file_type = ext[1:] if ext.startswith('.') else ext
            print(f"📝 插入文件记录 - 文件名: {real_name}, 类型: {file_type}, 原始名: {raw_name}")

            c.execute(
                "INSERT INTO files (filename, file_type, raw_filename, deleted) VALUES (?, ?, ?, 0)",
                (real_name, file_type, raw_name)
            )
            new_id = c.lastrowid
            conn.commit()

            print(f"✅ 数据库插入成功 - 新记录ID: {new_id}")

            # # 验证记录是否真的插入
            # c.execute("SELECT id, filename, raw_filename, file_type, deleted FROM files WHERE id = ?", (new_id,))
            # verified_row = c.fetchone()
            # if verified_row:
            #     print(f"🔍 数据库验证成功 - 记录: {dict(verified_row)}")
            # else:
            #     print("❌ 数据库验证失败 - 未找到插入的记录")

            # 在数据库插入成功后，修改验证代码：
            print(f"✅ 数据库插入成功 - 新记录ID: {new_id}")

            # 验证记录是否真的插入
            c.execute("SELECT id, filename, raw_filename, file_type, deleted FROM files WHERE id = ?", (new_id,))
            verified_row = c.fetchone()
            if verified_row:
                # 正确的方式访问行数据
                print(
                    f"🔍 数据库验证成功 - ID: {verified_row[0]}, 文件名: {verified_row[1]}, 原始名: {verified_row[2]}, 类型: {verified_row[3]}")
            else:
                print("❌ 数据库验证失败 - 未找到插入的记录")

        except Exception as e:
            print(f"❌ 数据库操作异常: {e}")
            if conn:
                conn.rollback()
            return make_response(jsonify({"error": f"数据库操作失败: {str(e)}"}), 500)
        finally:
            if conn:
                conn.close()
                print("🔒 数据库连接已关闭")

        # 6. 返回成功响应
        print("📤 返回成功响应...")
        response_data = {
            "id": new_id,
            "filename": raw_name,  # 返回原始中文名
            "file_type": file_type,
            "disk_name": real_name,  # 添加磁盘文件名用于调试
            "file_id": file_id,  # 添加文件ID用于调试
            "message": "文件上传并保存成功"
        }

        print(f"✅ 上传完成 - 返回数据: {response_data}")
        print("=" * 50)

        return make_response(
            jsonify(response_data),
            200,
            {'Content-Type': 'application/json'}
        )

    else:
        print(f"❌ 文件类型不允许: {file.filename}")
        print(f"📋 允许的扩展名: {ALLOWED_EXTENSIONS}")
        return make_response(jsonify({"error": "File type not allowed"}), 400)


