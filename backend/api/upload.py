# -*- coding:utf-8 -*-

from flask import Blueprint, request, jsonify, make_response
from backend.utils.constants import UPLOAD_FOLDER, DATABASE
from backend.models.database_manager import DatabaseManager
import hashlib, pathlib, uuid, os
from pathlib import Path
import sqlite3

from backend.utils.constants import ALLOWED_EXTENSIONS

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
    print("&&&&&&&&&&&&&&&&&&&")
    if 'file' not in request.files:
        return make_response(jsonify({"error": "No file part"}), 400)

    file = request.files['file']
    if file.filename == '':
        return make_response(jsonify({"error": "No selected file"}), 400)

    if file and allowed_file(file.filename):
        ext = os.path.splitext(file.filename)[1].lower()
        raw_name = file.filename

        # 1. 计算内容 MD5（同一文件永远同名）
        content = file.read()                      # 注意：read 后指针在末尾
        md5 = hashlib.md5(content).hexdigest()
        real_name = f"{md5}{ext}"
        path = Path(UPLOAD_FOLDER) / real_name

        # 2. 磁盘不存在才写
        if not path.exists():
            path.write_bytes(content)

        # 3. 写库（raw_filename 用原始中文名）
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
            (real_name, ext[1:], raw_name)
        )
        new_id = c.lastrowid
        conn.commit()
        conn.close()

        # 4. 返回（前端仍看中文名）
        return make_response(
            jsonify({
                "id": new_id,
                "filename": raw_name,
                "file_type": ext[1:],
                "message": "文件上传并保存成功"
            }),
            200,
            {'Content-Type': 'application/json'}
        )

    return make_response(jsonify({"error": "File type not allowed"}), 400)
