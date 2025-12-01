#!/usr/bin/env python3
"""
批量图片表格分析工具 - 直接设置参数版本
"""

import os
import sys
import time
from pathlib import Path
from typing import List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.analyzer import FinancialTableAnalyzer
from core.ocr_service import TableOCRService
from core.aligner import TableDataAligner
from utils.config import settings


class BatchTableProcessor:
    """批量表格处理器"""

    def __init__(self):
        self.analyzer = FinancialTableAnalyzer()
        self.ocr_service = TableOCRService()
        self.aligner = TableDataAligner()

    def find_images(self, input_dir: str, pattern: str = "*", recursive: bool = True) -> List[str]:
        """查找目录中的图片文件"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}
        image_paths = []

        if recursive:
            # 递归查找所有子目录
            for root, _, files in os.walk(input_dir):
                for file in files:
                    file_path = Path(file)
                    if file_path.suffix.lower() in image_extensions:
                        if pattern == "*" or pattern in file:
                            image_paths.append(os.path.join(root, file))
        else:
            # 只查找当前目录
            for file in os.listdir(input_dir):
                file_path = Path(file)
                if file_path.suffix.lower() in image_extensions:
                    if pattern == "*" or pattern in file:
                        image_paths.append(os.path.join(input_dir, file))

        # 按文件名排序
        image_paths.sort()
        return image_paths

    def process_single_image(self, image_path: str, output_dir: str) -> dict:
        """处理单张图片"""
        base_name = Path(image_path).stem
        print(f"  📄 处理: {os.path.basename(image_path)}")

        try:
            # 1. LLM分析
            llm_result = self.analyzer.analyze([image_path])
            llm_output = os.path.join(output_dir, f"{base_name}_llm.json")
            self.analyzer.save_results_to_json(llm_result, llm_output)

            # 2. OCR识别
            ocr_result = self.ocr_service.recognize_table_from_file(image_path)
            ocr_output = os.path.join(output_dir, f"{base_name}_ocr.json")
            self.ocr_service.save_result_to_json(ocr_result, ocr_output)

            # 3. 数据对齐
            aligned_json = os.path.join(output_dir, f"{base_name}_aligned.json")
            aligned_excel = os.path.join(output_dir, f"{base_name}_aligned.xlsx")

            aligned_tables = self.aligner.align_data(
                llm_path=llm_output,
                ocr_path=ocr_output,
                output_path=aligned_json,
                excel_path=aligned_excel,
                use_image_id=True
            )

            result = {
                "status": "success",
                "image_path": image_path,
                "aligned_tables": aligned_tables,
                "alignment_summary": {
                    "total_aligned_tables": len(aligned_tables),
                    "average_similarity": sum(t.get('similarity_score', 0) for t in aligned_tables) / len(
                        aligned_tables) if aligned_tables else 0
                },
                "output_files": {
                    "llm": llm_output,
                    "ocr": ocr_output,
                    "json": aligned_json,
                    "excel": aligned_excel
                }
            }

            print(
                f"  ✅ 完成! 表格: {len(aligned_tables)}个, 相似度: {result['alignment_summary']['average_similarity']:.2f}")
            return result

        except Exception as e:
            print(f"  ❌ 失败: {e}")
            return {
                "status": "failed",
                "image_path": image_path,
                "error": str(e),
                "aligned_tables": [],
                "alignment_summary": {
                    "total_aligned_tables": 0,
                    "average_similarity": 0
                }
            }

    def batch_process(self, input_dir: str, output_dir: str, pattern: str = "*",
                      limit: int = None, recursive: bool = True) -> dict:
        """批量处理图片"""
        print("🔍 查找图片文件...")
        image_paths = self.find_images(input_dir, pattern, recursive)

        if not image_paths:
            print("❌ 未找到图片文件")
            return {}

        if limit:
            image_paths = image_paths[:limit]
            print(f"📝 限制处理前 {limit} 张图片")

        print(f"📁 找到 {len(image_paths)} 张图片")
        print("=" * 60)

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        batch_results = {
            "batch_info": {
                "input_dir": input_dir,
                "output_dir": output_dir,
                "total_images": len(image_paths),
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "pattern": pattern,
                "recursive": recursive,
                "limit": limit
            },
            "image_results": [],
            "statistics": {
                "processed": 0,
                "succeeded": 0,
                "failed": 0,
                "total_tables": 0,
                "total_processing_time": 0
            }
        }

        start_time = time.time()

        for i, image_path in enumerate(image_paths, 1):
            print(f"\n[{i}/{len(image_paths)}] ", end="")

            image_start = time.time()
            result = self.process_single_image(image_path, output_dir)
            processing_time = time.time() - image_start

            result["processing_time"] = round(processing_time, 2)
            batch_results["image_results"].append(result)

            # 更新统计
            batch_results["statistics"]["processed"] += 1
            if result["status"] == "success":
                batch_results["statistics"]["succeeded"] += 1
                batch_results["statistics"]["total_tables"] += len(result["aligned_tables"])
            else:
                batch_results["statistics"]["failed"] += 1

        # 计算总体统计
        total_time = time.time() - start_time
        batch_results["statistics"]["total_processing_time"] = round(total_time, 2)
        batch_results["batch_info"]["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        batch_results["batch_info"]["total_time_seconds"] = total_time

        # 保存批量结果
        self.save_batch_results(batch_results, output_dir)

        return batch_results

    def save_batch_results(self, batch_results: dict, output_dir: str):
        """保存批量处理结果"""
        # JSON格式结果
        json_path = os.path.join(output_dir, "batch_results.json")
        import json
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2)

        # 文本报告
        report_path = os.path.join(output_dir, "processing_report.txt")
        self.generate_text_report(batch_results, report_path)

        print(f"\n💾 批量结果已保存:")
        print(f"   JSON: {json_path}")
        print(f"   报告: {report_path}")

    def generate_text_report(self, batch_results: dict, report_path: str):
        """生成文本报告"""
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("财务表格批量分析报告\n")
            f.write("=" * 50 + "\n\n")

            batch_info = batch_results["batch_info"]
            stats = batch_results["statistics"]

            f.write(f"输入目录: {batch_info['input_dir']}\n")
            f.write(f"输出目录: {batch_info['output_dir']}\n")
            f.write(f"开始时间: {batch_info['start_time']}\n")
            f.write(f"结束时间: {batch_info['end_time']}\n")
            f.write(f"总耗时: {stats['total_processing_time']}秒\n\n")

            f.write("处理统计:\n")
            f.write(f"  总图片数: {batch_info['total_images']}\n")
            f.write(f"  已处理: {stats['processed']}\n")
            f.write(f"  成功: {stats['succeeded']}\n")
            f.write(f"  失败: {stats['failed']}\n")
            f.write(f"  总表格数: {stats['total_tables']}\n\n")

            f.write("详细结果:\n")
            f.write("-" * 50 + "\n")

            for i, result in enumerate(batch_results["image_results"], 1):
                f.write(f"\n{i}. {os.path.basename(result['image_path'])}\n")
                f.write(f"   状态: {'✅ 成功' if result['status'] == 'success' else '❌ 失败'}\n")
                f.write(f"   耗时: {result.get('processing_time', 0)}秒\n")

                if result["status"] == "success":
                    summary = result["alignment_summary"]
                    f.write(f"   表格数: {summary['total_aligned_tables']}\n")
                    f.write(f"   平均相似度: {summary['average_similarity']:.2f}\n")
                else:
                    f.write(f"   错误: {result['error']}\n")


def main(main_dir):
    """主函数 - 在这里直接设置参数"""

    # ======================== 在这里设置参数 ========================
    INPUT_DIR = fr"{main_dir}\pngs"  # 输入图片目录
    OUTPUT_DIR = fr"{main_dir}\table_analyzer\batch_results"  # 输出目录
    PATTERN = "*"  # 文件匹配模式，如 "*.png", "*table*"
    LIMIT = None  # 限制处理数量，None表示不限制
    RECURSIVE = True  # 是否递归子目录
    # ======================== 参数设置结束 ========================

    # 检查输入目录是否存在
    if not os.path.exists(INPUT_DIR):
        print(f"❌ 输入目录不存在: {INPUT_DIR}")
        print("💡 请检查 INPUT_DIR 参数是否正确")
        return

    processor = BatchTableProcessor()

    print("🚀 启动批量表格分析...")
    print(f"📁 输入目录: {INPUT_DIR}")
    print(f"💾 输出目录: {OUTPUT_DIR}")
    print(f"🔍 文件模式: {PATTERN}")
    if LIMIT:
        print(f"📊 处理限制: {LIMIT} 张图片")
    print(f"📂 递归查找: {'是' if RECURSIVE else '否'}")
    print("=" * 60)

    # 执行批量处理
    results = processor.batch_process(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        pattern=PATTERN,
        limit=LIMIT,
        recursive=RECURSIVE
    )

    # 显示最终统计
    if results:
        stats = results["statistics"]
        print("\n" + "=" * 60)
        print("🎉 批量处理完成!")
        print("=" * 60)
        print(f"📊 最终统计:")
        print(f"   总图片: {stats['processed']}")
        print(f"   成功: {stats['succeeded']} ✅")
        print(f"   失败: {stats['failed']} ❌")
        print(f"   总表格: {stats['total_tables']}")
        print(f"   总耗时: {stats['total_processing_time']}秒")
        if stats['processed'] > 0:
            print(f"   平均每张: {stats['total_processing_time'] / stats['processed']:.1f}秒")


if __name__ == "__main__":

    import os

    cur_dir = os.getcwd()
    main_dir = os.path.dirname(cur_dir)
    main(main_dir)