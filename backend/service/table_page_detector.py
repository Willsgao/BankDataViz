# -*- coding:utf-8 -*-

from pathlib import Path
from ultralytics import YOLO
from pdf2image import convert_from_path

# 模型第一次会自动下载，放到项目目录方便离线
MODEL_PATH = Path(__file__).parent.parent / "weights" / "yolov8n.pt"
model = YOLO(MODEL_PATH)

def detect_table_pages1(pdf_path: Path, dpi: int = 72) -> list[int]:
    """
    返回含表格的页码（0-based）
    """
    images = convert_from_path(pdf_path, dpi=dpi)
    table_pages = []
    for idx, img in enumerate(images):
        results = model(img, verbose=False)
        # 只要检测出 table 类别（COCO 里 id=0 是 person，这里用自定义模型更准，但 demo 先这样）
        has_table = any(int(box.cls) == 0 for box in results[0].boxes)
        if has_table:
            table_pages.append(idx)
    return table_pages


def detect_table_pages(pdf_path: Path, dpi: int = 72, images: list = None) -> list[int]:
    """
    images=None 时内部转图；已传图则直接用
    """
    if images is None:
        images = convert_from_path(pdf_path, dpi=dpi)
    table_pages = []
    for idx, img in enumerate(images):
        results = model(img, verbose=False)
        if any(int(box.cls) == 0 for box in results[0].boxes):
            table_pages.append(idx)
    return table_pages