# -*- coding:utf-8 -*-
"""
版面检测蓝图：提供单张图片的版面分析接口
GET /api/layout/<pdf_folder>/<png_name>
"""
from pathlib import Path
from flask import Blueprint, jsonify
from backend.utils.constants import PNG_OUTPUT_ROOT
from backend.service.layout_service import layout_detect

layout_bp = Blueprint('layout', __name__)


@layout_bp.get('/api/layout/<pdf_folder>/<png_name>')
def api_layout(pdf_folder: str, png_name: str):
    png_path = Path(PNG_OUTPUT_ROOT) / pdf_folder / png_name
    if not png_path.exists():
        # 统一失败格式
        return jsonify({
            "success": False,
            "error": f"PNG file not found: {png_name}",
            "message": "图片不存在"
        }), 404
    try:
        result = layout_detect(png_path)
        # 统一成功格式
        return jsonify({
            "success": True,
            "data": result,
            "message": "版面检测成功"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "版面检测失败"
        }), 500