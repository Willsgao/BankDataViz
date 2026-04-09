# -*- coding: utf-8 -*-
"""修复 excel_files 表缺少的列"""

from backend.models.unified_db import UnifiedDatabaseManager

db = UnifiedDatabaseManager()
conn = db.connect()
cursor = conn.cursor()

# 检查表结构
cursor.execute('PRAGMA table_info(excel_files)')
columns = cursor.fetchall()
print('excel_files 表结构:')
for col in columns:
    print(' ', col)

# 检查是否有 review_status 列
column_names = [col[1] for col in columns]
if 'review_status' not in column_names:
    print()
    print('缺少 review_status 列，正在添加...')
    cursor.execute("ALTER TABLE excel_files ADD COLUMN review_status TEXT DEFAULT 'auto'")
    cursor.execute("ALTER TABLE excel_files ADD COLUMN review_issues TEXT DEFAULT ''")
    cursor.execute("ALTER TABLE excel_files ADD COLUMN reviewed_by TEXT DEFAULT ''")
    cursor.execute("ALTER TABLE excel_files ADD COLUMN reviewed_at TIMESTAMP")
    conn.commit()
    print('✅ 添加完成')
else:
    print('✅ review_status 列已存在')

conn.close()
