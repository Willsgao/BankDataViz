"""
图片操作模块
"""
import base64
import io
from pathlib import Path
from flask import jsonify, send_from_directory
from PIL import Image


def get_png_list(pdf_folder, output_dir):
    """列出某 PDF 的所有 PNG"""
    out_dir = Path(output_dir) / pdf_folder

    if not out_dir.exists():
        return jsonify({"error": "PNG folder not found"}), 404
    pngs = sorted(p.name for p in out_dir.glob("*.png"))
    return jsonify({"total": len(pngs), "pngs": pngs})


def serve_png(pdf_folder, png_name, output_dir):
    """单张 PNG 访问"""
    return send_from_directory(Path(output_dir) / pdf_folder, png_name)


def rotate_and_save(pdf_folder, png_name, output_dir, request):
    """旋转并保存"""
    angle = request.json.get('angle', 90)
    png_path = Path(output_dir) / pdf_folder / png_name
    if not png_path.exists():
        return jsonify({"error": "PNG not found"}), 404

    img = Image.open(png_path)
    rotated = img.rotate(-angle, expand=True)
    rotated.save(png_path)
    return jsonify({"message": "rotated and saved"})


def save_rotated_subimage(folder, png_name, output_dir, request):
    """保存前端裁剪子图"""
    try:
        data = request.get_json()
        img_bytes = base64.b64decode(data['image'])
        img = Image.open(io.BytesIO(img_bytes))
        save_dir = Path(output_dir) / folder
        save_dir.mkdir(exist_ok=True)
        img.save(save_dir / png_name, format='PNG')
        return jsonify({'code': 0, 'msg': 'saved'})
    except Exception as e:
        return jsonify({'code': 1, 'msg': str(e)}), 500


def detect_layout(pdf_folder, png_name, output_dir):
    """单张 PNG 版面分区"""
    png_path = Path(output_dir) / pdf_folder / png_name
    if not png_path.exists():
        return jsonify({"error": "PNG not found"}), 404

    try:
        from backend.service.layout_service import layout_detect
        result = layout_detect(png_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def batch_cut_tables_handler(task_id, output_dir, request):
    """批量切割图表 版面分区"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        pdf_folder = data.get('pdf_folder')
        png_names = data.get('png_names', [])

        if not pdf_folder or not isinstance(png_names, list) or len(png_names) == 0:
            return jsonify({
                "success": False,
                "error": "参数错误：需提供非空的pdf_folder和png_names列表"
            }), 400

        steps = data.get('steps')
        from backend.service.layout_service import batch_cut_tables
        batch_result = batch_cut_tables(
            pdf_folder=pdf_folder,
            png_names=png_names,
            output_root=output_dir,
            steps=steps
        )

        return jsonify(batch_result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"接口处理失败: {str(e)}"
        }), 500


def get_folder_images(folder_path, static_dir):
    """获取文件夹中的图片列表"""
    folder_dir = Path(static_dir) / folder_path
    if not folder_dir.exists():
        return jsonify({"success": False, "error": "文件夹不存在"}), 404

    images = []
    for img_file in sorted(folder_dir.glob("*.png")):
        images.append({
            "name": img_file.name,
            "url": f"/static/{folder_path}/{img_file.name}"
        })

    return jsonify({
        "success": True,
        "data": {
            "images": images,
            "total": len(images)
        }
    })


def serve_static_image(filename, joined_tables_dir):
    """提供 /static/converted/ 路径的图片访问"""
    try:
        parts = filename.split('/')
        if len(parts) < 2:
            return jsonify({"error": "Invalid filename format"}), 400

        folder = parts[0]
        png_name = parts[1]
        target_dir = Path(joined_tables_dir) / folder

        if target_dir.exists():
            return send_from_directory(str(target_dir), png_name)
        else:
            return jsonify({"error": "Directory not found"}), 404
    except Exception as e:
        return jsonify({"error": "File not found"}), 404