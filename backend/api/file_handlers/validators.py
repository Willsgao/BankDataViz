# -*- coding:utf-8 -*-

import os
from werkzeug.datastructures import FileStorage
from typing import Tuple, Optional
from pathlib import Path


class ValidationError(Exception):
    """自定义验证异常"""

    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# Excel文件验证 - Flask版本
def validate_excel_file(file: FileStorage, max_size_mb=50):
    """验证Excel文件 - Flask版本"""
    if not file or file.filename == '':
        raise ValidationError('没有选择文件')

    allowed_extensions = ['.xlsx', '.xls']
    ext = Path(file.filename).suffix.lower()

    if ext not in allowed_extensions:
        raise ValidationError(
            f'不支持的文件格式，仅支持Excel文件: {", ".join(allowed_extensions)}'
        )

    # 验证文件大小
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # 重置文件指针

    if file_size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'文件大小不能超过{max_size_mb}MB')

    return True


# 转换参数验证 - Flask版本
def validate_conversion_params(orientation: str, pages: str) -> Tuple[str, Optional[range]]:
    """验证转换参数 - Flask版本"""
    if orientation not in ["portrait", "landscape"]:
        raise ValidationError("orientation参数必须是portrait或landscape")

    page_range = None
    if pages != "all":
        try:
            if '-' in pages:
                start, end = map(int, pages.split('-'))
                page_range = range(start, end + 1)
            else:
                page_num = int(pages)
                page_range = range(page_num, page_num + 1)
        except ValueError:
            raise ValidationError("pages参数格式错误，示例: '1-3' 或 '2'")

    return orientation, page_range



