import sys
sys.path.insert(0, r'F:\wills\codes\DocuVista')
from backend.utils import constants
print("DATABASE_PATH:", constants.DATABASE_PATH)

import os
if os.path.exists(constants.DATABASE_PATH):
    size = os.path.getsize(constants.DATABASE_PATH)
    print(f"File size: {size} bytes")
else:
    print("File does not exist")

import sqlite3
conn = sqlite3.connect(constants.DATABASE_PATH)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)
if 'api_call_log' in tables:
    cur.execute("SELECT COUNT(*) FROM api_call_log")
    print("api_call_log rows:", cur.fetchone()[0])
else:
    print("api_call_log NOT FOUND")
conn.close()
