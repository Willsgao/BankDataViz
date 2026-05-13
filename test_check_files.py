# -*- coding:utf-8 -*-
import sqlite3

db_path = r'F:\wills\codes\DocuVista\data\backend\docuvista.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('SELECT id, name, excel_path FROM files LIMIT 5')
rows = cursor.fetchall()
print("数据库中的文件:")
for r in rows:
    print(f"  ID: {r[0]}, Name: {r[1]}, Path: {r[2]}")
conn.close()