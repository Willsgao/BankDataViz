# backend/utils/config.py
"""
后端配置管理 - 增强版，包含表格处理器配置
所有路径都必须基于 PROJECT_ROOT_STR 作为根目录
"""

import os
import json
from pathlib import Path

# 导入常量配置
try:
    from backend.utils.constants import (
        PROJECT_ROOT_STR,
        UPLOAD_FOLDER,
        PNG_OUTPUT_ROOT,
        EXCEL_OUTPUT_ROOT,
        DATABASE,
        ALLOWED_EXTENSIONS
    )
except ImportError:
    # 如果导入失败，使用默认值
    PROJECT_ROOT_STR = os.getcwd()
    UPLOAD_FOLDER = 'data/backend/static/uploads'
    PNG_OUTPUT_ROOT = 'data/backend/static/pdf2pngs'
    EXCEL_OUTPUT_ROOT = 'data/backend/static/excel_data'
    DATABASE = 'data/database.db'
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


class Config:
    """主配置类 - 整合表格处理器配置"""

    def __init__(self):
        # 首先确保 PROJECT_ROOT_STR 是绝对路径
        self.PROJECT_ROOT = Path(PROJECT_ROOT_STR).resolve()
        self.MAIN_ROOT = str(self.PROJECT_ROOT)

        print(f"[Config] 项目根目录（绝对路径）: {self.MAIN_ROOT}")

        self._config = self._load_config()
        self._setup_derived_config()
        self._setup_table_processor_config()

    def _load_config(self):
        """加载配置文件 - 所有路径基于 PROJECT_ROOT"""
        try:
            config_path = self.PROJECT_ROOT / 'project-config.json'

            print(f"[Config] 配置文件路径: {config_path}")

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
                "defaultModelId": "doubao-1-5-vision-pro-250328",
                "maxTokens": 4000
            },
            "table_processor": {
                "llm": {
                    "api_key": "90b9c47f-815c-4216-913a-3d1a567e35ac",
                    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                    "model_name": "doubao-1-5-vision-pro-250328"
                },
                "ocr": {
                    "provider": "tencent",
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
                    "temp_dir": "data/backend/temp_imgs",
                    "obj_cache": "data/backend/obj_cache",
                    "ocr_raw": "data/backend/ocr_raw",
                    "ocr_final": "data/backend/ocr_final",
                    "llm_cache": "data/backend/llm_cache",
                    "outputs": "data/backend/outputs"
                }
            }
        }

    def _setup_derived_config(self):
        """设置衍生配置 - 所有路径基于 PROJECT_ROOT"""
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

        # 🔥 关键修改：所有路径都基于 PROJECT_ROOT
        # 文件路径配置 - 基于项目根目录
        self.UPLOAD_FOLDER = self._get_absolute_path(UPLOAD_FOLDER)
        self.EXCEL_DATA_FOLDER = self._get_absolute_path(EXCEL_OUTPUT_ROOT)
        self.JOINED_TABLES_FOLDER = self._get_absolute_path(self._config['paths']['joinedTablesFolder'])
        self.PNG_OUTPUT_ROOT = self._get_absolute_path(PNG_OUTPUT_ROOT)
        # 🔥 新增：JSON 快照根目录（用于 /excel/save-final 及 /excel/latest-data）
        snapshot_rel = self._config['paths'].get('snapshotFolder', 'static/modify_data')
        self.SNAPSHOT_ROOT = self._get_absolute_path(snapshot_rel)
        os.makedirs(self.SNAPSHOT_ROOT, exist_ok=True)   # 启动即自动建好

        # LLM配置（通用）
        self.LLM_DEFAULT_BASE_URL = self._config['llm']['defaultBaseUrl']
        self.LLM_DEFAULT_MODEL_ID = self._config['llm']['defaultModelId']
        self.LLM_MAX_TOKENS = self._config['llm']['maxTokens']

        # 数据库配置 - 基于项目根目录
        self.DATABASE_PATH = self._get_absolute_path(DATABASE)

        # 允许的文件扩展名
        self.ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS

    def _setup_table_processor_config(self):
        """设置表格处理器专用配置 - 所有路径基于 PROJECT_ROOT"""
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

        # 🔥 关键修复：表格处理器所有路径都使用 table_processor 配置中的路径
        # 不要引用主项目中的任何 backend/static/ 路径
        paths_config = table_config.get('paths', {})

        # 临时目录
        self.TABLE_TEMP_DIR = self._get_absolute_path(paths_config.get('temp_dir', "data/backend/temp_imgs"))

        # 缓存目录
        self.TABLE_OBJ_CACHE_DIR = self._get_absolute_path(paths_config.get('obj_cache', "data/backend/obj_cache"))
        self.TABLE_OCR_RAW_DIR = self._get_absolute_path(paths_config.get('ocr_raw', "data/backend/ocr_raw"))
        self.TABLE_OCR_FINAL_DIR = self._get_absolute_path(paths_config.get('ocr_final', "data/backend/ocr_final"))
        self.TABLE_LLM_CACHE_DIR = self._get_absolute_path(paths_config.get('llm_cache', "data/backend/llm_cache"))

        # 🔥 输出目录：使用 table_processor 自己的 outputs，不要用主项目的 EXCEL_DATA_FOLDER
        table_output_dir = paths_config.get('outputs', "data/backend/outputs")
        self.TABLE_OUTPUT_DIR = self._get_absolute_path(table_output_dir)

        print(f"[Config] 表格处理器输出目录: {self.TABLE_OUTPUT_DIR}")

        # 创建目录
        self._create_table_dirs()

    def _get_absolute_path(self, relative_path):
        """将相对路径转换为基于 PROJECT_ROOT 的绝对路径"""
        if not relative_path:
            return ""

        # 如果已经是绝对路径，直接返回
        if os.path.isabs(relative_path):
            return relative_path

        # 基于 PROJECT_ROOT 转换为绝对路径
        absolute_path = self.PROJECT_ROOT / relative_path
        return str(absolute_path.resolve())

    def _create_table_dirs(self):
        """创建表格处理需要的目录"""
        dirs_to_create = [
            self.TABLE_TEMP_DIR,
            self.TABLE_OUTPUT_DIR,
            self.TABLE_OBJ_CACHE_DIR,
            self.TABLE_OCR_RAW_DIR,
            self.TABLE_OCR_FINAL_DIR,
            self.TABLE_LLM_CACHE_DIR
        ]
        for dir_path in dirs_to_create:
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                print(f"[Config] 创建目录: {dir_path}")

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


class TableConfig:
    """表格处理配置类 - 所有路径基于主配置的 PROJECT_ROOT"""

    def __init__(self, config: Config = None):
        self.config = config
        self.PROJECT_ROOT = config.PROJECT_ROOT if config else Path(PROJECT_ROOT_STR).resolve()

        if self.config:
            # 如果传入主配置，则从主配置读取
            self._init_from_main_config()
        else:
            # 否则使用独立的配置（也基于 PROJECT_ROOT）
            self._init_from_env_and_defaults()

        # 确保目录存在
        self._create_dirs()

    def _init_from_main_config(self):
        """从主配置读取"""
        # LLM配置
        self.llm_api_key = self.config.TABLE_LLM_API_KEY
        self.llm_base_url = self.config.TABLE_LLM_BASE_URL
        self.llm_model_name = self.config.TABLE_LLM_MODEL_NAME

        # OCR配置
        self.ocr_provider = self.config.OCR_PROVIDER
        self.ocr_api_key = self.config.BAIDU_OCR_API_KEY
        self.ocr_secret_key = self.config.BAIDU_OCR_SECRET_KEY
        self.tencent_secret_id = self.config.TENCENT_SECRET_ID
        self.tencent_secret_key = self.config.TENCENT_SECRET_KEY
        self.tencent_region = self.config.TENCENT_REGION

        # 处理配置
        self._ocr_timeout = self.config.OCR_TIMEOUT
        self._ocr_max_retries = self.config.OCR_MAX_RETRIES
        self.extract_rows = self.config.EXTRACT_ROWS
        self.extract_cols = self.config.EXTRACT_COLS
        self.max_retries = self.config.MAX_RETRIES
        self.timeout = self.config.TIMEOUT

        # 🔥 路径配置 - 确保使用表格处理器自己的路径
        self.temp_dir = self.config.TABLE_TEMP_DIR
        self.output_dir = self.config.TABLE_OUTPUT_DIR  # 使用 TABLE_OUTPUT_DIR 而不是 TABLE_OUTPUT_DIR
        self.obj_cache_dir = self.config.TABLE_OBJ_CACHE_DIR
        self.ocr_raw_dir = self.config.TABLE_OCR_RAW_DIR
        self.ocr_final_dir = self.config.TABLE_OCR_FINAL_DIR
        self.llm_cache_dir = self.config.TABLE_LLM_CACHE_DIR

        print(f"[TableConfig] 输出目录设置为: {self.output_dir}")

        # 环境变量配置
        self._init_env_vars()

    def _init_from_env_and_defaults(self):
        """从环境变量和默认值初始化 - 所有路径基于 PROJECT_ROOT"""
        # ========== LLM配置 ==========
        self.llm_api_key = "90b9c47f-815c-4216-913a-3d1a567e35ac"
        self.llm_base_url = "https://ark.cn-beijing.volces.com/api/v3"
        self.llm_model_name = "doubao-1-5-vision-pro-250328"

        # ========== OCR配置 - 多OCR支持 ==========
        self.ocr_provider = "tencent"
        self.ocr_api_key = "Id7EZH2q6IOSlivHbwHHbWwz"
        self.ocr_secret_key = "leeZiDapOBp6nGZssuuzABgSZubNgSLu"
        self.tencent_secret_id = "AKIDYDfuyrX1KTPFsJagZEguuiJhtsdCTbWG"
        self.tencent_secret_key = "c1DCxXv8B3jBP3ZsQp1760iHftwpX2KP"
        self.tencent_region = "ap-shanghai"

        # ========== 处理配置 ==========
        self._ocr_timeout = 30
        self._ocr_max_retries = 3
        self.extract_rows = 10
        self.extract_cols = 3
        self.max_retries = 3
        self.timeout = 30

        # ========== 路径配置 ==========
        # 🔥 所有路径都基于 PROJECT_ROOT
        print(f"[TableConfig] 使用项目根目录: {self.PROJECT_ROOT}")

        data_backend_dir = self.PROJECT_ROOT / "data" / "backend"
        data_backend_dir.mkdir(parents=True, exist_ok=True)

        # 输出目录 - 环境变量优先，但都转换为基于 PROJECT_ROOT 的绝对路径
        output_dir_env = os.getenv("OUTPUT_DIR")
        if output_dir_env:
            self.output_dir = self._to_absolute_path(output_dir_env)
        else:
            self.output_dir = str(data_backend_dir / "outputs")

        # 其他目录
        self.temp_dir = self._to_absolute_path(os.getenv("TEMP_DIR") or str(data_backend_dir / "temp_imgs"))
        self.obj_cache_dir = self._to_absolute_path(os.getenv("OBJ_CACHE_DIR") or str(data_backend_dir / "obj_cache"))
        self.ocr_raw_dir = self._to_absolute_path(os.getenv("OCR_RAW_DIR") or str(data_backend_dir / "ocr_raw"))
        self.ocr_final_dir = self._to_absolute_path(os.getenv("OCR_FINAL_DIR") or str(data_backend_dir / "ocr_final"))
        self.llm_cache_dir = self._to_absolute_path(os.getenv("LLM_CACHE_DIR") or str(data_backend_dir / "llm_cache"))

        # ========== 环境变量配置 ==========
        self._init_env_vars()

    def _to_absolute_path(self, path):
        """将路径转换为基于 PROJECT_ROOT 的绝对路径"""
        if not path:
            return ""

        if os.path.isabs(path):
            return path

        # 基于 PROJECT_ROOT
        return str((self.PROJECT_ROOT / path).resolve())

    def _init_env_vars(self):
        """初始化环境变量相关配置"""
        # OCR 调试
        self.debug_ocr = os.getenv("OCR_DEBUG", "false").lower() == "true"
        self.debug_ocr_keep_mb = int(os.getenv("OCR_DEBUG_KEEP_MB", "0"))

        # LLM 调试
        self.debug_llm = os.getenv("LLM_DEBUG", "false").lower() == "true"

        # 对象存储配置
        self.OBJECT_STORE = os.getenv("OBJECT_STORE", "local")
        local_store = os.getenv("LOCAL_OBJECT_STORE")
        self.LOCAL_OBJECT_STORE = self._to_absolute_path(local_store) if local_store else self.obj_cache_dir
        self.OBJECT_STORE_BUCKET = os.getenv("OBJECT_STORE_BUCKET", "")

        # 强制刷新开关
        self.OCR_FORCE_REFRESH = os.getenv("OCR_FORCE_REFRESH", "false").lower() == "true"
        self.LLM_FORCE_REFRESH = os.getenv("LLM_FORCE_REFRESH", "false").lower() == "true"

        # 🔥 数据库配置 - 基于 PROJECT_ROOT
        env_db_url = os.getenv("CACHE_URL")
        if env_db_url:
            self.CACHE_URL = env_db_url
        else:
            # 创建缓存目录（绝对路径）
            cache_dir = self.PROJECT_ROOT / "data" / "backend" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / "api_cache.db"

            # 🔥 使用绝对路径
            abs_cache_path = cache_path.resolve()
            self.CACHE_URL = f"sqlite:///{abs_cache_path}"

        print(f"[TableConfig] 数据库连接URL: {self.CACHE_URL}")

    def _create_dirs(self):
        """创建必要的目录"""
        dirs_to_create = []

        if hasattr(self, 'temp_dir') and self.temp_dir:
            dirs_to_create.append(self.temp_dir)

        if hasattr(self, 'output_dir') and self.output_dir:
            dirs_to_create.append(self.output_dir)

        if hasattr(self, 'obj_cache_dir') and self.obj_cache_dir:
            dirs_to_create.append(self.obj_cache_dir)

        if hasattr(self, 'ocr_raw_dir') and self.ocr_raw_dir:
            dirs_to_create.append(self.ocr_raw_dir)

        if hasattr(self, 'ocr_final_dir') and self.ocr_final_dir:
            dirs_to_create.append(self.ocr_final_dir)

        if hasattr(self, 'llm_cache_dir') and self.llm_cache_dir:
            dirs_to_create.append(self.llm_cache_dir)

        if hasattr(self, 'LOCAL_OBJECT_STORE') and self.LOCAL_OBJECT_STORE:
            dirs_to_create.append(self.LOCAL_OBJECT_STORE)

        for dir_path in dirs_to_create:
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                print(f"[TableConfig] 创建目录: {dir_path}")

    # 🔥 简化方法，直接返回属性（已经是绝对路径）
    def get_absolute_ocr_raw_dir(self):
        """获取OCR原始数据目录的绝对路径"""
        return getattr(self, 'ocr_raw_dir', '')

    def get_absolute_ocr_final_dir(self):
        """获取OCR最终数据目录的绝对路径"""
        return getattr(self, 'ocr_final_dir', '')

    # 属性访问器
    @property
    def OCR_RAW_DIR(self):
        return self.get_absolute_ocr_raw_dir()

    @property
    def OCR_FINAL_DIR(self):
        return self.get_absolute_ocr_final_dir()

    @property
    def ocr_timeout(self):
        return getattr(self, '_ocr_timeout', 30)

    @property
    def OCR_TIMEOUT(self):
        return self.ocr_timeout

    @property
    def ocr_max_retries(self):
        return getattr(self, '_ocr_max_retries', 3)

    @property
    def OCR_MAX_RETRIES(self):
        return self.ocr_max_retries

    @property
    def LLM_CACHE_DIR(self):
        return getattr(self, 'llm_cache_dir', '')

    @ocr_timeout.setter
    def ocr_timeout(self, value):
        self._ocr_timeout = value

    @ocr_max_retries.setter
    def ocr_max_retries(self, value):
        self._ocr_max_retries = value

    # 兼容性属性
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
    def TENCENT_SECRET_ID(self):
        return self.tencent_secret_id

    @property
    def TENCENT_SECRET_KEY(self):
        return self.tencent_secret_key

    @property
    def TENCENT_REGION(self):
        return self.tencent_region

    @property
    def EXTRACT_ROWS(self):
        return self.extract_rows

    @property
    def EXTRACT_COLS(self):
        return self.extract_cols

    @property
    def MAX_RETRIES(self):
        return self.max_retries

    @property
    def TIMEOUT(self):
        return self.timeout


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
    'MAIN_ROOT': config.MAIN_ROOT
}

API_PATHS = {
    'BASE_PREFIX': config.API_PREFIX,
    'STATIC_PREFIX': config.STATIC_PREFIX,
    'UPLOAD_PREFIX': config.UPLOAD_PREFIX
}

__all__ = ['config', 'tableconfig', 'SERVER_CONFIG', 'FRONTEND_CONFIG', 'FILE_PATHS', 'API_PATHS']
