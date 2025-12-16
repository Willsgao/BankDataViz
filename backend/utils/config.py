<<<<<<< HEAD
# backend/utils/_config_shim.py
=======
# backend/utils/config.py
>>>>>>> f662bba3fc86341539408e13dff693eb5f844420
"""
后端配置管理 - 增强版，包含表格处理器配置
"""

import os
import json
from pathlib import Path

# 导入常量配置
try:
    from .constants import (
        MAIN_ROOT,
        UPLOAD_FOLDER,
        PNG_OUTPUT_ROOT,
        EXCEL_OUTPUT_ROOT,
        DATABASE,
        ALLOWED_EXTENSIONS
    )
except ImportError:
    # 如果导入失败，使用默认值
    MAIN_ROOT = os.getcwd()
    UPLOAD_FOLDER = 'backend/static/uploads'
    PNG_OUTPUT_ROOT = 'backend/static/pdf2pngs'
    EXCEL_OUTPUT_ROOT = 'backend/static/excel_data'
    DATABASE = 'backend/data/database.db'
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


class Config:
    """主配置类 - 整合表格处理器配置"""

    def __init__(self):
        self._config = self._load_config()
        self._setup_derived_config()
        self._setup_table_processor_config()  # 新增：表格处理器配置

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
        """默认配置 - 包含表格处理器配置"""
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
            },
            # 新增表格处理器配置部分
            "table_processor": {
                "llm": {
                    "api_key": "90b9c47f-815c-4216-913a-3d1a567e35ac",
                    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                    "model_name": "doubao-1-5-vision-pro-250328"
                },
                "ocr": {
                    "provider": "tencent",  # baidu 或 tencent
                    "timeout": 30,
                    "max_retries": 3
                },
                "baidu_ocr": {
                    "api_key": "Id7EZH2q6IOSlivHbwHHbWwz",
                    "secret_key": "leeZiDapOBp6nGZssuuzABgSZubNgSLu"
                },
                "tencent_ocr": {
                    "secret_id": "AKIDYDfuyrX1KTPFsJagZEguuiJhtsdCTbWG",
                    "secret_key": "c1DCxXv8B3jBP3ZsQp1760iHftwpX2KP",
                    "region": "ap-shanghai"
                },
                "processing": {
                    "extract_rows": 10,
                    "extract_cols": 3,
                    "max_retries": 3,
                    "timeout": 30
                },
                "paths": {
                    "temp_dir": "temp_imgs"
                }
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

        # 文件路径配置 - 从 constants.py 导入
        self.UPLOAD_FOLDER = UPLOAD_FOLDER
        self.EXCEL_DATA_FOLDER = EXCEL_OUTPUT_ROOT
        self.JOINED_TABLES_FOLDER = self._config['paths']['joinedTablesFolder']
        self.PNG_OUTPUT_ROOT = PNG_OUTPUT_ROOT
        self.MAIN_ROOT = Path(MAIN_ROOT)

        # LLM配置（通用）
        self.LLM_DEFAULT_BASE_URL = self._config['llm']['defaultBaseUrl']
        self.LLM_DEFAULT_MODEL_ID = self._config['llm']['defaultModelId']
        self.LLM_MAX_TOKENS = self._config['llm']['maxTokens']

        # 数据库配置 - 从 constants.py 导入
        self.DATABASE_PATH = DATABASE

        # 允许的文件扩展名
        self.ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS

    def _setup_table_processor_config(self):
        """设置表格处理器专用配置"""
        table_config = self._config.get('table_processor', {})

        # LLM配置（表格专用）
        llm_config = table_config.get('llm', {})
        self.TABLE_LLM_API_KEY = llm_config.get('api_key', "90b9c47f-815c-4216-913a-3d1a567e35ac")
        self.TABLE_LLM_BASE_URL = llm_config.get('base_url', "https://ark.cn-beijing.volces.com/api/v3")
        self.TABLE_LLM_MODEL_NAME = llm_config.get('model_name', "doubao-1-5-vision-pro-250328")

        # OCR配置
        ocr_config = table_config.get('ocr', {})
        self.OCR_PROVIDER = ocr_config.get('provider', 'tencent')
        self.OCR_TIMEOUT = ocr_config.get('timeout', 30)
        self.OCR_MAX_RETRIES = ocr_config.get('max_retries', 3)

        # 百度OCR
        baidu_config = table_config.get('baidu_ocr', {})
        self.BAIDU_OCR_API_KEY = baidu_config.get('api_key', "Id7EZH2q6IOSlivHbwHHbWwz")
        self.BAIDU_OCR_SECRET_KEY = baidu_config.get('secret_key', "leeZiDapOBp6nGZssuuzABgSZubNgSLu")

        # 腾讯OCR
        tencent_config = table_config.get('tencent_ocr', {})
        self.TENCENT_SECRET_ID = tencent_config.get('secret_id', "AKIDYDfuyrX1KTPFsJagZEguuiJhtsdCTbWG")
        self.TENCENT_SECRET_KEY = tencent_config.get('secret_key', "c1DCxXv8B3jBP3ZsQp1760iHftwpX2KP")
        self.TENCENT_REGION = tencent_config.get('region', "ap-shanghai")

        # 处理配置
        processing_config = table_config.get('processing', {})
        self.EXTRACT_ROWS = processing_config.get('extract_rows', 10)
        self.EXTRACT_COLS = processing_config.get('extract_cols', 3)
        self.MAX_RETRIES = processing_config.get('max_retries', 3)
        self.TIMEOUT = processing_config.get('timeout', 30)

        # 路径配置
        paths_config = table_config.get('paths', {})
        self.TABLE_TEMP_DIR = paths_config.get('temp_dir', "temp_imgs")

        # 使用主项目的输出目录
        self.TABLE_OUTPUT_DIR = self.EXCEL_DATA_FOLDER

        # 创建目录
        self._create_table_dirs()

    def _create_table_dirs(self):
        """创建表格处理需要的目录"""
        import os
        dirs_to_create = [
            self.TABLE_TEMP_DIR,
            self.TABLE_OUTPUT_DIR
        ]
        for dir_path in dirs_to_create:
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

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


<<<<<<< HEAD
# 修改后的 TableConfig 类
class TableConfig:
    """表格处理配置类 - 整合了table_processor的所有配置"""

    def __init__(self):
        # ========== LLM配置 ==========
        self.llm_api_key = "90b9c47f-815c-4216-913a-3d1a567e35ac"
        self.llm_base_url = "https://ark.cn-beijing.volces.com/api/v3"
        self.llm_model_name = "doubao-1-5-vision-pro-250328"

        # ========== OCR配置 - 多OCR支持 ==========
        self.ocr_provider = "tencent"  # 默认使用腾讯OCR，可选: "tencent" 或 "baidu"

        # 百度OCR配置
        self.ocr_api_key = "Id7EZH2q6IOSlivHbwHHbWwz"
        self.ocr_secret_key = "leeZiDapOBp6nGZssuuzABgSZubNgSLu"

        # 腾讯OCR配置
        self.tencent_secret_id = "AKIDYDfuyrX1KTPFsJagZEguuiJhtsdCTbWG"
        self.tencent_secret_key = "c1DCxXv8B3jBP3ZsQp1760iHftwpX2KP"
        self.tencent_region = "ap-shanghai"  # 区域: ap-shanghai, ap-beijing 等

        # ========== 处理配置 ==========
        self.ocr_timeout = 30
        self.ocr_max_retries = 3
        self.extract_rows = 10  # 提取的行数
        self.extract_cols = 3  # 提取的列数
        self.max_retries = 3  # 最大重试次数
        self.timeout = 30  # 超时时间

        # OCR 调试：是否落盘/保留字节
        self.debug_ocr = os.getenv("OCR_DEBUG", "false").lower() == "true"
        self.debug_ocr_keep_mb = int(os.getenv("OCR_DEBUG_KEEP_MB", "0"))
        # LLM 调试：是否打印 prompt
        self.debug_llm = os.getenv("LLM_DEBUG", "false").lower() == "true"

        self.CACHE_URL = os.getenv("CACHE_URL", "sqlite:///./cache.db")
        self.OBJECT_STORE = os.getenv("OBJECT_STORE", "local")
        self.LOCAL_OBJECT_STORE = os.getenv("LOCAL_OBJECT_STORE", "./obj_cache")
        self.OBJECT_STORE_BUCKET = os.getenv("OBJECT_STORE_BUCKET", "")
        # 强制刷新开关
        self.OCR_FORCE_REFRESH = os.getenv("OCR_FORCE_REFRESH", "false").lower() == "true"
        self.LLM_FORCE_REFRESH = os.getenv("LLM_FORCE_REFRESH", "false").lower() == "true"

        # ========== 路径配置 ==========
        # 从主配置中获取基础路径
        config_instance = Config()
        main_root = Path(config_instance.MAIN_ROOT)

        # ========== 路径配置（环境变量优先，绝对路径兜底，永不 None） ==========
        # 1. 输出目录
        self.output_dir = os.getenv("OUTPUT_DIR") or r"F:\wills\codes\DocuVista\test_codes\table_analyzer_codes/outputs"

        # 2. 临时目录
        self.temp_dir = os.getenv("TEMP_DIR") or r"F:\wills\codes\DocuVista\test_codes\table_analyzer_codes/temp"

        # 3. 本地对象存储目录
        self.LOCAL_OBJECT_STORE = os.getenv("LOCAL_OBJECT_STORE") or r"F:\wills\codes\DocuVista\test_codes\table_analyzer_codes/obj_cache"

        # 4. 确保目录存在（只建一次）
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.LOCAL_OBJECT_STORE, exist_ok=True)



    def _create_dirs(self):
        """创建必要的目录"""
        import os
        for dir_path in [self.temp_dir, self.output_dir]:
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                print(f"创建目录: {dir_path}")

    # 为了保持兼容性，添加属性访问器
    @property
    def LLM_API_KEY(self):
        return self.llm_api_key

    @property
    def LLM_BASE_URL(self):
        return self.llm_base_url

    @property
    def LLM_MODEL_NAME(self):
        return self.llm_model_name

    @property
    def OCR_API_KEY(self):
        return self.ocr_api_key

    @property
    def OCR_SECRET_KEY(self):
        return self.ocr_secret_key

    @property
    def OCR_TIMEOUT(self):
        return self.ocr_timeout

    @property
    def OCR_MAX_RETRIES(self):
        return self.ocr_max_retries
=======
# 为了保持向后兼容性，保留TableConfig类（但内容从主配置读取）
class TableConfig:
    """表格处理器配置类 - 兼容层"""

    def __init__(self, config: Config):
        self.config = config

    @property
    def llm_api_key(self):
        return self.config.TABLE_LLM_API_KEY

    @property
    def llm_base_url(self):
        return self.config.TABLE_LLM_BASE_URL

    @property
    def llm_model_name(self):
        return self.config.TABLE_LLM_MODEL_NAME

    @property
    def ocr_provider(self):
        return self.config.OCR_PROVIDER

    @property
    def ocr_api_key(self):
        return self.config.BAIDU_OCR_API_KEY

    @property
    def ocr_secret_key(self):
        return self.config.BAIDU_OCR_SECRET_KEY

    @property
    def tencent_secret_id(self):
        return self.config.TENCENT_SECRET_ID

    @property
    def tencent_secret_key(self):
        return self.config.TENCENT_SECRET_KEY

    @property
    def tencent_region(self):
        return self.config.TENCENT_REGION

    @property
    def ocr_timeout(self):
        return self.config.OCR_TIMEOUT

    @property
    def ocr_max_retries(self):
        return self.config.OCR_MAX_RETRIES

    @property
    def extract_rows(self):
        return self.config.EXTRACT_ROWS

    @property
    def extract_cols(self):
        return self.config.EXTRACT_COLS

    @property
    def max_retries(self):
        return self.config.MAX_RETRIES

    @property
    def timeout(self):
        return self.config.TIMEOUT

    @property
    def temp_dir(self):
        return self.config.TABLE_TEMP_DIR

    @property
    def output_dir(self):
        return self.config.TABLE_OUTPUT_DIR
>>>>>>> f662bba3fc86341539408e13dff693eb5f844420


# 创建全局配置实例
config = Config()

# 创建表格处理器配置实例（兼容性）
tableconfig = TableConfig(config)

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

__all__ = ['config', 'tableconfig', 'SERVER_CONFIG', 'FRONTEND_CONFIG', 'FILE_PATHS', 'API_PATHS']