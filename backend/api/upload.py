# -*- coding:utf-8 -*-

from flask import Blueprint, request, jsonify, make_response
from backend.utils.constants import UPLOAD_FOLDER, DATABASE
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

@upload_bp.route('/upload1', methods=['POST'])
def upload_file1():
    if 'file' not in request.files:
        return make_response(jsonify({"error": "No file part"}), 400)

    file = request.files['file']
    if file.filename == '':
        return make_response(jsonify({"error": "No selected file"}), 400)

    if file and allowed_file(file.filename):
        ext = os.path.splitext(file.filename)[1].lower()
        raw_name = file.filename  # 原始的带中文的文件名

        # 1. 生成唯一ID作为存储文件名（代替MD5）
        file_id = str(uuid.uuid4())
        real_name = f"{file_id}{ext}"  # 使用UUID作为存储文件名
        path = Path(UPLOAD_FOLDER) / real_name

        # 2. 读取并保存文件内容
        content = file.read()
        path.write_bytes(content)

        # 3. 添加到文件映射（记录原始中文名）
        file_mapping_service.add_mapping(file_id, raw_name, ext[1:].lower())

        # 4. 写库（同时保存ID和原始中文名）
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # 自动补列（首次运行）
        need_cols = {'raw_filename': 'TEXT', 'deleted': 'INTEGER DEFAULT 0'}
        c.execute("PRAGMA table_info(files)")
        exist_cols = {col[1] for col in c.fetchall()}
        for col, def_type in need_cols.items():
            if col not in exist_cols:
                c.execute(f"ALTER TABLE files ADD COLUMN {col} {def_type}")
                conn.commit()

        c.execute(
            "INSERT INTO files (filename, file_type, raw_filename, deleted) VALUES (?, ?, ?, 0)",
            (real_name, ext[1:], raw_name)  # filename存储UUID名称，raw_filename存储原始中文名
        )
        new_id = c.lastrowid
        conn.commit()
        conn.close()

        # 5. 返回原始中文名给前端
        return make_response(
            jsonify({
                "id": new_id,
                "filename": raw_name,  # 返回原始中文名
                "file_type": ext[1:],
                "message": "文件上传并保存成功"
            }),
            200,
            {'Content-Type': 'application/json'}
        )

    return make_response(jsonify({"error": "File type not allowed"}), 400)


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return make_response(jsonify({"error": "No file part"}), 400)

    file = request.files['file']
    if file.filename == '':
        return make_response(jsonify({"error": "No selected file"}), 400)

    if file and allowed_file(file.filename):
        ext = os.path.splitext(file.filename)[1].lower()
        raw_name = file.filename  # 原始的带中文的文件名

        # 1. 生成唯一ID作为存储文件名 - 使用UUID格式
        file_id = str(uuid.uuid4())
        real_name = f"{file_id}{ext}"  # 使用UUID作为存储文件名
        path = Path(UPLOAD_FOLDER) / real_name

        # 2. 读取并保存文件内容
        content = file.read()
        path.write_bytes(content)

        # 3. 添加到文件映射（记录原始中文名）
        file_mapping_service.add_mapping(file_id, raw_name, ext[1:].lower())

        # 4. 写库（使用相同的UUID作为文件名）
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # 自动补列（首次运行）
        need_cols = {'raw_filename': 'TEXT', 'deleted': 'INTEGER DEFAULT 0'}
        c.execute("PRAGMA table_info(files)")
        exist_cols = {col[1] for col in c.fetchall()}
        for col, def_type in need_cols.items():
            if col not in exist_cols:
                c.execute(f"ALTER TABLE files ADD COLUMN {col} {def_type}")
                conn.commit()

        # 使用UUID作为文件名存储
        c.execute(
            "INSERT INTO files (filename, file_type, raw_filename, deleted) VALUES (?, ?, ?, 0)",
            (real_name, ext[1:], raw_name)  # filename存储UUID名称
        )
        new_id = c.lastrowid
        conn.commit()
        conn.close()

        # 5. 返回原始中文名给前端
        return make_response(
            jsonify({
                "id": new_id,
                "filename": raw_name,  # 返回原始中文名
                "file_type": ext[1:],
                "message": "文件上传并保存成功"
            }),
            200,
            {'Content-Type': 'application/json'}
        )

    return make_response(jsonify({"error": "File type not allowed"}), 400)