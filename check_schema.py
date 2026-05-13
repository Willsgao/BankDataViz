import sqlite3
db = 'F:/wills/codes/DocuVista/data/database.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("PRAGMA table_info(files)")
cols = c.fetchall()
print('=== files 表结构 ===')
for col in cols:
    print(f'  {col["name"]} ({col["type"]})')

c.execute('SELECT * FROM files LIMIT 1')
row = c.fetchone()
if row:
    print()
    print('=== 第一行数据 ===')
    print(dict(row))
conn.close()
