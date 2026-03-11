# -*- coding:utf-8 -*-
"""
增量处理模块使用示例
文件：backend/core/services/incremental_processor/usage_example.py
"""

from backend.core.incremental_processor.incremental_service import incremental_service


def example_usage():
    """使用示例"""

    # 示例图片路径
    pdf_folder = "example_pdf"
    image_paths = [
        "path/to/image1.png",
        "path/to/image2.png",
        "path/to/image3.png"
    ]

    def mock_processing_callback(image_paths, **kwargs):
        """模拟处理函数"""
        print(f"🔄 处理 {len(image_paths)} 张图片")
        return {
            'success': True,
            'processed_count': len(image_paths),
            'message': '处理完成'
        }

    # 调用增量处理
    result = incremental_service.process_with_incremental_check(
        pdf_folder=pdf_folder,
        all_image_paths=image_paths,
        processing_callback=mock_processing_callback,
        table_type="financial",
        bank_name="示例银行"
    )

    print(f"处理结果: {result}")


if __name__ == "__main__":
    example_usage()