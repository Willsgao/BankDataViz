# -*- coding:utf-8 -*-
"""
TableConfig：表格处理专用配置类
支持独立初始化（无 Config 实例时）或从 Config 实例委托初始化

所有路径均基于 Config.PROJECT_ROOT，绝对路径存储，
不依赖其他模块的运行时状态。
"""
import os
from pathlib import Path

from ._paths import get_absolute_path, create_table_dirs, create_backend_dirs


class TableConfig:
    """表格处理配置类 - 所有路径基于主配置的 PROJECT_ROOT"""

    def __init__(self, config=None):
        """
        Args:
            config: Config 实例。若传入，则从 Config 委托初始化；
                   否则独立初始化（使用环境变量 + 默认值）。
        """
        self.config = config
        self.PROJECT_ROOT = config.PROJECT_ROOT if config else Path(
            os.getenv("PROJECT_ROOT", os.getcwd())
        ).resolve()

        if self.config:
            self._init_from_main_config()
        else:
            self._init_from_env_and_defaults()

        self._create_dirs()

    # -------------------------------------------------------------------------
    # 初始化分支
    # -------------------------------------------------------------------------
    def _init_from_main_config(self):
        """从主 Config 实例委托读取（推荐方式）"""
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

        # 路径配置 - 使用表格处理器自己的目录
        self.temp_dir = self.config.TABLE_TEMP_DIR
        self.output_dir = self.config.TABLE_OUTPUT_DIR
        self.obj_cache_dir = self.config.TABLE_OBJ_CACHE_DIR
        self.ocr_raw_dir = self.config.TABLE_OCR_RAW_DIR
        self.ocr_final_dir = self.config.TABLE_OCR_FINAL_DIR
        self.llm_cache_dir = self.config.TABLE_LLM_CACHE_DIR

        print(f"[TableConfig] 输出目录设置为: {self.output_dir}")

        self._init_env_vars()

    def _init_from_env_and_defaults(self):
        """从环境变量和默认值独立初始化（无 Config 时的 fallback）"""
        # LLM配置
        self.llm_api_key = os.environ.get("LLM_API_KEY", "")
        self.llm_base_url = "https://ark.cn-beijing.volces.com/api/v3"
        self.llm_model_name = "doubao-1-5-vision-pro-32k-250115"

        # OCR配置
        self.ocr_provider = "tencent"
        self.ocr_api_key = os.environ.get("BAIDU_OCR_API_KEY", "")
        self.ocr_secret_key = os.environ.get("BAIDU_OCR_SECRET_KEY", "")
        self.tencent_secret_id = os.environ.get("TENCENT_SECRET_ID", "")
        self.tencent_secret_key = os.environ.get("TENCENT_SECRET_KEY", "")
        self.tencent_region = "ap-shanghai"

        # 处理配置
        self._ocr_timeout = 30
        self._ocr_max_retries = 3
        self.extract_rows = 10
        self.extract_cols = 3
        self.max_retries = 3
        self.timeout = 30

        # 路径配置
        print(f"[TableConfig] 使用项目根目录: {self.PROJECT_ROOT}")

        data_backend_dir = create_backend_dirs(str(self.PROJECT_ROOT))

        # 输出目录（环境变量优先，均转为绝对路径）
        output_dir_env = os.environ.get("OUTPUT_DIR")
        if output_dir_env:
            self.output_dir = get_absolute_path(str(self.PROJECT_ROOT), output_dir_env)
        else:
            self.output_dir = os.path.join(data_backend_dir, "outputs")

        self.temp_dir = get_absolute_path(
            str(self.PROJECT_ROOT), os.environ.get("TEMP_DIR") or os.path.join(data_backend_dir, "temp_imgs")
        )
        self.obj_cache_dir = get_absolute_path(
            str(self.PROJECT_ROOT), os.environ.get("OBJ_CACHE_DIR") or os.path.join(data_backend_dir, "obj_cache")
        )
        self.ocr_raw_dir = get_absolute_path(
            str(self.PROJECT_ROOT), os.environ.get("OCR_RAW_DIR") or os.path.join(data_backend_dir, "ocr_raw")
        )
        self.ocr_final_dir = get_absolute_path(
            str(self.PROJECT_ROOT), os.environ.get("OCR_FINAL_DIR") or os.path.join(data_backend_dir, "ocr_final")
        )
        self.llm_cache_dir = get_absolute_path(
            str(self.PROJECT_ROOT), os.environ.get("LLM_CACHE_DIR") or os.path.join(data_backend_dir, "llm_cache")
        )

        self._init_env_vars()

    def _init_env_vars(self):
        """初始化环境变量相关配置"""
        # OCR / LLM 调试开关
        self.debug_ocr = os.environ.get("OCR_DEBUG", "false").lower() == "true"
        self.debug_ocr_keep_mb = int(os.environ.get("OCR_DEBUG_KEEP_MB", "0"))
        self.debug_llm = os.environ.get("LLM_DEBUG", "false").lower() == "true"

        # 对象存储
        self.OBJECT_STORE = os.environ.get("OBJECT_STORE", "local")
        local_store = os.environ.get("LOCAL_OBJECT_STORE")
        self.LOCAL_OBJECT_STORE = (
            get_absolute_path(str(self.PROJECT_ROOT), local_store)
            if local_store else self.obj_cache_dir
        )
        self.OBJECT_STORE_BUCKET = os.environ.get("OBJECT_STORE_BUCKET", "")

        # 强制刷新开关
        self.OCR_FORCE_REFRESH = os.environ.get("OCR_FORCE_REFRESH", "false").lower() == "true"
        self.LLM_FORCE_REFRESH = os.environ.get("LLM_FORCE_REFRESH", "false").lower() == "true"

        # 数据库连接 URL
        env_db_url = os.environ.get("CACHE_URL")
        if env_db_url:
            self.CACHE_URL = env_db_url
        else:
            cache_dir = Path(self.PROJECT_ROOT) / "data" / "backend" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.CACHE_URL = f"sqlite:///{cache_dir.resolve() / 'api_cache.db'}"

        print(f"[TableConfig] 数据库连接URL: {self.CACHE_URL}")

    def _create_dirs(self):
        """创建必要的目录"""
        dirs = []
        for attr in ("temp_dir", "output_dir", "obj_cache_dir",
                     "ocr_raw_dir", "ocr_final_dir", "llm_cache_dir",
                     "LOCAL_OBJECT_STORE"):
            val = getattr(self, attr, None)
            if val:
                dirs.append(val)

        create_table_dirs(dirs)

    # -------------------------------------------------------------------------
    # 路径查询方法
    # -------------------------------------------------------------------------
    def get_absolute_ocr_raw_dir(self):
        return getattr(self, "ocr_raw_dir", "")

    def get_absolute_ocr_final_dir(self):
        return getattr(self, "ocr_final_dir", "")

    def get_ocr_raw_path(self, pdf_uuid, page_num, filename=None):
        return self.get_pdf_path(
            self.ocr_raw_dir, pdf_uuid,
            filename or f"page_{page_num}_raw.json"
        )

    def get_ocr_final_path(self, pdf_uuid, page_num, filename=None):
        return self.get_pdf_path(
            self.ocr_final_dir, pdf_uuid,
            filename or f"page_{page_num}_final.json"
        )

    def get_llm_cache_path(self, pdf_uuid, page_num, filename=None):
        return self.get_pdf_path(
            self.llm_cache_dir, pdf_uuid,
            filename or f"page_{page_num}_analysis.pkl"
        )

    def get_obj_cache_path(self, pdf_uuid, cache_type, page_num, filename=None):
        if cache_type == "ocr":
            base_dir = Path(self.obj_cache_dir) / "ocr"
        elif cache_type == "llm":
            base_dir = Path(self.obj_cache_dir) / "llm"
        else:
            base_dir = Path(self.obj_cache_dir) / cache_type

        return self.get_pdf_path(str(base_dir), pdf_uuid,
                                 filename or f"page_{page_num}.pkl")

    def get_output_path(self, pdf_uuid, filename=None):
        return self.get_pdf_path(self.output_dir, pdf_uuid, filename)

    def get_pdf_path(self, base_dir, pdf_uuid, filename=None):
        """获取基于 PDF UUID 的完整路径（绝对路径）"""
        if not pdf_uuid:
            raise ValueError("pdf_uuid is required")

        base_dir_path = Path(base_dir)
        pdf_dir = base_dir_path / pdf_uuid
        pdf_dir.mkdir(parents=True, exist_ok=True)

        if filename:
            return str(pdf_dir / filename)
        return str(pdf_dir)

    # -------------------------------------------------------------------------
    # 属性访问器（兼容性：支持大写属性名访问）
    # -------------------------------------------------------------------------
    @property
    def OCR_RAW_DIR(self):
        return self.get_absolute_ocr_raw_dir()

    @property
    def OCR_FINAL_DIR(self):
        return self.get_absolute_ocr_final_dir()

    @property
    def ocr_timeout(self):
        return getattr(self, "_ocr_timeout", 30)

    @ocr_timeout.setter
    def ocr_timeout(self, value):
        self._ocr_timeout = value

    @property
    def OCR_TIMEOUT(self):
        return self.ocr_timeout

    @property
    def ocr_max_retries(self):
        return getattr(self, "_ocr_max_retries", 3)

    @ocr_max_retries.setter
    def ocr_max_retries(self, value):
        self._ocr_max_retries = value

    @property
    def OCR_MAX_RETRIES(self):
        return self.ocr_max_retries

    @property
    def LLM_CACHE_DIR(self):
        return getattr(self, "llm_cache_dir", "")

    # 大写兼容性属性（映射到小写内部属性）
    @property
    def OCR_PROVIDER(self):
        return self.ocr_provider

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
