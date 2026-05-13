# -*- coding:utf-8 -*-
import sqlite3

db_path = r'F:\wills\codes\DocuVista\data\database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看 files 表结构
print("files 表结构:")
cursor.execute("PRAGMA table_info(files)")
for col in cursor.fetchall():
    print(f"  {col}")

# 查看 files 表数据
print("\nfiles 表数据:")
cursor.execute("SELECT * FROM files LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(f"  {row}")

conn.close()