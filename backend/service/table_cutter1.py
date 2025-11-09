# table_cutter.py (彻底修复版)

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from PIL import Image


def resort_boxes(boxes: List[Dict]) -> List[Dict]:
    """对检测框进行排序：先Y后X"""
    return sorted(boxes, key=lambda b: (b["coordinate"][1], b["coordinate"][0]))


def is_contained(inner: List[float], outer: List[float], tol: int = 3) -> bool:
    """判断inner是否被outer包含（带容差）"""
    return (outer[0] - tol <= inner[0] and
            outer[1] - tol <= inner[1] and
            inner[2] <= outer[2] + tol and
            inner[3] <= outer[3] + tol)


def filter_nested_tables(boxes: List[Dict], tol: int = 3) -> List[int]:
    """过滤嵌套表格，返回需要保留的索引"""
    table_indices = [i for i, box in enumerate(boxes) if box.get("label") == "table"]
    keep_indices = []

    for i, idx in enumerate(table_indices):
        current_coord = boxes[idx]["coordinate"]
        is_nested = False

        for j, other_idx in enumerate(table_indices):
            if i == j:
                continue
            other_coord = boxes[other_idx]["coordinate"]
            if is_contained(current_coord, other_coord, tol):
                is_nested = True
                break

        if not is_nested:
            keep_indices.append(idx)

    return keep_indices


def merge_adjacent_tables(boxes: List[Dict]) -> None:
    """合并相邻的表格（同页纵向合并）"""
    last_table_idx = -1

    for i, box in enumerate(boxes):
        if box.get("label") != "table":
            continue

        # 检查与前一个表格之间的内容
        between_range = range(last_table_idx + 1, i)
        if between_range and all(boxes[k].get("label") == "text" for k in between_range):
            # 调整当前表格的上边界以包含中间的文本
            min_upper = min(boxes[k]["coordinate"][1] for k in between_range)
            box["coordinate"][1] = min_upper

        last_table_idx = i




def should_join_with_prev(current_page_dir: Path) -> Optional[Path]:
    """
    判断当前页是否需要与前一页拼接
    """
    current_dir_name = current_page_dir.name

    # 提取当前页码
    current_page_num = extract_page_num_from_dir(current_dir_name)
    if current_page_num is None or current_page_num <= 1:
        return None

    # 构建前一页目录名
    prev_page_num = current_page_num - 1
    base_name = current_dir_name.rsplit('_', 1)[0]
    prev_dir_name = f"{base_name}_{prev_page_num:03d}"
    prev_page_dir = current_page_dir.parent / prev_dir_name

    if not prev_page_dir.exists():
        return None

    # 获取前一页的最后一张表格和当前页的第一张表格
    prev_tables = sorted(prev_page_dir.glob("*_table_*.png"))
    current_tables = sorted(current_page_dir.glob("*_table_*.png"))

    if not prev_tables or not current_tables:
        return None

    last_prev_table = prev_tables[-1]
    first_current_table = current_tables[0]

    # 检查拼接条件：前一页表格名包含"last"，当前页表格是第一个
    prev_table_idx = extract_table_index(last_prev_table.name)
    current_table_idx = extract_table_index(first_current_table.name)

    # 简单逻辑：如果索引连续且前一页是最后一个，当前页是第一个，则拼接
    if (prev_table_idx is not None and current_table_idx is not None and
            current_table_idx == prev_table_idx + 1):
        return last_prev_table

    return None


def save_joined_table(prev_table_path: Path, current_table_path: Path, output_dir: Path, pdf_folder: str = "") -> Path:
    """保存拼接后的表格"""
    # 读取图片
    prev_img = Image.open(prev_table_path)
    current_img = Image.open(current_table_path)

    # 纵向拼接
    widths, heights = zip(*(img.size for img in [prev_img, current_img]))
    total_height = sum(heights)
    max_width = max(widths)

    joined_image = Image.new(prev_img.mode, (max_width, total_height))
    joined_image.paste(prev_img, (0, 0))
    joined_image.paste(current_img, (0, prev_img.height))

    # 构建输出路径
    if pdf_folder:
        output_dir = output_dir / pdf_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    # 使用前一页的文件名作为输出文件名
    output_path = output_dir / prev_table_path.name

    # 保存拼接结果
    joined_image.save(output_path)

    print(f"✅ 表格拼接完成: {output_path}")
    return output_path


def extract_page_num_from_dir(dir_name: str) -> Optional[int]:
    """从目录名提取页码"""
    match = re.search(r'_(\d{3})$', dir_name)
    return int(match.group(1)) if match else None


def extract_table_index(filename: str) -> Optional[int]:
    """从文件名提取表格索引"""
    match = re.search(r'_table_(\d+)', filename)
    return int(match.group(1)) if match else None


def extract_page_num(filename: str) -> Optional[int]:
    """从文件名中提取页码"""
    match = re.search(r'_(\d{3})_', filename)
    return int(match.group(1)) if match else None


def enhanced_group_tables_by_index(all_page_tables: Dict) -> Dict[int, List[Tuple[str, Path]]]:
    """增强版：基于内容连续性的表格分组"""
    table_groups = {}

    # 按页码排序
    sorted_pages = sorted(all_page_tables.items(), key=lambda x: x[1].get('page_num', 0))

    current_table_idx = 1
    prev_page_tables = []

    for png_name, page_info in sorted_pages:
        current_tables = page_info.get('tables', [])
        current_page_num = page_info.get('page_num', 0)

        # 对当前页表格排序
        current_tables_sorted = sorted(current_tables, key=lambda x: extract_table_index(x.name) or 0)

        for table_path in current_tables_sorted:
            # 检查是否应该与前一页的表格关联
            should_join = False

            if prev_page_tables:
                last_prev_table = prev_page_tables[-1]
                # 基于表格位置和内容的连续性判断
                if is_likely_continuous(last_prev_table, table_path, current_page_num):
                    should_join = True

            if should_join and table_groups.get(current_table_idx):
                # 添加到现有表格组
                table_groups[current_table_idx].append((png_name, table_path))
            else:
                # 创建新的表格组
                current_table_idx += 1
                table_groups[current_table_idx] = [(png_name, table_path)]

        prev_page_tables = current_tables_sorted

    return table_groups


def is_likely_continuous(prev_table: Path, current_table: Path, current_page_num: int) -> bool:
    """判断两个表格是否可能连续"""
    try:
        # 1. 检查文件名索引连续性
        prev_idx = extract_table_index(prev_table.name)
        curr_idx = extract_table_index(current_table.name)

        if prev_idx is not None and curr_idx is not None:
            if curr_idx == 1 and prev_idx >= 1:  # 当前页第一个表格可能是前一页的延续
                return True

        # 2. 检查图片内容连续性（简单版：检查表格顶部位置）
        prev_img = Image.open(prev_table)
        curr_img = Image.open(current_table)

        # 如果前一页表格在页面底部，当前页表格在页面顶部，则可能连续
        prev_bottom_ratio = get_bottom_position_ratio(prev_table)
        curr_top_ratio = get_top_position_ratio(current_table)

        if prev_bottom_ratio > 0.8 and curr_top_ratio < 0.2:  # 前一页底部，当前页顶部
            return True

        # 3. 检查表格结构相似性（列数、宽度等）
        if have_similar_structure(prev_img, curr_img):
            return True

    except Exception as e:
        print(f"连续性检测出错: {e}")

    return False


def get_bottom_position_ratio(table_path: Path) -> float:
    """获取表格在原始页面中的底部位置比例"""
    # 需要从布局信息中获取表格在原始页面的位置
    # 这里需要您补充从layout_json中获取表格原始位置信息的逻辑
    return 0.0


def get_top_position_ratio(table_path: Path) -> float:
    """获取表格在原始页面中的顶部位置比例"""
    # 同样需要从布局信息中获取
    return 0.0


def have_similar_structure(img1: Image.Image, img2: Image.Image) -> bool:
    """简单判断两个表格结构是否相似"""
    # 比较宽度、列数等特征
    width1, height1 = img1.size
    width2, height2 = img2.size

    # 宽度相似且都是表格结构
    width_ratio = min(width1, width2) / max(width1, width2)
    return width_ratio > 0.8  # 宽度相似度阈值


def cut_final_tables(
        img_path: Union[str, Path],
        layout_json: Dict,
        out_dir: Union[str, Path],
        confidence_threshold: float = 0.5,
        tol: int = 3
) -> List[Path]:
    """
    修复版：确保同一原图的所有切割图都在同一个目录
    """
    img_path = Path(img_path)
    out_dir = Path(out_dir)

    # 关键修复：直接使用指定的输出目录，不创建子目录
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 切割到统一目录: {out_dir}")

    # 打开原图
    original_image = Image.open(img_path)
    stem_name = img_path.stem  # 如：057bde4fe7fe351b24eb4d8b2b489c44_001

    # 从JSON中提取表格检测框
    boxes = (layout_json.get("res", {}).get("boxes", []) or
             layout_json.get("layout", []))

    # 过滤出置信度达标的表格
    tables = [
        box for box in boxes
        if box.get("label") == "table" and box.get("score", 0.0) >= confidence_threshold
    ]

    print(f"检测到 {len(tables)} 个表格")

    # 过滤嵌套表格
    kept_indices = filter_nested_tables(tables, tol)
    print(f"过滤嵌套后保留 {len(kept_indices)} 个表格")

    saved_paths = []

    # 一次性切割并保存到统一目录
    for i, table_idx in enumerate(kept_indices, 1):
        table = tables[table_idx]
        coordinates = table["coordinate"]
        x1, y1, x2, y2 = map(round, coordinates)

        # 生成文件名：包含原图名称确保唯一性
        filename = f"{stem_name}_table_{i}.png"
        save_path = out_dir / filename

        # 严格检查是否已存在
        if save_path.exists():
            print(f"⚠️ 文件已存在，跳过保存: {save_path}")
            saved_paths.append(save_path)
            continue

        # 从原图裁剪表格区域
        table_image = original_image.crop((x1, y1, x2, y2))

        # 保存图片
        table_image.save(save_path)
        saved_paths.append(save_path)

        print(f"✅ 保存表格 {i}: {filename}")

    print(f"🎯 原图 {stem_name} 共保存 {len(saved_paths)} 个表格到统一目录")
    return saved_paths





# 导出所有需要的函数
__all__ = [
    'cut_final_tables',
    'should_join_with_prev',
    'save_joined_table',
    'extract_page_num_from_dir',
    'extract_table_index',
    'extract_page_num',
]