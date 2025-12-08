# -*- coding:utf-8 -*-

import os
from typing import Optional

try:
    # 尝试导入新版本的 pydantic-settings
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        # 回退到旧版本的 pydantic
        from pydantic import BaseSettings
    except ImportError:
        # 如果都没有，使用简单的配置类
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)


class Settings(BaseSettings):
    """统一配置管理"""

    # LLM配置
    llm_api_key: str = "90b9c47f-815c-4216-913a-3d1a567e35ac"
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_model_name: str = "doubao-1-5-vision-pro-250328"

    # OCR配置
    ocr_api_key: str = "Id7EZH2q6IOSlivHbwHHbWwz"
    ocr_secret_key: str = "leeZiDapOBp6nGZssuuzABgSZubNgSLu"
    ocr_timeout: int = 30
    ocr_max_retries: int = 3

    # 表格分析配置
    extract_rows: int = 10  # 提取的行数（从第22行可以看到默认值应该是10）
    extract_cols: int = 3   # 提取的列数（从第23行可以看到默认值应该是3）
    max_retries: int = 3    # 最大重试次数
    timeout: int = 30       # 超时时间

    # 路径配置
    temp_dir: str = "./temp_imgs"
    output_dir: str = "../enhanced_table_analyzer/output"

    class Config:
        env_file = ".env"


# 简单的配置类作为备选
class SimpleSettings:
    """简单的配置类，不依赖 pydantic"""

    def __init__(self):
        self.llm_api_key = "90b9c47f-815c-4216-913a-3d1a567e35ac"
        self.llm_base_url = "https://ark.cn-beijing.volces.com/api/v3"
        self.llm_model_name = "doubao-1-5-vision-pro-250328"

        self.ocr_api_key = "Id7EZH2q6IOSlivHbwHHbWwz"
        self.ocr_secret_key = "leeZiDapOBp6nGZssuuzABgSZubNgSLu"
        self.ocr_timeout = 30
        self.ocr_max_retries = 3

        # 表格分析配置
        self.extract_rows = 10  # 提取的行数
        self.extract_cols = 3   # 提取的列数
        self.max_retries = 3    # 最大重试次数
        self.timeout = 30       # 超时时间

        self.temp_dir = "./temp_imgs"
        self.output_dir = "../enhanced_table_analyzer/output"


# 根据环境选择配置实现
try:
    settings = Settings()
except Exception as e:
    print(f"⚠️  Pydantic配置加载失败，使用简单配置: {e}")
    settings = SimpleSettings()