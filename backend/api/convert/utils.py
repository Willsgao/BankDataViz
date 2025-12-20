"""
工具函数模块
"""
from datetime import datetime


def calculate_duration(start_time_str, end_time_str):
    """计算处理时长"""
    if not start_time_str or not end_time_str:
        return "未知"

    try:
        start = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        duration = end - start
        return f"{duration.total_seconds():.1f}秒"
    except:
        return "未知"