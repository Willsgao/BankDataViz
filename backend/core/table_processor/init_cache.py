# 文件：backend/core/services/table_processor/init_cache.py
"""
初始化缓存系统 - 创建数据库表
"""

import sys
from pathlib import Path

# 设置项目根路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def init_cache_system():
    """初始化缓存系统"""
    print("🔧 初始化缓存系统...")

    try:
        from backend.core.table_processor.cache_gateway import ensure_table
        from backend.configs.config import tableconfig

        print(f"数据库URL: {tableconfig.CACHE_URL}")

        ensure_table()
        print("✅ 缓存表创建成功")

        # 测试连接
        from backend.core.table_processor.cache_gateway import get_cache_stats
        try:
            stats = get_cache_stats()
            print(f"当前缓存记录数: {stats['total_records']}")
        except:
            print("⚠️  缓存表已创建，但暂无数据")

    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    init_cache_system()