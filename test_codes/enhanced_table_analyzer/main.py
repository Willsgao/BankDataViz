# -*- coding:utf-8 -*-

import json
import os
from test_codes.enhanced_table_analyzer.analyzer import FinancialTableAnalyzer
from test_codes.enhanced_table_analyzer.config import settings
from test_codes.enhanced_table_analyzer.utils.image_utils import ImageUtils

# 导入Excel导出模块
try:
    from test_codes.enhanced_table_analyzer.excel_exporter import generate_excel_directly

    EXCEL_EXPORT_AVAILABLE = True
except ImportError as e:
    EXCEL_EXPORT_AVAILABLE = False
    print(f"⚠️  Excel导出模块不可用: {e}")


def main(input_dir, output_dir):
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
            result = analyzer.analyze_image(img_path, ocr_service)

            # 保存JSON结果
            json_filename = f"{os.path.splitext(os.path.basename(img_path))[0]}_analysis.json"
            json_path = os.path.join(output_dir, json_filename)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  已保存JSON结果到: {json_filename}")

            # 导出Excel
            if EXCEL_EXPORT_AVAILABLE:
                try:
                    excel_path = generate_excel_directly(result, img_path, output_dir)
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
    input_dir = r"E:\Datas\base_pros\DocuVista\test_codes\pngs"
    output_dir = r"E:\Datas\base_pros\DocuVista\test_codes\enhanced_table_analyzer\output"
    main(input_dir, output_dir)