# backend/models/fix_database.py
import sqlite3
import os
from pathlib import Path


def fix_database():
    # 自动检测数据库路径（从backend/models向上找到项目根目录）
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent  # backend/models -> backend -> project_root
    db_path = project_root / "data" / "database.db"

    print(f"🔍 项目根目录: {project_root}")
    print(f"🔍 数据库路径: {db_path}")

    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. 检查当前files表结构
        print("\n📊 检查files表当前结构...")
        cursor.execute("PRAGMA table_info(files)")
        columns = cursor.fetchall()

        print("当前files表结构:")
        column_names = []
        for col in columns:
            column_names.append(col[1])
            print(f"  {col[1]} ({col[2]})")

        # 2. 检查是否缺少created_at
        if 'created_at' not in column_names:
            print("\n🔄 检测到缺少created_at字段，开始修复...")

            # 方法1：先添加没有默认值的列，然后更新
            print("📝 方法1: 分步添加created_at字段...")

            # 第一步：添加没有默认值的列
            cursor.execute('ALTER TABLE files ADD COLUMN created_at TIMESTAMP')
            print("✅ 已添加created_at字段（无默认值）")

            # 第二步：为现有记录设置值（使用upload_time或当前时间）
            cursor.execute('UPDATE files SET created_at = COALESCE(upload_time, datetime("now"))')
            print("✅ 已为现有记录设置created_at值")

            # 方法2：如果方法1不行，使用重建表的方法
            # 但先尝试方法1，因为它更安全

            conn.commit()
            print("🎉 files表修复完成！")
        else:
            print("✅ files表已包含created_at字段，无需修复")

        # 3. 验证修复结果
        print("\n📊 验证修复后的结构...")
        cursor.execute("PRAGMA table_info(files)")
        updated_columns = cursor.fetchall()

        print("修复后files表结构:")
        for col in updated_columns:
            print(f"  {col[1]} ({col[2]})")

        # 4. 检查数据
        print("\n📊 检查数据...")
        cursor.execute("SELECT id, filename, created_at FROM files LIMIT 3")
        rows = cursor.fetchall()

        if rows:
            print("示例数据:")
            for row in rows:
                print(f"  ID:{row[0]}, 文件:{row[1]}, 创建时间:{row[2]}")
        else:
            print("ℹ️ files表没有数据")

        return True

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        print("🔄 尝试使用重建表的方法...")

        try:
            # 重建表的方法（更复杂但更可靠）
            return rebuild_files_table(conn, cursor, column_names)
        except Exception as e2:
            print(f"❌ 重建表也失败: {e2}")
            conn.rollback()
            return False
    finally:
        conn.close()


def rebuild_files_table(conn, cursor, old_column_names):
    """通过重建表来修复结构"""
    print("🔄 开始使用重建表方法修复...")

    # 1. 备份现有数据
    cursor.execute("SELECT * FROM files")
    existing_data = cursor.fetchall()
    print(f"📊 备份 {len(existing_data)} 条记录")

    # 2. 创建临时表（包含created_at字段）
    cursor.execute('''
        CREATE TABLE files_temp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            file_type TEXT NOT NULL,
            raw_filename TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted INTEGER DEFAULT 0,
            file_size INTEGER,
            page_count INTEGER,
            processed INTEGER DEFAULT 0,
            file_hash TEXT,
            upload_count INTEGER DEFAULT 1,
            last_uploaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bank_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_path TEXT
        )
    ''')

    # 3. 迁移数据
    for row in existing_data:
        # 构建INSERT语句，处理created_at字段
        placeholders = ', '.join(['?' for _ in range(len(row) + 1)])  # 增加一个位置给created_at
        values = list(row) + [None]  # 为created_at添加占位

        cursor.execute(f'INSERT INTO files_temp VALUES ({placeholders})', values)

    # 4. 替换表
    cursor.execute("DROP TABLE files")
    cursor.execute("ALTER TABLE files_temp RENAME TO files")

    # 5. 为现有记录设置created_at值
    cursor.execute('UPDATE files SET created_at = COALESCE(upload_time, datetime("now"))')

    conn.commit()
    print("✅ 通过重建表方法修复完成")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 开始修复数据库files表结构")
    print("=" * 60)

    success = fix_database()

    if success:
        print("\n🎉 数据库修复完成！")
        print("💡 请重启你的应用验证修复结果")
    else:
        print("\n❌ 数据库修复失败")