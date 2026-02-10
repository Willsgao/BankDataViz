# test_fix.py
import sqlite3
from pathlib import Path


def test_fix():
    # 连接数据库
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    db_path = project_root / "data" / "database.db"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. 检查api_call_log表结构
        print("🔍🔍 检查api_call_log表结构...")
        cursor.execute("PRAGMA table_info(api_call_log)")
        columns = cursor.fetchall()

        print("当前api_call_log表结构:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

        # 2. 检查唯一约束
        print("\n🔍🔍 检查唯一约束...")
        cursor.execute("PRAGMA index_list(api_call_log)")
        indexes = cursor.fetchall()

        for index in indexes:
            print(f"索引: {index[1]}, 唯一: {index[2]}")
            if index[2]:  # 唯一索引
                cursor.execute(f"PRAGMA index_info({index[1]})")
                index_info = cursor.fetchall()
                print(f"  包含列: {[info[2] for info in index_info]}")

        # 3. 测试插入数据（验证ON CONFLICT是否工作）
        print("\n🔍🔍 测试ON CONFLICT功能...")
        try:
            cursor.execute('''
                INSERT INTO api_call_log(md5, provider, model_id, cost_usd,
                                         prompt_tokens, completion_tokens, s3_key, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT (md5, provider) DO UPDATE
                  SET cost_usd = EXCLUDED.cost_usd
            ''', ('test_md5_123', 'tencent', 'tencent', 0.0, 0, 0, 'test_key', 'succ'))

            print("✅ ON CONFLICT 测试成功！")
            conn.commit()

        except Exception as e:
            print(f"❌ ON CONFLICT 测试失败: {e}")
            conn.rollback()

    finally:
        conn.close()


if __name__ == "__main__":
    test_fix()