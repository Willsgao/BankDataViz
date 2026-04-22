"""诊断：检查数据库 files 表的完整结构"""
import sqlite3
from pathlib import Path

# 使用与后端相同的路径
DB_PATH = Path(__file__).parent / 'data' / 'database.db'
print(f"数据库路径: {DB_PATH}")
print(f"数据库存在: {DB_PATH.exists()}\n")

if DB_PATH.exists():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 表是否存在
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
    result = c.fetchone()
    print(f"files 表存在: {result is not None}\n")

    # 列结构
    c.execute("PRAGMA table_info(files)")
    columns = c.fetchall()
    print("列结构:")
    for col in columns:
        print(f"  {col[1]:<20} {col[2]:<20} null={col[3]} default={col[4]}")

    # 示例数据
    c.execute("SELECT * FROM files LIMIT 3")
    rows = c.fetchall()
    print(f"\n示例数据 ({len(rows)} 行):")
    for row in rows:
        print(f"  {dict(row)}")

    conn.close()
