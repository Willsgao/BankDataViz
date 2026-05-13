# -*- coding:utf-8 -*-
"""
数据访问层 (Data Access Layer)

核心目标：解耦数据来源，支持切换数据源（Excel/数据库）而不影响上层代码。

架构：
- DataSource (ABC): 抽象基类，定义统一接口
- ExcelDataSource: Excel文件数据源（当前实现）
- DatabaseDataSource: 数据库数据源（预留，未来扩展）
- DataSourceFactory: 工厂类，根据配置创建数据源

使用方式：
    from backend.services.data_access_layer import DataSourceFactory
    
    # 创建数据源
    ds = DataSourceFactory.create('excel', {'base_path': '/path/to/files'})
    
    # 统一接口调用
    sheets = ds.get_sheet_names(file_id)
    data = ds.get_sheet_data(file_id, sheet_name)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import os


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class FileInfo:
    """档案信息"""
    id: str
    name: str
    source_path: str
    source_type: str = 'excel'  # 'excel' or 'database'
    created_at: Optional[str] = None
    status: str = 'completed'  # pending, processing, completed, failed


@dataclass
class SheetSummary:
    """
    Sheet摘要 - 用于前端展示
    """
    name: str
    row_count: int
    col_count: int
    header_preview: List[List[str]] = field(default_factory=list)  # 前3行表头
    row_preview: List[Dict[str, str]] = field(default_factory=list)  # 前3行数据


@dataclass
class SheetData:
    """
    Sheet完整数据 - 用于规则引擎
    """
    name: str
    headers: List[List[str]] = field(default_factory=list)  # 多行表头
    rows: List[Dict[str, Any]] = field(default_factory=list)  # 数据行，key为列索引或列名
    
    # 原始数据（保留，用于复杂场景）
    raw_ws: Any = None  # 原始worksheet对象（openpyxl.Worksheet）
    
    @property
    def row_count(self) -> int:
        return len(self.rows) if self.rows else 0
    
    @property
    def col_count(self) -> int:
        if self.headers and self.headers[0]:
            return len(self.headers[0])
        if self.rows and self.rows[0]:
            return len(self.rows[0])
        return 0


# =============================================================================
# 抽象接口
# =============================================================================

class DataSource(ABC):
    """
    数据源抽象基类
    
    所有数据源必须实现此接口，规则引擎只依赖此接口，不关心数据从哪来。
    """
    
    @abstractmethod
    def get_file_list(self) -> List[FileInfo]:
        """获取档案列表"""
        pass
    
    @abstractmethod
    def get_file_info(self, file_id: str) -> Optional[FileInfo]:
        """获取指定档案信息"""
        pass
    
    @abstractmethod
    def get_sheet_names(self, file_id: str) -> List[str]:
        """获取某个档案的所有Sheet名称"""
        pass
    
    @abstractmethod
    def get_sheet_summary(self, file_id: str, sheet_name: str) -> SheetSummary:
        """获取Sheet摘要（用于前端预览）"""
        pass
    
    @abstractmethod
    def get_sheet_data(self, file_id: str, sheet_name: str) -> SheetData:
        """获取Sheet完整数据（用于规则引擎）"""
        pass
    
    @abstractmethod
    def get_all_sheets_data(self, file_id: str) -> List[SheetData]:
        """获取档案所有Sheet数据（批量获取，用于规则匹配）"""
        pass
    
    @abstractmethod
    def get_excel_path(self, file_id: str) -> str:
        """获取Excel文件路径（用于兼容现有代码）"""
        pass


# =============================================================================
# 工厂类
# =============================================================================

class DataSourceFactory:
    """
    数据源工厂
    
    根据配置创建对应的数据源实例。
    
    使用示例：
        # 创建Excel数据源
        ds = DataSourceFactory.create('excel', {'base_path': '/path/to/files'})
        
        # 创建数据库数据源（未来）
        ds = DataSourceFactory.create('database', {'host': 'localhost', 'port': 3306})
    """
    
    _sources: Dict[str, type] = {}
    _default_source: Optional[DataSource] = None
    
    @classmethod
    def register(cls, source_type: str, source_class: type):
        """注册数据源类型"""
        cls._sources[source_type] = source_class
    
    @classmethod
    def create(cls, source_type: str, config: Dict[str, Any] = None) -> DataSource:
        """
        创建数据源实例
        
        Args:
            source_type: 数据源类型 ('excel', 'database')
            config: 数据源配置
            
        Returns:
            DataSource 实例
        """
        if source_type not in cls._sources:
            raise ValueError(
                f"不支持的数据源类型: {source_type}。"
                f"可选: {list(cls._sources.keys())}"
            )
        
        source_class = cls._sources[source_type]
        return source_class(**(config or {}))
    
    @classmethod
    def set_default(cls, source: DataSource):
        """设置默认数据源"""
        cls._default_source = source
    
    @classmethod
    def get_default(cls) -> Optional[DataSource]:
        """获取默认数据源"""
        return cls._default_source


# =============================================================================
# 注册内置数据源
# =============================================================================

# 注意：这里只是导入注册，实际注册在对应模块中
# from backend.services.dal.excel_source import ExcelDataSource
# DataSourceFactory.register('excel', ExcelDataSource)
