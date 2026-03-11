# 文件：backend/core/services/table_processor/cache_manager.py
"""
缓存管理工具 - 用于手动清理和查看缓存
"""

import sys
from pathlib import Path

# 设置项目根路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.table_processor.cache_gateway import (
    clear_cache, get_cache_stats, clear_old_cache, delete, get
)


def show_stats():
    """显示缓存统计信息"""
    print("📊 缓存统计信息:")
    print("-" * 50)

    try:
        stats = get_cache_stats()

        print(f"总缓存记录数: {stats['total_records']}")
        print(f"总API调用成本: ${stats['total_cost_usd']:.4f}")

        # 显示所有实际provider（关键！）
        if stats['all_providers']:
            print(f"实际Provider列表: {', '.join(stats['all_providers'])}")
        else:
            print("实际Provider列表: 无")
        print()

        if stats['providers']:
            print("按提供商统计:")
            for provider_info in stats['providers']:
                print(f"  {provider_info['provider']}:")
                print(f"    记录数: {provider_info['record_count']}")
                print(f"    总费用: ${provider_info['total_cost']:.4f}")
                if provider_info['oldest']:
                    print(f"    最早记录: {provider_info['oldest'][:10]}")
                print()
        else:
            print("暂无缓存数据")
    except Exception as e:
        print(f"❌ 获取统计信息失败: {str(e)}")


def clear_all_cache():
    """清除所有缓存"""
    print("⚠️  即将清除所有缓存，确认吗？(y/N)")
    confirm = input().strip().lower()

    if confirm == 'y':
        try:
            count = clear_cache("all")
            print(f"✅ 已清除 {count} 条缓存记录")
        except Exception as e:
            print(f"❌ 清除缓存失败: {str(e)}")
    else:
        print("❌ 操作已取消")


def clear_by_type():
    """按类型清除缓存"""
    print("选择要清除的缓存类型:")
    print("1. OCR缓存 (baidu, tencent等)")
    print("2. LLM缓存 (openai, claude等)")
    print("3. 所有缓存")
    print("0. 返回主菜单")

    choice = input("请输入选项 (0-3): ").strip()

    try:
        if choice == "1":
            count = clear_cache("ocr")
            print(f"✅ 已清除 {count} 条OCR缓存记录")
        elif choice == "2":
            count = clear_cache("llm")
            print(f"✅ 已清除 {count} 条LLM缓存记录")
        elif choice == "3":
            clear_all_cache()
        elif choice == "0":
            return
        else:
            print("❌ 无效选项")
    except Exception as e:
        print(f"❌ 清除缓存失败: {str(e)}")


def clear_old():
    """清除旧缓存"""
    try:
        days_input = input("输入要保留的天数 (默认7): ").strip()
        if not days_input:
            days = 7
        else:
            days = int(days_input)

        if days <= 0:
            print("❌ 天数必须大于0")
            return

        confirm = input(f"确认清除 {days} 天前的旧缓存吗？(y/N): ").strip().lower()
        if confirm == 'y':
            count = clear_old_cache(days)
            print(f"✅ 已清除 {count} 条超过 {days} 天的缓存记录")
        else:
            print("❌ 操作已取消")
    except ValueError:
        print("❌ 请输入有效数字")
    except Exception as e:
        print(f"❌ 清除旧缓存失败: {str(e)}")


def delete_specific():
    """删除特定缓存记录"""
    print("删除特定缓存记录")
    md5 = input("请输入md5值: ").strip()
    provider = input("请输入提供商: ").strip()

    if not md5 or not provider:
        print("❌ md5和提供商不能为空")
        return

    try:
        # 先检查是否存在
        record = get(md5, provider)
        if not record:
            print("❌ 未找到该缓存记录")
            return

        print(f"找到缓存记录:")
        print(f"  S3 Key: {record.s3_key}")
        print(f"  费用: ${record.cost_usd:.4f}")
        print(f"  令牌数: 输入{record.prompt_tokens}/输出{record.completion_tokens}")

        confirm = input("确认删除吗？(y/N): ").strip().lower()
        if confirm == 'y':
            delete(md5, provider)
            print("✅ 缓存记录已删除")
        else:
            print("❌ 操作已取消")
    except Exception as e:
        print(f"❌ 删除缓存记录失败: {str(e)}")


def test_connection():
    """测试数据库连接"""
    print("测试数据库连接...")
    try:
        stats = get_cache_stats()
        print(f"✅ 连接成功！数据库中有 {stats['total_records']} 条记录")
        return True
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        return False


def main():
    """主菜单"""
    # 先测试数据库连接
    if not test_connection():
        print("请检查数据库配置或确保表已创建")
        print("可以使用以下命令初始化表:")
        print("  from backend.core.services.table_processor.cache_gateway import ensure_table")
        print("  ensure_table()")
        return

    while True:
        print("\n" + "=" * 50)
        print("📁 缓存管理系统")
        print("=" * 50)
        print("1. 查看缓存统计")
        print("2. 按类型清除缓存")
        print("3. 清除所有缓存")
        print("4. 清除旧缓存")
        print("5. 删除特定缓存记录")
        print("0. 退出")
        print("-" * 50)

        choice = input("请选择操作 (0-5): ").strip()

        if choice == "0":
            print("👋 再见！")
            break
        elif choice == "1":
            show_stats()
        elif choice == "2":
            clear_by_type()
        elif choice == "3":
            clear_all_cache()
        elif choice == "4":
            clear_old()
        elif choice == "5":
            delete_specific()
        else:
            print("❌ 无效选项，请重新选择")

        if choice != "0":
            input("\n按回车键返回主菜单...")


if __name__ == "__main__":
    main()