# table_cutter_join.py (优化版 - 最终拼接处理)

import re
from pathlib import Path
from typing import List, Dict, Optional, Union
from PIL import Image


def consolidate_final_tables(
        crop_root: Union[str, Path],
        join_root: Union[str, Path],
        pdf_folder: str
) -> Dict[str, List[Path]]:
    """
    最终整合：将裁剪的表格按索引分组并拼接
    返回：{table_index: [最终图片路径]}
    """
    crop_root = Path(crop_root) / pdf_folder
    join_root = Path(join_root) / pdf_folder
    join_root.mkdir(parents=True, exist_ok=True)

    if not crop_root.exists():
        print(f"警告：裁剪目录不存在 {crop_root}")
        return {}

    # 收集所有表格，按索引分组
    table_groups = {}

    for page_dir in crop_root.iterdir():
        if not page_dir.is_dir():
            continue

        for table_file in page_dir.glob("*_table_*.png"):
            table_idx = extract_table_index(table_file.name)
            if table_idx is None:
                continue

            if table_idx not in table_groups:
                table_groups[table_idx] = []

            # 按页码排序
            page_num = extract_page_num_from_dir(page_dir.name) or 0
            table_groups[table_idx].append({
                'path': table_file,
                'page_num': page_num,
                'page_dir': page_dir.name
            })

    # 对每个表格组的图片按页码排序
    for table_idx in table_groups:
        table_groups[table_idx].sort(key=lambda x: x['page_num'])

    # 执行最终拼接
    final_results = {}

    for table_idx, table_list in table_groups.items():
        if not table_list:
            continue

        if len(table_list) == 1:
            # 单页表格，直接复制
            final_path = join_root / f"table_{table_idx:03d}.png"
            Image.open(table_list[0]['path']).save(final_path)
            final_results[table_idx] = [final_path]
            print(f"表格 {table_idx}: 单页 -> {final_path}")

        else:
            # 多页表格，纵向拼接
            image_paths = [item['path'] for item in table_list]
            final_path = join_root / f"table_{table_idx:03d}_joined.png"

            # 拼接图片
            images = [Image.open(path) for path in image_paths]
            widths, heights = zip(*(img.size for img in images))
            total_height = sum(heights)
            max_width = max(widths)

            combined_image = Image.new(images[0].mode, (max_width, total_height))
            y_offset = 0
            for img in images:
                combined_image.paste(img, (0, y_offset))
                y_offset += img.height

            combined_image.save(final_path)
            final_results[table_idx] = [final_path]

            print(f"表格 {table_idx}: {len(table_list)}页拼接 -> {final_path}")

    return final_results


def extract_table_index(filename: str) -> Optional[int]:
    """从文件名提取表格索引"""
    match = re.search(r'_table_(\d+)', filename)
    return int(match.group(1)) if match else None


def extract_page_num_from_dir(dir_name: str) -> Optional[int]:
    """从目录名提取页码"""
    match = re.search(r'_(\d{3})$', dir_name)
    return int(match.group(1)) if match else None



if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="最终表格拼接处理")
    parser.add_argument("-i", "--img_dir", required=True, help="原始图片目录")
    parser.add_argument("-l", "--layout_json", required=True, help="布局JSON文件")
    parser.add_argument("-f", "--pdf_folder", required=True, help="PDF文件夹名")
    parser.add_argument("-o", "--output_root", default="static", help="输出根目录")
    parser.add_argument("-c", "--confidence", type=float, default=0.5, help="置信度阈值")

    args = parser.parse_args()

    # 读取布局数据
    with open(args.layout_json, 'r', encoding='utf-8') as f:
        layout_data = json.load(f)

