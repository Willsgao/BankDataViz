"""
PDF → PNG 转图蓝图
"""
import uuid
import io
import base64
from pathlib import Path
from flask import Blueprint, request, jsonify, send_from_directory
from backend.models.database_manager import DatabaseManager
from backend.utils.constants import UPLOAD_FOLDER, PNG_OUTPUT_ROOT
from backend.service.pdf_convert_service import background_convert_table_only
from backend.service.layout_service import batch_cut_tables


# 确保输出目录存在
Path(PNG_OUTPUT_ROOT).mkdir(parents=True, exist_ok=True)

convert_bp = Blueprint('convert', __name__)
db = DatabaseManager()


# ---------------- 1. 提交异步转图 ----------------
@convert_bp.post('/convert-pdf-async/<path:pdf_name>')
def api_convert_pdf_async(pdf_name: str):
    """接收中文或 UUID 文件名 → 返回 jobId"""
    real_name = _map_to_disk(pdf_name)
    if not real_name:
        return jsonify({"error": "PDF 不存在"}), 404

    pdf_path = Path(UPLOAD_FOLDER) / real_name
    out_dir = Path(PNG_OUTPUT_ROOT) / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    # 缓存命中直接返回
    existing = sorted(p.name for p in out_dir.glob("*.png"))
    if existing:
        return jsonify({"hitCache": True, "total": len(existing),
                        "pngs": existing, "folder": pdf_path.stem})

    job_id = uuid.uuid4().hex
    from backend.api.convert import PROGRESS          # 避免循环导入
    PROGRESS[job_id] = {"total": 0, "finished": 0, "percent": 0}
    background_convert_table_only(pdf_path, out_dir, job_id, PROGRESS)
    return jsonify({"jobId": job_id, "message": "任务已提交"})


# ---------------- 2. 轮询进度 ----------------
PROGRESS = {}     # 内存进度表


@convert_bp.get('/progress/<job_id>')
def api_progress(job_id: str):
    return jsonify(PROGRESS.get(job_id, {"state": "unknown", "percent": 0}))


# ---------------- 3. 列出某 PDF 的所有 PNG ----------------
@convert_bp.get('/png-list/<pdf_folder>')
def api_png_list(pdf_folder: str):
    out_dir = Path(PNG_OUTPUT_ROOT) / pdf_folder
    if not out_dir.exists():
        return jsonify({"error": "PNG folder not found"}), 404
    pngs = sorted(p.name for p in out_dir.glob("*.png"))
    return jsonify({"total": len(pngs), "pngs": pngs})


# ---------------- 4. 单张 PNG 访问 ----------------
@convert_bp.get('/png/<pdf_folder>/<png_name>')
def api_serve_png(pdf_folder: str, png_name: str):
    return send_from_directory(Path(PNG_OUTPUT_ROOT) / pdf_folder, png_name)


# ---------------- 5. 旋转并保存 ----------------
@convert_bp.post('/png/rotate/<pdf_folder>/<png_name>')
def rotate_png(pdf_folder: str, png_name: str):
    angle = request.json.get('angle', 90)
    png_path = Path(PNG_OUTPUT_ROOT) / pdf_folder / png_name
    if not png_path.exists():
        return jsonify({"error": "PNG not found"}), 404

    from PIL import Image
    img = Image.open(png_path)
    rotated = img.rotate(-angle, expand=True)
    rotated.save(png_path)
    return jsonify({"message": "rotated and saved"})


# ---------------- 6. 保存前端裁剪子图 ----------------
@convert_bp.post('/save-rotated-sub/<folder>/<png_name>')
def save_rotated_sub(folder: str, png_name: str):
    try:
        data = request.get_json()
        img_bytes = base64.b64decode(data['image'])
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        save_dir = Path(PNG_OUTPUT_ROOT) / folder
        save_dir.mkdir(exist_ok=True)
        img.save(save_dir / png_name, format='PNG')
        return jsonify({'code': 0, 'msg': 'saved'})
    except Exception as e:
        return jsonify({'code': 1, 'msg': str(e)}), 500


# ---------------- 工具：中文/UUID → 磁盘名 ----------------
from sqlite3 import Cursor, Connection  # 需导入对应类型（假设使用sqlite3）

def _map_to_disk(filename: str) -> str | None:
    """返回磁盘文件名；若文件不存在或已软删则返回 None"""
    conn: Connection | None = db.connect()
    if not conn:
        return None
    try:
        c: Cursor = conn.cursor()
        c.execute(
            "SELECT filename FROM files "
            "WHERE (raw_filename = ? OR filename = ?) AND deleted = 0",
            (filename, filename)
        )
        row = c.fetchone()
        return row["filename"] if row else None
    except Exception as e:
        print(f"数据库查询错误: {e}")
        return None
    finally:
        conn.close()


# ---------------- 7. 单张 PNG 版面分区 ----------------
@convert_bp.get('/layout/<pdf_folder>/<png_name>')
def api_layout(pdf_folder: str, png_name: str):
    """
    对已经转图完成的单张 PNG 做版面检测
    返回：{ json: <原始 layout>, table_zones: [[x1,y1,x2,y2], ...] }
    """
    png_path = Path(PNG_OUTPUT_ROOT) / pdf_folder / png_name
    print("png_path111111::", png_path)
    if not png_path.exists():
        return jsonify({"error": "PNG not found"}), 404
    print("png_path22222222::", png_path)
    try:
        from backend.service.layout_service import layout_detect
        result = layout_detect(png_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- 8. 批量切割图表 版面分区 ----------------
# @convert_bp.route('/batch-cut-table/<task_id>', methods=['POST', 'OPTIONS'])  # 显式添加 OPTIONS 方法
@convert_bp.route('/batch-cut-table1/<task_id>', methods=['POST', 'OPTIONS'])
def batch_cut_table1(task_id):
    """
    批量裁切图片中的表格
    请求体：
    {
        "pdf_folder": "子文件夹名称",  # 图片所在文件夹（相对于PNG_OUTPUT_ROOT）
        "png_names": ["img1.png", "img2.png", ...]  # 需要处理的图片文件名列表
    }
    """
    print("11111111111")
    # 处理跨域预检请求
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    # 解析请求参数
    try:
        data = request.get_json()
        pdf_folder = data.get('pdf_folder')
        png_names = data.get('png_names', [])
        print("22222222222:", data)

        # 参数校验
        if not pdf_folder or not isinstance(png_names, list) or len(png_names) == 0:
            return jsonify({
                "error": "参数错误：需提供非空的pdf_folder和png_names列表"
            }), 400

        # 调用服务层批量裁切逻辑
        batch_results = batch_cut_tables(
            pdf_folder=pdf_folder,
            png_names=png_names,
            output_root=PNG_OUTPUT_ROOT
        )


        # 统计结果
        success_count = sum(1 for res in batch_results if res["success"])
        total = len(batch_results)

        print("444444444444444")

        return jsonify({
            "task_id": task_id,
            "total": total,
            "success_count": success_count,
            "fail_count": total - success_count,
            "message": f"批量处理完成，成功{success_count}/{total}张",
            "details": batch_results
        })

    except Exception as e:
        return jsonify({"error": f"接口处理失败: {str(e)}"}), 500


@convert_bp.route('/batch-cut-table/<task_id>', methods=['POST', 'OPTIONS'])
def batch_cut_table(task_id):
    """
    批量裁切图片中的表格
    """
    print("11111111111")
    # 处理跨域预检请求
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    # 解析请求参数
    try:
        data = request.get_json()
        pdf_folder = data.get('pdf_folder')
        png_names = data.get('png_names', [])
        print("22222222222:", data)

        # 参数校验
        if not pdf_folder or not isinstance(png_names, list) or len(png_names) == 0:
            return jsonify({
                "success": False,
                "error": "参数错误：需提供非空的pdf_folder和png_names列表"
            }), 400

        # 调用服务层批量裁切逻辑
        batch_result = batch_cut_tables(
            pdf_folder=pdf_folder,
            png_names=png_names,
            output_root=PNG_OUTPUT_ROOT
        )

        print("444444444444444")
        print(batch_result)

        # 直接返回 batch_result
        return jsonify(batch_result)

    except Exception as e:
        print(f"❌ 接口处理异常: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": f"接口处理失败: {str(e)}"
        }), 500


@convert_bp.get('/api/folder-images/<path:folder_path>')
def api_folder_images(folder_path: str):
    """获取文件夹中的图片列表"""
    folder_dir = Path("static") / folder_path
    if not folder_dir.exists():
        return jsonify({"success": False, "error": "文件夹不存在"}), 404

    images = []
    for img_file in sorted(folder_dir.glob("*.png")):
        images.append({
            "name": img_file.name,
            "url": f"/{folder_path}/{img_file.name}"
        })

    return jsonify({
        "success": True,
        "data": {
            "images": images,
            "total": len(images)
        }
    })

