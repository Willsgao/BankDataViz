# -*- coding:utf-8 -*-
import sqlite3

conn = sqlite3.connect('F:/wills/codes/DocuVista/data/database.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', tables)

if ('excel_files',) in tables:
    cursor.execute('PRAGMA table_info(excel_files)')
    print('excel_files columns:', cursor.fetchall())
else:
    print('excel_files table NOT found!')

conn.close()
