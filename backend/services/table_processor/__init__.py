# table_processor/__init__.py

# 只暴露最顶层的类，隐藏内部实现细节
from .end_to_end_pipeline import TableReconstructionPipeline
from .llm_table_structure_parser import EnhancedFinancialTableAnalyzer
from .table_rebuilder import TableReconstructor

# 可选：提供快捷创建函数
def create_processor(config=None):
    """创建表格处理器的快捷方式"""
    return TableReconstructionPipeline(config or {})

# 定义外部可以导入的内容
__all__ = [
    'TableReconstructionPipeline',
    'EnhancedFinancialTableAnalyzer',
    'TableReconstructor',
    'create_processor'
]