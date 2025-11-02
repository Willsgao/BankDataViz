
from backend.llm_services.state_manager import state_manager


def get_table_processor():
    """获取金融表格处理器"""
    return state_manager.get_table_processor()

def get_non_financial_table_service():
    """获取普通表格服务单例实例"""
    return state_manager.get_non_financial_table_service()

def get_appropriate_processor(table_type=None):
    """根据表格类型获取合适的处理器"""
    return state_manager.get_appropriate_processor(table_type)


