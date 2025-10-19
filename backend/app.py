#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
@Project    ：DocuVista
@File       ：app.py
@Author     ：IronmanJay
@Date       ：2025/7/28 13:34
@Describe   ：后端主程序
"""

import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

from concurrent.futures import ThreadPoolExecutor
import atexit

executor = ThreadPoolExecutor(max_workers=4)
atexit.register(lambda executor=executor: executor.shutdown(wait=True, cancel_futures=True))


# 配置
UPLOAD_FOLDER = 'static/uploads'
DATABASE = 'data/database.db'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)


def init_db():
    """
    数据库初始化
    :return: None
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # 创建文本表
    c.execute('''CREATE TABLE IF NOT EXISTS texts
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     content
                     TEXT
                 )''')

    # 创建文件表
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     filename
                     TEXT
                     NOT
                     NULL,
                     file_type
                     TEXT
                     NOT
                     NULL,
                     created_at
                     TIMESTAMP
                     DEFAULT
                     CURRENT_TIMESTAMP
                 )''')

    # 检查并初始化文本记录
    c.execute("SELECT COUNT(*) FROM texts")
    count = c.fetchone()[0]
    if count == 0:
        c.execute("INSERT INTO texts (content) VALUES (?)", ('',))
        print("初始化了一条空文本记录")
    elif count > 1:
        print(f"警告: 文本表中有 {count} 条记录，应该只有1条")

    conn.commit()
    conn.close()
    print("数据库初始化完成")

# 数据库初始化
init_db()

def allowed_file(filename):
    """
    辅助函数
    :param filename: 目标文件名
    :return: 格式化后的文件名
    """
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    文件上传
    :return: 文件是否上传成功
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        # 保存到数据库
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        file_type = filename.split('.')[-1].lower()
        c.execute("INSERT INTO files (filename, file_type) VALUES (?, ?)",
                  (filename, file_type))
        # 获取新插入的ID
        new_id = c.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            "id": new_id,
            "filename": filename,
            "file_type": file_type,
            "message": "文件上传并保存成功"
        })

    return jsonify({"error": "File type not allowed"}), 400


@app.route('/files', methods=['GET'])
def list_files():
    """
    列出所有文件
    :return: 所有文件信息
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, filename, file_type, created_at FROM files ORDER BY created_at DESC")
    # 创建字典列表保持前端向后兼容
    files = []
    for row in c.fetchall():
        files.append({
            "id": row[0],
            "filename": row[1],
            "file_type": row[2],
            "created_at": row[3]
        })
    conn.close()
    return jsonify(files)


@app.route('/file/<filename>', methods=['GET'])
def get_file(filename):
    """
    获取单个文件
    :param filename: 目标文件名
    :return: 单个文件信息
    """
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/text', methods=['GET', 'POST'])
def text():
    """
    文本处理
    :return: 文本是否处理成功
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if request.method == 'GET':
        c.execute("SELECT content FROM texts WHERE id=1")
        result = c.fetchone()
        conn.close()
        content = result[0] if result else ""
        return jsonify({"content": content})
    else:
        data = request.json
        c.execute("UPDATE texts SET content=? WHERE id=1", (data['content'],))
        conn.commit()
        conn.close()
        return jsonify({"status": "saved", "message": "富文本内容已保存"})


@app.route('/database', methods=['GET'])
def get_database():
    """
    获取数据库内容
    :return: 获取到的数据库内容
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # 获取文本内容
    c.execute("SELECT * FROM texts")
    texts = [{"id": row[0], "content": row[1]} for row in c.fetchall()]

    # 获取文件内容
    c.execute("SELECT * FROM files")
    files = [{"id": row[0], "filename": row[1], "type": row[2], "created_at": row[3]}
             for row in c.fetchall()]

    conn.close()

    return jsonify({
        "texts": texts,
        "files": files
    })


# ===== 新增：删除文件接口 =====
@app.route('/file/<filename>', methods=['DELETE'])
def delete_file(filename):
    """删除单个文件 + 数据库记录"""
    try:
        # 1. 删数据库记录
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("DELETE FROM files WHERE filename = ?", (filename,))
        conn.commit()
        conn.close()

        # 2. 删硬盘文件
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({'message': '已删除'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 放在所有 import 之后，Flask 实例之后
from pathlib import Path
from backend.service.pdf_convert_service import PdfConvertService, background_convert, background_convert_table_only   # 关键 1

UPLOAD_FOLDER = 'static/uploads'
PNG_OUTPUT_ROOT = 'static/pdf2pngs'          # 统一放 PNG 的根目录
Path(PNG_OUTPUT_ROOT).mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# ② 列出某 PDF 的所有 PNG 文件名
# -------------------------------------------------
@app.route('/api/png-list/<pdf_folder>')
def api_png_list(pdf_folder: str):
    """
    pdf_folder 就是上一步返回的 folder 字段
    """
    out_dir = Path(PNG_OUTPUT_ROOT) / pdf_folder
    if not out_dir.exists():
        return jsonify({"error": "PNG folder not found"}), 404
    pngs = sorted(out_dir.glob("*.png"))
    return jsonify({
        "total": len(pngs),
        "pngs":  [p.name for p in pngs]
    })

# -------------------------------------------------
# ③ 单张 PNG 访问
# -------------------------------------------------
@app.route('/api/png/<pdf_folder>/<png_name>')
def api_serve_png(pdf_folder: str, png_name: str):
    out_dir = Path(PNG_OUTPUT_ROOT) / pdf_folder
    return send_from_directory(out_dir, png_name)

from concurrent.futures import ThreadPoolExecutor
import uuid
executor = ThreadPoolExecutor(max_workers=4)
PROGRESS = {}     # 内存进度表


# ---------- 异步转图进度查询 ----------
@app.route('/api/progress/<job_id>')
def api_progress(job_id):
    """
    返回当前 job 的进度
    格式：{ "state": "running" | "done" | "error", "percent": 0~100 }
    """
    if job_id not in PROGRESS:
        return jsonify({"state": "unknown", "percent": 0}), 404
    return jsonify(PROGRESS[job_id])



# -------------------------------------------------
# ① 提交转图任务（异步秒返回）  --  REWRITTEN
# -------------------------------------------------
@app.route('/api/convert-pdf-async/<pdf_name>', methods=['POST'])
def api_convert_pdf_async(pdf_name: str):
    pdf_path = Path(UPLOAD_FOLDER) / pdf_name
    print("YYYYYYYYYYYYYYY")
    if not pdf_path.exists():
        return jsonify({"error": "PDF not found"}), 404

    out_dir = Path(PNG_OUTPUT_ROOT) / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    # fast cache-hit check
    existing = [p.name for p in out_dir.glob("*.png")]
    if existing:
        return jsonify({"hitCache": True, "total": len(existing),
                        "pngs": sorted(existing), "folder": pdf_path.stem})

    job_id = uuid.uuid4().hex
    # 先占坑，避免前端第一次轮询 404
    PROGRESS[job_id] = {"total": 0, "finished": 0, "percent": 0}
    executor.submit(background_convert_table_only, pdf_path, out_dir, job_id, PROGRESS)
    return jsonify({"jobId": job_id, "message": "任务已提交"})



# -------------------------------------------------
# ② 同步转图接口（可选保留） --  REWRITTEN
# -------------------------------------------------
@app.route('/api/convert-pdf/<pdf_name>', methods=['POST'])
def api_convert_pdf(pdf_name: str):
    pdf_path = Path(UPLOAD_FOLDER) / pdf_name
    if not pdf_path.exists():
        return jsonify({"error": "PDF not found"}), 404

    out_dir = Path(PNG_OUTPUT_ROOT) / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 直接调用流式单页版（阻塞，适合小文件）
        from backend.service.pdf_convert_service import background_convert_table_only
        job_id = uuid.uuid4().hex
        background_convert_table_only(pdf_path, out_dir, job_id, PROGRESS)   # 同步执行
        pngs = sorted(p.name for p in out_dir.glob("*.png"))
        return jsonify({"total": len(pngs), "pngs": pngs, "folder": pdf_path.stem})
    except Exception as e:
        return jsonify({"error": f"convert failed: {e}"}), 500



# 放在文件尾部，与其他 import 放一起即可
from backend.pipeline.pipeline import Pipeline
executor = ThreadPoolExecutor(max_workers=2)
PROGRESS_PIPE = {}          # 简易内存进度表

@app.route('/api/pipeline/<pdf_name>', methods=['POST'])
def submit_pipeline(pdf_name: str):
    job_id = uuid.uuid4().hex
    PROGRESS_PIPE[job_id] = {"state": "running", "percent": 0}
    def run():
        try:
            PROGRESS_PIPE[job_id]["percent"] = 20
            path = Pipeline(pdf_name.replace('.pdf','')).run()
            PROGRESS_PIPE[job_id] = {"state": "done", "percent": 100, "url": f"/static/pipeline_cache/{pdf_name.replace('.pdf','')}/final.xlsx"}
        except Exception as e:
            PROGRESS_PIPE[job_id] = {"state": "error", "percent": -1, "msg": str(e)}
    executor.submit(run)
    return jsonify(jobId=job_id)


@app.route('/api/pipeline/progress/<job_id>')
def pipe_progress(job_id: str):
    return jsonify(PROGRESS_PIPE.get(job_id, {"state": "unknown", "percent": 0}))





@app.route('/api/png/rotate/<pdf_folder>/<png_name>', methods=['POST'])
def rotate_png(pdf_folder: str, png_name: str):
    angle = request.json.get('angle', 90)  # 默认顺时针90度
    png_path = Path(PNG_OUTPUT_ROOT) / pdf_folder / png_name
    if not png_path.exists():
        return jsonify({"error": "PNG not found"}), 404

    img = Image.open(png_path)
    rotated = img.rotate(-angle, expand=True)  # PIL逆时针为正，所以取负
    rotated.save(png_path)

    return jsonify({"message": "rotated and saved"})





from flask import Blueprint, request, jsonify
import base64, io, os
from PIL import Image

# 后端 app.py 中
rotate_bp = Blueprint('rotate', __name__, url_prefix='/api')  # 蓝图 prefix 为 /api


@rotate_bp.post('/save-rotated-sub/<folder>/<pngName>')
def save_rotated_sub(folder, pngName):
    try:
        data = request.get_json()
        image_b64 = data['image']  # 前端已处理前缀，无需再split
        img_bytes = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(img_bytes))

        # 保存到与前端访问一致的目录（PNG_OUTPUT_ROOT）
        save_dir = os.path.join(PNG_OUTPUT_ROOT, folder)  # 关键修改
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, pngName)
        img.save(save_path, format='PNG')

        return jsonify({'code': 0, 'msg': 'saved'})
    except Exception as e:
        return jsonify({'code': 1, 'msg': str(e)}), 500


# 在文件末尾，app.run()之前添加
app.register_blueprint(rotate_bp)  # 注册旋转相关的蓝图


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
