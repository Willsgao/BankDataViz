"""
文件相关蓝图
"""
from flask import Blueprint, request, jsonify, send_from_directory
from backend.models.database_manager import DatabaseManager
from backend.utils.constants import UPLOAD_FOLDER
from pathlib import Path

file_bp = Blueprint('file', __name__)

db = DatabaseManager()

# ---------- 1. 列表（不含软删） ----------
@file_bp.get('/files')
def list_files():
    conn = db.connect()
    if not conn:
        return jsonify({"error": "数据库连接失败"}), 500
    c = conn.cursor()
    c.execute(
        "SELECT id, filename, raw_filename, file_type, created_at "
        "FROM files WHERE deleted = 0 ORDER BY created_at DESC"
    )
    rows = c.fetchall()
    conn.close()

    return jsonify([
        {
            "id": r["id"],
            "filename": r["raw_filename"] or r["filename"],  # 优先中文
            "disk_name": r["filename"],                      # UUID 实体名
            "file_type": r["file_type"],
            "created_at": r["created_at"],
        }
        for r in rows
    ])


# ---------- 2. 下载/预览（不返回已软删） ----------
@file_bp.get('/file/<path:filename>')
def get_file(filename):
    """
    filename 可能是中文原始名，也可能是磁盘 UUID 名；
    一律先查库映射到真实磁盘名，且只返回未删除的。
    """
    conn = db.connect()
    if not conn:
        return jsonify({"error": "数据库连接失败"}), 500
    c = conn.cursor()
    c.execute(
        "SELECT filename FROM files "
        "WHERE (raw_filename = ? OR filename = ?) AND deleted = 0",
        (filename, filename)
    )
    row = c.fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "文件不存在或已隐藏"}), 404

    real_name = row["filename"]          # 磁盘 UUID 文件名
    return send_from_directory(UPLOAD_FOLDER, real_name)


# ---------- 3. 软删除 ----------
@file_bp.delete('/file/<path:filename>')
def delete_file(filename):
    """
    仅把 deleted 置 1，不真删磁盘文件
    """
    conn = db.connect()
    if not conn:
        return jsonify({"error": "数据库连接失败"}), 500
    c = conn.cursor()

    # 先找真实磁盘名
    c.execute(
        "SELECT filename FROM files "
        "WHERE (raw_filename = ? OR filename = ?) AND deleted = 0",
        (filename, filename)
    )
    row = c.fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "文件不存在"}), 404

    real_name = row["filename"]
    c.execute("UPDATE files SET deleted = 1 WHERE filename = ?", (real_name,))
    conn.commit()
    conn.close()
    return jsonify({"message": "已隐藏"}), 200