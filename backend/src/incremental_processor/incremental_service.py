# -*- coding:utf-8 -*-
"""
独立增量处理服务 - 不修改现有代码，通过包装器调用
文件：backend/src/services/incremental_processor/incremental_service.py
"""

from pathlib import Path
from typing import List, Dict, Any, Callable
from datetime import datetime

from .simple_incremental_processor import SimpleIncrementalProcessor


class IncrementalProcessingService:
    """独立增量处理服务"""

    def __init__(self, record_file_path=None):
        """
        初始化增量处理服务

        Args:
            record_file_path: 记录文件路径
        """
        self.processor = SimpleIncrementalProcessor(record_file_path)
        print("✅✅ 独立增量处理服务初始化完成")

    def process_with_incremental_check(self, pdf_folder: str, all_image_paths: List[str],
                                       processing_callback: Callable, **callback_kwargs) -> Dict[str, Any]:
        """
        增量处理入口函数

        Args:
            pdf_folder: PDF文件夹名称
            all_image_paths: 所有图片完整路径列表
            processing_callback: 实际处理图片的回调函数
            **callback_kwargs: 传递给回调函数的参数

        Returns:
            dict: 处理结果
        """
        print(f"🚀🚀 开始增量处理: {pdf_folder}")

        # 1. 提取图片名称
        image_names = [Path(img_path).name for img_path in all_image_paths]
        print(f"📸📸 输入图片: {len(image_names)} 张")

        # 2. 过滤已处理的图片
        images_to_process = self.processor.filter_processed_images(pdf_folder, image_names)

        if not images_to_process:
            print("🎯🎯 所有图片都已处理过，无需处理")
            return {
                'success': True,
                'incremental_processing': True,
                'message': '所有图片都已处理过，无需重复处理',
                'stats': self.processor.get_processing_stats(pdf_folder, image_names),
                'processed_count': 0,
                'skipped_count': len(image_names),
                'total_images': len(image_names)
            }

        # 3. 构建需要处理的图片路径
        images_to_process_paths = []
        for img_path in all_image_paths:
            if Path(img_path).name in images_to_process:
                images_to_process_paths.append(img_path)

        print(f"🔄🔄 需要处理 {len(images_to_process_paths)} 张新图片")

        # 4. 调用实际的处理函数
        try:
            # 调用原有的处理逻辑
            result = processing_callback(
                image_paths=images_to_process_paths,
                **callback_kwargs
            )

            # 5. 如果处理成功，标记为已处理
            if result.get('success', False):
                self.processor.mark_images_processed(pdf_folder, images_to_process)
                print(f"✅✅ 增量处理完成: {pdf_folder}")

                # 增强返回结果
                result['incremental_processing'] = True
                result['incremental_stats'] = {
                    'total_images': len(image_names),
                    'processed_this_time': len(images_to_process),
                    'skipped_images': len(image_names) - len(images_to_process),
                    'completion_percentage': self.processor.get_processing_stats(pdf_folder, image_names)[
                        'progress_percentage'],
                    'processing_timestamp': datetime.now().isoformat()
                }
            else:
                print(f"❌❌ 处理失败，不更新记录: {pdf_folder}")

            return result

        except Exception as e:
            print(f"💥💥 增量处理异常: {e}")
            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'error': f'增量处理失败: {str(e)}',
                'incremental_processing': True,
                'pdf_folder': pdf_folder,
                'total_images': len(image_names),
                'images_to_process': len(images_to_process)
            }

    def get_processing_status(self, pdf_folder: str, image_names: List[str] = None) -> Dict[str, Any]:
        """
        获取处理状态

        Args:
            pdf_folder: PDF文件夹名称
            image_names: 图片名称列表（可选）

        Returns:
            dict: 状态信息
        """
        if image_names is None:
            image_names = []

        stats = self.processor.get_processing_stats(pdf_folder, image_names)

        return {
            'pdf_folder': pdf_folder,
            'incremental_processing': True,
            'stats': stats,
            'needs_processing': stats['unprocessed_images'] > 0,
            'status_timestamp': datetime.now().isoformat()
        }

    def clear_processing_records(self, pdf_folder: str = None):
        """
        清空处理记录

        Args:
            pdf_folder: 指定PDF文件夹，如果为None则清空所有
        """
        if pdf_folder:
            self.processor.clear_pdf_records(pdf_folder)
        else:
            self.processor.clear_all_records()

    def get_all_processing_records(self) -> Dict[str, Any]:
        """
        获取所有处理记录

        Returns:
            dict: 所有记录信息
        """
        pdf_folders = self.processor.get_all_pdf_folders()

        records_info = {}
        for pdf_folder in pdf_folders:
            records_info[pdf_folder] = {
                'processed_count': len(self.processor.records.get(pdf_folder, [])),
                'image_list': self.processor.records.get(pdf_folder, [])[:10]  # 只显示前10个
            }

        return {
            'total_pdf_folders': len(pdf_folders),
            'records': records_info,
            'record_file': str(self.processor.record_file)
        }


# 全局实例
incremental_service = IncrementalProcessingService()