"""
安全迁移脚本 - 提供具体的迁移操作
"""

import os
import shutil
from pathlib import Path

# 修复导入：使用相对导入
from .migration_tool import migration_tool


def safe_migration_demo():
    """
    安全迁移演示 - 不实际修改文件，只展示操作
    """
    print("🛡️ 安全迁移演示开始...")

    # 1. 生成迁移报告
    print("\n1. 生成迁移报告...")
    report = migration_tool.generate_migration_report()

    print(f"📊 发现 {len(report['summary']['files_need_migration'])} 个文件需要迁移")
    for file in report['summary']['files_need_migration']:
        print(f"   - {file}")

    # 2. 创建迁移计划
    print("\n2. 创建迁移计划...")
    plan = migration_tool.create_migration_plan()

    # 3. 创建迁移指南
    print("\n3. 创建迁移指南...")
    guide_path = migration_tool.create_migration_guide()

    print(f"📖 迁移指南已创建: {guide_path}")

    # 4. 演示迁移操作（不实际执行）
    print("\n4. 迁移操作演示（安全模式）...")
    for step in plan["steps"]:
        print(f"📝 文件: {step['file']}")
        print(f"   当前导入: {', '.join(step['current_imports'])}")
        print(f"   建议修改: {', '.join(step['suggested_changes'])}")
        print(f"   风险等级: {step['risk_level']}")
        print("   🛡️ 安全模式: 只显示，不实际修改")
        print()

    print("✅ 安全迁移演示完成")
    print("💡 实际迁移时，请按照迁移指南逐步操作")


def check_readiness():
    """检查迁移准备状态"""
    print("🔍 检查迁移准备状态...")

    # 简化检查，避免复杂的依赖
    checks = {
        "项目根目录存在": Path(__file__).parent.parent.parent.exists(),
        "数据库文件存在": Path(migration_tool.project_root / "data/database.db").exists(),
        "迁移工具可用": True,  # 如果能运行到这里，说明工具可用
    }

    all_passed = all(checks.values())

    print("📋 准备状态检查结果:")
    for check, passed in checks.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {check}: {status}")

    return all_passed


if __name__ == "__main__":
    print("=" * 60)
    print("🛡️ 数据库统一管理器安全迁移工具")
    print("=" * 60)

    if check_readiness():
        print("\n🎯 所有检查通过，可以开始迁移")
        safe_migration_demo()
    else:
        print("\n⚠️ 部分检查未通过，请先解决问题再迁移")