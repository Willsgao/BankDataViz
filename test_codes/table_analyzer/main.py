import os
import argparse
import time
import json
from typing import Dict, Any, List, Union
from pathlib import Path

from core.analyzer import FinancialTableAnalyzer
from core.ocr_service import TableOCRService
from core.aligner import TableDataAligner
from utils.config import settings


class FinancialTablePipeline:
    """统一的财务表格分析管道 - 支持批量处理"""

    def __init__(self):
        self.analyzer = FinancialTableAnalyzer()
        self.ocr_service = TableOCRService()
        self.aligner = TableDataAligner()

    def process_single_image(self, image_path: str, output_dir: str = None) -> Dict:
        """处理单张图片的完整流程"""
        if output_dir is None:
            output_dir = os.getcwd()

        os.makedirs(output_dir, exist_ok=True)
        base_name = Path(image_path).stem

        print(f"🔍 开始处理图片: {image_path}")

        # 1. LLM分析
        print("📊 进行LLM分析...")
        llm_result = self.analyzer.analyze([image_path])

        # 使用图片特定的命名
        llm_output = os.path.join(output_dir, f"{base_name}_llm.json")
        self.analyzer.save_results_to_json(llm_result, llm_output)

        # 2. OCR识别
        print("🔤 进行OCR识别...")
        ocr_result = self.ocr_service.recognize_table_from_file(image_path)

        # 使用图片特定的命名
        ocr_output = os.path.join(output_dir, f"{base_name}_ocr.json")
        self.ocr_service.save_result_to_json(ocr_result, ocr_output)

        # 3. 数据对齐
        print("🔄 进行数据对齐...")

        # 使用图片特定的命名
        aligned_json_path = os.path.join(output_dir, f"{base_name}_aligned.json")
        aligned_excel_path = os.path.join(output_dir, f"{base_name}_aligned.xlsx")

        aligned_tables = self.aligner.align_data(
            llm_path=llm_output,
            ocr_path=ocr_output,
            output_path=aligned_json_path,
            excel_path=aligned_excel_path,
            use_image_id=True
        )

        # 构建完整的结果字典
        result = {
            "image_path": image_path,
            "image_id": ocr_result.get("image_info", {}).get("image_id", ""),
            "aligned_tables": aligned_tables,
            "alignment_summary": {
                "total_aligned_tables": len(aligned_tables),
                "unmatched_llm_tables": len(self.aligner.unmatched_llm_tables),
                "unmatched_ocr_tables": len(self.aligner.unmatched_ocr_tables),
                "average_similarity": sum(t.get('similarity_score', 0) for t in aligned_tables) / len(
                    aligned_tables) if aligned_tables else 0
            },
            "output_files": {
                "llm_output": llm_output,
                "ocr_output": ocr_output,
                "aligned_json": aligned_json_path,
                "aligned_excel": aligned_excel_path
            }
        }

        print("✅ 单张图片处理完成!")
        return result

    def batch_process_images(self, image_paths: List[str], output_dir: str = None) -> Dict:
        """批量处理多张图片"""
        if output_dir is None:
            output_dir = os.getcwd()

        os.makedirs(output_dir, exist_ok=True)

        print(f"🚀 开始批量处理 {len(image_paths)} 张图片...")
        print("=" * 60)

        batch_results = {
            "batch_info": {
                "total_images": len(image_paths),
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "output_dir": output_dir
            },
            "image_results": [],
            "batch_summary": {
                "total_aligned_tables": 0,
                "total_images_processed": 0,
                "total_images_failed": 0,
                "overall_average_similarity": 0,
                "total_processing_time": 0
            }
        }

        start_time = time.time()
        processed_count = 0
        failed_count = 0

        for i, image_path in enumerate(image_paths, 1):
            print(f"\n📄 处理进度: {i}/{len(image_paths)}")
            print(f"🖼️  正在处理: {os.path.basename(image_path)}")

            try:
                # 处理单张图片
                single_result = self.process_single_image(image_path, output_dir)
                batch_results["image_results"].append(single_result)

                # 更新批量统计
                batch_results["batch_summary"]["total_aligned_tables"] += len(single_result["aligned_tables"])
                batch_results["batch_summary"]["total_images_processed"] += 1
                processed_count += 1

                # 打印单张图片结果
                summary = single_result["alignment_summary"]
                print(
                    f"   ✅ 完成! 表格: {summary['total_aligned_tables']}个, 相似度: {summary['average_similarity']:.2f}")

            except Exception as e:
                print(f"   ❌ 处理失败: {e}")
                # 记录失败信息
                failed_result = {
                    "image_path": image_path,
                    "error": str(e),
                    "aligned_tables": [],
                    "alignment_summary": {
                        "total_aligned_tables": 0,
                        "unmatched_llm_tables": 0,
                        "unmatched_ocr_tables": 0,
                        "average_similarity": 0
                    }
                }
                batch_results["image_results"].append(failed_result)
                batch_results["batch_summary"]["total_images_failed"] += 1
                failed_count += 1

        # 计算总体统计
        total_time = time.time() - start_time
        batch_results["batch_summary"]["total_processing_time"] = round(total_time, 2)
        batch_results["batch_info"]["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        batch_results["batch_info"]["total_processing_time_seconds"] = total_time

        # 计算总体平均相似度
        successful_results = [r for r in batch_results["image_results"] if
                              r["alignment_summary"]["total_aligned_tables"] > 0]
        if successful_results:
            total_similarity = sum(r["alignment_summary"]["average_similarity"] for r in successful_results)
            batch_results["batch_summary"]["overall_average_similarity"] = total_similarity / len(successful_results)

        # 保存批量处理结果
        batch_output_path = os.path.join(output_dir, "batch_processing_results.json")
        with open(batch_output_path, 'w', encoding='utf-8') as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print("🎉 批量处理完成!")
        print(f"📊 处理统计:")
        print(f"   总图片数: {len(image_paths)}")
        print(f"   成功处理: {processed_count}")
        print(f"   处理失败: {failed_count}")
        print(f"   总表格数: {batch_results['batch_summary']['total_aligned_tables']}")
        print(f"   总体相似度: {batch_results['batch_summary']['overall_average_similarity']:.2f}")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   批量结果: {batch_output_path}")

        return batch_results

    def process_image_directory(self, image_dir: str, output_dir: str = None) -> Dict:
        """处理图片目录中的所有图片"""
        if not os.path.exists(image_dir):
            raise FileNotFoundError(f"图片目录不存在: {image_dir}")

        # 查找所有图片文件
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
        image_paths = []

        for root, _, files in os.walk(image_dir):
            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    image_paths.append(os.path.join(root, file))

        if not image_paths:
            print(f"❌ 在目录 {image_dir} 中未找到图片文件")
            return {}

        print(f"📁 在目录中找到 {len(image_paths)} 张图片")

        # 按文件名排序
        image_paths.sort()

        return self.batch_process_images(image_paths, output_dir)

    def process_pdf(self, pdf_path: str, output_dir: str = None) -> Dict:
        """处理PDF文件（转换为图片后批量处理）"""
        if output_dir is None:
            output_dir = os.getcwd()

        os.makedirs(output_dir, exist_ok=True)
        pdf_name = Path(pdf_path).stem

        print(f"🔍 开始处理PDF: {pdf_path}")

        # 1. 将PDF转为图片
        print("📄 转换PDF为图片...")
        temp_dir = os.path.join(output_dir, f"{pdf_name}_temp_images")
        image_paths = self.analyzer.image_utils.pdf_to_images(pdf_path, temp_dir)

        print(f"✅ PDF转换为 {len(image_paths)} 张图片")

        # 2. 批量处理图片
        batch_results = self.batch_process_images(image_paths, output_dir)

        # 添加PDF信息
        batch_results["pdf_info"] = {
            "pdf_path": pdf_path,
            "total_pages": len(image_paths),
            "temp_image_dir": temp_dir
        }

        # 清理临时图片（可选）
        cleanup = input("\n🗑️  是否清理临时图片文件？(y/N): ").lower().strip()
        if cleanup == 'y':
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print("✅ 临时图片已清理")
        else:
            print("💾 临时图片保留在: " + temp_dir)

        return batch_results


def find_images_in_directory(directory: str) -> List[str]:
    """在目录中查找所有图片文件"""
    image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
    image_paths = []

    for root, _, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                image_paths.append(os.path.join(root, file))

    return sorted(image_paths)


def main():
    """命令行入口 - 支持批量处理"""
    parser = argparse.ArgumentParser(description="财务表格分析管道 - 批量处理版")
    parser.add_argument("--input", help="输入文件路径（图片、PDF或目录）", default="")
    parser.add_argument("--image_dir", help="图片目录路径", default="")
    parser.add_argument("-o", "--output", help="输出目录", default="./batch_output")
    parser.add_argument("--type", choices=["image", "pdf", "directory", "batch"], help="输入类型")
    parser.add_argument("--recursive", action="store_true", help="递归查找子目录中的图片")

    args = parser.parse_args()

    pipeline = FinancialTablePipeline()

    # 如果没有命令行参数，使用原先的测试方式
    if not args.input and not args.image_dir:
        print("🚀 使用测试配置...")

        code_dir = os.getcwd()
        parent_dir = os.path.dirname(code_dir)

        # 测试图片目录
        test_image_dir = os.path.join(parent_dir, "pngs")

        if os.path.exists(test_image_dir):
            print(f"📁 使用测试图片目录: {test_image_dir}")
            result = pipeline.process_image_directory(test_image_dir, code_dir)
        else:
            # 单张测试图片
            test_image = os.path.join(parent_dir, "pngs", "514001_158.png")
            if os.path.exists(test_image):
                print(f"📄 使用测试图片: {test_image}")
                result = pipeline.process_single_image(test_image, code_dir)
            else:
                print("❌ 未找到测试文件，请使用命令行参数指定输入")
                return

    else:
        # 使用命令行参数
        input_path = args.input or args.image_dir

        if args.type == "pdf" or (args.input and args.input.lower().endswith('.pdf')):
            result = pipeline.process_pdf(input_path, args.output)
        elif args.type == "directory" or os.path.isdir(input_path):
            result = pipeline.process_image_directory(input_path, args.output)
        else:
            # 单张图片处理
            result = pipeline.process_single_image(input_path, args.output)

    # 打印最终摘要
    if "batch_summary" in result:
        summary = result["batch_summary"]
        print(f"\n🎯 批量处理摘要:")
        print(f"   总图片数: {summary['total_images_processed'] + summary['total_images_failed']}")
        print(f"   成功处理: {summary['total_images_processed']}")
        print(f"   处理失败: {summary['total_images_failed']}")
        print(f"   总表格数: {summary['total_aligned_tables']}")
        print(f"   总体相似度: {summary['overall_average_similarity']:.2f}")
        print(f"   总耗时: {summary['total_processing_time']}秒")


if __name__ == "__main__":
    main()