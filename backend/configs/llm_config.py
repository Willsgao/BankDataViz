# backend/configs/llm_config.py
import os

# API配置（从环境变量读取，.env 中配置 LLM_API_KEY）
# 重要：fallback 为空字符串，若未配置 .env 则调用会失败（安全优先）
ARK_API_KEY = os.environ.get("LLM_API_KEY", "")
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# 模型配置
DEFAULT_MODEL_ID = "doubao-1-5-vision-pro-250328"

# 处理配置
MAX_TOKENS_CONFIG = {
    "default": 6000,
    "standard": 8000,
    "standard_extended": 10000,
    "complex": 13000,
    "max_limit": 16000
}

# 图片大小对应的token增量配置
IMAGE_SIZE_TOKEN_INCREMENT = {
    3000000: 5000,
    2000000: 3000,
    1500000: 2000,
    1000000: 1000
}

# 复杂度到处理模式的映射
COMPLEXITY_MODE_MAPPING = {
    "极简单": "simple",
    "简单": "simple",
    "中等-紧凑型": "standard",
    "中等-扩展型": "standard",
    "复杂": "complex",
    "极复杂": "complex"
}

# 提示词配置（可以在这里定义，也可以单独文件）
PROMPT_NAMES = {
    "assessment": "ASSESSMENT_PROMPT",
    "simple": "STANDARD_PROMPT",
    "standard": "STANDARD_PROMPT",
    "complex": "COMPLEX_PROMPT"
}


# llm_config.py 中增加以下内容

# 在 COMPLEXITY_MODE_MAPPING 后面添加
TABLE_TYPE_MODE_MAPPING = {
    "financial": {
        "极简单": "simple",
        "简单": "simple",
        "中等-紧凑型": "standard",
        "中等-扩展型": "standard",
        "复杂": "complex",
        "极复杂": "complex"
    },
    "non_financial": {
        "极简单": "non_financial",
        "简单": "non_financial",
        "中等-紧凑型": "non_financial",
        "中等-扩展型": "non_financial",
        "复杂": "non_financial",
        "极复杂": "non_financial"
    }
}

# 在 PROMPT_NAMES 中添加
PROMPT_NAMES = {
    "assessment": "ASSESSMENT_PROMPT",
    "simple": "STANDARD_PROMPT",
    "standard": "STANDARD_PROMPT",
    "complex": "COMPLEX_PROMPT",
    "non_financial": "NON_FINANCIAL_PROMPT"  # 新增
}