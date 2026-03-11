# 新建工具模块 backend/services/image_utils.py
from PIL import Image
from pathlib import Path
from typing import List

def concat_images_vertically(img_paths: List[Path], out_path: Path) -> Path:
    """纵向拼接图片并保存（从table_cutter_join.py迁移）"""
    imgs = [Image.open(p) for p in img_paths]
    widths, heights = zip(*(i.size for i in imgs))
    total_h, max_w = sum(heights), max(widths)
    new_img = Image.new(imgs[0].mode, (max_w, total_h))
    y = 0
    for im in imgs:
        new_img.paste(im, (0, y))
        y += im.height
    new_img.save(out_path)
    return out_path

def concat_images(imgs: List[Image.Image]) -> Image.Image:
    """纵向拼接图片对象（从table_cutter.py的_concat_imgs重命名迁移）"""
    widths, heights = zip(*(i.size for i in imgs))
    total_h, max_w = sum(heights), max(widths)
    new_img = Image.new(imgs[0].mode, (max_w, total_h))
    y = 0
    for im in imgs:
        new_img.paste(im, (0, y))
        y += im.height
    return new_img