# table_processor/_config_shim.py
"""适配器文件 - 转发到公共配置"""
from backend.configs.config import tableconfig

# 保持原有接口不变
settings = tableconfig

# 可选：添加警告日志
import warnings
warnings.warn("_config_shim.py is deprecated, use backend.utils.config.tableconfig instead")