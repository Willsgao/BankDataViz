# layout_service.py (修复跨页关联逻辑)


import base64
import json
import requests
from PIL import Image
from pathlib import Path
from typing import List, Dict, Union, Tuple

DEFAULT_CONFIDENCE_THRESHOLD = 0.5
# REMOTE_LAYOUT_URL = "http://i-2.gpushare.com:59537/layout"
REMOTE_LAYOUT_URL = "http://i-2.gpushare.com:37987/layout"

from backend.service.table_cutter import (
    cut_final_tables,
    extract_table_index,
    extract_page_num
)


def layout_detect(
        png_path: Union[str, Path],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> Dict[str, Union[Dict, List[Dict]]]:
    """远程布局检测"""
    path = Path(png_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    resp = requests.post(
        REMOTE_LAYOUT_URL,
        json={"png_b64": b64},
        timeout=60
    )
    resp.raise_for_status()
    json_data = resp.json()

    table_zones = []
    for idx, obj in enumerate(json_data.get("layout", [])):
        if obj["type"].lower() == "table" and obj.get("score", 0.0) >= confidence_threshold:
            table_zones.append({
                "table_id": idx,
                "bbox": [int(round(x)) for x in obj["bbox"]],
                "confidence": round(obj.get("score", 0.0), 4)
            })

    print(f"Image {path.name} 检测到 {len(table_zones)} 个有效表格")
    return {"json": json_data, "table_zones": table_zones}


def concat_images_vertically(img_paths: List[Path], out_path: Path) -> Path:
    """纵向拼接图片"""
    imgs = [Image.open(p) for p in img_paths]

    if not imgs:
        raise ValueError("没有图片可拼接")

    widths, heights = zip(*(i.size for i in imgs))
    total_height = sum(heights)
    max_width = max(widths)

    new_img = Image.new(imgs[0].mode, (max_width, total_height))

    y_offset = 0
    for im in imgs:
        new_img.paste(im, (0, y_offset))
        y_offset += im.height

    out_path.parent.mkdir(parents=True, exist_ok=True)
    new_img.save(out_path)

    print(f"拼接完成: {len(img_paths)} 张图片 -> {out_path}")
    return out_path


def batch_cut_tables(
        pdf_folder: str,
        png_names: List[str],
        output_root: Union[str, Path],
        confidence_threshold: float = 0.5
):
    """
    修复版本：严格遵循相邻图片拼接逻辑，避免错误拼接
    """
    try:
        output_root = Path(output_root)
        layout_res = {}

        # 目录常量
        JOINED_ROOT = Path("static/joined_tables")
        CROP_ROOT = Path("static/cropped_tables")
        LAYOUT_ROOT = Path("static/layout_result")

        crop_out_root = CROP_ROOT / pdf_folder
        crop_out_root.mkdir(parents=True, exist_ok=True)

        # 按页码排序处理
        sorted_pngs = sorted(png_names, key=lambda x: extract_page_num(x) or 0)

        # 存储所有页面的表格信息，用于后续处理
        all_page_tables = {}

        print(f"开始处理 {len(sorted_pngs)} 个页面...")

        # 第一步：检查并处理每个页面（只切割一次）
        for png_name in sorted_pngs:
            png_path = output_root / pdf_folder / png_name
            page_stem = png_path.stem
            page_out_dir = crop_out_root / page_stem

            try:
                print(f"\n📄 检查页面: {png_name}")

                # 检查是否已经处理过
                existing_tables = sorted(page_out_dir.glob("*_table_*.png"))
                if page_out_dir.exists() and existing_tables:
                    print(f"✅ 使用现有表格: {len(existing_tables)} 个表格")
                    current_tables = existing_tables

                    # 从保存的布局文件读取布局信息
                    layout_file = LAYOUT_ROOT / f"{pdf_folder}_layout.json"
                    if layout_file.exists():
                        with open(layout_file, 'r', encoding='utf-8') as f:
                            all_layout_data = json.load(f)
                        layout_res[png_name] = all_layout_data.get(png_name, {})
                else:
                    print(f"🔄 处理新页面: {png_name}")

                    # 远程推理
                    with open(png_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    resp = requests.post(
                        REMOTE_LAYOUT_URL,
                        json={"png_b64": b64, "confidence": confidence_threshold},
                        timeout=120
                    )
                    resp.raise_for_status()
                    remote_result = resp.json()
                    layout_res[png_name] = remote_result

                    # 单页裁切
                    saved_paths = cut_final_tables(
                        img_path=png_path,
                        layout_json=remote_result,
                        out_dir=page_out_dir,
                        confidence_threshold=confidence_threshold
                    )
                    current_tables = saved_paths
                    print(f"✅ 初次切割完成: {len(current_tables)} 个表格")

                # 存储当前页的表格信息
                all_page_tables[png_name] = {
                    'page_dir': page_out_dir,
                    'tables': current_tables,
                    'page_num': extract_page_num(png_name) or 0
                }

            except Exception as e:
                print(f"❌ 处理页面 {png_name} 时出错: {e}")
                all_page_tables[png_name] = {'tables': [], 'page_num': 0}

        # 第二步：严格遵循相邻图片拼接逻辑
        print(f"\n🔄 开始处理跨页表格拼接...")

        # 使用严格的相邻图片分组逻辑
        table_groups = strict_adjacent_grouping(all_page_tables)

        # 处理每个表格组
        final_joined_tables = process_table_groups(table_groups, JOINED_ROOT, pdf_folder)

        # 第三步：获取拼接文件夹中的所有图片文件
        joined_folder = JOINED_ROOT / pdf_folder
        joined_images = []
        if joined_folder.exists():
            # 获取所有PNG文件并按名称排序
            for img_file in sorted(joined_folder.glob("*.png")):
                relative_path = f"joined_tables/{pdf_folder}/{img_file.name}"
                joined_images.append(relative_path)

        # 构建最终返回结果
        final_response = {
            "success": True,
            "message": f"批量处理完成，成功生成 {len(joined_images)} 个表格文件",
            "data": {
                "total": len(joined_images),
                "joined": joined_images,  # 返回具体的文件路径列表
                "joined_tables_folder": str(joined_folder.absolute())  # 新增：绝对路径地址
            },
            "details": {
                "pdf_folder": pdf_folder,
                "processed_pages": len(sorted_pngs),
                "total_tables": len(final_joined_tables),
                "absolute_path": str(joined_folder.absolute())  # 或者在details中也放一份
            }
        }

        print(f"\n🎉 处理完成!")
        print(f"最终生成 {len(joined_images)} 个表格文件")
        print(f"拼接图片列表: {joined_images}")

        print("final_response:", final_response)

        return final_response

    except Exception as e:
        print(f"❌ batch_cut_tables 整体处理失败: {e}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "message": "批量裁切处理异常"
        }


def strict_adjacent_grouping(all_page_tables: Dict) -> Dict[int, List[Tuple[str, Path]]]:
    """
    严格相邻分组：确保不丢失任何图片，只对真正相邻的图片进行拼接
    """
    # 首先按页码和表格索引收集所有表格
    all_tables = []

    # 按页码排序
    sorted_pages = sorted(all_page_tables.items(), key=lambda x: x[1].get('page_num', 0))

    for png_name, page_info in sorted_pages:
        tables = page_info.get('tables', [])
        # 按表格索引排序
        sorted_tables = sorted(tables, key=lambda x: extract_table_index(x.name) or 0)

        for table_path in sorted_tables:
            all_tables.append({
                'png_name': png_name,
                'table_path': table_path,
                'page_num': page_info.get('page_num', 0),
                'table_idx': extract_table_index(table_path.name) or 0,
                'filename': table_path.name
            })

    # 应用严格的相邻检测逻辑，确保不丢失图片
    table_groups = {}
    current_group_idx = 1
    current_group = []

    i = 0
    while i < len(all_tables):
        current_table = all_tables[i]
        stay_state = 0

        # 检查是否应该与下一个表格拼接
        if i + 1 < len(all_tables):
            next_table = all_tables[i + 1]

            # 严格遵循 re_join_sub_images_idx_7.py 的逻辑
            current_file = current_table['filename']
            next_file = next_table['filename']

            # 关键逻辑：检查文件名连续性
            if 'last' in current_file and '_0_' in next_file:
                # 提取索引
                try:
                    current_parts = current_file.split('_')
                    next_parts = next_file.split('_')

                    # 查找表格索引位置
                    current_idx_pos = -1
                    next_idx_pos = -1

                    # 查找 'table' 后面的数字
                    for j, part in enumerate(current_parts):
                        if part == 'table' and j + 1 < len(current_parts):
                            current_idx_pos = j + 1
                            break

                    for j, part in enumerate(next_parts):
                        if part == 'table' and j + 1 < len(next_parts):
                            next_idx_pos = j + 1
                            break

                    if current_idx_pos != -1 and next_idx_pos != -1:
                        pre_idx = int(current_parts[current_idx_pos])
                        post_idx = int(next_parts[next_idx_pos])

                        # 检查索引连续性
                        if post_idx == pre_idx + 1:
                            stay_state = 1
                            print(f"🔗 检测到相邻表格: {current_file} -> {next_file}")
                except (ValueError, IndexError) as e:
                    print(f"⚠️ 解析文件名失败: {current_file} -> {next_file}, 错误: {e}")

        # 将当前表格添加到当前组
        current_group.append((current_table['png_name'], current_table['table_path']))

        # 根据 stay_state 决定是否继续当前组
        if not stay_state:
            # 不拼接，结束当前组
            table_groups[current_group_idx] = current_group.copy()
            current_group_idx += 1
            current_group = []
            i += 1  # 移动到下一个表格
        else:
            # 需要拼接，继续当前组，i 会在循环中自动递增
            i += 1

    # 处理最后一组（如果有的话）
    if current_group:
        table_groups[current_group_idx] = current_group

    # 验证：确保没有丢失任何表格
    total_grouped_tables = sum(len(group) for group in table_groups.values())
    total_original_tables = len(all_tables)

    if total_grouped_tables != total_original_tables:
        print(f"❌ 表格丢失警告: 原始 {total_original_tables} 个表格, 分组后 {total_grouped_tables} 个表格")
        # 紧急修复：如果有丢失，将所有表格作为独立组
        table_groups = {}
        for idx, table in enumerate(all_tables, 1):
            table_groups[idx] = [(table['png_name'], table['table_path'])]
        print("🔄 已启用紧急修复：所有表格作为独立组处理")
    else:
        print(f"✅ 表格完整性验证通过: 所有 {total_original_tables} 个表格都已分组")

    print(f"📊 严格分组完成: 共 {len(table_groups)} 个表格组")
    for group_idx, tables in table_groups.items():
        table_names = [Path(t[1]).name for t in tables]
        print(f"  组 {group_idx} ({len(tables)} 个表格): {table_names}")

    return table_groups



def process_table_groups(table_groups: Dict[int, List[Tuple[str, Path]]],
                         join_root: Path, pdf_folder: str) -> Dict[int, Path]:
    """处理表格组，进行拼接和最终保存"""
    final_tables = {}

    for table_idx, table_list in table_groups.items():
        if not table_list:
            continue

        print(f"\n📊 处理表格组 {table_idx}: {len(table_list)} 个部分")

        if len(table_list) == 1:
            # 单页表格，直接复制
            _, table_path = table_list[0]
            final_path = join_root / pdf_folder / table_path.name
            final_path.parent.mkdir(parents=True, exist_ok=True)

            if not final_path.exists():
                Image.open(table_path).save(final_path)
                print(f"✅ 单页表格: {final_path.name}")
            else:
                print(f"⚠️ 表格已存在: {final_path.name}")

            final_tables[table_idx] = final_path

        else:
            # 多页表格，需要拼接
            image_paths = [table_path for _, table_path in table_list]
            final_path = join_root / pdf_folder / f"table_{table_idx}_joined.png"
            final_path.parent.mkdir(parents=True, exist_ok=True)

            if not final_path.exists():
                concat_images_vertically(image_paths, final_path)
                print(f"✅ 拼接表格: {len(image_paths)} 页 -> {final_path.name}")
            else:
                print(f"⚠️ 拼接表格已存在: {final_path.name}")

            final_tables[table_idx] = final_path

    return final_tables




# 保持向后兼容的导出
__all__ = [
    'batch_cut_tables',
    'layout_detect',
    'concat_images_vertically'
]