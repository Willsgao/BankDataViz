"""
全局状态共享模块
"""

# 全局任务状态存储
TASK_RESULTS = {}
PROCESSING_STATUS = {}

# 全局处理器实例
_table_processor_instance = None
_non_financial_table_service = None