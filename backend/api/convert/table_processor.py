"""
表格处理模块 - 业务逻辑层
职责：封装表格处理业务逻辑，不包含API响应
"""
from flask import jsonify
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.utils.constants import DATABASE_PATH, FILTERED_TABLES_DIR, EXCEL_DATA_DIR
from backend.models.unified_db import NewDatabaseManager
from backend.src.services.table_processor.table_rebuilder import TableReconstructor
from backend.src.services.table_processor.ocr_gateway import TableOCRService
from backend.src.services.table_processor.llm_table_structure_parser import EnhancedFinancialTableAnalyzer


# ========== 1. 导入表格处理管道 ==========
try:
    from backend.src.services.table_processor.end_to_end_pipeline import batch_example
    from backend.configs.config import tableconfig
    PIPELINE_AVAILABLE = True
    print("✅ 表格处理管道导入成功")
except ImportError as e:
    print(f"⚠️ 表格处理管道导入失败: {e}")
    PIPELINE_AVAILABLE = False


# PDF数据聚合器
class PDFDataAggregator:
    """
    PDF数据聚合器 - 在内存中聚合所有表格数据
    用于最后一次性写入Excel，避免中间文件
    """

    def __init__(self, pdf_folder, bank_name=""):
        """
        初始化PDF数据聚合器

        Args:
            pdf_folder: PDF文件夹名称
            bank_name: 银行名称（用于最终文件名）
        """
        self.pdf_folder = pdf_folder
        self.bank_name = bank_name
        self.tables_data = []  # 存储所有表格的二维数组数据
        self.table_names = []  # 存储每个表格的Sheet名称
        self.image_refs = []  # 存储每个表格对应的图片信息
        self.lock = threading.RLock()  # 线程安全锁
        self.created_at = datetime.now()
        self.last_updated = self.created_at

    def add_table(self, image_name, table_data, sheet_name=None, image_path=None):
        """
        添加一个表格数据到聚合器

        Args:
            image_name: 图片文件名
            table_data: 表格数据（二维列表）
            sheet_name: 可选的Sheet名称
            image_path: 图片完整路径（可选）
        """
        with self.lock:
            if not table_data:
                print(f"⚠️ 空表格数据，跳过: {image_name}")
                return False

            # 验证表格数据
            if not isinstance(table_data, list) or len(table_data) == 0:
                print(f"⚠️ 无效表格数据格式: {image_name}")
                return False

            # 生成Sheet名称
            if not sheet_name:
                sheet_name = self._generate_sheet_name(image_name, len(self.tables_data))

            # 清理Sheet名称
            from backend.src.services.table_processor.table_rebuilder import TableReconstructor
            reconstructor = TableReconstructor()
            cleaned_sheet_name = reconstructor._clean_sheet_name(sheet_name)

            # 存储数据
            self.tables_data.append(table_data)
            self.table_names.append(cleaned_sheet_name)
            self.image_refs.append({
                'image_name': image_name,
                'image_path': image_path,
                'added_at': datetime.now().isoformat(),
                'table_shape': f"{len(table_data)}行×{len(table_data[0]) if table_data else 0}列"
            })

            self.last_updated = datetime.now()

            print(f"📊 聚合表格: {image_name} -> Sheet: '{cleaned_sheet_name}' "
                  f"({len(table_data)}行×{len(table_data[0]) if table_data else 0}列)")

            return True

    def _generate_sheet_name(self, image_name, table_index):
        """
        生成Sheet名称

        Args:
            image_name: 图片文件名
            table_index: 表格索引

        Returns:
            str: Sheet名称
        """
        from pathlib import Path

        # 移除扩展名
        stem = Path(image_name).stem

        # 尝试提取页码
        page_num = ""
        for i, char in enumerate(stem):
            if char.isdigit():
                # 找到连续数字作为页码
                j = i
                while j < len(stem) and stem[j].isdigit():
                    page_num += stem[j]
                    j += 1
                if len(page_num) >= 2:  # 至少2位数字才认为是页码
                    page_num = f"P{page_num.zfill(3)}"
                    break
                page_num = ""

        # 构建Sheet名称
        if page_num:
            return f"{page_num}_表{table_index + 1}"
        else:
            return f"表{table_index + 1}_{stem}"

    def get_statistics(self):
        """
        获取聚合器统计信息

        Returns:
            dict: 统计信息
        """
        with self.lock:
            total_tables = len(self.tables_data)
            total_rows = sum(len(table) for table in self.tables_data)
            total_cells = sum(len(table) * len(table[0]) if table and len(table[0]) > 0 else 0
                              for table in self.tables_data)

            return {
                'pdf_folder': self.pdf_folder,
                'bank_name': self.bank_name,
                'total_tables': total_tables,
                'total_rows': total_rows,
                'total_cells': total_cells,
                'table_names': self.table_names.copy(),
                'created_at': self.created_at.isoformat(),
                'last_updated': self.last_updated.isoformat(),
                'image_refs': self.image_refs.copy()
            }

    def save_to_excel(self, output_path):
        """
        将所有表格数据一次性写入Excel

        Args:
            output_path: 输出Excel文件路径

        Returns:
            bool: 是否成功
        """
        with self.lock:
            if not self.tables_data:
                print(f"⚠️ 聚合器中没有表格数据: {self.pdf_folder}")
                return False

            print(f"🔄 开始写入Excel: {self.pdf_folder}")
            print(f"  表格数量: {len(self.tables_data)}")
            print(f"  输出路径: {output_path}")

            try:
                # 导入并调用TableReconstructor的保存方法
                from backend.src.services.table_processor.table_rebuilder import TableReconstructor
                reconstructor = TableReconstructor()

                success = reconstructor.step9_save_to_excel_optimized(
                    tables_data=self.tables_data,
                    output_file=output_path,
                    table_names=self.table_names
                )

                if success:
                    print(f"✅ Excel写入成功: {output_path}")
                    stats = self.get_statistics()
                    print(f"📊 统计: {stats['total_tables']}个表格, "
                          f"{stats['total_rows']}行, {stats['total_cells']}个单元格")
                else:
                    print(f"❌ Excel写入失败: {output_path}")

                return success

            except Exception as e:
                print(f"❌ 保存Excel异常: {e}")
                import traceback
                traceback.print_exc()
                return False

    def clear(self):
        """清空聚合器数据（释放内存）"""
        with self.lock:
            table_count = len(self.tables_data)
            self.tables_data.clear()
            self.table_names.clear()
            self.image_refs.clear()
            print(f"🗑️ 清空聚合器: {self.pdf_folder}, 释放 {table_count} 个表格")

    def __len__(self):
        """获取表格数量"""
        with self.lock:
            return len(self.tables_data)

    def __str__(self):
        """字符串表示"""
        stats = self.get_statistics()
        return (f"PDFDataAggregator(pdf_folder={self.pdf_folder}, "
                f"tables={stats['total_tables']}, "
                f"rows={stats['total_rows']})")


# PDF聚合器管理器
class PDFAggregatorManager:
    """
    PDF聚合器管理器 - 全局管理所有PDF的数据聚合器
    单例模式，确保全局只有一个管理器实例
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._aggregators = {}  # pdf_folder -> PDFDataAggregator
                    self._aggregator_locks = {}  # 每个聚合器的独立锁
                    self._processing_status = {}  # PDF处理状态跟踪
                    self._initialized = True
                    print("✅ PDF聚合器管理器初始化完成")

    def get_aggregator(self, pdf_folder, bank_name=""):
        """
        获取或创建PDF数据聚合器

        Args:
            pdf_folder: PDF文件夹名称
            bank_name: 银行名称

        Returns:
            PDFDataAggregator: 数据聚合器实例
        """
        with self._lock:
            if pdf_folder not in self._aggregators:
                self._aggregators[pdf_folder] = PDFDataAggregator(pdf_folder, bank_name)

                # 初始化处理状态
                self._processing_status[pdf_folder] = {
                    'status': 'processing',  # processing, merging, completed, failed
                    'total_images': 0,
                    'processed_images': 0,
                    'failed_images': 0,
                    'start_time': datetime.now().isoformat(),
                    'last_update': datetime.now().isoformat(),
                    'expected_images': 0  # 可选：预期的总图片数
                }

                print(f"📁 创建PDF聚合器: {pdf_folder} (银行: {bank_name})")

            return self._aggregators[pdf_folder]

    def register_processing_job(self, pdf_folder, total_images, bank_name=""):
        """
        注册PDF处理任务

        Args:
            pdf_folder: PDF文件夹名称
            total_images: 总图片数
            bank_name: 银行名称
        """
        with self._lock:
            # 确保聚合器存在
            self.get_aggregator(pdf_folder, bank_name)

            # 更新状态
            self._processing_status[pdf_folder].update({
                'total_images': total_images,
                'expected_images': total_images,
                'status': 'processing',
                'start_time': datetime.now().isoformat(),
                'last_update': datetime.now().isoformat()
            })

            print(f"📝 注册PDF处理任务: {pdf_folder}, 总图片数: {total_images}")

    def update_processing_status(self, pdf_folder,
                                 processed_images=None,
                                 failed_images=None,
                                 status=None):
        """
        更新PDF处理状态

        Args:
            pdf_folder: PDF文件夹名称
            processed_images: 已处理的图片数（可选）
            failed_images: 失败的图片数（可选）
            status: 状态更新（可选）
        """
        with self._lock:
            if pdf_folder not in self._processing_status:
                return False

            if processed_images is not None:
                self._processing_status[pdf_folder]['processed_images'] = processed_images

            if failed_images is not None:
                self._processing_status[pdf_folder]['failed_images'] = failed_images

            if status is not None:
                self._processing_status[pdf_folder]['status'] = status

            self._processing_status[pdf_folder]['last_update'] = datetime.now().isoformat()
            return True

    def mark_image_completed(self, pdf_folder, image_name, table_count=1):
        """
        标记一张图片处理完成

        Args:
            pdf_folder: PDF文件夹名称
            image_name: 图片文件名
            table_count: 该图片包含的表格数量

        Returns:
            tuple: (是否所有图片都完成, 完成比例)
        """
        with self._lock:
            if pdf_folder not in self._processing_status:
                return False, 0

            status = self._processing_status[pdf_folder]
            status['processed_images'] = status.get('processed_images', 0) + 1

            # 记录完成的图片
            if 'completed_images' not in status:
                status['completed_images'] = []
            status['completed_images'].append({
                'name': image_name,
                'table_count': table_count,
                'completed_at': datetime.now().isoformat()
            })

            # 计算进度
            total_images = status.get('total_images', 0)
            processed = status['processed_images']

            if total_images > 0:
                progress = (processed / total_images) * 100
                print(f"📊 {pdf_folder}: 图片 {image_name} 完成 "
                      f"({processed}/{total_images}, {progress:.1f}%)")
            else:
                progress = 0

            # 检查是否所有图片都完成
            all_completed = (total_images > 0 and processed >= total_images)

            if all_completed:
                status['status'] = 'ready_to_merge'
                status['completion_time'] = datetime.now().isoformat()
                print(f"🎯 {pdf_folder}: 所有图片处理完成，准备合并")

            return all_completed, progress

    def get_processing_status(self, pdf_folder):
        """
        获取PDF处理状态

        Args:
            pdf_folder: PDF文件夹名称

        Returns:
            dict: 处理状态信息
        """
        with self._lock:
            if pdf_folder not in self._processing_status:
                return None

            status = self._processing_status[pdf_folder].copy()

            # 添加聚合器信息
            if pdf_folder in self._aggregators:
                aggregator = self._aggregators[pdf_folder]
                status['aggregator_stats'] = aggregator.get_statistics()
                status['tables_count'] = len(aggregator)

            return status

    def get_all_status(self):
        """
        获取所有PDF的处理状态

        Returns:
            dict: 所有PDF的状态
        """
        with self._lock:
            result = {}
            for pdf_folder in self._processing_status:
                result[pdf_folder] = self.get_processing_status(pdf_folder)
            return result

    def finalize_pdf(self, pdf_folder, output_dir=None, force=False):
        """
        最终化PDF处理，生成Excel文件

        Args:
            pdf_folder: PDF文件夹名称
            output_dir: 输出目录（可选，默认使用tableconfig.output_dir）
            force: 是否强制最终化（即使图片未全部完成）

        Returns:
            tuple: (是否成功, Excel文件路径, 错误信息)
        """
        with self._lock:
            if pdf_folder not in self._aggregators:
                return False, None, f"PDF聚合器不存在: {pdf_folder}"

            aggregator = self._aggregators[pdf_folder]
            status = self._processing_status.get(pdf_folder, {})

            # 检查是否可以合并
            if not force:
                total_images = status.get('total_images', 0)
                processed_images = status.get('processed_images', 0)

                if total_images > 0 and processed_images < total_images:
                    return False, None, f"图片未全部完成 ({processed_images}/{total_images})"

            # 生成输出路径
            try:
                if output_dir is None:
                    from backend.configs.config import tableconfig
                    output_dir = Path(tableconfig.output_dir) / pdf_folder
                else:
                    output_dir = Path(output_dir) / pdf_folder

                output_dir.mkdir(parents=True, exist_ok=True)

                # 生成文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if aggregator.bank_name:
                    filename = f"{aggregator.bank_name}_{pdf_folder}_{timestamp}.xlsx"
                else:
                    filename = f"{pdf_folder}_合并_{timestamp}.xlsx"

                output_path = output_dir / filename

                # 更新状态为合并中
                self.update_processing_status(pdf_folder, status='merging')

                print(f"🔄 开始最终化PDF: {pdf_folder}")
                print(f"  输出文件: {output_path}")
                print(f"  表格数量: {len(aggregator)}")

                # 保存Excel
                success = aggregator.save_to_excel(str(output_path))

                if success:
                    # 更新状态为完成
                    self.update_processing_status(pdf_folder, status='completed')
                    status['final_excel'] = str(output_path)
                    status['finalized_at'] = datetime.now().isoformat()

                    # 可选：清理聚合器数据（释放内存）
                    # aggregator.clear()

                    print(f"✅ PDF最终化完成: {pdf_folder} -> {output_path}")
                    return True, str(output_path), None
                else:
                    self.update_processing_status(pdf_folder, status='failed')
                    return False, None, "Excel保存失败"

            except Exception as e:
                import traceback
                error_msg = f"最终化失败: {str(e)}"
                print(f"❌ {error_msg}")
                traceback.print_exc()

                self.update_processing_status(pdf_folder, status='failed')
                return False, None, error_msg

    def cleanup(self, pdf_folder=None):
        """
        清理聚合器

        Args:
            pdf_folder: 要清理的PDF文件夹名称，如果为None则清理所有

        Returns:
            int: 清理的聚合器数量
        """
        with self._lock:
            if pdf_folder:
                # 清理单个PDF
                if pdf_folder in self._aggregators:
                    self._aggregators[pdf_folder].clear()
                    del self._aggregators[pdf_folder]

                if pdf_folder in self._processing_status:
                    del self._processing_status[pdf_folder]

                print(f"🧹 清理PDF聚合器: {pdf_folder}")
                return 1
            else:
                # 清理所有
                count = len(self._aggregators)
                for agg in self._aggregators.values():
                    agg.clear()

                self._aggregators.clear()
                self._processing_status.clear()

                print(f"🧹 清理所有PDF聚合器: {count} 个")
                return count

    def get_active_pdfs(self):
        """
        获取正在处理的PDF列表

        Returns:
            list: PDF文件夹名称列表
        """
        with self._lock:
            return list(self._processing_status.keys())

    def __contains__(self, pdf_folder):
        """检查PDF是否在管理中"""
        with self._lock:
            return pdf_folder in self._aggregators

    def __len__(self):
        """获取管理的PDF数量"""
        with self._lock:
            return len(self._aggregators)


# 创建全局管理器实例
pdf_aggregator_manager = PDFAggregatorManager()


class TableProcessingService:
    """表格处理服务类 - 纯业务逻辑"""

    def __init__(self):
        self.output_base_dir = self._get_output_dir()
        self._reconstructor = TableReconstructor()

    def _get_output_dir(self) -> Path:
        """获取输出目录"""
        try:
            output_dir = Path(tableconfig.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir
        except:
            # 回退到默认目录
            default_dir = Path("data/backend/outputs")
            default_dir.mkdir(parents=True, exist_ok=True)
            return default_dir

    def validate_images(self, pdf_folder: str, png_names: list, png_output_dir) -> tuple:
        """
        验证图片是否存在（只检查前几条数据）
        返回: (是否全部存在, 有效图片路径列表, 缺失图片名称列表)
        """
        missing_images = []
        valid_images = []

        # 只检查前5条数据（可以根据需要调整数量）
        check_count = min(5, len(png_names))
        check_names = png_names[:check_count]

        print(f"🔍 验证图片 - 文件夹: {pdf_folder}")
        print(f"📄 总图片数: {len(png_names)}, 只检查前 {check_count} 条")

        # 确保 png_output_dir 是 Path 对象
        if isinstance(png_output_dir, str):
            from pathlib import Path
            png_output_dir = Path(png_output_dir)
            print(f"✅ 路径对象: {png_output_dir}")

        # 检查PDF子目录
        pdf_folder_path = png_output_dir / pdf_folder
        print(f"📁 检查子目录: {pdf_folder_path}")

        if not pdf_folder_path.exists():
            print(f"❌ 子目录不存在")
            # 为了测试，我们假设只有目录不存在这一个问题
            # 实际上可能所有图片都不存在，但这里只检查前几条
            for png_name in check_names:
                missing_images.append(png_name)
            return False, [], check_names  # 只返回检查过的图片

        # 验证前几条图片
        for i, png_name in enumerate(check_names):
            print(f"  检查图片 {i + 1}/{check_count}: {png_name}")

            try:
                # 清理可能的路径前缀
                if '/' in png_name:
                    png_name = png_name.split('/')[-1]
                    print(f"    🔧 清理后: {png_name}")

                # 检查扩展名
                if not png_name.lower().endswith('.png'):
                    if '.' not in png_name:
                        png_name = f"{png_name}.png"
                        print(f"    🔧 添加扩展名: {png_name}")

                # 构建完整路径
                image_path = pdf_folder_path / png_name
                print(f"    📁 完整路径: {image_path}")

                # 检查文件是否存在
                if image_path.exists():
                    valid_images.append(str(image_path))
                    print(f"    ✅ 文件存在")
                else:
                    missing_images.append(png_name)
                    print(f"    ❌ 文件不存在")

                    # 列出目录中的实际文件（前3个）作为参考
                    if i == 0:  # 只在第一个文件缺失时列出参考
                        actual_files = list(pdf_folder_path.glob("*.png"))[:3]
                        if actual_files:
                            print(f"    🔍 目录中实际文件示例: {[f.name for f in actual_files]}")

            except Exception as e:
                print(f"    💥 检查出错: {e}")
                missing_images.append(png_name)

        print(f"📊 验证结果 (前{check_count}条):")
        print(f"  - 有效图片: {len(valid_images)} 张")
        print(f"  - 缺失图片: {len(missing_images)} 张")

        if missing_images:
            print(f"  - 缺失的图片: {missing_images}")

        # 如果前几条都不存在，说明整个列表可能都有问题
        if len(missing_images) == check_count:
            print(f"⚠️  前{check_count}条图片都不存在，可能整个列表都有问题")
            return False, [], png_names  # 返回所有缺失

        # 如果前几条存在，说明格式正确，返回成功（假设其他图片也存在）
        if len(valid_images) == check_count:
            print(f"✅ 前{check_count}条验证通过，格式正确")
            # 这里可以只返回前几条验证过的，或者扩展验证全部
            return True, valid_images, []

        # 部分存在的情况
        print(f"⚠️  部分图片存在，格式可能需要调整")
        return False, valid_images, missing_images


    def process_images(self, pdf_folder: str, valid_images: List[str],
                      bank_name: str = "") -> Dict[str, Any]:
        """
        处理图片表格 - 核心业务逻辑
        返回: 处理结果字典（不包含API响应）
        """
        print(f"📊 开始处理表格 - 文件夹: {pdf_folder}, 图片数: {len(valid_images)}")

        if not PIPELINE_AVAILABLE:
            return {
                "success": False,
                "error": "表格处理管道不可用",
                "total_images": len(valid_images)
            }

        try:
            # 创建输出目录
            output_dir = self.output_base_dir / pdf_folder
            output_dir.mkdir(parents=True, exist_ok=True)

            print(f"📁 输出目录: {output_dir}")

            # 调用批量处理函数
            result = batch_example(
                image_paths=valid_images,
                output_dir=str(output_dir),
                bank_name=bank_name
            )

            # 解析结果
            return self._parse_processing_result(result, valid_images)

        except Exception as e:
            print(f"❌ 表格处理失败: {e}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e),
                "total_images": len(valid_images)
            }

    def _parse_processing_result(self, raw_result: Dict[str, Any],
                               valid_images: List[str]) -> Dict[str, Any]:
        """解析处理结果"""
        if not raw_result.get('success', False):
            return {
                "success": False,
                "error": raw_result.get('error', '未知错误'),
                "total_images": len(valid_images)
            }

        # 提取成功的结果和Excel文件
        results = []
        excel_files = []
        success_count = 0

        for res in raw_result.get('results', []):
            if res.get('success'):
                success_count += 1
                results.append({
                    "image_path": Path(res.get('image_path', '')).name,
                    "success": True,
                    "output_file": res.get('output_file', ''),
                    "processing_time": res.get('processing_time', 0)
                })
                if res.get('output_file'):
                    excel_files.append(res['output_file'])

        # 统计信息
        stats = raw_result.get('stats', {})

        return {
            "success": True,
            "total_images": len(valid_images),
            "success_count": success_count,
            "failed_count": len(valid_images) - success_count,
            "processing_time": stats.get('processing_time', 0),
            "excel_files": excel_files,
            "raw_results": results,
            "raw_stats": stats
        }

    def get_excel_files(self, pdf_folder: str) -> List[Dict[str, Any]]:
        """获取指定文件夹的Excel文件列表"""
        output_dir = self.output_base_dir / pdf_folder
        excel_files = []

        if output_dir.exists():
            for excel_file in output_dir.glob("*.xlsx"):
                excel_files.append({
                    "filename": excel_file.name,
                    "path": str(excel_file),
                    "size": excel_file.stat().st_size,
                    "modified_time": datetime.fromtimestamp(
                        excel_file.stat().st_mtime
                    ).isoformat(),
                    "relative_download_path": f"{pdf_folder}/{excel_file.name}"
                })

        return excel_files

    def get_excel_file_path(self, pdf_folder: str, filename: str) -> Optional[Path]:
        """获取Excel文件路径"""
        file_path = self.output_base_dir / pdf_folder / filename

        # 安全检查
        try:
            file_path_resolved = file_path.resolve()
            base_dir_resolved = self.output_base_dir.resolve()

            # 确保文件在输出目录内（防止路径遍历攻击）
            if str(file_path_resolved).startswith(str(base_dir_resolved)):
                return file_path if file_path.exists() else None
        except:
            pass

        return None

    def _extract_tables_from_excel202(self, excel_file_path):
        """
        从Excel文件中提取表格数据

        Args:
            excel_file_path: Excel文件路径

        Returns:
            tuple: (tables_data, sheet_names)
                   tables_data: 表格数据列表
                   sheet_names: Sheet名称列表
        """
        try:
            import openpyxl
            from pathlib import Path

            if not Path(excel_file_path).exists():
                print(f"⚠️ Excel文件不存在: {excel_file_path}")
                return [], []

            wb = openpyxl.load_workbook(excel_file_path, data_only=True)

            tables_data = []
            sheet_names = []

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]

                # 获取最大行列
                max_row = ws.max_row
                max_col = ws.max_column

                if max_row == 0 or max_col == 0:
                    continue

                # 提取表格数据
                table_data = []
                for row in range(1, max_row + 1):
                    row_data = []
                    for col in range(1, max_col + 1):
                        cell = ws.cell(row=row, column=col)
                        row_data.append(cell.value)
                    table_data.append(row_data)

                if table_data:  # 只添加非空表格
                    tables_data.append(table_data)
                    sheet_names.append(sheet_name)

            wb.close()

            print(f"📖 从Excel提取: {Path(excel_file_path).name}, "
                  f"{len(tables_data)} 个表格, {sum(len(t) for t in tables_data)} 行")

            return tables_data, sheet_names

        except Exception as e:
            print(f"❌ Excel数据提取失败 {excel_file_path}: {e}")
            import traceback
            traceback.print_exc()
            return [], []

    # 在 table_processor.py 中找到数据提取部分，添加顺序标记
    def _extract_tables_from_excel(self, excel_file_path):
        """从Excel文件中提取表格数据 - 支持双表头（修正错位问题）"""
        try:
            import openpyxl
            from pathlib import Path

            if not Path(excel_file_path).exists():
                print(f"⚠️ Excel文件不存在: {excel_file_path}")
                return [], []

            wb = openpyxl.load_workbook(excel_file_path, data_only=True)
            tables_data = []
            sheet_names = []

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                max_row = ws.max_row
                max_col = ws.max_column

                # 1. 提取结构元数据（固定格式）
                metadata = {
                    "sheet_name": sheet_name,
                    "total_rows": max_row,
                    "total_cols": max_col,
                    "has_dual_headers": True,
                    "data_start_row": 2,  # 数据从第2行开始
                    "data_start_col": 2,  # 数据从第2列开始
                    "dimensions": {
                        "horizontal_count": max_col - 1,  # 横向表头数量
                        "vertical_count": max_row - 1  # 纵向表头数量
                    }
                }

                # 2. 提取表头数据（单独数组）
                headers = {
                    "top_left": ws.cell(row=1, column=1).value,  # 左上角
                    "horizontal": [],  # 横向表头 [H1, H2, H3...]
                    "vertical": []  # 纵向表头 [V1, V2, V3...]
                }

                # 提取横向表头（第一行，第2列开始）
                for col in range(2, max_col + 1):
                    headers["horizontal"].append(
                        ws.cell(row=1, column=col).value or f"列{col - 1}"
                    )

                # 提取纵向表头（第一列，第2行开始）
                for row in range(2, max_row + 1):
                    headers["vertical"].append(
                        ws.cell(row=row, column=1).value or f"行{row - 1}"
                    )

                # 3. 提取纯数据表格（二维数组，不含表头）
                data_matrix = []
                for data_row in range(2, max_row + 1):
                    row_data = []
                    for data_col in range(2, max_col + 1):
                        row_data.append(
                            ws.cell(row=data_row, column=data_col).value
                        )
                    data_matrix.append(row_data)

                # 4. 组装返回数据（三个独立部分）
                table_data = {
                    "metadata": metadata,
                    "headers": headers,
                    "data": data_matrix  # 纯数据，格式固定
                }

                tables_data.append(table_data)
                sheet_names.append(sheet_name)

            return tables_data, sheet_names

        except Exception as e:
            print(f"❌ Excel数据提取失败 {excel_file_path}: {e}")
            import traceback
            traceback.print_exc()
            return [], []


    def _run_ocr_llm_memory_pipeline(self, image_path: str, bank_name: str = ""):
        """
        纯算法流水线：OCR → LLM → 内存表格数据
        返回 (tables_data, sheet_names)
        """
        from backend.src.services.table_processor.ocr_gateway import TableOCRService
        from backend.src.services.table_processor.llm_table_structure_parser import EnhancedFinancialTableAnalyzer

        ocr_result = TableOCRService().recognize_table(image_path)
        if not ocr_result.get('tables_result'):
            return [], []

        llm_result = EnhancedFinancialTableAnalyzer().analyze_image(image_path, ocr_result)
        if not llm_result.get('tables_structure', {}).get('tables'):
            return [], []

        return self._reconstructor.process_all_tables_to_memory(
            ocr_result=ocr_result,
            llm_result=llm_result,
            image_path=image_path,
            bank_name=bank_name
        )

    def _process_single_image_to_memory(self, image_path, pdf_folder, bank_name=""):
        """代理到统一流水线，保持对外签名不变"""
        return self._run_ocr_llm_memory_pipeline(image_path, bank_name)[0]  # 只要数据，不要 sheet_names

    def extract_tables_with_names(self, image_path: str, bank_name: str = ""):
        """外部可调用：返回 (tables_data, sheet_names)"""
        return self._run_ocr_llm_memory_pipeline(image_path, bank_name)


# ========== 2. 异步处理包装器 ==========
def create_table_processing_task(pdf_folder: str, valid_images: List[str],
                               bank_name: str = "") -> Dict[str, Any]:
    """
    创建表格处理任务（供异步调用）
    返回任务信息，不启动线程
    """
    job_id = str(uuid.uuid4())

    return {
        "job_id": job_id,
        "pdf_folder": pdf_folder,
        "valid_images": valid_images,
        "bank_name": bank_name,
        "total_images": len(valid_images),
        "created_at": datetime.now().isoformat()
    }


def execute_table_processing(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行表格处理（供线程调用）
    返回处理结果
    """
    service = TableProcessingService()

    result = service.process_images(
        pdf_folder=task_info["pdf_folder"],
        valid_images=task_info["valid_images"],
        bank_name=task_info.get("bank_name", "")
    )

    # 合并任务信息和处理结果
    final_result = {
        **task_info,
        **result,
        "completed_at": datetime.now().isoformat()
    }

    return final_result


# ========== 3. 创建全局服务实例 ==========
table_processing_service = TableProcessingService()


# ========== 4. API 接口函数 ==========
def submit_table_processing_task(pdf_folder, filtered_tables_dir, request, progress_tracker):
    """提交表格处理任务"""
    try:
        print(f"📥 提交表格处理任务: pdf_folder={pdf_folder}")

        # 获取请求数据
        data = request.get_json() or {}
        table_type = data.get('table_type', 'financial')
        use_ocr = data.get('use_ocr', True)
        bank_name = data.get('bank_name', '')

        # 可选的png_names参数，如果未提供则从目录获取
        png_names = data.get('png_names', [])

        print(f"  配置参数: table_type={table_type}, use_ocr={use_ocr}, bank_name={bank_name}")
        print(f"  可选png_names: {len(png_names)}个")

        # 如果未提供png_names，自动从筛选目录获取
        tables_dir = Path(filtered_tables_dir) / pdf_folder / "tables"
        if not png_names:
            if tables_dir.exists():
                png_names = [f.name for f in tables_dir.glob("*.png")]
                print(f"  自动从目录获取 {len(png_names)} 张表格图片")
            else:
                return jsonify({
                    "success": False,
                    "error": f"表格目录不存在: {tables_dir}",
                    "suggestion": "请先完成图片筛选"
                }), 400

        if not png_names:
            return jsonify({
                "success": False,
                "error": "没有找到表格图片",
                "suggestion": "筛选后没有发现包含表格的图片"
            }), 400

        # 生成作业ID
        job_id = f"table_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        # 构建完整的图片路径列表
        image_paths = []
        for png_name in png_names:
            img_path = tables_dir / png_name
            if img_path.exists():
                image_paths.append(str(img_path))
            else:
                print(f"⚠️ 图片不存在: {img_path}")

        if not image_paths:
            return jsonify({
                "success": False,
                "error": "没有找到有效的图片文件",
                "suggestion": "请检查筛选后的图片文件是否存在"
            }), 400

        print(f"📸 找到 {len(image_paths)} 张有效图片")

        # 创建进度记录
        progress_tracker.init_table_job(
            job_id=job_id,
            job_info={
                "pdf_folder": pdf_folder,
                "table_type": table_type,
                "bank_name": bank_name,
                "total_images": len(image_paths),
                "image_paths": image_paths,
                "status": "pending",
                "stage": "pending",
                "progress": 0,
                "start_time": datetime.now().isoformat(),
                "processed_images": 0,
                "results": [],
                "error": None
            }
        )

        print(f"✅ 创建作业成功: job_id={job_id}")

        def async_process_table():
            """异步处理表格的线程函数"""
            try:
                print(f"🚀 开始异步处理表格任务: {job_id}")

                # 更新状态为处理中
                progress_tracker.update_table_job(job_id, {
                    "status": "processing",
                    "stage": "starting",
                    "progress": 5,
                    "message": "开始处理表格图片..."
                })

                # 执行真实的表格处理
                process_table_images_real(job_id, pdf_folder, image_paths, table_type, bank_name, progress_tracker)

                print(f"🎉 表格处理任务完成: {job_id}")

            except Exception as e:
                print(f"❌ 异步处理异常: {e}")
                import traceback
                traceback.print_exc()

                progress_tracker.update_table_job(job_id, {
                    "status": "failed",
                    "stage": "failed",
                    "progress": 0,
                    "error": str(e),
                    "end_time": datetime.now().isoformat(),
                    "message": f"处理失败: {str(e)}"
                })

        # 启动异步线程
        thread = threading.Thread(target=async_process_table, daemon=True)
        thread.start()

        print(f"🎯 异步处理线程已启动")

        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": "表格解析任务已提交",
            "pdf_folder": pdf_folder,
            "table_type": table_type,
            "bank_name": bank_name,
            "total_images": len(image_paths),
            "auto_detected_images": data.get('png_names') is None
        })

    except Exception as e:
        print(f"💥 提交表格处理任务失败: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": f"提交任务失败: {str(e)}"
        }), 500


def process_table_images_real(job_id, pdf_folder, image_paths, table_type, bank_name, progress_tracker):
    """真实的表格处理函数 - 使用聚合系统"""
    try:
        table_service = TableProcessingService()
        image_paths = image_paths[:4]

        total_images = len(image_paths)
        print(f"🔧 开始真实表格处理: {pdf_folder} - {total_images} 张图片")

        # ========== 第1步：注册PDF处理任务 ==========
        pdf_aggregator_manager.register_processing_job(pdf_folder, total_images, bank_name)

        # 更新进度：注册完成
        progress_tracker.update_table_job(job_id, {
            "stage": "registered",
            "progress": 5,
            "total_images": total_images,
            "message": f"已注册PDF处理任务: {total_images} 张图片"
        })

        # ========== 第2步：获取PDF聚合器 ==========
        aggregator = pdf_aggregator_manager.get_aggregator(pdf_folder, bank_name)

        results = []
        success_count = 0
        failed_count = 0
        total_tables_extracted = 0

        # ========== 第3步：选择处理器 ==========
        use_batch_processor = (total_images > 20)

        if use_batch_processor:
            print(f"📊 使用批量处理器处理 {total_images} 张图片")

            # 更新进度
            progress_tracker.update_table_job(job_id, {
                "stage": "batch_processing",
                "progress": 10,
                "message": f"使用批量处理器处理 {total_images} 张图片"
            })

            # 调用批量处理
            from backend.configs.config import tableconfig
            output_dir = Path(tableconfig.output_dir) / pdf_folder
            output_dir.mkdir(parents=True, exist_ok=True)

            result = batch_example(
                image_paths=image_paths,
                output_dir=str(output_dir),
                bank_name=bank_name
            )

            if result.get('success'):
                # 解析批量处理结果
                for res in result.get('results', []):
                    image_name = Path(res.get('image_path', '')).name

                    if res.get('success'):
                        # 对于批量处理，我们需要重构逻辑来获取表格数据
                        # 这里假设批量处理返回了Excel文件路径
                        excel_file = res.get('output_file')

                        if excel_file and Path(excel_file).exists():
                            try:
                                # 从Excel读取表格数据并添加到聚合器
                                tables_data, sheet_names = table_service._extract_tables_from_excel(excel_file)

                                for table_idx, (table_data, sheet_name) in enumerate(zip(tables_data, sheet_names)):
                                    success = aggregator.add_table(
                                        image_name=image_name,
                                        table_data=table_data,
                                        sheet_name=f"{image_name}_表{table_idx + 1}",
                                        image_path=res.get('image_path')
                                    )

                                    if success:
                                        total_tables_extracted += 1

                                success_count += 1
                                results.append({
                                    "image_path": image_name,
                                    "success": True,
                                    "tables_extracted": len(tables_data),
                                    "processing_time": res.get('processing_time', 0)
                                })

                                # 标记图片完成
                                all_completed, progress = pdf_aggregator_manager.mark_image_completed(
                                    pdf_folder, image_name, len(tables_data)
                                )

                            except Exception as e:
                                print(f"❌ 批量处理结果提取失败 {image_name}: {e}")
                                failed_count += 1
                                results.append({
                                    "image_path": image_name,
                                    "success": False,
                                    "error": f"数据提取失败: {str(e)}"
                                })
                        else:
                            failed_count += 1
                            results.append({
                                "image_path": image_name,
                                "success": False,
                                "error": "Excel文件未生成"
                            })
                    else:
                        failed_count += 1
                        results.append({
                            "image_path": image_name,
                            "success": False,
                            "error": res.get('error', '批量处理失败')
                        })

                        # 标记为失败但完成
                        pdf_aggregator_manager.mark_image_completed(pdf_folder, image_name, 0)
            else:
                raise Exception(f"批量处理失败: {result.get('error')}")

        else:
            print(f"📊 使用标准处理器逐张处理 {total_images} 张图片")

            # 逐张处理
            for i, image_path in enumerate(image_paths):
                image_name = Path(image_path).name

                # 更新进度
                progress = 10 + (i / total_images * 70)  # 留出空间给最后合并
                current_stage = "ocr" if i < total_images * 0.3 else "llm" if i < total_images * 0.6 else "reconstruction"

                progress_tracker.update_table_job(job_id, {
                    "stage": current_stage,
                    "progress": int(progress),
                    "processed_images": i,
                    "current_image": image_name,
                    "message": f"正在处理第 {i + 1}/{total_images} 张图片 ({current_stage})"
                })

                print(f"🖼️ 处理图片 {i + 1}/{total_images}: {image_name}")

                try:
                    # ========== 核心修改：直接处理到内存，不生成Excel ==========
                    tables_data, sheet_names = table_service._run_ocr_llm_memory_pipeline(
                        image_path=image_path,
                        bank_name=bank_name
                    )

                    if tables_data:
                        # 将表格数据添加到聚合器
                        for table_data, sheet_name in zip(tables_data, sheet_names):
                            success = aggregator.add_table(
                                image_name=image_name,
                                table_data=table_data,
                                sheet_name=sheet_name,  # ← 用内存版返回的真实名字
                                image_path=image_path
                            )

                            if success:
                                total_tables_extracted += 1

                        success_count += 1
                        results.append({
                            "image_path": image_name,
                            "success": True,
                            "tables_extracted": len(tables_data),
                            "processing_time": 0  # 实际处理时间需要从处理函数获取
                        })

                        print(f"✅ 图片处理成功: {image_name}, 提取 {len(tables_data)} 个表格")
                    else:
                        failed_count += 1
                        results.append({
                            "image_path": image_name,
                            "success": False,
                            "error": "未提取到表格数据"
                        })
                        print(f"⚠️ 图片处理未提取到表格: {image_name}")

                    # 标记图片完成
                    all_completed, progress = pdf_aggregator_manager.mark_image_completed(
                        pdf_folder, image_name, len(sheet_names) if tables_data else 0
                    )

                    # if all_completed:
                    #     # 立即触发最终合并，不用再等前端轮询
                    #     pdf_aggregator_manager.finalize_pdf(pdf_folder, EXCEL_DATA_DIR)

                    # 更新总进度
                    progress_tracker.update_table_job(job_id, {
                        "progress": int(10 + ((i + 1) / total_images * 70)),
                        "processed_images": i + 1,
                        "success_count": success_count
                    })

                except Exception as img_error:
                    print(f"❌ 图片处理失败 {image_name}: {img_error}")
                    import traceback
                    traceback.print_exc()

                    failed_count += 1
                    results.append({
                        "image_path": image_name,
                        "success": False,
                        "error": str(img_error)
                    })

                    # 标记为失败但完成
                    pdf_aggregator_manager.mark_image_completed(pdf_folder, image_name, 0)

        # ========== 第4步：所有图片处理完成，开始最终合并 ==========
        print(f"🔄 所有图片处理完成，开始最终合并: {pdf_folder}")

        # 更新进度：开始合并
        progress_tracker.update_table_job(job_id, {
            "stage": "merging",
            "progress": 85,
            "message": f"正在合并 {len(aggregator)} 个表格..."
        })

        print(f"🔍 调用 finalize_pdf 前，聚合器状态: {len(aggregator)} 个表格")

        try:
            # 最终化PDF，生成Excel
            success, excel_path, error_msg = pdf_aggregator_manager.finalize_pdf(pdf_folder, EXCEL_DATA_DIR)

            print(f"🔍 finalize_pdf 返回结果:")
            print(f"  success: {success}")
            print(f"  excel_path: {excel_path}")
            print(f"  error_msg: {error_msg}")

            excel_files = [excel_path] if success and excel_path else []

            print(f"🔍 Excel文件列表: {excel_files}")

            # ========== 第5步：处理完成 ==========
            print(f"🔄 开始更新进度到100%...")

            progress_tracker.update_table_job(job_id, {
                "status": "completed" if success else "failed",
                "stage": "completed",
                "progress": 100,
                "processed_images": total_images,
                "success_count": success_count,
                "failed_count": failed_count,
                "total_tables_extracted": total_tables_extracted,
                "final_excel": excel_path if success else None,
                "aggregator_stats": aggregator.get_statistics(),
                "results": results,
                "excel_files": excel_files,
                "end_time": datetime.now().isoformat(),
                "message": f"表格处理完成: 成功 {success_count}/{total_images} 张, 提取 {total_tables_extracted} 个表格",
                "summary": {
                    "total_images": total_images,
                    "successful_images": success_count,
                    "failed_images": failed_count,
                    "tables_extracted": total_tables_extracted,
                    "final_excel_generated": success,
                    "final_excel_path": excel_path if success else None,
                    "success_rate": f"{(success_count / total_images * 100):.1f}%" if total_images > 0 else "0%"
                }
            })

            print(f"✅ 进度已更新到100%")

            # 可选：清理聚合器数据（释放内存）
            if success:
                aggregator.clear()
                print(f"🧹 清理聚合器数据: {pdf_folder}")

            print(f"✅ PDF表格处理完成: {pdf_folder}")
            print(f"📊 统计: 图片 {success_count}/{total_images} 成功, "
                  f"表格 {total_tables_extracted} 个, "
                  f"最终Excel: {excel_path if success else '无'}")

        except Exception as e:
            print(f"❌ 最终合并阶段发生异常: {e}")
            import traceback
            traceback.print_exc()

            # 即使异常，也要更新进度到100%并标记为失败
            progress_tracker.update_table_job(job_id, {
                "status": "failed",
                "stage": "failed",
                "progress": 100,
                "error": str(e),
                "end_time": datetime.now().isoformat(),
                "message": f"最终合并失败: {str(e)}"
            })

            print(f"⚠️ 已将失败状态更新到进度管理器")


    except Exception as e:
        print(f"❌ 表格处理失败: {e}")
        import traceback
        traceback.print_exc()

        # 更新失败状态
        progress_tracker.update_table_job(job_id, {
            "status": "failed",
            "stage": "failed",
            "error": str(e),
            "end_time": datetime.now().isoformat(),
            "message": f"处理失败: {str(e)}"
        })


# 保留get_table_results函数
def get_table_results(pdf_folder, progress_tracker):
    """API: 查询表格处理结果"""
    from flask import jsonify

    try:
        # 1. 获取内存中的任务
        folder_tasks = progress_tracker.get_folder_tasks(pdf_folder)

        # 2. 获取Excel文件
        service = TableProcessingService()
        excel_files = service.get_excel_files(pdf_folder)

        # 3. 返回结果
        return jsonify({
            "success": True,
            "pdf_folder": pdf_folder,
            "data": {
                "tasks": folder_tasks,
                "excel_files": excel_files,
                "task_count": len(folder_tasks),
                "excel_count": len(excel_files)
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"查询失败: {str(e)}"
        }), 500


def download_excel_file(pdf_folder, filename):
    """API: 下载Excel文件"""
    from flask import send_from_directory, jsonify

    try:
        service = TableProcessingService()
        file_path = service.get_excel_file_path(pdf_folder, filename)

        if not file_path or not file_path.exists():
            return jsonify({
                "success": False,
                "error": "文件不存在"
            }), 404

        return send_from_directory(
            directory=str(file_path.parent),
            path=filename,
            as_attachment=True,
            download_name=f"表格处理结果_{pdf_folder}_{filename}"
        )

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"下载失败: {str(e)}"
        }), 500




def get_available_steps():
    """API: 获取可用步骤"""
    from flask import jsonify
    try:
        from backend.service.layout_service import processing_pipeline
        steps = processing_pipeline.get_available_steps()
        return jsonify({
            "success": True,
            "data": {
                "steps": steps,
                "count": len(steps)
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


import concurrent.futures
from threading import Semaphore
from typing import List, Dict, Any


class HighVolumeTableProcessor:
    """高容量表格处理器 - 处理上百张图片"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            'max_ocr_workers': 4,  # OCR线程数（I/O密集型）
            'max_llm_workers': 2,  # LLM线程数（GPU限制）
            'max_reconstruct_workers': 3,  # 重构线程数
            'batch_size': 10,  # 批次大小，控制内存
            'queue_size': 50  # 队列缓冲
        }

        # 资源限制信号量
        self.gpu_semaphore = Semaphore(self.config['max_llm_workers'])

    def process_hundred_images(self, image_paths: List[str], bank_name: str = "") -> Dict[str, Any]:
        """
        处理上百张图片的优化方案
        """
        total_images = len(image_paths)
        print(f"🚀 开始处理 {total_images} 张图片")

        # 1. 分批处理，避免内存爆炸
        batches = self._create_batches(image_paths, self.config['batch_size'])

        all_results = []

        with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.config['max_ocr_workers'] +
                            self.config['max_llm_workers'] +
                            self.config['max_reconstruct_workers']
        ) as executor:

            # 提交批次任务
            future_to_batch = {}
            for batch_idx, batch_images in enumerate(batches):
                future = executor.submit(
                    self._process_batch_pipeline,
                    batch_images, batch_idx, bank_name
                )
                future_to_batch[future] = batch_idx

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                    print(f"✅ 批次 {batch_idx + 1}/{len(batches)} 处理完成")
                except Exception as e:
                    print(f"❌ 批次 {batch_idx} 处理失败: {e}")

        # 汇总统计
        return self._aggregate_results(all_results, total_images)

    def _create_batches(self, image_paths: List[str], batch_size: int) -> List[List[str]]:
        """创建批次"""
        return [image_paths[i:i + batch_size]
                for i in range(0, len(image_paths), batch_size)]

    def _process_batch_pipeline(self, batch_images: List[str],
                                batch_idx: int, bank_name: str) -> List[Dict[str, Any]]:
        """
        批次内的流水线处理
        """
        batch_results = []

        # 阶段1: OCR识别（并行）
        ocr_results = []
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(self.config['max_ocr_workers'], len(batch_images))
        ) as ocr_executor:
            ocr_futures = {
                ocr_executor.submit(self._ocr_recognize, img_path): img_path
                for img_path in batch_images
            }

            for future in concurrent.futures.as_completed(ocr_futures):
                img_path = ocr_futures[future]
                try:
                    ocr_result = future.result()
                    ocr_results.append((img_path, ocr_result))
                except Exception as e:
                    print(f"❌ OCR失败 {img_path}: {e}")
                    ocr_results.append((img_path, {'success': False, 'error': str(e)}))

        # 阶段2: LLM分析（受GPU限制）
        llm_results = []
        for img_path, ocr_result in ocr_results:
            if ocr_result.get('success'):
                # 使用信号量限制并发
                with self.gpu_semaphore:
                    llm_result = self._llm_analyze(img_path, ocr_result)
                    llm_results.append((img_path, ocr_result, llm_result))
            else:
                llm_results.append((img_path, ocr_result, {'success': False, 'error': 'OCR失败'}))

        # 阶段3: 表格重构（并行）
        for img_path, ocr_result, llm_result in llm_results:
            if llm_result.get('success'):
                try:
                    reconstruct_result = self._table_reconstruct(
                        ocr_result, llm_result, img_path, bank_name
                    )
                    batch_results.append({
                        'image_path': img_path,
                        'success': reconstruct_result.get('success', False),
                        'output_file': reconstruct_result.get('output_file'),
                        'processing_time': reconstruct_result.get('processing_time', 0)
                    })
                except Exception as e:
                    batch_results.append({
                        'image_path': img_path,
                        'success': False,
                        'error': str(e)
                    })
            else:
                batch_results.append({
                    'image_path': img_path,
                    'success': False,
                    'error': llm_result.get('error', 'LLM分析失败')
                })

        return batch_results

    def _ocr_recognize(self, image_path: str) -> Dict[str, Any]:
        """OCR识别"""
        ocr_service = TableOCRService()
        return ocr_service.recognize_table(image_path)

    def _llm_analyze(self, image_path: str, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """LLM分析（GPU密集型）"""
        analyzer = EnhancedFinancialTableAnalyzer()
        return analyzer.analyze_image(image_path, ocr_result)

    def _table_reconstruct(self, ocr_result: Dict[str, Any],
                           llm_result: Dict[str, Any],
                           image_path: str, bank_name: str) -> Dict[str, Any]:
        """表格重构"""
        reconstructor = TableReconstructor()

        # 生成输出文件路径
        from pathlib import Path
        image_name = Path(image_path).stem
        output_dir = Path("data/backend/outputs/large_batch")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = str(output_dir / f"{image_name}_reconstructed.xlsx")

        success = reconstructor.process_all_tables(
            ocr_result=ocr_result,
            llm_result=llm_result,
            output_file=output_file,
            image_path=image_path,
            bank_name=bank_name
        )

        return {
            'success': success,
            'output_file': output_file if success else None
        }

    def _aggregate_results(self, all_results: List[Dict], total_images: int) -> Dict[str, Any]:
        """汇总结果"""
        successful = sum(1 for r in all_results if r.get('success'))
        failed = total_images - successful

        return {
            'success': failed == 0,
            'total_images': total_images,
            'successful': successful,
            'failed': failed,
            'results': all_results,
            'summary': {
                'success_rate': f"{(successful / total_images * 100):.1f}%",
                'failed_images': [
                    r['image_path'] for r in all_results
                    if not r.get('success')
                ]
            }
        }


def process_large_batch(pdf_folder: str, image_paths: List[str],
                        bank_name: str = "") -> Dict[str, Any]:
    """
    处理大批量图片的接口
    """
    processor = HighVolumeTableProcessor({
        'max_ocr_workers': 6,
        'max_llm_workers': 2,  # 根据GPU显存调整
        'max_reconstruct_workers': 4,
        'batch_size': 15,
        'queue_size': 30
    })

    return processor.process_hundred_images(image_paths, bank_name)

def _ensure_table_processing_db():
    """确保表格处理数据库表存在"""
    global _table_processing_db_initialized

    if _table_processing_db_initialized:
        return True

    try:

        db_handler = NewDatabaseManager(DATABASE_PATH)
        db_handler.init_table_processing_db()
        _table_processing_db_initialized = True
        return True
    except Exception as e:
        print(f"⚠️ 数据库表初始化失败，但继续处理: {e}")
        return False


# def update_job_progress(job_id, updates):
def update_job_progress(job_id, updates, progress_tracker):
    """更新任务进度"""
    if job_id in progress_tracker.TABLE_PROCESSING_JOBS:
        progress_tracker.TABLE_PROCESSING_JOBS[job_id].update(updates)

        # 保存到数据库
        try:
            from backend.utils.constants import DATABASE_PATH
            db_handler = NewDatabaseManager(DATABASE_PATH)
            job_info = progress_tracker.TABLE_PROCESSING_JOBS[job_id].copy()
            job_info['job_id'] = job_id
            db_handler.save_table_processing_record(job_info)
        except Exception as e:
            print(f"⚠️ 保存进度到数据库失败: {e}")

_table_processing_db_initialized = False

def process_tables_async(job_id, pdf_folder, valid_images, bank_name):
    """
    异步处理表格的完整实现
    """
    print(f"🚀 开始异步处理表格 - Job ID: {job_id}")
    print(f"📊 图片数量: {len(valid_images)} 张")

    try:
        # 确保数据库表存在
        _ensure_table_processing_db()

        # 更新进度为开始
        update_job_progress(job_id, {
            "status": "processing",
            "stage": "starting",
            "progress": 5,
            "total_images": len(valid_images)
        })

        # ========== 智能选择处理器 ==========
        results = []
        excel_files = []

        if len(valid_images) > 20:
            print("🔧 使用高容量处理器（批量>20）")

            # 创建高容量处理器
            processor = HighVolumeTableProcessor({
                'max_ocr_workers': min(8, len(valid_images) // 3),
                'max_llm_workers': 2,
                'max_reconstruct_workers': 4,
                'batch_size': 15
            })

            # 定义进度回调
            def progress_callback(processed, total, stage):
                progress = 10 + (processed / total * 80)  # 10%-90%
                update_job_progress(job_id, {
                    "stage": stage,
                    "progress": int(progress),
                    "processed_images": processed,
                    "current_stage": stage,
                    "current_image": f"批次处理中 ({processed}/{total})"
                })
                print(f"📊 处理进度: {stage} - {processed}/{total} ({int(progress)}%)")

            # 执行处理
            batch_result = processor.process_hundred_images(
                valid_images, bank_name, progress_callback
            )

            # 解析结果
            if batch_result.get('success'):
                for res in batch_result.get('results', []):
                    if res.get('success'):
                        results.append({
                            "image_path": Path(res.get('image_path', '')).name,
                            "success": True,
                            "output_file": res.get('output_file', ''),
                            "processing_time": res.get('processing_time', 0)
                        })
                        if res.get('output_file'):
                            excel_files.append(res['output_file'])
                    else:
                        results.append({
                            "image_path": Path(res.get('image_path', '')).name,
                            "success": False,
                            "error": res.get('error', '处理失败')
                        })

        else:
            print("🔧 使用标准处理器（批量≤20）")

            # 创建标准处理器
            service = TableProcessingService()

            # 逐张处理（可改为小批量并行）
            for i, image_path in enumerate(valid_images):
                image_name = Path(image_path).name

                # 更新进度
                progress = 10 + (i / len(valid_images) * 80)
                update_job_progress(job_id, {
                    "stage": "processing",
                    "progress": int(progress),
                    "processed_images": i,
                    "current_image": image_name,
                    "current_stage": "processing"
                })

                try:
                    # 处理单张图片
                    print(f"🖼️ 处理图片 {i + 1}/{len(valid_images)}: {image_name}")

                    # 这里应该是处理单张的逻辑
                    # 暂时调用批量处理，传入单张图片
                    result = service.process_images(
                        pdf_folder, [image_path], bank_name
                    )

                    if result.get('success'):
                        # 解析单张结果
                        for res in result.get('raw_results', []):
                            if res.get('success'):
                                results.append({
                                    "image_path": image_name,
                                    "success": True,
                                    "output_file": res.get('output_file', ''),
                                    "processing_time": res.get('processing_time', 0)
                                })
                                if res.get('output_file'):
                                    excel_files.append(res['output_file'])
                    else:
                        results.append({
                            "image_path": image_name,
                            "success": False,
                            "error": result.get('error', '处理失败')
                        })

                except Exception as img_error:
                    print(f"❌ 图片处理失败 {image_name}: {img_error}")
                    results.append({
                        "image_path": image_name,
                        "success": False,
                        "error": str(img_error)
                    })

        # ========== 处理完成 ==========
        success_count = sum(1 for r in results if r.get('success'))

        update_job_progress(job_id, {
            "status": "completed",
            "stage": "completed",
            "progress": 100,
            "processed_images": len(valid_images),
            "success_count": success_count,
            "failed_count": len(valid_images) - success_count,
            "results": results,
            "excel_files": excel_files,
            "end_time": datetime.now().isoformat(),
            "summary": {
                "total_images": len(valid_images),
                "successful": success_count,
                "failed": len(valid_images) - success_count,
                "excel_files_count": len(excel_files)
            }
        })

        print(f"✅ 表格处理任务完成 - Job ID: {job_id}")
        print(f"📊 成功: {success_count}, 失败: {len(valid_images) - success_count}")

    except Exception as e:
        print(f"❌ 表格处理任务失败 - Job ID: {job_id}, 错误: {e}")
        import traceback
        traceback.print_exc()

        update_job_progress(job_id, {
            "status": "failed",
            "stage": "failed",
            "error": str(e),
            "end_time": datetime.now().isoformat()
        })



def execute_single_step_handler(step_name, output_dir, request):
    """分步执行表格处理 - 真正的分步实现"""

    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        pdf_folder = data.get('pdf_folder')
        png_names = data.get('png_names', [])
        previous_context = data.get('previous_context', {})

        if not pdf_folder or not png_names:
            return jsonify({
                "success": False,
                "error": "参数错误：需提供pdf_folder和png_names"
            }), 400

        # 根据步骤名称执行不同的逻辑
        if step_name == "ocr":
            result = execute_ocr_step(pdf_folder, png_names, output_dir)
        elif step_name == "llm":
            result = execute_llm_step(pdf_folder, png_names, previous_context, output_dir)
        elif step_name == "reconstruct":
            result = execute_reconstruct_step(pdf_folder, png_names, previous_context, output_dir)
        elif step_name == "export":
            result = execute_export_step(pdf_folder, png_names, previous_context, output_dir)
        else:
            return jsonify({
                "success": False,
                "error": f"不支持的步骤: {step_name}"
            }), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"分步执行失败: {str(e)}"
        }), 500


def execute_ocr_step(pdf_folder, png_names, output_dir):
    """执行OCR步骤"""
    try:
        results = {}
        ocr_service = TableOCRService()

        for png_name in png_names:
            # 构建图片路径
            from backend.utils.constants import JOINED_TABLES_DIR
            image_path = JOINED_TABLES_DIR / pdf_folder / png_name

            if not image_path.exists():
                results[png_name] = {"success": False, "error": "图片不存在"}
                continue

            # 执行OCR
            ocr_result = ocr_service.recognize_table(str(image_path))
            results[png_name] = {
                "success": True,
                "result": ocr_result,
                "tables_count": len(ocr_result.get('tables_result', []))
            }

        return {
            "success": True,
            "step": "ocr",
            "results": results,
            "message": f"OCR识别完成，处理{len(png_names)}张图片"
        }

    except Exception as e:
        return {
            "success": False,
            "step": "ocr",
            "error": str(e)
        }


def execute_llm_step(pdf_folder, png_names, previous_context, output_dir):
    """执行LLM分析步骤"""
    try:

        # 检查是否有OCR结果
        ocr_results = previous_context.get('ocr_results', {})
        if not ocr_results:
            return {
                "success": False,
                "step": "llm",
                "error": "需要先执行OCR步骤"
            }

        results = {}
        analyzer = EnhancedFinancialTableAnalyzer()

        for png_name in png_names:
            # 获取OCR结果
            ocr_result = ocr_results.get(png_name, {}).get('result')
            if not ocr_result:
                results[png_name] = {"success": False, "error": "没有OCR结果"}
                continue

            # 构建图片路径
            from backend.utils.constants import JOINED_TABLES_DIR
            image_path = JOINED_TABLES_DIR / pdf_folder / png_name

            # 执行LLM分析
            llm_result = analyzer.analyze_image(str(image_path), ocr_result)

            if llm_result.get('success'):
                results[png_name] = {
                    "success": True,
                    "result": llm_result,
                    "tables_count": llm_result['processing_stats']['visual_tables_count']
                }
            else:
                results[png_name] = {
                    "success": False,
                    "error": llm_result.get('error', 'LLM分析失败')
                }

        return {
            "success": True,
            "step": "llm",
            "results": results,
            "message": f"LLM分析完成，处理{len(png_names)}张图片"
        }

    except Exception as e:
        return {
            "success": False,
            "step": "llm",
            "error": str(e)
        }


def execute_reconstruct_step(pdf_folder, png_names, previous_context, output_dir):
    """执行表格重构步骤"""
    try:

        # 检查前置结果
        ocr_results = previous_context.get('ocr_results', {})
        llm_results = previous_context.get('llm_results', {})

        if not ocr_results or not llm_results:
            return {
                "success": False,
                "step": "reconstruct",
                "error": "需要先执行OCR和LLM步骤"
            }

        results = {}
        reconstructor = TableReconstructor()

        for png_name in png_names:
            # 获取前置结果
            ocr_result = ocr_results.get(png_name, {}).get('result')
            llm_result = llm_results.get(png_name, {}).get('result')

            if not ocr_result or not llm_result:
                results[png_name] = {"success": False, "error": "缺少前置结果"}
                continue

            # 生成输出文件路径
            from pathlib import Path
            output_path = Path(output_dir) / pdf_folder
            output_path.mkdir(parents=True, exist_ok=True)
            excel_file = str(output_path / f"{Path(png_name).stem}_reconstructed.xlsx")

            effect_png_dir = FILTERED_TABLES_DIR / pdf_folder / png_name
            print("effect_png_dir::::", effect_png_dir)
            # 执行表格重构
            success = reconstructor.process_all_tables(
                ocr_result=ocr_result,
                llm_result=llm_result,
                output_file=excel_file,
                final_output_file=excel_file,
                image_path=str(effect_png_dir),
                bank_name=""
            )

            if success:
                results[png_name] = {
                    "success": True,
                    "output_file": excel_file,
                    "message": "表格重构成功"
                }
            else:
                results[png_name] = {
                    "success": False,
                    "error": "表格重构失败"
                }

        return {
            "success": True,
            "step": "reconstruct",
            "results": results,
            "message": f"表格重构完成"
        }

    except Exception as e:
        return {
            "success": False,
            "step": "reconstruct",
            "error": str(e)
        }


def execute_export_step(pdf_folder, png_names, previous_context, output_dir):
    """执行数据导出步骤"""
    # 在实际中，重构步骤通常已经生成Excel文件
    # 所以导出步骤可能只是文件整理或格式转换
    reconstruct_results = previous_context.get('reconstruct_results', {})

    excel_files = []
    for png_name in png_names:
        result = reconstruct_results.get(png_name, {})
        if result.get('success') and result.get('output_file'):
            excel_files.append(result['output_file'])

    return {
        "success": True,
        "step": "export",
        "excel_files": excel_files,
        "message": f"导出完成，生成{len(excel_files)}个Excel文件"
    }

