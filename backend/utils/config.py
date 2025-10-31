# backend/utils/config.py
"""
后端配置管理
从项目根目录的 project-config.json 读取配置
"""

import os
import json
from pathlib import Path


class Config:
    """配置类"""

    def __init__(self):
        self._config = self._load_config()
        self._setup_derived_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            # 获取项目根目录路径
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / 'project-config.json'

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"Warning: Config file not found at {config_path}, using default config")
                return self._get_default_config()
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}, using default config")
            return self._get_default_config()

    def _get_default_config(self):
        """默认配置"""
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
                "uploadPrefix": "/upload"
            },
            "paths": {
                "uploadFolder": "static/uploads",
                "excelDataFolder": "static/excel_data",
                "joinedTablesFolder": "static/joined_tables",
                "pngOutputFolder": "static/png_output"
            },
            "llm": {
                "defaultBaseUrl": "https://ark.cn-beijing.volces.com/api/v3",
                "defaultModelId": "doubao-1-5-vision-pro-250328",
                "maxTokens": 4000
            }
        }

    def _setup_derived_config(self):
        """设置衍生配置"""
        # 后端配置
        self.BACKEND_HOST = os.getenv('BACKEND_HOST', self._config['servers']['backend']['host'])
        self.BACKEND_PORT = int(os.getenv('BACKEND_PORT', self._config['servers']['backend']['port']))
        self.BACKEND_BASE_URL = os.getenv('BACKEND_BASE_URL', self._config['servers']['backend']['baseUrl'])
        self.DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

        # 前端配置
        self.FRONTEND_HOST = os.getenv('FRONTEND_HOST', self._config['servers']['frontend']['host'])
        self.FRONTEND_PORT = int(os.getenv('FRONTEND_PORT', self._config['servers']['frontend']['port']))
        self.FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', self._config['servers']['frontend']['baseUrl'])

        # API配置
        self.API_PREFIX = os.getenv('API_PREFIX', self._config['api']['prefix'])
        self.STATIC_PREFIX = os.getenv('STATIC_PREFIX', self._config['api']['staticPrefix'])
        self.UPLOAD_PREFIX = os.getenv('UPLOAD_PREFIX', self._config['api']['uploadPrefix'])

        # 文件路径配置
        self.UPLOAD_FOLDER = self._config['paths']['uploadFolder']
        self.EXCEL_DATA_FOLDER = self._config['paths']['excelDataFolder']
        self.JOINED_TABLES_FOLDER = self._config['paths']['joinedTablesFolder']
        self.PNG_OUTPUT_ROOT = self._config['paths']['pngOutputFolder']
        self.MAIN_ROOT = Path(__file__).parent.parent

        # LLM配置
        self.LLM_DEFAULT_BASE_URL = self._config['llm']['defaultBaseUrl']
        self.LLM_DEFAULT_MODEL_ID = self._config['llm']['defaultModelId']
        self.LLM_MAX_TOKENS = self._config['llm']['maxTokens']

        # 数据库配置
        self.DATABASE_PATH = 'backend/data/files.db'

    @property
    def backend_api_base_url(self):
        return f"{self.BACKEND_BASE_URL}{self.API_PREFIX}"

    @property
    def backend_static_base_url(self):
        return f"{self.BACKEND_BASE_URL}{self.STATIC_PREFIX}"

    def get_api_url(self, endpoint):
        return f"{self.backend_api_base_url}{endpoint}"

    def get_static_url(self, path):
        return f"{self.backend_static_base_url}/{path}"

    def get_full_url(self, path):
        if path.startswith('/api/'):
            return self.get_api_url(path.replace('/api/', ''))
        elif path.startswith('/static/'):
            return self.get_static_url(path.replace('/static/', ''))
        else:
            return f"{self.BACKEND_BASE_URL}{path}"


# 创建全局配置实例
config = Config()

# 导出常用配置（保持兼容性）
SERVER_CONFIG = {
    'HOST': config.BACKEND_HOST,
    'PORT': config.BACKEND_PORT,
    'DEBUG': config.DEBUG
}

FRONTEND_CONFIG = {
    'HOST': config.FRONTEND_HOST,
    'PORT': config.FRONTEND_PORT,
    'BASE_URL': config.FRONTEND_BASE_URL
}

FILE_PATHS = {
    'UPLOAD_FOLDER': config.UPLOAD_FOLDER,
    'EXCEL_DATA_FOLDER': config.EXCEL_DATA_FOLDER,
    'JOINED_TABLES_FOLDER': config.JOINED_TABLES_FOLDER,
    'PNG_OUTPUT_ROOT': config.PNG_OUTPUT_ROOT,
    'MAIN_ROOT': str(config.MAIN_ROOT)
}

API_PATHS = {
    'BASE_PREFIX': config.API_PREFIX,
    'STATIC_PREFIX': config.STATIC_PREFIX,
    'UPLOAD_PREFIX': config.UPLOAD_PREFIX
}

__all__ = ['config', 'SERVER_CONFIG', 'FRONTEND_CONFIG', 'FILE_PATHS', 'API_PATHS']