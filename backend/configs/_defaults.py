# -*- coding:utf-8 -*-
"""
默认配置字典模块（仅含 fallback 数据，无业务逻辑）
当 project-config.json 不存在时使用此配置
"""

# 类常量（供 get_default_config() 使用，必须在此模块顶层定义）
_LLM_MODEL_NAME_DEFAULT = "doubao-1-5-vision-pro-32k-250115"


def get_default_config():
    """
    返回默认配置字典。
    放在函数里而非模块顶层常量，确保 LLM_MODEL_NAME_DEFAULT 在运行时求值，
    避免与 Config 类的类属性产生混淆。
    """
    return {
        "project": {
            "name": "DocuVista",
            "version": "1.0.0"
        },
        "servers": {
            "backend": {
                "host": "127.0.0.1",
                "port": 5000,
                "baseUrl": "http://127.0.0.1:5000"
            },
            "frontend": {
                "host": "localhost",
                "port": 8080,
                "baseUrl": "http://localhost:8080"
            }
        },
        "api": {
            "prefix": "/api",
            "staticPrefix": "/static",
            "uploadPrefix": "/api/upload"
        },
        "paths": {
            "uploadFolder": "static/uploads",
            "excelDataFolder": "static/excel_data",
            "joinedTablesFolder": "static/joined_tables",
            "pngOutputFolder": "static/png_output"
        },
        "llm": {
            "defaultBaseUrl": "https://ark.cn-beijing.volces.com/api/v3",
            "defaultModelId": _LLM_MODEL_NAME_DEFAULT,
            "maxTokens": 4000
        },
        "table_processor": {
            "llm": {
                "api_key": "",           # 空字符串，安全优先；真实 Key 放 .env
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model_name": _LLM_MODEL_NAME_DEFAULT
            },
            "ocr": {
                "provider": "tencent",
                "timeout": 30,
                "max_retries": 3
            },
            "baidu_ocr": {
                "api_key": "",            # 空字符串，安全优先
                "secret_key": ""         # 空字符串，安全优先
            },
            "tencent_ocr": {
                "secret_id": "",
                "secret_key": "",
                "region": "ap-shanghai"
            },
            "processing": {
                "extract_rows": 10,
                "extract_cols": 3,
                "max_retries": 3,
                "timeout": 30
            },
            "paths": {
                "temp_dir": "data/backend/temp_imgs",
                "obj_cache": "data/backend/obj_cache",
                "ocr_raw": "data/backend/ocr_raw",
                "ocr_final": "data/backend/ocr_final",
                "llm_cache": "data/backend/llm_cache",
                "outputs": "data/backend/outputs"
            }
        }
    }
