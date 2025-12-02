# -*- coding:utf-8 -*-

import json
import os
from test_codes.enhanced_table_analyzer.analyzer import FinancialTableAnalyzer
from test_codes.enhanced_table_analyzer.config import settings
from test_codes.enhanced_table_analyzer.utils.image_utils import ImageUtils

# 导入Excel导出模块
try:
    # 导入新的导出函数
    from test_codes.enhanced_table_analyzer.excel_exporter import export_analysis_to_excel

    EXCEL_EXPORT_AVAILABLE = True
except ImportError as e:
    EXCEL_EXPORT_AVAILABLE = False
    print(f"⚠️  Excel导出模块不可用: {e}")


def generate_excel_compatible111(result: dict, img_path: str, output_dir: str) -> str:
    """
    兼容函数：调用新的export_analysis_to_excel函数

    Args:
        result: 分析结果
        img_path: 图片路径
        output_dir: 输出目录

    Returns:
        Excel文件路径
    """
    import os

    # 生成输出文件名
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    output_filename = f"{base_name}_aligned.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    # 提取OCR数据
    ocr_data = []
    tables_analysis = result.get("tables_analysis", [])
    for table_result in tables_analysis:
        if table_result.get("success", False):
            source_data = table_result.get("source_data", {})
            ocr_extract = source_data.get("ocr_extract", {})
            if ocr_extract:
                ocr_data.append(ocr_extract)

    # 调用新的导出函数
    return export_analysis_to_excel(result, output_path, ocr_data)


def generate_excel_compatible(result: dict, img_path: str, output_dir: str) -> str:
    import os

    base_name = os.path.splitext(os.path.basename(img_path))[0]
    output_filename = f"{base_name}_aligned.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    # 提取OCR数据 - 修正版本
    ocr_data = []
    tables_analysis = result.get("tables_analysis", [])

    for table_result in tables_analysis:
        if table_result.get("success", False):
            # 尝试从table_info中获取OCR数据
            table_info = table_result.get("table_info", {})
            # 或者从其他地方获取原始OCR数据
            # 这里需要根据实际的OCR数据存储位置调整

            # 临时方案：如果OCR数据不可用，就传空列表
            ocr_data.append({})

    try:
        return export_analysis_to_excel(result, output_path, ocr_data)
    except Exception as e:
        print(f"Excel导出失败: {e}")
        # 尝试不传递OCR数据
        return export_analysis_to_excel(result, output_path, None)

def main(input_dir, output_dir, json_file=""):
    """主函数"""

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    print(f"正在扫描文件夹: {input_dir}")

    # 检查文件夹是否存在
    if not os.path.exists(input_dir):
        print(f"错误: 文件夹不存在 - {input_dir}")
        return

    # 扫描图片文件
    import glob
    image_extensions = ['*.png', '*.jpg', '*.jpeg']
    image_paths = []

    for ext in image_extensions:
        image_paths.extend(glob.glob(os.path.join(input_dir, ext)))

    image_paths = sorted(list(set(image_paths)))

    print(f"找到 {len(image_paths)} 个图片文件")

    if len(image_paths) == 0:
        print("错误: 在指定文件夹中未找到任何图片文件")
        return

    # 询问用户确认
    response = input(f"\n是否开始分析这 {len(image_paths)} 个图片文件？(y/n): ")
    if response.lower() != 'y':
        print("操作已取消")
        return

    # 初始化分析器
    analyzer = FinancialTableAnalyzer()
    from test_codes.enhanced_table_analyzer.ocr_service import TableOCRService
    ocr_service = TableOCRService()

    print("\n开始批量分析图片...")

    # 逐个处理图片
    for idx, img_path in enumerate(image_paths):
        print(f"\n[{idx + 1}/{len(image_paths)}] 处理图片: {os.path.basename(img_path)}")

        try:
            # 分析图片
            result = analyzer.analyze_image(img_path, ocr_service, json_file)

            # 保存JSON结果
            json_filename = f"{os.path.splitext(os.path.basename(img_path))[0]}_analysis.json"
            json_path = os.path.join(output_dir, json_filename)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  已保存JSON结果到: {json_filename}")

            # 导出Excel
            if EXCEL_EXPORT_AVAILABLE:
                try:
                    # 使用新的兼容函数
                    excel_path = generate_excel_compatible(result, img_path, output_dir)
                    print(f"  已保存Excel结果到: {os.path.basename(excel_path)}")
                except Exception as e:
                    print(f"  Excel导出失败: {str(e)}")
            else:
                print("  ⚠️  Excel导出功能未启用")

        except Exception as e:
            print(f"  处理失败: {str(e)}")

    print(f"\n{'=' * 60}")
    print("批量分析完成!")


if __name__ == "__main__":
    # 直接指定图片文件夹地址

    main_dir = os.getcwd()
    par_dir = os.path.dirname(main_dir)
    input_dir = fr"{par_dir}\pngs"
    output_dir = fr"{par_dir}\enhanced_table_analyzer\output"
    json_file = fr"{par_dir}\data_555.json"
    main(input_dir, output_dir, json_file)