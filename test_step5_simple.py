#!/usr/bin/env python3
"""
最终测试脚本 - 最简版本
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

print("🎯 数据库统一管理器 - 最终测试")

try:
    # 直接导入并测试核心功能
    from database.export import unified_db_manager

    print("✅ 统一管理器导入成功")
    print(f"   数据库路径: {unified_db_manager.db_path}")

    # 测试基本功能
    health_info = unified_db_manager.check_database_health()
    print(f"✅ 数据库健康检查: {len(health_info['tables'])} 个表")

    # 测试文件统计
    stats = unified_db_manager.get_file_statistics()
    if stats:
        print(f"✅ 文件统计: {stats['total_files']} 个文件")

    print("\n🎉 所有核心功能测试通过！")
    print("📋 下一步：查看 DATABASE_MIGRATION_GUIDE.md 开始迁移")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()