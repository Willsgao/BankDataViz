# -*- coding:utf-8 -*-
"""
极简增量处理模块
文件：backend/src/services/incremental_processor/__init__.py
"""

from .simple_incremental_processor import SimpleIncrementalProcessor, incremental_processor
from .incremental_service import IncrementalProcessingService, incremental_service
from .api_wrapper import IncrementalAPIWrapper, incremental_api_wrapper

__all__ = [
    'SimpleIncrementalProcessor',
    'IncrementalProcessingService',
    'IncrementalAPIWrapper',
    'incremental_processor',
    'incremental_service',
    'incremental_api_wrapper'
]

print("✅✅ 极简增量处理模块加载完成")