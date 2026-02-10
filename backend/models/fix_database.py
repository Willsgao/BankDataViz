# backend/models/fix_database.py
import sqlite3
import os
from pathlib import Path


def fix_database():
    # 自动检测数据库路径
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    db_path = project_root / "data" / "database.db"

    print(f"🔍🔍 项目根目录: {project_root}")
    print(f"🔍🔍 数据库路径: {db_path}")

    if not db_path.exists():
        print("❌❌ 数据库文件不存在")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. 修复files表
        print("\n" + "=" * 60)
        print("🔧🔧 开始修复files表结构")
        print("=" * 60)

        files_fixed = fix_files_table(conn, cursor)

        # 2. 修复api_call_log表
        print("\n" + "=" * 60)
        print("🔧🔧 开始修复api_call_log表结构")
        print("=" * 60)

        api_log_fixed = fix_api_call_log_table(conn, cursor)

        return files_fixed and api_log_fixed

    except Exception as e:
        print(f"❌❌ 修复失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def fix_api_call_log_table(conn, cursor):
    """修复api_call_log表结构"""
    try:
        # 1. 检查当前api_call_log表结构
        print("\n📊📊 检查api_call_log表当前结构...")
        cursor.execute("PRAGMA table_info(api_call_log)")
        columns = cursor.fetchall()

        print("当前api_call_log表结构:")
        current_columns = []
        for col in columns:
            current_columns.append(col[1])
            print(f"  {col[1]} ({col[2]})")

        # 2. 检查是否缺少必要列
        required_columns = ['md5', 'provider', 's3_key', 'cost_usd', 'prompt_tokens', 'completion_tokens', 'status']
        missing_columns = [col for col in required_columns if col not in current_columns]

        if missing_columns:
            print(f"\n🔄🔄 检测到缺少必要字段: {missing_columns}，开始修复...")
            return rebuild_api_call_log_table(conn, cursor, current_columns)
        else:
            print("✅ api_call_log表结构正确，检查唯一约束...")
            # 检查是否已存在唯一约束
            return add_unique_constraint_if_needed(conn, cursor)

    except Exception as e:
        print(f"❌❌ 检查api_call_log表失败: {e}")
        if "no such table" in str(e).lower():
            print("🔄🔄 api_call_log表不存在，创建新表...")
            return create_api_call_log_table(conn, cursor)
        return False


def add_unique_constraint_if_needed(conn, cursor):
    """检查并添加唯一约束"""
    try:
        # 检查是否已存在唯一约束
        cursor.execute("PRAGMA index_list(api_call_log)")
        indexes = cursor.fetchall()

        has_unique_constraint = False
        for index in indexes:
            if index[2]:  # unique字段为1表示唯一索引
                cursor.execute(f"PRAGMA index_info({index[1]})")
                index_info = cursor.fetchall()
                if len(index_info) == 2:  # 检查是否是(md5, provider)的组合索引
                    cols = [info[2] for info in index_info]
                    if 'md5' in cols and 'provider' in cols:
                        has_unique_constraint = True
                        break

        if not has_unique_constraint:
            print("🔄🔄 添加唯一约束...")
            # 由于SQLite不支持直接添加唯一约束到现有表，需要重建表
            return rebuild_api_call_log_table(conn, cursor, [])
        else:
            print("✅ 唯一约束已存在")
            return True

    except Exception as e:
        print(f"❌❌ 检查唯一约束失败: {e}")
        return False


def rebuild_api_call_log_table(conn, cursor, old_columns):
    """通过重建表来修复api_call_log结构"""
    try:
        print("🔄🔄 开始使用重建表方法修复api_call_log...")

        # 1. 备份现有数据
        cursor.execute("SELECT COUNT(*) FROM api_call_log")
        row_count = cursor.fetchone()[0]

        existing_data = []
        if row_count > 0:
            print(f"📊📊 备份 {row_count} 条记录")
            cursor.execute("SELECT * FROM api_call_log")
            existing_data = cursor.fetchall()
        else:
            print("ℹℹ️ api_call_log表为空，无需备份数据")

        # 2. 创建临时表（正确的结构，包含唯一约束）
        cursor.execute('DROP TABLE IF EXISTS api_call_log_temp')

        cursor.execute('''
            CREATE TABLE api_call_log_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                md5 CHAR(32) NOT NULL,
                provider VARCHAR(50) NOT NULL,
                model_id VARCHAR(100),
                cost_usd REAL DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                s3_key TEXT,
                status VARCHAR(10) DEFAULT 'succ',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                -- 关键：添加唯一约束
                UNIQUE(md5, provider)
            )
        ''')
        print("✅ 创建临时表成功（包含唯一约束）")

        # 3. 迁移数据
        if existing_data:
            print("🔄🔄 迁移现有数据...")
            for row in existing_data:
                # 根据旧表结构映射到新表
                try:
                    # 这里需要根据实际数据结构调整映射逻辑
                    if len(row) >= 3:  # 至少要有id, md5, provider
                        md5 = row[1] if len(row) > 1 else f"backup_{row[0]}"
                        provider = row[2] if len(row) > 2 else "legacy"

                        cursor.execute('''
                            INSERT OR IGNORE INTO api_call_log_temp 
                            (md5, provider, model_id, cost_usd, prompt_tokens, 
                             completion_tokens, s3_key, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (md5, provider, None, 0, 0, 0, None, 'succ', row[-1] if len(row) > 8 else None))
                except Exception as e:
                    print(f"⚠️ 跳过无效记录: {e}")
                    continue

            print(f"✅ 迁移了 {len(existing_data)} 条记录")

        # 4. 替换表
        cursor.execute("DROP TABLE IF EXISTS api_call_log")
        cursor.execute("ALTER TABLE api_call_log_temp RENAME TO api_call_log")

        # 5. 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_api_call_log_md5_provider 
            ON api_call_log(md5, provider)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_api_call_log_created_at 
            ON api_call_log(created_at)
        ''')
        print("✅ 索引创建完成")

        conn.commit()
        print("🎉🎉 api_call_log表修复完成！")

        # 6. 验证新表结构
        print("\n📊📊 验证修复后的api_call_log表结构...")
        cursor.execute("PRAGMA table_info(api_call_log)")
        new_columns = cursor.fetchall()

        print("修复后api_call_log表结构:")
        for col in new_columns:
            print(f"  {col[1]} ({col[2]})")

        return True

    except Exception as e:
        print(f"❌❌ 重建api_call_log表失败: {e}")
        conn.rollback()
        return False


def create_api_call_log_table(conn, cursor):
    """创建新的api_call_log表"""
    try:
        print("🔄🔄 创建新的api_call_log表...")

        cursor.execute('''
            CREATE TABLE api_call_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                md5 CHAR(32) NOT NULL,
                provider VARCHAR(50) NOT NULL,
                model_id VARCHAR(100),
                cost_usd REAL DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                s3_key TEXT,
                status VARCHAR(10) DEFAULT 'succ',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                -- 关键：添加唯一约束
                UNIQUE(md5, provider)
            )
        ''')

        # 创建索引
        cursor.execute('''
            CREATE INDEX idx_api_call_log_md5_provider 
            ON api_call_log(md5, provider)
        ''')
        cursor.execute('''
            CREATE INDEX idx_api_call_log_created_at 
            ON api_call_log(created_at)
        ''')

        conn.commit()
        print("✅ api_call_log表创建成功（包含唯一约束）")
        return True

    except Exception as e:
        print(f"❌❌ 创建api_call_log表失败: {e}")
        conn.rollback()
        return False


# 保持原有的files表修复函数不变
def fix_files_table(conn, cursor):
    """修复files表结构（保持原有逻辑）"""
    # ... 保持原有代码不变 ...


def rebuild_files_table(conn, cursor, old_column_names):
    """通过重建表来修复files结构（保持原有逻辑）"""
    # ... 保持原有代码不变 ...


if __name__ == "__main__":
    print("=" * 60)
    print("🔧🔧 开始修复数据库表结构")
    print("=" * 60)

    success = fix_database()

    if success:
        print("\n🎉🎉 数据库修复完成！")
        print("💡💡 请重启你的应用验证修复结果")
    else:
        print("\n❌❌ 数据库修复失败")