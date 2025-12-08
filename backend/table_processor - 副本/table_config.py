# -*- coding:utf-8 -*-
import os


# 保留原有类结构，只修改内部实现
class SimpleSettings:
    """配置类 - 直接在代码中配置API"""

    def __init__(self):
        # ========== 在这里直接修改你的API密钥 ==========

        # LLM配置
        self.llm_api_key = "90b9c47f-815c-4216-913a-3d1a567e35ac"  # ← 改这里
        self.llm_base_url = "https://ark.cn-beijing.volces.com/api/v3"
        self.llm_model_name = "doubao-1-5-vision-pro-250328"

        # OCR配置
        self.ocr_api_key = "Id7EZH2q6IOSlivHbwHHbWwz"  # ← 改这里
        self.ocr_secret_key = "leeZiDapOBp6nGZssuuzABgSZubNgSLu"  # ← 改这里

        # 其他配置保持不变...
        self.ocr_timeout = 30
        self.ocr_max_retries = 3
        self.extract_rows = 10
        self.extract_cols = 3
        self.max_retries = 3
        self.timeout = 30
        self.temp_dir = "./temp_imgs"
        self.output_dir = "../../test_codes/enhanced_table_analyzer/output"

        # 创建目录
        self._create_dirs()

    def _create_dirs(self):
        """创建必要的目录"""
        for dir_path in [self.temp_dir, self.output_dir]:
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)


# 关键：保持变量名不变，其他文件才能正常导入
settings = SimpleSettings()