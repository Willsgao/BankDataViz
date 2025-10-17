# -*- coding:utf-8 -*-
"""
多通道表格 bbox 召回 + NMS 合并
author : you
date   : 2025-10-17
"""
from pathlib import Path
from typing import List, Tuple
import numpy as np
import pdfplumber

# ---------- 一、懒加载 YOLO ----------
_MODEL_PATH = Path(__file__).parent.parent / "weights" / "yolov8n.pt"
_yolo = None

def _get_yolo():
    global _yolo
    if _yolo is None:
        from ultralytics import YOLO
        _yolo = YOLO(_MODEL_PATH)
    return _yolo

# ---------- 二、通道1：YOLO 视觉 ----------
def _ch1_yolo(pdf_path: Path, dpi: int = 72) -> List[Tuple[int, Tuple[int, int, int, int]]]:
    from pdf2image import convert_from_path
    images = convert_from_path(pdf_path, dpi=dpi)
    model = _get_yolo()
    bboxes = []
    for page_idx, img in enumerate(images):
        results = model(img, verbose=False)
        w, h = img.size
        for b in results[0].boxes:
            if int(b.cls) == 0:          # 0 号类别是 table
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                bboxes.append((page_idx, (int(x1), int(y1), int(x2), int(y2))))


    return bboxes

# ---------- 三、通道2：pdfplumber 线条 ----------
def _ch2_lines(pdf_path: Path) -> List[Tuple[int, Tuple[int, int, int, int]]]:
    bboxes = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            lines = page.lines or []
            if not lines:
                continue
            # 所有横线/竖线的外接矩形
            xs = [l['x0'] for l in lines] + [l['x1'] for l in lines]
            ys = [l['y0'] for l in lines] + [l['y1'] for l in lines]
            if not xs:
                continue
            bbox = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
            bboxes.append((page_idx, bbox))
    return bboxes

# ---------- 四、通道3：文本块聚类（无框表） ----------
def _ch3_text_cluster(pdf_path: Path) -> List[Tuple[int, Tuple[int, int, int, int]]]:
    bboxes = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            chars = page.chars
            if not chars:
                continue
            # 按 y 中心聚行
            ys = [int((c['y0'] + c['y1']) / 2) for c in chars]
            cols = [int((c['x0'] + c['x1']) / 2) for c in chars]
            # 简单 heuristic：行数 > 4 且列数 > 2
            uniq_y = sorted(set(ys))
            uniq_x = sorted(set(cols))
            if len(uniq_y) > 4 and len(uniq_x) > 2:
                x0, y0, x1, y1 = min(c['x0'] for c in chars), min(c['y0'] for c in chars), \
                                 max(c['x1'] for c in chars), max(c['y1'] for c in chars)
                bboxes.append((page_idx, (int(x0), int(y0), int(x1), int(y1))))
    return bboxes

# ---------- 五、NMS + 并集 ----------
def _nms(boxes: List[Tuple[int, int, int, int]], iou_thr: float = 0.2):
    """numpy 版 NMS，返回保留索引"""
    if not boxes:
        return []
    boxes = np.array(boxes, dtype=np.float32)
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = areas.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[np.where(iou <= iou_thr)[0] + 1]
    return keep

def _union_boxes(boxes: List[Tuple[int, int, int, int]], margin: int = 5):
    """同一页靠得很近的框直接并成大框"""
    if not boxes:
        return []
    boxes = np.array(boxes)
    x1, y1, x2, y2 = boxes.T
    ux1, uy1, ux2, uy2 = max(0, x1.min() - margin), max(0, y1.min() - margin), \
                         x2.max() + margin, y2.max() + margin
    return [(int(ux1), int(uy1), int(ux2), int(uy2))]

# ---------- 六、统一入口 ----------
def detect_table_pages(pdf_path: Path,
                       dpi: int = 72,
                       images=None) -> List[Tuple[int, Tuple[int, int, int, int]]]:
    """
    返回 List[(page_idx, (x1,y1,x2,y2))]  0-based 页码
    """
    # 1. 多通道召回
    print("**************000000000000")
    bboxes = []
    bboxes += _ch1_yolo(pdf_path, dpi)
    print("%%%%%%%%%0000000000")
    bboxes += _ch2_lines(pdf_path)
    print("%%%%%%%%%1111111111")
    bboxes += _ch3_text_cluster(pdf_path)
    print("**************1111111111111")
    # 2. 按页分组
    from collections import defaultdict
    page_dict = defaultdict(list)
    for page_idx, box in bboxes:
        page_dict[page_idx].append(box)
    print("**************2222222222222")
    # 3. 每页 NMS + 并集
    final = []
    for page_idx, boxes in page_dict.items():
        keep_idx = _nms(boxes, iou_thr=0.2)
        kept = [boxes[i] for i in keep_idx]
        # 可选：再把保留框并成一个大框（召回优先）
        big_box = _union_boxes(kept, margin=5)
        final.append((page_idx, big_box[0]))
    print("**************333333333333333")
    return final


def detect_table_page(pdf_path: Path,
                      page_idx: int,
                      dpi: int = 72) -> List[Tuple[int, int, int, int]]:
    """
    只处理指定的一页，返回这张页上的表格 bbox
    """
    from pdf2image import convert_from_path
    # 只转这一页
    img = convert_from_path(pdf_path,
                           first_page=page_idx + 1,
                           last_page=page_idx + 1,
                           dpi=dpi)[0]
    bboxes = []

    # ---------- 1. YOLO ----------
    model = _get_yolo()
    results = model(img, verbose=False)
    w, h = img.size
    for b in results[0].boxes:
        if int(b.cls) == 0:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            bboxes.append((int(x1), int(y1), int(x2), int(y2)))

    # ---------- 2. pdfplumber 线条 ----------
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_idx]
        lines = page.lines or []
        if lines:
            xs = [l['x0'] for l in lines] + [l['x1'] for l in lines]
            ys = [l['y0'] for l in lines] + [l['y1'] for l in lines]
            bbox = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
            bboxes.append(bbox)

    # ---------- 3. 文本聚类 ----------
    chars = page.chars
    if chars:
        ys = [int((c['y0'] + c['y1']) / 2) for c in chars]
        cols = [int((c['x0'] + c['x1']) / 2) for c in chars]
        if len(set(ys)) > 4 and len(set(cols)) > 2:
            x0 = min(c['x0'] for c in chars)
            y0 = min(c['y0'] for c in chars)
            x1 = max(c['x1'] for c in chars)
            y1 = max(c['y1'] for c in chars)
            bboxes.append((int(x0), int(y0), int(x1), int(y1)))

    # ---------- 4. NMS ----------
    keep_idx = _nms(bboxes, iou_thr=0.2)
    kept = [bboxes[i] for i in keep_idx]
    big_box = _union_boxes(kept, margin=5)

    return big_box[0] if big_box else None


# ---------- 七、旧接口兼容 ----------
detect_table_pages1 = detect_table_pages


# ---------- 八、自测 ----------
# F:\Program Files (x86)\Release-24\poppler-24.08.0\Library\bin
import time
from pdf2image import convert_from_path
poppler_bin = r"F:\Program Files (x86)\Release-24\poppler-24.08.0\Library\bin"
dpf_file = r"E:/Datas/bank_data/images/601939建设银行2024年年度报告.pdf"
# ---------- 八、稳健版：先确认文件真的生成了 ----------
if __name__ == "__main__":
    import time, gc
    pdf = Path(r"E:/Datas/bank_data/images/601939建设银行2024年年度报告.pdf")
    t0 = time.time()

    with pdfplumber.open(pdf) as p:
        total = len(p.pages)

    for page_idx in range(total):
        box = detect_table_page(pdf, page_idx, dpi=72)
        if box:
            print(f"page {page_idx}  table  {box}")
        gc.collect()          # 主动释放循环引用

    print("总耗时:", time.time() - t0)