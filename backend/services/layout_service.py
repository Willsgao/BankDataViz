# layout_service.py (修复跨页关联逻辑)

import base64
import json
import requests
from PIL import Image
from pathlib import Path
from typing import List, Dict, Union, Tuple, Optional
from dataclasses import dataclass

DEFAULT_CONFIDENCE_THRESHOLD = 0.5
from backend.utils.constants import REMOTE_LAYOUT_URL

from backend.services.table_cutter import (
    cut_final_tables,
    extract_table_index,
    extract_page_num
)


@dataclass
class ProcessingStep:
    """处理步骤基类"""
    name: str
    description: str

    def execute(self, context: Dict) -> Dict:
        raise NotImplementedError


class LayoutDetectionStep(ProcessingStep):
    """步骤1: 布局检测"""

    def __init__(self):
        super().__init__("layout_detection", "检测页面布局和表格区域")

    def execute(self, context: Dict) -> Dict:
        pdf_folder = context['pdf_folder']
        png_names = context['png_names']
        output_root = context['output_root']
        confidence_threshold = context.get('confidence_threshold', 0.5)

        print(f"🔍 开始布局检测步骤...")

        output_root = Path(output_root)
        layout_res = {}
        all_page_tables = {}

        # 创建布局结果目录
        static_parent = output_root.parent
        LAYOUT_ROOT = static_parent / "layout_result" / pdf_folder
        LAYOUT_ROOT.mkdir(parents=True, exist_ok=True)

        # 按页码排序处理
        sorted_pngs = sorted(png_names, key=lambda x: extract_page_num(x) or 0)

        for png_name in sorted_pngs:
            png_path = output_root / pdf_folder / png_name

            try:
                print(f"📄 检测页面布局: {png_name}")

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

                # 存储布局结果
                all_page_tables[png_name] = {
                    'layout_data': remote_result,
                    'page_num': extract_page_num(png_name) or 0
                }

            except Exception as e:
                print(f"❌ 布局检测失败 {png_name}: {e}")
                all_page_tables[png_name] = {'layout_data': {}, 'page_num': 0}

        # 保存布局结果到文件
        layout_file = LAYOUT_ROOT / f"{pdf_folder}_layout.json"
        with open(layout_file, 'w', encoding='utf-8') as f:
            json.dump(layout_res, f, ensure_ascii=False, indent=2)

        context['layout_results'] = layout_res
        context['all_page_tables'] = all_page_tables
        context['layout_file'] = layout_file

        print(f"✅ 布局检测完成: {len(layout_res)} 个页面")
        return context


class TableCuttingStep(ProcessingStep):
    """步骤2: 表格切割"""

    def __init__(self):
        super().__init__("table_cutting", "切割检测到的表格区域")

    def execute(self, context: Dict) -> Dict:
        pdf_folder = context['pdf_folder']
        png_names = context['png_names']
        output_root = context['output_root']
        confidence_threshold = context.get('confidence_threshold', 0.5)
        layout_results = context.get('layout_results', {})
        all_page_tables = context.get('all_page_tables', {})

        print(f"🔪 开始表格切割步骤...")

        output_root = Path(output_root)
        static_parent = output_root.parent
        CROP_ROOT = static_parent / "cropped_tables" / pdf_folder
        CROP_ROOT.mkdir(parents=True, exist_ok=True)

        # 按页码排序处理
        sorted_pngs = sorted(png_names, key=lambda x: extract_page_num(x) or 0)

        for png_name in sorted_pngs:
            png_path = output_root / pdf_folder / png_name
            page_stem = png_path.stem
            page_out_dir = CROP_ROOT / page_stem

            try:
                print(f"📄 切割表格: {png_name}")

                # 检查是否已经处理过
                existing_tables = sorted(page_out_dir.glob("*_table_*.png"))
                if page_out_dir.exists() and existing_tables:
                    print(f"✅ 使用现有表格: {len(existing_tables)} 个表格")
                    current_tables = existing_tables
                else:
                    # 执行表格切割
                    layout_data = layout_results.get(png_name, {})
                    saved_paths = cut_final_tables(
                        img_path=png_path,
                        layout_json=layout_data,
                        out_dir=page_out_dir,
                        confidence_threshold=confidence_threshold
                    )
                    current_tables = saved_paths
                    print(f"✅ 表格切割完成: {len(current_tables)} 个表格")

                # 更新页面表格信息
                if png_name in all_page_tables:
                    all_page_tables[png_name]['tables'] = current_tables
                    all_page_tables[png_name]['page_dir'] = page_out_dir

            except Exception as e:
                print(f"❌ 表格切割失败 {png_name}: {e}")
                if png_name in all_page_tables:
                    all_page_tables[png_name]['tables'] = []

        context['all_page_tables'] = all_page_tables
        context['crop_root'] = CROP_ROOT

        print(f"✅ 表格切割完成")
        return context


class TableGroupingStep(ProcessingStep):
    """步骤3: 表格分组（跨页检测）"""

    def __init__(self):
        super().__init__("table_grouping", "检测跨页表格并进行分组")

    def execute(self, context: Dict) -> Dict:
        all_page_tables = context.get('all_page_tables', {})

        print(f"🔗 开始表格分组步骤...")

        # 使用严格的相邻图片分组逻辑
        table_groups = strict_adjacent_grouping(all_page_tables)
        print(">>table_groups>>>>")
        print(table_groups)

        context['table_groups'] = table_groups

        print(f"✅ 表格分组完成: {len(table_groups)} 个表格组")
        return context


class TableJoiningStep(ProcessingStep):
    """步骤4: 表格拼接"""

    def __init__(self):
        super().__init__("table_joining", "拼接跨页表格")

    def execute(self, context: Dict) -> Dict:
        pdf_folder = context['pdf_folder']
        output_root = context['output_root']
        table_groups = context.get('table_groups', {})

        print(f"🔄 开始表格拼接步骤...")

        output_root = Path(output_root)
        static_parent = output_root.parent
        JOINED_ROOT = static_parent / "joined_tables" / pdf_folder
        JOINED_ROOT.mkdir(parents=True, exist_ok=True)

        # 处理表格组，进行拼接和最终保存
        final_joined_tables = process_table_groups(
            table_groups, JOINED_ROOT, pdf_folder
        )

        # 获取拼接文件夹中的所有图片文件
        joined_images = []
        if JOINED_ROOT.exists():
            for img_file in sorted(JOINED_ROOT.glob("*.png")):
                relative_path = f"joined_tables/{pdf_folder}/{img_file.name}"
                joined_images.append(relative_path)
                print(f"✅ 找到表格文件: {relative_path}")

        context['joined_images'] = joined_images
        context['joined_root'] = JOINED_ROOT
        context['final_joined_tables'] = final_joined_tables

        print(f"✅ 表格拼接完成: {len(joined_images)} 个表格文件")
        return context


class TableProcessingPipeline:
    """表格处理管道"""

    def __init__(self):
        self.steps = {}
        self.register_default_steps()

    def register_default_steps(self):
        """注册默认处理步骤"""
        self.steps['layout'] = LayoutDetectionStep()
        self.steps['cut'] = TableCuttingStep()
        self.steps['group'] = TableGroupingStep()
        self.steps['join'] = TableJoiningStep()

    def register_step(self, name: str, step: ProcessingStep):
        """注册自定义步骤"""
        self.steps[name] = step

    def get_available_steps(self) -> List[str]:
        """获取可用步骤列表"""
        return list(self.steps.keys())

    def execute_step(self, step_name: str, context: Dict) -> Dict:
        """执行单个步骤"""
        if step_name not in self.steps:
            raise ValueError(f"未知步骤: {step_name}，可用步骤: {list(self.steps.keys())}")

        step = self.steps[step_name]
        print(f"\n{'=' * 50}")
        print(f"执行步骤: {step.name} - {step.description}")
        print(f"{'=' * 50}")

        return step.execute(context)

    def execute_pipeline(self, context: Dict, steps: Optional[List[str]] = None) -> Dict:
        """执行完整的处理管道"""
        if steps is None:
            steps = self.get_available_steps()

        current_context = context.copy()

        for step_name in steps:
            if step_name not in self.steps:
                raise ValueError(f"未知步骤: {step_name}")

            current_context = self.execute_step(step_name, current_context)

        return current_context


# 全局管道实例
processing_pipeline = TableProcessingPipeline()


# 保持原有函数兼容性，但内部使用新的管道系统
"""
重构后的批量表格处理函数，支持分步控制
"""
def batch_cut_tables(
        pdf_folder: str,
        png_names: List[str],
        output_root: Union[str, Path],
        confidence_threshold: float = 0.5,
        steps: Optional[List[str]] = None
):
    """
    批量切割表格主函数（修复版本）
    功能：处理PDF所有页面的表格检测、切割和跨页表格拼接
    伪代码：
        1. 初始化目录结构和变量
        2. 按页码排序处理每个页面
        3. 对每个页面进行远程布局检测或使用缓存结果
        4. 切割检测到的表格区域
        5. 使用严格相邻分组算法识别跨页表格
        6. 对跨页表格进行纵向拼接
        7. 返回处理结果和文件路径
    """

    try:
        # 初始化上下文
        context = {
            'pdf_folder': pdf_folder,
            'png_names': png_names,
            'output_root': output_root,
            'confidence_threshold': confidence_threshold
        }

        # 执行管道
        if steps is None:
            # 默认执行所有步骤
            result_context = processing_pipeline.execute_pipeline(context)
        else:
            # 执行指定步骤
            result_context = processing_pipeline.execute_pipeline(context, steps)

        # 构建最终返回结果
        joined_images = result_context.get('joined_images', [])

        final_response = {
            "success": True,
            "message": f"批量处理完成，成功生成 {len(joined_images)} 个表格文件",
            "data": {
                "total": len(joined_images),
                "joined": joined_images,
                "joined_tables_folder": str(result_context.get('joined_root', ''))
            },
            "details": {
                "pdf_folder": pdf_folder,
                "processed_pages": len(png_names),
                "total_tables": len(joined_images),
                "executed_steps": steps or processing_pipeline.get_available_steps()
            }
        }

        print(f"\n🎉 处理完成!")
        return final_response

    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "message": "批量裁切处理异常"
        }


# 新增：单独执行特定步骤的函数
def execute_single_step(
        step_name: str,
        pdf_folder: str,
        png_names: List[str],
        output_root: Union[str, Path],
        confidence_threshold: float = 0.5,
        previous_context: Optional[Dict] = None
):
    """执行单个处理步骤"""
    context = {
        'pdf_folder': pdf_folder,
        'png_names': png_names,
        'output_root': output_root,
        'confidence_threshold': confidence_threshold
    }

    if previous_context:
        context.update(previous_context)

    return processing_pipeline.execute_step(step_name, context)


# 远程布局检测函数
def layout_detect(
        png_path: Union[str, Path],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> Dict[str, Union[Dict, List[Dict]]]:
    """
        远程布局检测函数
        功能：调用远程布局检测服务，识别图片中的表格区域并返回检测结果
        伪代码：
            1. 验证图片文件存在性
            2. 将图片转换为base64编码
            3. 发送POST请求到远程布局检测服务
            4. 解析响应并过滤出置信度达标的表格区域
            5. 返回包含原始布局数据和表格区域的字典
    """
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


# """纵向拼接图片"""
def concat_images_vertically(img_paths: List[Path], out_path: Path) -> Path:
    """
        纵向图片拼接函数
        功能：将多张图片按垂直方向拼接成一张长图
        伪代码：
            1. 加载所有输入图片
            2. 计算拼接后的总高度和最大宽度
            3. 创建新的空白图片
            4. 按顺序将图片粘贴到新图片上
            5. 保存拼接结果并返回路径
    """
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


"""
严格相邻分组：确保不丢失任何图片，只对真正相邻的图片进行拼接
"""
def strict_adjacent_grouping1(all_page_tables: Dict) -> Dict[int, List[Tuple[str, Path]]]:

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


def strict_adjacent_grouping(all_page_tables: Dict) -> Dict[int, List[Tuple[str, Path]]]:
    """
    严格相邻分组：确保不丢失任何图片，只对真正相邻的图片进行拼接
    修复版本：基于页码连续性和表格索引一致性来判断跨页表格
    """
    """
    严格相邻分组函数
    功能：确保不丢失任何图片，只对真正相邻的图片进行拼接
    伪代码：
        1. 收集所有页面的表格并按页码和索引排序
        2. 遍历所有表格，检查文件名连续性
        3. 根据文件名模式判断是否为相邻表格
        4. 将连续的表格分到同一组
        5. 验证分组完整性，防止表格丢失
        6. 返回分组结果
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

    # 应用修复后的相邻检测逻辑
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
            current_file = current_table['filename']
            next_file = next_table['filename']

            # 修复：基于页码连续性和表格索引一致性来判断
            try:
                # 解析当前文件的页码和表格索引
                current_parts = current_file.split('_')
                next_parts = next_file.split('_')

                # 查找页码位置（文档ID后的第一个数字）
                current_page_num = current_table['page_num']
                next_page_num = next_table['page_num']

                # 获取表格索引
                current_table_idx = current_table['table_idx']
                next_table_idx = next_table['table_idx']

                # 关键修复逻辑：检查是否为连续的同一表格
                # 条件1：表格索引相同
                # 条件2：页码连续（下一页）
                # 条件3：当前表格标记为"last"或下一个表格标记为"0"（表示连续）
                if (current_table_idx == next_table_idx and
                        next_page_num == current_page_num + 1):

                    # 检查文件名中的连续性标记
                    current_has_last = 'last' in current_file.lower()
                    next_has_zero = '_0_' in next_file

                    # 如果当前表格标记为last且下一个表格标记为0，说明需要拼接
                    if current_has_last and next_has_zero:
                        stay_state = 1
                        print(f"🔗 检测到跨页表格连续性: {current_file} -> {next_file}")
                        print(f"   表格索引: {current_table_idx}, 页码: {current_page_num}->{next_page_num}")

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
            # 需要拼接，继续当前组
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

    # 打印分组详情
    print(f"📊 严格分组完成: 共 {len(table_groups)} 个表格组")
    for group_idx, tables in table_groups.items():
        table_names = [Path(t[1]).name for t in tables]
        page_nums = [all_page_tables[t[0]].get('page_num', 0) for t in tables]
        print(f"  组 {group_idx} ({len(tables)} 个表格, 页码: {page_nums}): {table_names}")

    return table_groups


"""处理表格组，进行拼接和最终保存 - 修正路径嵌套问题"""
def process_table_groups(table_groups: Dict[int, List[Tuple[str, Path]]],
                         join_root: Path, pdf_folder: str) -> Dict[int, Path]:
    """
    表格组处理函数
    功能：处理表格组，进行拼接和最终保存
    伪代码：
        1. 遍历所有表格组
        2. 对单页表格直接复制到目标目录
        3. 对多页表格进行纵向拼接
        4. 保存最终结果并记录文件路径
        5. 返回所有处理后的表格文件路径字典
    """
    final_tables = {}

    for table_idx, table_list in table_groups.items():
        if not table_list:
            continue

        print(f"\n📊 处理表格组 {table_idx}: {len(table_list)} 个部分")

        if len(table_list) == 1:
            # 单页表格，直接复制
            _, table_path = table_list[0]
            # 修正：不要再加 pdf_folder，join_root 已经包含了
            final_path = join_root / table_path.name  # ✅ 正确！
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
            # 修正：不要再加 pdf_folder，join_root 已经包含了
            final_path = join_root / f"table_{table_idx}_joined.png"  # ✅ 正确！
            final_path.parent.mkdir(parents=True, exist_ok=True)

            if not final_path.exists():
                concat_images_vertically(image_paths, final_path)
                print(f"✅ 拼接表格: {len(image_paths)} 页 -> {final_path.name}")
            else:
                print(f"⚠️ 拼接表格已存在: {final_path.name}")

            final_tables[table_idx] = final_path

    return final_tables





# 导出
__all__ = [
    'batch_cut_tables',
    'execute_single_step',
    'layout_detect',
    'concat_images_vertically',
    'processing_pipeline',
    'TableProcessingPipeline',
    'ProcessingStep'
]