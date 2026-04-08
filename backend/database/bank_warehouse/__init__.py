# -*- coding: utf-8 -*-
"""
银行数据仓库模块

包含：
- bank_schema: 表结构定义
- bank_migrator: 数据库迁移工具
- bank_warehouse: 数据仓库管理器

用法：
    from backend.database.bank_warehouse import BankWarehouseManager

    # 初始化数据库
    warehouse = BankWarehouseManager()
    warehouse.init_database()

    # 保存银行
    bank_id = warehouse.save_bank({
        'bank_code': 'ICBC',
        'bank_name': '中国工商银行',
        'bank_type': '国有大型银行'
    })
"""

from .bank_schema import (
    TableNames,
    BankType,
    ReportType,
    ReportStatus,
    ProcessingStatus,
    ChangeType,
    MemberLevel,
    ALL_TABLES,
)
from .bank_warehouse import BankWarehouseManager

__all__ = [
    'TableNames',
    'BankType',
    'ReportType',
    'ReportStatus',
    'ProcessingStatus',
    'ChangeType',
    'MemberLevel',
    'ALL_TABLES',
    'BankWarehouseManager',
]
