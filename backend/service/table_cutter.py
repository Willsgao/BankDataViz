# table_cutter.py (优化版 - 保留跨页拼接和标题补充功能)

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from PIL import Image


class TableCutter:
    def __init__(self, tol: int = 3):
        self.tol = tol

    # ----------------------------------------------------
    # 从 rebuild_sub_images_idx_6.py 移植的核心功能
    # ----------------------------------------------------
    @staticmethod
    def resort_boxes(boxes: List[Dict]) -> List[Dict]:
        """对检测框进行排序：先Y后X"""
        return sorted(boxes, key=lambda b: (b["coordinate"][1], b["coordinate"][0]))

    @staticmethod
    def replace_null_in_object(obj: Any) -> Any:
        """仅替换字典中的 null 值，不处理数组"""
        if isinstance(obj, dict):
            return {
                k: "" if v is None else TableCutter.replace_null_in_object(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [TableCutter.replace_null_in_object(item) for item in obj]
        else:
            return obj

    @staticmethod
    def get_resorted_level_info(input_info: Dict) -> Dict:
        """重新排序布局信息"""
        new_input_info = {}
        for idx, info in input_info.items():
            idx_info = info.get('res', {})
            boxes = idx_info.get('boxes', [])
            input_path = idx_info.get('input_path', '')
            sorted_boxes = TableCutter.resort_boxes(boxes)
            res = {
                'input_path': input_path,
                'boxes': sorted_boxes
            }
            new_input_info[idx] = res
        return new_input_info

    @staticmethod
    def get_new_info(json_file: Union[str, Path]) -> Dict:
        """从JSON文件获取处理后的布局信息"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cleaned_data = TableCutter.replace_null_in_object(data)
        return TableCutter.get_resorted_level_info(cleaned_data)

    @staticmethod
    def is_contained(inner: List[float], outer: List[float], tol: int = 3) -> bool:
        """判断inner是否被outer包含（带容差）"""
        return (
                outer[0] - tol <= inner[0] and
                outer[1] - tol <= inner[1] and
                inner[2] <= outer[2] + tol and
                inner[3] <= outer[3] + tol
        )

    @staticmethod
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
                if TableCutter.is_contained(current_coord, other_coord, tol):
                    is_nested = True
                    break

            if not is_nested:
                keep_indices.append(idx)

        return keep_indices

    def merge_adjacent_tables(self, boxes: List[Dict]) -> None:
        """合并相邻的表格（同页纵向合并）- 从原代码移植"""
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


    def is_first_table_without_text(self, table_idx, valid_boxes):
        """判断是否为第一个表格且前面没有文本内容"""
        # 如果是第一个表格，检查前面是否有文本
        for i in range(table_idx):
            box = valid_boxes[i]
            label = box.get("label", "")
            # 如果前面有文本或标题元素，说明不是纯表格开头
            if label in ["text", "title"]:
                return False
        return True


    def enhanced_cut_tables_with_context(
            self,
            img_path: Union[str, Path],
            layout_json: Dict,
            out_dir: Union[str, Path],
            confidence_threshold: float = 0.5,
            sub_name: str = "",
            pre_last_state: int = 0
    ) -> Tuple[List[Path], int]:

        img_path = Path(img_path)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"📁 增强切割到目录: {out_dir}")

        # 打开原图
        original_image = Image.open(img_path)
        stem_name = img_path.stem

        # 从JSON中提取检测框
        boxes = (layout_json.get("res", {}).get("boxes", []) or
                 layout_json.get("layout", []))

        # 过滤出置信度达标的元素
        valid_boxes = [
            box for box in boxes
            if box.get("score", 0.0) >= confidence_threshold
        ]

        print(f"检测到 {len(valid_boxes)} 个有效元素")

        # 过滤嵌套表格
        table_indices = [i for i, box in enumerate(valid_boxes) if box.get("label") == "table"]
        kept_table_indices = self.filter_nested_tables(valid_boxes, self.tol)
        print(f"过滤嵌套后保留 {len(kept_table_indices)} 个表格")

        # 合并相邻表格
        self.merge_adjacent_tables(valid_boxes)

        saved_paths = []
        cur_pre_last_state = 0

        # 处理每个保留的表格
        for i, table_idx in enumerate(kept_table_indices, 1):
            table_box = valid_boxes[table_idx]
            coordinates = table_box["coordinate"]

            # 查找表格上方的标题和文本
            title_boxes = self.find_above_titles_and_text(valid_boxes, table_idx, coordinates)

            # 调整表格区域以包含标题
            extended_coords = self.extend_table_with_titles(coordinates, title_boxes)

            x1, y1, x2, y2 = map(round, extended_coords)

            # 判断是否为第一个表格且前面没有文本
            is_first_without_text = self.is_first_table_without_text(table_idx, valid_boxes)

            # 判断是否为页面最后一个表格
            is_last_table = self.is_last_table_on_page(valid_boxes, table_idx)

            # 生成文件名（支持_0和_last组合）
            filename = self.generate_table_filename(
                stem_name, i, is_last_table, is_first_without_text, pre_last_state, sub_name
            )

            save_path = out_dir / filename

            # 从原图裁剪扩展后的表格区域
            table_image = original_image.crop((x1, y1, x2, y2))
            table_image.save(save_path)
            saved_paths.append(save_path)

            print(f"✅ 保存增强表格 {i}: {filename} (包含{len(title_boxes)}个标题/文本)")

            # 更新跨页状态
            if is_last_table:
                cur_pre_last_state = 1

        print(f"🎯 原图 {stem_name} 共保存 {len(saved_paths)} 个增强表格")
        return saved_paths, cur_pre_last_state


    def find_above_titles_and_text(self, boxes: List[Dict], table_idx: int, table_coords: List[float]) -> List[Dict]:
        """查找表格上方的标题和文本元素"""
        table_x1, table_y1, table_x2, table_y2 = table_coords
        title_boxes = []

        # 查找表格上方的元素
        for i, box in enumerate(boxes):
            if i >= table_idx:  # 只检查表格之前的元素
                continue

            label = box.get("label", "")
            coords = box.get("coordinate", [])
            if len(coords) < 4:
                continue

            box_x1, box_y1, box_x2, box_y2 = coords

            # 检查元素是否在表格上方且宽度与表格对齐
            if (box_y2 <= table_y1 and
                    self.is_horizontally_aligned(box_x1, box_x2, table_x1, table_x2) and
                    label in ["title", "text"]):
                title_boxes.append(box)

        return title_boxes

    def is_horizontally_aligned(self, box_x1: float, box_x2: float, table_x1: float, table_x2: float,
                                tolerance: float = 50) -> bool:
        """检查元素是否与表格水平对齐"""
        return (abs(box_x1 - table_x1) < tolerance and abs(box_x2 - table_x2) < tolerance)

    def extend_table_with_titles(self, table_coords: List[float], title_boxes: List[Dict]) -> List[float]:
        """扩展表格区域以包含标题"""
        if not title_boxes:
            return table_coords

        table_x1, table_y1, table_x2, table_y2 = table_coords
        min_y = table_y1

        # 找到最上方的标题
        for title in title_boxes:
            title_y1 = title["coordinate"][1]
            if title_y1 < min_y:
                min_y = title_y1

        # 扩展表格上边界
        extended_coords = [table_x1, min_y, table_x2, table_y2]
        return extended_coords

    def is_last_table_on_page(self, boxes: List[Dict], table_idx: int) -> bool:
        """判断是否为页面上的最后一个表格"""
        table_indices = [i for i, box in enumerate(boxes) if box.get("label") == "table"]
        return table_idx == table_indices[-1] if table_indices else False


    def generate_table_filename(self, stem_name: str, table_index: int,
                                is_last: bool, is_first_without_text: bool,
                                pre_last_state: int, sub_name: str = "") -> str:
        """生成表格文件名（支持_0和_last同时存在）"""
        if sub_name:
            base_name = f"{sub_name}_table_{table_index:03d}"
        else:
            base_name = f"{stem_name}_table_{table_index:03d}"

        # 跨页标记逻辑（支持组合）：
        marks = []

        # _0 标记条件：
        # - 前页有last标记且当前页是第一个表格（跨页续表）
        # - 或者当前页第一个表格前面没有文本（纯表格开头）
        if (pre_last_state and table_index == 1) or (table_index == 1 and is_first_without_text):
            marks.append("0")

        # _last 标记条件：页面最后一个表格
        if is_last:
            marks.append("last")

        # 组合标记
        if marks:
            base_name += "_" + "_".join(marks)

        print(
            f"📄 文件名: {base_name}.png (标记: {marks}, 前页状态: {pre_last_state}, 无文本开头: {is_first_without_text})")
        return f"{base_name}.png"

    def process_pdf_tables(
            self,
            json_file: Union[str, Path],
            ori_path: Union[str, Path],
            subs_save_path: Union[str, Path],
            join_save_path: Union[str, Path],
            sub_name: str = ""
    ) -> None:
        """
        处理PDF的所有表格（修复跨页状态传递）
        """
        sorted_info = self.get_new_info(json_file)

        subs_save_path = Path(subs_save_path)
        join_save_path = Path(join_save_path)
        subs_save_path.mkdir(parents=True, exist_ok=True)
        join_save_path.mkdir(parents=True, exist_ok=True)

        pre_last_state = 0  # 初始化跨页状态

        for idx, idx_info in sorted_info.items():
            # 创建子目录
            sub_idx_dir = subs_save_path / idx
            sub_idx_dir.mkdir(exist_ok=True)

            # 原始图片路径
            sub_idx_name = Path(ori_path) / f"{idx}.png"

            if not sub_idx_name.exists():
                print(f"⚠️ 跳过不存在的图片: {sub_idx_name}")
                continue

            print(f"📄 处理页面 {idx}, 跨页状态: {pre_last_state}")

            # 增强版表格切割 - 传递并接收跨页状态
            saved_tables, pre_last_state = self.enhanced_cut_tables_with_context(
                sub_idx_name,
                idx_info,
                sub_idx_dir,
                sub_name=idx,
                pre_last_state=pre_last_state  # 传递状态给当前页
            )

            print(f"✅ 页面 {idx} 处理完成, 输出状态: {pre_last_state}")
            print(f"📄 页面 {idx} 处理完成，保存 {len(saved_tables)} 个表格，跨页状态: {pre_last_state}")











# 导出函数
def extract_page_num_from_dir(dir_name: str) -> Optional[int]:
    """从目录名提取页码"""
    match = re.search(r'_(\d{3})$', dir_name)
    return int(match.group(1)) if match else None


def extract_table_index111(filename: str) -> Optional[int]:
    """从文件名提取表格索引"""
    match = re.search(r'_table_?(\d+)', filename) or re.search(r'_(\d{3})(?:_last|_0)?\.png', filename)
    return int(match.group(1)) if match else None


def extract_table_index(filename: str) -> Optional[int]:
    """从文件名提取表格索引（修复逻辑）"""
    # 匹配模式: {前缀}_table_{数字}_{后缀}.png
    patterns = [
        r'_table_(\d+)',  # _table_001
        r'_(\d{3})(?:_0|_last|_0_last)?\.png'  # _001_0.png 或 _001_last.png
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            index = int(match.group(1))
            print(f"🔍 提取表格索引: {filename} -> {index}")
            return index

    print(f"⚠️ 无法提取表格索引: {filename}")
    return None



def extract_page_num(filename: str) -> Optional[int]:
    """从文件名中提取页码"""
    match = re.search(r'_(\d{3})_', filename)
    return int(match.group(1)) if match else None



def cut_final_tables(
        img_path: Union[str, Path],
        layout_json: Dict,
        out_dir: Union[str, Path],
        confidence_threshold: float = 0.5,
        tol: int = 3
) -> List[Path]:
    """兼容性函数 - 单页处理场景"""
    cutter = TableCutter(tol=tol)
    saved_paths, _ = cutter.enhanced_cut_tables_with_context(  # ← 调用修改后的函数
        img_path, layout_json, out_dir, confidence_threshold
    )
    return saved_paths  # ← 只返回路径列表，保持兼容


__all__ = [
    'TableCutter',
    'cut_final_tables',
    'extract_page_num_from_dir',
    'extract_table_index',
    'extract_page_num',
]