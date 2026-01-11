#!/usr/bin/env python3
"""
第二步：迁移 backend/api/search_save_services.py
作用：迁移第二个文件，保持相同的安全流程
"""

from pathlib import Path
import shutil
from datetime import datetime


def create_file_backup(file_path):
    """创建文件备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.parent / f"{file_path.name}.backup.{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 备份已创建: {backup_path}")
    return backup_path


def analyze_search_save_services():
    """分析 backend/api/search_save_services.py 文件"""
    print("🎯 第二步：分析 backend/api/search_save_services.py 文件")
    print("⚠️  注意：这只是分析，不会修改任何文件")

    project_root = Path(__file__).parent
    file_path = project_root / "backend" / "api" / "search_save_services.py"

    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return None

    print(f"📄 分析文件: {file_path}")
    print("-" * 60)

    # 读取文件内容
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    # 查找需要修改的行
    modifications = []

    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()

        if "OldDatabaseManager" in line_stripped:
            print(f"🔍 第 {i} 行发现 OldDatabaseManager:")
            print(f"   代码: {line_stripped}")

            if "from backend.models.unified_db import DatabaseManager as OldDatabaseManager" in line_stripped:
                modifications.append({
                    'line': i,
                    'type': 'import',
                    'old': line_stripped,
                    'new': "from backend.database.export import OldDatabaseManagerAdapter",
                    'description': '导入语句'
                })
                print("   📝 类型: 导入语句")

            elif "db = OldDatabaseManager(DATABASE)" in line_stripped:
                modifications.append({
                    'line': i,
                    'type': 'instantiation',
                    'old': line_stripped,
                    'new': "db = OldDatabaseManagerAdapter(DATABASE)",
                    'description': '实例化语句'
                })
                print("   📝 类型: 实例化语句")

            print()

    return {
        'file_path': file_path,
        'modifications': modifications,
        'total_lines': len(lines),
        'content': content,
        'lines': lines
    }


def generate_migration_guide(analysis_result):
    """生成迁移指南"""
    if not analysis_result:
        return

    file_path = analysis_result['file_path']
    modifications = analysis_result['modifications']
    content = analysis_result['content']
    lines = analysis_result['lines']

    print("📋 第二步迁移指南")
    print("=" * 60)
    print(f"📄 目标文件: {file_path}")
    print(f"📏 文件总行数: {analysis_result['total_lines']}")
    print(f"🔧 需要修改: {len(modifications)} 处")
    print()

    if not modifications:
        print("✅ 无需修改")
        return

    print("🔍 具体修改内容:")
    print("-" * 40)
    for i, mod in enumerate(modifications, 1):
        print(f"{i}. 第 {mod['line']} 行 ({mod['description']}):")
        print(f"   旧代码: {mod['old']}")
        print(f"   新代码: {mod['new']}")
        print()

    print("🛠️ 手动执行步骤:")
    print("-" * 40)
    print("1. 备份原文件（重要！）")
    backup_path = create_file_backup(file_path)
    print()

    print("2. 使用文本编辑器打开文件:")
    print(f"   文件: {file_path}")
    print()

    print("3. 修改以下行:")
    for i, mod in enumerate(modifications, 1):
        print(f"   {i}. 找到第 {mod['line']} 行:")
        print(f"      将: {mod['old']}")
        print(f"      改为: {mod['new']}")
        print()

    print("4. 保存文件")
    print()

    print("5. 测试修改是否正确:")
    print("   - 启动应用")
    print("   - 测试搜索保存功能")
    print("   - 确保没有错误")
    print()

    print("⚠️  重要提醒:")
    print("   - 修改前务必备份")
    print("   - 修改后立即测试")
    print("   - 确认无误后再进行下一步")

    # 显示修改预览
    print("\n📋 修改预览:")
    print("-" * 40)

    # 模拟修改后的内容
    new_content = content
    for mod in modifications:
        new_content = new_content.replace(mod['old'], mod['new'])

    # 显示关键区域
    old_lines = content.split('\n')
    new_lines = new_content.split('\n')

    for mod in modifications:
        line_num = mod['line'] - 1
        start = max(0, line_num - 2)
        end = min(len(old_lines), line_num + 3)

        print(f"第 {mod['line']} 行修改:")
        for j in range(start, end):
            if j == line_num:
                print(f"  - {old_lines[j]}")
                print(f"  ↓ 修改为 ↓")
                print(f"  + {new_lines[j]}")
            else:
                print(f"    {old_lines[j]}")
        print()


def check_current_state():
    """检查当前文件状态"""
    print("🔍 检查当前文件状态...")
    project_root = Path(__file__).parent
    file_path = project_root / "backend" / "api" / "search_save_services.py"

    if not file_path.exists():
        print("❌ 文件不存在")
        return False

    content = file_path.read_text(encoding='utf-8')

    # 检查是否已经修改
    if "from backend.database.export import OldDatabaseManagerAdapter" in content:
        print("⚠️  文件可能已经部分修改")
        return True
    else:
        print("✅ 文件需要修改")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("🎯 数据库迁移 - 第二步")
    print("📝 迁移 backend/api/search_save_services.py")
    print("=" * 70)

    # 检查当前状态
    if check_current_state():
        print("💡 文件可能已经修改过，请先检查")

    # 分析文件
    analysis_result = analyze_search_save_services()

    # 生成迁移指南
    generate_migration_guide(analysis_result)

    print("\n✅ 第二步完成！")
    print("💡 下一步：按照指南手动修改 backend/api/search_save_services.py")
    print("📋 修改后测试搜索保存功能是否正常")
    print()
    print("📊 迁移进度: 1/4 个文件完成")
    print("🎯 剩余文件: 3 个")


if __name__ == "__main__":
    main()