# backend/services/table_processor/cache_gateway.py
import os, gzip, json
from sqlalchemy import create_engine, text
from datetime import datetime

DB_URL = os.getenv("CACHE_URL", "sqlite:///./cache.db")   # 开发默认 SQLite
engine = create_engine(DB_URL, future=True, pool_pre_ping=True)

def ensure_table():
    ddl = """
    CREATE TABLE IF NOT EXISTS api_call_log (
        id                BIGSERIAL PRIMARY KEY,
        md5               CHAR(32) NOT NULL,
        provider          VARCHAR(50) NOT NULL,
        model_id          VARCHAR(100),
        cost_usd          DECIMAL(10,6) DEFAULT 0,
        prompt_tokens     INT DEFAULT 0,
        completion_tokens INT DEFAULT 0,
        s3_key            TEXT,
        status            VARCHAR(10) DEFAULT 'succ',
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(md5, provider)
    );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))


def get(md5: str, provider: str):
    """返回 dict 或 None"""
    sql = text("""
        SELECT s3_key, cost_usd, prompt_tokens, completion_tokens
          FROM api_call_log
         WHERE md5 = :md5 AND provider = :provider AND status = 'succ'
         ORDER BY created_at DESC
         LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"md5": md5, "provider": provider}).first()
        return row._mapping if row else None      # ← 改这里

# backend/services/table_processor/cache_gateway.py
def upsert(md5: str, provider: str, model_id: str,
           cost_usd: float, prompt_tokens: int, completion_tokens: int,
           s3_key: str):
    sql = text("""
        INSERT INTO api_call_log(md5, provider, model_id, cost_usd,
                                 prompt_tokens, completion_tokens, s3_key, status, created_at)
        VALUES (:md5, :provider, :model_id, :cost_usd,
                :prompt_tokens, :completion_tokens, :s3_key, 'succ', :created_at)
        ON CONFLICT (md5, provider) DO UPDATE
          SET cost_usd = EXCLUDED.cost_usd,
              prompt_tokens = EXCLUDED.prompt_tokens,
              completion_tokens = EXCLUDED.completion_tokens,
              s3_key = EXCLUDED.s3_key,
              created_at = EXCLUDED.created_at
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "md5": md5,
            "provider": provider,
            "model_id": model_id,
            "cost_usd": cost_usd,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "s3_key": s3_key,
            "created_at": datetime.utcnow()
        })

