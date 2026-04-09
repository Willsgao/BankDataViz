
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List

# ====================================
# 1. OCR服务（复用analyzer中的OCR服务）
# ====================================
from backend.configs.config import tableconfig
from backend.core.table_processor.ocr_gateway import TableOCRService
from backend.core.table_processor.llm_table_structure_parser import EnhancedFinancialTableAnalyzer
from backend.core.table_processor.table_rebuilder import TableReconstructor


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

    def process_single_image(self, image_path: str, output_excel: str = None, final_output_file: str=None, bank_name="") -> Dict[str, Any]:
        """
        处理单张图片的完整流程
        """
        start_time = time.time()

        print(f"\n{'=' * 60}")
        print(f"开始处理图片: {image_path}")
        print(f"{'=' * 60}")

        # 1. OCR识别
        print("步骤1: OCR识别表格...")
        ocr_result = self.ocr_service.recognize_table(image_path)
        print(f"✅ OCR完成，识别到{len(ocr_result.get('tables_result', []))}个表格")

        # 2. LLM分析表头结构
        print("步骤2: LLM分析表格结构...")
        # try:
        llm_result = self.llm_analyzer.analyze_image(image_path, ocr_result)

        if not llm_result.get('success'):
            print(f"❌ LLM分析失败222: {llm_result.get('error', '未知错误')}")
            self.stats['failed'] += 1
            return {'success': False, 'error': 'LLM分析失败'}

        print(f"✅ LLM分析完成，识别到{llm_result['processing_stats']['visual_tables_count']}个逻辑表格")


        # 3. 表格重构
        print("步骤3: 重构表格数据...")
        try:
            # 生成输出文件名
            if output_excel is None:
                image_name = os.path.splitext(os.path.basename(image_path))[0]
                # 🔥 使用 tableconfig 中的绝对输出目录
                output_dir = Path(tableconfig.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_excel = str(output_dir / f"{image_name}_reconstructed.xlsx")


            # 重构表格（现在返回 dict 包含 review_results）
            result = self.table_reconstructor.process_all_tables(
                ocr_result=ocr_result,
                llm_result=llm_result,
                output_file=output_excel,
                final_output_file=final_output_file,
                image_path=image_path,
                bank_name=bank_name
            )

            success = result.get('success', False)
            review_results = result.get('review_results', [])

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
                    'processing_time': processing_time,
                    'review_results': review_results  # 新增审核结果
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

    def process_batch_images(self, image_paths: List[str], output_dir: str = None, bank_name="") -> Dict[str, Any]:
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
                image_name = os.path.splitext(os.path.basename(image_path))[0]

                # 确保 output_dir 是 Path 对象
                output_dir_path = Path(tableconfig.output_dir)
                output_dir_path.mkdir(parents=True, exist_ok=True)

                output_excel = str(output_dir_path / f"{image_name}_reconstructed.xlsx")
                final_output_file = str(output_dir_path / f"{image_name}_final.xlsx")

            # 处理单张图片
            result = self.process_single_image(image_path, output_excel, final_output_file, bank_name=bank_name)
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
def create_pipeline(config_instance=None):
    """
    创建完整的处理管道
    参数：config_instance - 可选的配置实例，如果不传则使用默认tableconfig
    """

    # 1. OCR服务
    ocr_service = TableOCRService()

    # 2. LLM分析器 - 现在构造函数已经使用全局配置
    llm_analyzer = EnhancedFinancialTableAnalyzer()

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


def batch_example(image_paths, output_dir=None, bank_name=""):
    """
    批量处理示例
    """
    # 创建管道
    pipeline = create_pipeline()

    # 如果没有指定输出目录，使用配置中的目录
    if output_dir is None:
        output_dir = tableconfig.output_dir

    print(f"输出目录: {output_dir}")

    # 确保目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 批量处理
    result = pipeline.process_batch_images(image_paths, output_dir, bank_name=bank_name)

    return result


if __name__ == "__main__":
    """简洁测试入口 - 只关注核心逻辑"""



    # 1. 设置项目根路径
    SCRIPT_DIR = Path(__file__).parent
    PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
    print("PROJECT_ROOT::", PROJECT_ROOT)
    sys.path.insert(0, str(PROJECT_ROOT))

    # 2. 导入必需模块（一次导入）
    try:
        from backend.core.table_processor.end_to_end_pipeline import batch_example
        from backend.core.table_processor.cache_gateway import ensure_table
    except ImportError as e:
        print(f"导入失败: {e}")
        print(f"请在项目根目录运行: cd {PROJECT_ROOT.parent}")
        sys.exit(1)

    # 3. 初始化缓存（使用config.py中的配置）
    ensure_table()

    # 4. 设置测试图片路径
    # 优先使用配置，否则用默认
    test_images_dir = PROJECT_ROOT / "test_codes" / "png2"

    print("test_images_dir::", test_images_dir)

    if not test_images_dir.exists():
        print(f"测试图片目录不存在: {test_images_dir}")
        sys.exit(1)

    image_files = [
        str(test_images_dir / f)
        for f in os.listdir(test_images_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]

    if not image_files:
        print(f"没有找到图片文件: {test_images_dir}")
        sys.exit(1)

    print(f"找到 {len(image_files)} 张测试图片")

    # 5. 设置输出目录（优先使用配置）
    try:
        output_dir = Path(tableconfig.output_dir)
    except:
        # 回退到data/backend/outputs
        output_dir = PROJECT_ROOT / "data" / "backend" / "outputs"

    output_dir.mkdir(parents=True, exist_ok=True)

    # 6. 执行批处理
    print(f"输出目录: {output_dir}")
    print("开始处理...\n")
    bank_name = "中国建设银行"
    result = batch_example(image_files, str(output_dir), bank_name)

    # 7. 简单结果输出
    if result.get('success'):
        print(f"✅ 完成! 成功: {result['stats']['successful']} 失败: {result['stats']['failed']}")
    else:
        print(f"⚠️  处理完成但有失败")

