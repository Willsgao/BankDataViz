import sqlite3

db_path = 'F:/wills/codes/DocuVista/data/database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询 api_call_log 表
cursor.execute("""
    SELECT md5, provider, s3_key, created_at
    FROM api_call_log
    WHERE provider IN ('baidu', 'tencent', 'aliyun')
    ORDER BY created_at DESC
    LIMIT 10
""")

rows = cursor.fetchall()
print(f"共 {len(rows)} 条 OCR 缓存记录\n")

for row in rows:
    md5, provider, s3_key, created = row
    print(f"md5: {md5}")
    print(f"provider: {provider}")
    print(f"s3_key: {s3_key}")
    print(f"created: {created}")
    print("-" * 50)

conn.close()
