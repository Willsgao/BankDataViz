# -*- coding:utf-8 -*-
"""
增量处理API包装器 - 为现有API提供增量处理支持
文件：backend/core/services/incremental_processor/api_wrapper.py
"""

from flask import jsonify
from typing import Any
from pathlib import Path

from backend.core.incremental_processor.incremental_service import IncrementalProcessingService


class IncrementalAPIWrapper:
    """增量处理API包装器"""

    def __init__(self):
        self.service = IncrementalProcessingService()
        print("✅✅ 增量处理API包装器初始化完成")

    def wrap_submit_table_processing(self, original_function, pdf_folder: str,
                                     filtered_tables_dir: str, request_obj, progress_tracker) -> Any:
        """
        包装提交表格处理任务的API

        Args:
            original_function: 原有的提交处理函数
            pdf_folder: PDF文件夹名称
            filtered_tables_dir: 筛选表格目录
            request_obj: Flask请求对象
            progress_tracker: 进度跟踪器

        Returns:
            Flask响应对象
        """
        try:
            # 获取请求数据
            if request_obj.content_type and 'application/json' in request_obj.content_type:
                data = request_obj.get_json() or {}
            else:
                data = request_obj.form.to_dict() or {}

            # 获取图片名称列表
            png_names = data.get('png_names', [])
            table_type = data.get('table_type', 'financial')
            bank_name = data.get('bank_name', '')

            print(f"📥📥 增量处理包装器: {pdf_folder}")
            print(f"  图片数量: {len(png_names)}")
            print(f"  表格类型: {table_type}")
            print(f"  银行名称: {bank_name}")

            # 构建图片路径
            image_paths = []
            tables_dir = Path(filtered_tables_dir) / pdf_folder / "tables"

            if not png_names and tables_dir.exists():
                # 自动从目录获取
                png_names = [f.name for f in tables_dir.glob("*.png")]
                print(f"  自动获取图片: {len(png_names)} 张")

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
                    "incremental_processing": True
                }), 400

            # 定义处理回调函数
            def processing_callback(image_paths, **kwargs):
                """调用原有的处理逻辑"""
                # 这里需要根据你的实际函数签名调整
                return original_function(
                    pdf_folder=pdf_folder,
                    image_paths=image_paths,
                    table_type=table_type,
                    bank_name=bank_name,
                    progress_tracker=progress_tracker,
                    # 其他必要参数...
                    **kwargs
                )

            # 调用增量处理服务
            result = self.service.process_with_incremental_check(
                pdf_folder=pdf_folder,
                all_image_paths=image_paths,
                processing_callback=processing_callback,
                table_type=table_type,
                bank_name=bank_name
            )

            return jsonify(result)

        except Exception as e:
            print(f"💥💥 增量处理包装器异常: {e}")
            import traceback
            traceback.print_exc()

            return jsonify({
                "success": False,
                "error": f"增量处理包装失败: {str(e)}",
                "incremental_processing": True
            }), 500

    def get_processing_status_api(self, pdf_folder: str) -> Any:
        """
        获取处理状态的API

        Args:
            pdf_folder: PDF文件夹名称

        Returns:
            Flask响应对象
        """
        try:
            status = self.service.get_processing_status(pdf_folder)
            return jsonify({
                "success": True,
                "data": status
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"获取状态失败: {str(e)}"
            }), 500

    def clear_records_api(self, pdf_folder: str = None) -> Any:
        """
        清空记录的API

        Args:
            pdf_folder: 指定PDF文件夹

        Returns:
            Flask响应对象
        """
        try:
            self.service.clear_processing_records(pdf_folder)

            if pdf_folder:
                message = f"已清空 {pdf_folder} 的处理记录"
            else:
                message = "已清空所有处理记录"

            return jsonify({
                "success": True,
                "message": message
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"清空记录失败: {str(e)}"
            }), 500


# 全局实例
incremental_api_wrapper = IncrementalAPIWrapper()