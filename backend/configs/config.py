# backend/configs/config.py
"""
后端配置管理 - 模块化版本

架构说明：
  - _defaults.py   : 默认配置字典（fallback）
  - _paths.py      : 路径工具函数（跨模块复用）
  - table_config.py: TableConfig 独立类
  - config.py     : Config 主类 + 单例导出

所有路径均基于 PROJECT_ROOT_STR，所有凭证优先从环境变量读取。
"""
import os
import json
from pathlib import Path

from ._defaults import get_default_config
from ._paths import get_absolute_path, create_table_dirs

# 导入常量（来自 backend.utils.constants）
try:
    from backend.utils.constants import (
        PROJECT_ROOT_STR,
        UPLOAD_FOLDER,
        PNG_OUTPUT_ROOT,
        EXCEL_OUTPUT_ROOT,
        DATABASE,
        ALLOWED_EXTENSIONS,
    )
except ImportError:
    PROJECT_ROOT_STR = os.getcwd()
    UPLOAD_FOLDER = "data/backend/static/uploads"
    PNG_OUTPUT_ROOT = "data/backend/static/pdf2pngs"
    EXCEL_OUTPUT_ROOT = "data/backend/static/excel_data"
    DATABASE = "data/database.db"
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif"}


class Config:
    """主配置类 - 整合所有后端配置"""

    # 类常量（供 _get_default_config 引用）
    LLM_MODEL_NAME_DEFAULT = "doubao-1-5-vision-pro-32k-250115"

    def __init__(self):
        self.PROJECT_ROOT = Path(PROJECT_ROOT_STR).resolve()
        self.MAIN_ROOT = str(self.PROJECT_ROOT)

        print(f"[Config] 项目根目录（绝对路径）: {self.MAIN_ROOT}")

        self._config = self._load_config()
        self._setup_derived_config()
        self._setup_table_processor_config()
        self._setup_admin_config()

    # -------------------------------------------------------------------------
    # 配置加载
    # -------------------------------------------------------------------------
    def _load_config(self):
        """加载 project-config.json；缺失时使用 _defaults 中的 fallback"""
        try:
            config_path = self.PROJECT_ROOT / "project-config.json"
            print(f"[Config] 配置文件路径: {config_path}")

            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print(f"[Config] project-config.json 不存在，使用默认配置")
                return get_default_config()
        except Exception as e:
            print(f"[Config] 加载配置文件失败: {e}，使用默认配置")
            return get_default_config()

    # -------------------------------------------------------------------------
    # 服务器 / API / 路径 / LLM 基础配置
    # -------------------------------------------------------------------------
    def _setup_derived_config(self):
        """设置衍生配置（服务器 / API / 路径 / LLM 通用配置）"""
        # 后端 / 前端服务器
        self.BACKEND_HOST = os.getenv("BACKEND_HOST",
                                      self._config["servers"]["backend"]["host"])
        self.BACKEND_PORT = int(os.getenv("BACKEND_PORT",
                                          self._config["servers"]["backend"]["port"]))
        self.BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL",
                                          self._config["servers"]["backend"]["baseUrl"])
        self.DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

        self.FRONTEND_HOST = os.getenv("FRONTEND_HOST",
                                       self._config["servers"]["frontend"]["host"])
        self.FRONTEND_PORT = int(os.getenv("FRONTEND_PORT",
                                           self._config["servers"]["frontend"]["port"]))
        self.FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL",
                                            self._config["servers"]["frontend"]["baseUrl"])

        # API 配置
        self.API_PREFIX = os.getenv("API_PREFIX", self._config["api"]["prefix"])
        self.STATIC_PREFIX = os.getenv("STATIC_PREFIX", self._config["api"]["staticPrefix"])
        self.UPLOAD_PREFIX = os.getenv("UPLOAD_PREFIX", self._config["api"]["uploadPrefix"])

        # 文件路径（均转为绝对路径）
        self.UPLOAD_FOLDER = get_absolute_path(str(self.PROJECT_ROOT), UPLOAD_FOLDER)
        self.EXCEL_DATA_FOLDER = get_absolute_path(str(self.PROJECT_ROOT), EXCEL_OUTPUT_ROOT)
        self.JOINED_TABLES_FOLDER = get_absolute_path(
            str(self.PROJECT_ROOT), self._config["paths"]["joinedTablesFolder"]
        )
        self.PNG_OUTPUT_ROOT = get_absolute_path(str(self.PROJECT_ROOT), PNG_OUTPUT_ROOT)

        # JSON 快照目录（用于 /excel/save-final 及 /excel/latest-data）
        snapshot_rel = self._config["paths"].get("snapshotFolder", "static/modify_data")
        self.SNAPSHOT_ROOT = get_absolute_path(str(self.PROJECT_ROOT), snapshot_rel)
        os.makedirs(self.SNAPSHOT_ROOT, exist_ok=True)

        # LLM 通用配置
        print(f"[Config] _config keys: {list(self._config.keys())}")
        self.LLM_DEFAULT_BASE_URL = self._config["llm"]["defaultBaseUrl"]
        self.LLM_DEFAULT_MODEL_ID = self._config["llm"]["defaultModelId"]
        self.LLM_MAX_TOKENS = self._config["llm"]["maxTokens"]

        # 数据库
        self.DATABASE_PATH = get_absolute_path(str(self.PROJECT_ROOT), DATABASE)

        # 允许的文件扩展名
        self.ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS

    # -------------------------------------------------------------------------
    # 表格处理器配置（LLM / OCR / 路径）
    # -------------------------------------------------------------------------
    def _setup_table_processor_config(self):
        """设置表格处理器专用配置"""
        table_config = self._config.get("table_processor", {})

        # LLM（表格专用）
        llm_cfg = table_config.get("llm", {})
        self.TABLE_LLM_API_KEY = llm_cfg.get("api_key", "")
        self.TABLE_LLM_BASE_URL = llm_cfg.get(
            "base_url", "https://ark.cn-beijing.volces.com/api/v3"
        )
        self.TABLE_LLM_MODEL_NAME = llm_cfg.get("model_name", self.LLM_MODEL_NAME_DEFAULT)

        # OCR
        ocr_cfg = table_config.get("ocr", {})
        self.OCR_PROVIDER = ocr_cfg.get("provider", "tencent")
        print("self.OCR_PROVIDER:", self.OCR_PROVIDER)
        self.OCR_TIMEOUT = ocr_cfg.get("timeout", 30)
        self.OCR_MAX_RETRIES = ocr_cfg.get("max_retries", 3)

        # 百度 OCR
        baidu_cfg = table_config.get("baidu_ocr", {})
        self.BAIDU_OCR_API_KEY = baidu_cfg.get("api_key", "")
        self.BAIDU_OCR_SECRET_KEY = baidu_cfg.get("secret_key", "")

        # 腾讯 OCR
        tencent_cfg = table_config.get("tencent_ocr", {})
        self.TENCENT_SECRET_ID = tencent_cfg.get("secret_id", "")
        self.TENCENT_SECRET_KEY = tencent_cfg.get("secret_key", "")
        print("tencent_cfg:", tencent_cfg, self.TENCENT_SECRET_ID)
        self.TENCENT_REGION = tencent_cfg.get("region", "ap-shanghai")

        # 处理参数
        proc_cfg = table_config.get("processing", {})
        self.EXTRACT_ROWS = proc_cfg.get("extract_rows", 10)
        self.EXTRACT_COLS = proc_cfg.get("extract_cols", 3)
        self.MAX_RETRIES = proc_cfg.get("max_retries", 3)
        self.TIMEOUT = proc_cfg.get("timeout", 30)

        # 表格处理器路径（使用 table_processor 配置中的路径）
        paths_cfg = table_config.get("paths", {})

        self.TABLE_TEMP_DIR = get_absolute_path(
            str(self.PROJECT_ROOT), paths_cfg.get("temp_dir", "data/backend/temp_imgs")
        )
        self.TABLE_OBJ_CACHE_DIR = get_absolute_path(
            str(self.PROJECT_ROOT), paths_cfg.get("obj_cache", "data/backend/obj_cache")
        )
        self.TABLE_OCR_RAW_DIR = get_absolute_path(
            str(self.PROJECT_ROOT), paths_cfg.get("ocr_raw", "data/backend/ocr_raw")
        )
        self.TABLE_OCR_FINAL_DIR = get_absolute_path(
            str(self.PROJECT_ROOT), paths_cfg.get("ocr_final", "data/backend/ocr_final")
        )
        self.TABLE_LLM_CACHE_DIR = get_absolute_path(
            str(self.PROJECT_ROOT), paths_cfg.get("llm_cache", "data/backend/llm_cache")
        )
        self.TABLE_OUTPUT_DIR = get_absolute_path(
            str(self.PROJECT_ROOT), paths_cfg.get("outputs", "data/backend/outputs")
        )

        print(f"[Config] 表格处理器输出目录: {self.TABLE_OUTPUT_DIR}")

        self._create_table_dirs()

    def _create_table_dirs(self):
        """创建表格处理需要的目录"""
        create_table_dirs([
            self.TABLE_TEMP_DIR,
            self.TABLE_OUTPUT_DIR,
            self.TABLE_OBJ_CACHE_DIR,
            self.TABLE_OCR_RAW_DIR,
            self.TABLE_OCR_FINAL_DIR,
            self.TABLE_LLM_CACHE_DIR,
        ])

    # -------------------------------------------------------------------------
    # 管理员配置
    # -------------------------------------------------------------------------
    def _setup_admin_config(self):
        """设置管理员凭证（从环境变量读取）"""
        self.SUPER_ADMIN = {
            "username": "admin",
            "password": os.environ.get("SUPER_ADMIN_PASSWORD", "admin123"),  # 本地开发 fallback
            "role": "super_admin",
            "permissions": ["parse", "review", "data"],
        }

        self.AVAILABLE_PERMISSIONS = {
            "parse": "数据解析",
            "review": "数据审核",
            "data": "数据看板",
        }

        print(f"[Config] 超级管理员配置已加载，用户名: {self.SUPER_ADMIN['username']}")

    # -------------------------------------------------------------------------
    # URL 工具方法
    # -------------------------------------------------------------------------
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
        if path.startswith("/api/"):
            return self.get_api_url(path.replace("/api/", ""))
        elif path.startswith("/static/"):
            return self.get_static_url(path.replace("/static/", ""))
        else:
            return f"{self.BACKEND_BASE_URL}{path}"


# ============================================================================
# 全局单例实例（向后兼容：所有已引用 backend.configs.config 的文件无需任何改动）
# ============================================================================
config = Config()

from .table_config import TableConfig

tableconfig = TableConfig(config)

# 常用配置字典（向后兼容）
SERVER_CONFIG = {
    "HOST": config.BACKEND_HOST,
    "PORT": config.BACKEND_PORT,
    "DEBUG": config.DEBUG,
}

FRONTEND_CONFIG = {
    "HOST": config.FRONTEND_HOST,
    "PORT": config.FRONTEND_PORT,
    "BASE_URL": config.FRONTEND_BASE_URL,
}

FILE_PATHS = {
    "UPLOAD_FOLDER": config.UPLOAD_FOLDER,
    "EXCEL_DATA_FOLDER": config.EXCEL_DATA_FOLDER,
    "JOINED_TABLES_FOLDER": config.JOINED_TABLES_FOLDER,
    "PNG_OUTPUT_ROOT": config.PNG_OUTPUT_ROOT,
    "MAIN_ROOT": config.MAIN_ROOT,
}

API_PATHS = {
    "BASE_PREFIX": config.API_PREFIX,
    "STATIC_PREFIX": config.STATIC_PREFIX,
    "UPLOAD_PREFIX": config.UPLOAD_PREFIX,
}

__all__ = [
    "config",
    "TableConfig",
    "tableconfig",
    "SERVER_CONFIG",
    "FRONTEND_CONFIG",
    "FILE_PATHS",
    "API_PATHS",
]

# 快速测试
if __name__ == "__main__":
    c = Config()
    tc = tableconfig
    print(f"OCR原始数据路径: {tc.get_ocr_raw_path('test-uuid', 1)}")
