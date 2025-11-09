# table_cutter_join.py (优化版 - 保留跨页拼接功能)

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from PIL import Image
from backend.service.table_cutter import TableCutter, extract_table_index, extract_page_num_from_dir


class TableJoiner:
    def __init__(self, tol: int = 3):
        self.tol = tol
        self.cutter = TableCutter(tol)

    def should_join_tables(self, prev_table: Path, current_table: Path) -> bool:
        """
        判断两个表格是否应该拼接（基于原逻辑）
        """
        prev_name = prev_table.name
        curr_name = current_table.name

        # 检查文件名中的跨页标记（从原代码移植的逻辑）
        has_prev_last = '_last' in prev_name
        has_curr_zero = '_0_' in curr_name or '_0.' in curr_name

        if has_prev_last and has_curr_zero:
            # 提取索引进行比较
            prev_idx = extract_table_index(prev_name)
            curr_idx = extract_table_index(curr_name)

            if prev_idx is not None and curr_idx is not None:
                # 索引连续则拼接
                return curr_idx == prev_idx + 1

        return False

    def concat_images_vertically(self, img_paths: List[Path], out_path: Path = None) -> Image.Image:
        """
        纵向拼接图片（从 re_join_sub_images_idx_7.py 移植）
        """
        imgs = [Image.open(p) for p in img_paths]

        # 统一用第一张的 mode，宽度取最大
        widths, heights = zip(*(i.size for i in imgs))
        total_height = sum(heights)
        max_width = max(widths)

        new_img = Image.new(imgs[0].mode, (max_width, total_height))

        y_offset = 0
        for im in imgs:
            new_img.paste(im, (0, y_offset))
            y_offset += im.height

        if out_path:
            new_img.save(out_path)
            print("拼接保存 ->", out_path)

        return new_img

    def re_join_sub_images(self, ori_path: Union[str, Path], new_join_save_path: Union[str, Path] = '') -> Dict[
        str, List[Path]]:
        """
        将切片重新拼回整页/整表（从 re_join_sub_images_idx_7.py 移植并优化）
        """
        ori_path = Path(ori_path)
        new_join_save_path = Path(new_join_save_path) if new_join_save_path else ori_path.parent / "joined"
        new_join_save_path.mkdir(parents=True, exist_ok=True)

        # 收集所有图片文件
        all_files = {}
        file_index = 1

        for file_path in ori_path.rglob("*.png"):
            all_files[file_index] = [file_path.name, file_path]
            file_index += 1

        # 分组需要拼接的图片
        join_groups = []
        current_group = []
        current_name = ""

        for i, (file, file_path) in all_files.items():
            should_stay = False

            # 检查是否应该与下一张图片拼接
            if i + 1 in all_files:
                next_file = all_files[i + 1][0]

                # 原逻辑：包含'last'和'_0_'的连续索引图片需要拼接
                if '_last' in file and '_0_' in next_file:
                    try:
                        prev_idx = int(file.split('_')[1])
                        next_idx = int(next_file.split('_')[1])
                        if prev_idx + 1 == next_idx:
                            should_stay = True
                    except (IndexError, ValueError):
                        pass

            if not should_stay:
                if current_group:
                    current_group.append(file_path)
                    join_groups.append((current_name, current_group))
                    current_group = []
                    current_name = ""
                else:
                    # 单张图片
                    join_groups.append((file, [file_path]))
            else:
                if not current_name:
                    current_name = file
                current_group.append(file_path)

        # 处理最后一组
        if current_group:
            join_groups.append((current_name, current_group))

        # 执行拼接
        result_dict = {}
        for name, img_paths in join_groups:
            if len(img_paths) == 1:
                # 单张图片，直接复制
                output_path = new_join_save_path / name
                Image.open(img_paths[0]).save(output_path)
                result_dict[name] = [output_path]
            else:
                # 多张图片拼接
                output_path = new_join_save_path / f"joined_{name}"
                self.concat_images_vertically(img_paths, output_path)
                result_dict[name] = [output_path]

        return result_dict

    def consolidate_final_tables(
            self,
            crop_root: Union[str, Path],
            join_root: Union[str, Path],
            pdf_folder: str
    ) -> Dict[str, List[Path]]:
        """
        最终整合：将裁剪的表格按索引分组并拼接，支持跨页和标题补充
        """
        crop_root = Path(crop_root) / pdf_folder
        join_root = Path(join_root) / pdf_folder
        join_root.mkdir(parents=True, exist_ok=True)

        if not crop_root.exists():
            print(f"警告：裁剪目录不存在 {crop_root}")
            return {}

        # 使用增强的分组逻辑
        table_groups = self.enhanced_group_tables(crop_root)

        # 执行最终拼接
        final_results = {}
        for table_idx, table_list in table_groups.items():
            if not table_list:
                continue

            if len(table_list) == 1:
                # 单页表格
                final_path = join_root / f"table_{table_idx:03d}.png"
                Image.open(table_list[0]['path']).save(final_path)
                final_results[str(table_idx)] = [final_path]
                print(f"表格 {table_idx}: 单页 -> {final_path}")

            else:
                # 多页表格拼接
                image_paths = [item['path'] for item in table_list]
                final_path = join_root / f"table_{table_idx:03d}_joined.png"

                self.concat_images_vertically(image_paths, final_path)
                final_results[str(table_idx)] = [final_path]
                print(f"表格 {table_idx}: {len(table_list)}页拼接 -> {final_path}")

        return final_results

    def enhanced_group_tables(self, crop_root: Path) -> Dict[int, List[Dict]]:
        """
        增强版表格分组：基于内容连续性和跨页标记
        """
        table_groups = {}
        all_tables = []

        # 收集所有表格并按页码排序
        for page_dir in crop_root.iterdir():
            if not page_dir.is_dir():
                continue

            page_num = extract_page_num_from_dir(page_dir.name) or 0

            for table_file in page_dir.glob("*.png"):
                table_idx = extract_table_index(table_file.name)
                if table_idx is None:
                    continue

                all_tables.append({
                    'path': table_file,
                    'page_num': page_num,
                    'page_dir': page_dir.name,
                    'filename': table_file.name,
                    'table_idx': table_idx
                })

        # 按页码和文件名排序
        all_tables.sort(key=lambda x: (x['page_num'], x['filename']))

        # 智能分组
        current_group_idx = 1
        table_groups[current_group_idx] = []

        for i, table in enumerate(all_tables):
            if not table_groups[current_group_idx]:
                table_groups[current_group_idx].append(table)
                continue

            # 获取前一个表格
            prev_table = table_groups[current_group_idx][-1]

            # 判断是否应该分组
            if self.should_group_tables(prev_table, table):
                table_groups[current_group_idx].append(table)
            else:
                # 创建新组
                current_group_idx += 1
                table_groups[current_group_idx] = [table]

        return table_groups

    def should_group_tables(self, prev_table: Dict, current_table: Dict) -> bool:
        """
        判断两个表格是否应该分在同一组
        """
        # 1. 检查跨页标记
        prev_name = prev_table['filename']
        curr_name = current_table['filename']

        if self.should_join_tables(Path(prev_name), Path(curr_name)):
            return True

        # 2. 检查页码连续性
        if current_table['page_num'] != prev_table['page_num'] + 1:
            return False

        # 3. 检查表格索引连续性
        if current_table['table_idx'] != prev_table['table_idx']:
            return False

        # 4. 检查表格结构相似性
        try:
            prev_img = Image.open(prev_table['path'])
            curr_img = Image.open(current_table['path'])
            return self.have_similar_structure(prev_img, curr_img)
        except Exception:
            return False

    def have_similar_structure(self, img1: Image.Image, img2: Image.Image) -> bool:
        """判断两个表格结构是否相似"""
        width1, height1 = img1.size
        width2, height2 = img2.size

        # 宽度相似度
        width_ratio = min(width1, width2) / max(width1, width2)
        return width_ratio > 0.8  # 宽度相似度阈值


# 使用示例
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="增强版表格拼接处理")
    parser.add_argument("-i", "--input_dir", required=True, help="输入目录")
    parser.add_argument("-o", "--output_dir", required=True, help="输出目录")
    parser.add_argument("-f", "--pdf_folder", required=True, help="PDF文件夹名")
    parser.add_argument("-j", "--json_file", help="布局JSON文件（可选）")

    args = parser.parse_args()

    joiner = TableJoiner()

    # 执行拼接
    results = joiner.consolidate_final_tables(
        crop_root=args.input_dir,
        join_root=args.output_dir,
        pdf_folder=args.pdf_folder
    )

    print(f"✅ 拼接完成，共处理 {len(results)} 个表格")

__all__ = [
    'TableJoiner',
    'consolidate_final_tables',
]