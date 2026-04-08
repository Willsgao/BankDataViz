# -*- coding:utf-8 -*-
"""清理无效的 LLM 缓存记录"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.configs.config import config
from sqlalchemy import create_engine, text

db_path = config.DATABASE_PATH
print(f"数据库路径: {db_path}")
print(f"数据库存在: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    engine = create_engine(f"sqlite:///{db_path}")

    # 查看 LLM 缓存记录数量
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM api_call_log WHERE provider LIKE 'llm:%'"))
        count = result.scalar()
        print(f"LLM 缓存记录数: {count}")

        # 查看一些记录
        if count > 0:
            print("\n前 5 条 LLM 缓存记录:")
            result = conn.execute(text("SELECT id, md5, provider, s3_key FROM api_call_log WHERE provider LIKE 'llm:%' LIMIT 5"))
            for row in result:
                print(f"  id={row[0]}, md5={row[1]}, provider={row[2]}, s3_key={row[3]}")

    print("\n是否删除所有 LLM 缓存记录? (y/n)")
    choice = input("> ")
    if choice.lower() == 'y':
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM api_call_log WHERE provider LIKE 'llm:%'"))
            print("已删除所有 LLM 缓存记录")
    else:
        print("取消删除")
