import time
from typing import Dict, Any, List


# ====================================
# 1. OCR服务（复用analyzer中的OCR服务）
# ====================================

from backend.services.table_processor import TableOCRService
from backend.services.table_processor.llm_table_structure_parser import EnhancedFinancialTableAnalyzer
from backend.services.table_processor import TableReconstructor



# ====================================
# 4. 端到端管道
# ====================================

class TableReconstructionPipeline:
    """
    端到端表格重构管道
    输入：图片路径 → 输出：Excel文件
    """

    def __init__(self, ocr_service, llm_analyzer, table_reconstructor):
        """
        初始化管道组件
        """
        self.ocr_service = ocr_service
        self.llm_analyzer = llm_analyzer
        self.table_reconstructor = table_reconstructor

        # 处理统计
        self.stats = {
            'total_images': 0,
            'successful': 0,
            'failed': 0,
            'processing_time': 0
        }

    def process_single_image(self, image_path: str, output_excel: str = None, final_output_file: str=None) -> Dict[str, Any]:
        """
        处理单张图片的完整流程
        """
        start_time = time.time()

        print(f"\n{'=' * 60}")
        print(f"开始处理图片: {image_path}")
        print(f"{'=' * 60}")

        # 1. OCR识别
        print("步骤1: OCR识别表格...")
        try:
            ocr_result = self.ocr_service.recognize_table(image_path)
            print(f"✅ OCR完成，识别到{len(ocr_result.get('tables_result', []))}个表格")
        except Exception as e:
            print(f"❌ OCR识别失败: {str(e)}")
            self.stats['failed'] += 1
            return {'success': False, 'error': f'OCR失败: {str(e)}'}

        # 2. LLM分析表头结构
        print("步骤2: LLM分析表格结构...")
        try:
            llm_result = self.llm_analyzer.analyze_image(image_path, ocr_result)

            print("llm_resultllm_result:")
            from pprint import pprint
            pprint(llm_result)

            if not llm_result.get('success'):
                print(f"❌ LLM分析失败: {llm_result.get('error', '未知错误')}")
                self.stats['failed'] += 1
                return {'success': False, 'error': 'LLM分析失败'}

            print(f"✅ LLM分析完成，识别到{llm_result['processing_stats']['visual_tables_count']}个逻辑表格")

        except Exception as e:
            print(f"❌ LLM分析失败: {str(e)}")
            self.stats['failed'] += 1
            return {'success': False, 'error': f'LLM分析失败: {str(e)}'}

        # 3. 表格重构
        print("步骤3: 重构表格数据...")
        try:
            # 生成输出文件名
            if output_excel is None:
                import os
                image_name = os.path.splitext(os.path.basename(image_path))[0]
                output_excel = f"{image_name}_reconstructed.xlsx"

            # 重构表格
            success = self.table_reconstructor.process_all_tables(
                ocr_result=ocr_result,
                llm_result=llm_result,
                output_file=output_excel,
                final_output_file=final_output_file
            )

            if success:
                processing_time = time.time() - start_time
                print(f"✅ 表格重构成功！耗时: {processing_time:.2f}秒")
                print(f"   输出文件: {output_excel}")

                self.stats['successful'] += 1
                self.stats['processing_time'] += processing_time

                return {
                    'success': True,
                    'ocr_result': ocr_result,
                    'llm_result': llm_result,
                    'output_file': output_excel,
                    'processing_time': processing_time
                }
            else:
                print(f"❌ 表格重构失败")
                self.stats['failed'] += 1
                return {'success': False, 'error': '表格重构失败'}

        except Exception as e:
            print(f"❌ 表格重构失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.stats['failed'] += 1
            return {'success': False, 'error': f'表格重构失败: {str(e)}'}

    def process_batch_images(self, image_paths: List[str], output_dir: str = None) -> Dict[str, Any]:
        """
        批量处理多张图片
        """
        print(f"\n{'=' * 60}")
        print(f"开始批量处理 {len(image_paths)} 张图片")
        print(f"{'=' * 60}")

        results = []
        self.stats['total_images'] = len(image_paths)

        for i, image_path in enumerate(image_paths, 1):
            print(f"\n处理图片 {i}/{len(image_paths)}")

            # 生成输出路径
            output_excel = None
            final_output_file = None
            if output_dir:
                import os
                image_name = os.path.splitext(os.path.basename(image_path))[0]
                output_excel = os.path.join(output_dir, f"{image_name}_reconstructed.xlsx")
                output_excel = os.path.join(output_dir, f"{image_name}_final.xlsx")

            # 处理单张图片
            result = self.process_single_image(image_path, output_excel, final_output_file)
            result['image_path'] = image_path
            results.append(result)

        # 汇总统计
        print(f"\n{'=' * 60}")
        print(f"批量处理完成统计:")
        print(f"  总图片数: {self.stats['total_images']}")
        print(f"  成功: {self.stats['successful']}")
        print(f"  失败: {self.stats['failed']}")
        print(f"  平均耗时: {self.stats['processing_time'] / max(self.stats['successful'], 1):.2f}秒/图片")
        print(f"{'=' * 60}")

        return {
            'success': self.stats['failed'] == 0,
            'results': results,
            'stats': self.stats.copy()
        }


# ====================================
# 5. 配置和主函数
# ====================================

# -*- coding:utf-8 -*-

import os


class Config:
    """配置类"""
    # LLM配置
    LLM_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    LLM_API_KEY = "90b9c47f-815c-4216-913a-3d1a567e35ac"
    LLM_MODEL_NAME = "doubao-1-5-vision-pro-250328"

    # OCR配置
    OCR_API_KEY = "Id7EZH2q6IOSlivHbwHHbWwz"
    OCR_SECRET_KEY = "leeZiDapOBp6nGZssuuzABgSZubNgSLu"
    OCR_TIMEOUT = 30
    OCR_MAX_RETRIES = 3

    # 表格分析配置
    EXTRACT_ROWS = 10  # 提取的行数
    EXTRACT_COLS = 3  # 提取的列数
    MAX_RETRIES = 3  # 最大重试次数
    TIMEOUT = 30  # 超时时间

    # 路径配置
    TEMP_DIR = "./temp_imgs"
    OUTPUT_DIR = "../../test_codes/enhanced_table_analyzer/output"


# 创建配置实例
config = Config()
settings = config  # 别名，保持兼容性


def create_pipeline():
    """
    创建完整的处理管道
    """
    # 1. OCR服务
    ocr_service = TableOCRService()

    # 2. LLM分析器 - 根据EnhancedFinancialTableAnalyzer的实际构造函数参数调整
    # 通常analyzer应该接收config对象或直接使用全局配置
    try:
        # 尝试创建analyzer（可能需要检查analyzer的实际构造函数）
        # 方法1：直接使用默认构造函数
        llm_analyzer = EnhancedFinancialTableAnalyzer()

        # 方法2：如果需要配置，可能需要这样：
        # from test_codes.enhanced_table_analyzer.config import Config as AnalyzerConfig
        # 或者查看analyzer的实际定义来了解正确的参数
    except TypeError as e:
        print(f"创建LLM分析器失败: {e}")
        print("请检查EnhancedFinancialTableAnalyzer的构造函数参数...")
        # 回退到其他创建方式
        # 尝试使用位置参数
        llm_analyzer = EnhancedFinancialTableAnalyzer(
            Config.LLM_BASE_URL,
            Config.LLM_API_KEY,
            Config.LLM_MODEL_NAME
        )

    # 3. 表格重构器
    table_reconstructor = TableReconstructor()

    # 4. 创建管道
    pipeline = TableReconstructionPipeline(
        ocr_service=ocr_service,
        llm_analyzer=llm_analyzer,
        table_reconstructor=table_reconstructor
    )

    return pipeline


# ====================================
# 6. 使用示例
# ====================================

def main(image_path):
    """
    主函数：处理单张图片示例
    """
    # 创建管道
    print("初始化表格重构管道...")

    try:
        pipeline = create_pipeline()
    except Exception as e:
        print(f"❌ 创建管道失败: {e}")
        print("尝试检查analyzer的构造函数...")
        import traceback
        traceback.print_exc()
        return


    # 处理图片
    result = pipeline.process_single_image(image_path)

    # 输出结果
    if result['success']:
        print(f"\n✅ 处理成功！")
        print(f"   输出文件: {result['output_file']}")
        print(f"   处理耗时: {result['processing_time']:.2f}秒")
    else:
        print(f"\n❌ 处理失败: {result.get('error', '未知错误')}")


def batch_example(image_paths, output_dir):
    """
    批量处理示例
    """
    # 创建管道
    pipeline = create_pipeline()

    # 批量处理
    result = pipeline.process_batch_images(image_paths, output_dir)


if __name__ == "__main__":

    # 输入图片路径
    image_path = r"E:\Datas\base_pros\DocuVista\test_codes\pngs\123.png"

    # # 运行单张图片处理
    # main(image_path)

    # 批量图片路径
    image_paths = [
    ]
    cur_dir = os.getcwd()
    par_dir = os.path.dirname(cur_dir)
    print("cur_dir:", cur_dir)
    # png_dir = fr"{par_dir}\png2"
    png_dir = r"C:\Users\1\Desktop\pngs"
    for root,_,files in os.walk(png_dir):
        for file in files:
            filename = fr"{png_dir}\{file}"
            image_paths.append(filename)
    print("image_paths:", image_paths)

    # 输出目录
    # output_dir = fr"{cur_dir}\outputs"
    output_dir = r"F:\wills\codes\DocuVista\test_codes\table_analyzer_codes\outputs1"
    print(">>>>>>>>output_dir>>>>>>>>>>>")
    print(output_dir)

    batch_example(image_paths, output_dir)