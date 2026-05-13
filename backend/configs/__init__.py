# -*- coding:utf-8 -*-
"""
backend.configs 包

向后兼容导出：所有引用 "from backend.configs import config, tableconfig, ..."
的文件均可正常工作。
"""
from .config import (
    config,
    TableConfig,
    tableconfig,
    SERVER_CONFIG,
    FRONTEND_CONFIG,
    FILE_PATHS,
    API_PATHS,
)

__all__ = [
    "config",
    "TableConfig",
    "tableconfig",
    "SERVER_CONFIG",
    "FRONTEND_CONFIG",
    "FILE_PATHS",
    "API_PATHS",
]
