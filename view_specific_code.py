#!/usr/bin/env python3
"""
查看具体代码位置 - 第二步：查看不修改
作用：显示需要修改的具体代码行，不进行任何修改
"""

from pathlib import Path


def view_specific_code():
    """查看具体的代码位置"""
    print("🔍 第二步：查看具体代码位置")
    print("⚠️  注意：这只是查看，不会修改任何文件")

    project_root = Path(__file__).parent

    # 重点关注的文件（根据第一步分析结果）
    focus_files = [
        "backend/models/database_manager.py",
        "backend/services/non_financial_table_service.py",
        "backend/services/table_llm_service.py",
        "backend/api/file.py",
        "backend/api/search_save_services.py"
    ]

    found_files = []

    for file_path in focus_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"\n📄 文件: {file_path}")
            print("-" * 60)

            content = full_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            # 查找包含 OldDatabaseManager 的行
            old_manager_lines = []
            for i, line in enumerate(lines, 1):
                if "OldDatabaseManager" in line:
                    old_manager_lines.append((i, line.strip()))

            if old_manager_lines:
                found_files.append(file_path)
                print(f"🔍 找到 {len(old_manager_lines)} 处 OldDatabaseManager 使用:")
                for line_num, line_content in old_manager_lines:
                    print(f"   行 {line_num}: {line_content}")

                    # 显示上下文
                    start = max(0, line_num - 2)
                    end = min(len(lines), line_num + 2)
                    print("   上下文:")
                    for j in range(start, end):
                        marker = ">>>" if j == line_num - 1 else "   "
                        print(f"      {marker} {j + 1}: {lines[j]}")
                    print()
            else:
                print("✅ 未找到 OldDatabaseManager 使用")

    return found_files


def generate_migration_plan(found_files):
    """生成迁移计划"""
    print("\n" + "=" * 80)
    print("📋 迁移计划建议")
    print("=" * 80)

    if not found_files:
        print("✅ 没有发现需要迁移的文件")
        return

    print(f"🎯 发现 {len(found_files)} 个文件需要迁移:")
    for i, file_path in enumerate(found_files, 1):
        print(f"{i}. {file_path}")

    print(f"\n💡 建议迁移顺序:")
    print("1. 先迁移简单的、非核心的文件")
    print("2. 逐个文件迁移，迁移后立即测试")
    print("3. 最后迁移核心业务文件")

    print(f"\n⚠️  重要提醒:")
    print("   - 每次只迁移一个文件")
    print("   - 迁移前备份原文件")
    print("   - 迁移后立即测试功能")


if __name__ == "__main__":
    print("🎯 第二步：查看具体代码（不修改）")
    found_files = view_specific_code()
    generate_migration_plan(found_files)

    print(f"\n✅ 查看完成！下一步：手动迁移单个文件")
    print("💡 建议从最简单的文件开始迁移")