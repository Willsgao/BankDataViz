# backend/utils/migrate_db.py
import os
import shutil
from pathlib import Path
from backend.utils.constants import DATABASE as NEW_DB_PATH


def migrate_if_needed():
    """如果需要，迁移旧数据库到新位置"""
    old_locations = [
        'data/database.db',
        'database.db',
        'backend/database.db',
    ]

    new_path = Path(NEW_DB_PATH)

    # 如果新数据库已存在，不迁移
    if new_path.exists():
        print(f"✅ 目标数据库已存在: {new_path}")
        return True

    # 查找旧数据库
    for old_path in old_locations:
        old_path_obj = Path(old_path)
        if old_path_obj.exists():
            print(f"🔧 发现旧数据库: {old_path}")
            print(f"🔧 迁移到: {new_path}")

            # 确保目标目录存在
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # 复制数据库文件
            shutil.copy2(old_path_obj, new_path)

            print(f"✅ 数据库已迁移")

            # 可选：创建软链接保持兼容性
            try:
                os.symlink(new_path, old_path_obj)
                print(f"🔗 创建软链接: {old_path} -> {new_path}")
            except:
                pass

            return True

    print("⚠️ 未找到可迁移的数据库")
    return False