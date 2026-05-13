# backend/services/table_processor/cache_gateway.py
from datetime import datetime
from sqlalchemy import create_engine, text

from backend.configs.config import config  # ✅ 使用主配置
# 使用主数据库，而不是缓存数据库
DB_URL = f"sqlite:///{config.DATABASE_PATH}"  # ✅ 连接到主数据库
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

# 模块加载时自动创建表
ensure_table()


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
        return row._mapping if row else None


def delete(md5: str, provider: str):
    """删除缓存记录"""
    sql = text("""
        DELETE FROM api_call_log
        WHERE md5 = :md5 AND provider = :provider
    """)
    with engine.begin() as conn:
        conn.execute(sql, {"md5": md5, "provider": provider})


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


# 在 cache_gateway.py 中添加以下函数
def clear_cache(cache_type: str = "all"):
    """
    清除指定类型或所有缓存

    Args:
        cache_type: 缓存类型
            - "all": 清除所有缓存
            - "ocr": 清除OCR相关缓存
            - "llm": 清除LLM分析缓存
    """
    from sqlalchemy import text

    # 根据你的实际provider调整
    sql_mapping = {
        "all": "DELETE FROM api_call_log",
        "ocr": "DELETE FROM api_call_log WHERE provider IN ('baidu', 'tencent', 'aliyun')",
        # 关键修改：匹配你的实际provider模式
        "llm": "DELETE FROM api_call_log WHERE provider LIKE '%doubao%' OR provider LIKE 'llm:%'"
    }

    if cache_type not in sql_mapping:
        raise ValueError(f"不支持的缓存类型: {cache_type}。可用: {list(sql_mapping.keys())}")

    with engine.begin() as conn:
        result = conn.execute(text(sql_mapping[cache_type]))
        print(f"✅ 已清除 {result.rowcount} 条缓存记录")
        return result.rowcount

def get_cache_stats():
    """
    获取缓存统计信息
    """
    from sqlalchemy import text

    stats_sql = text("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT md5) as unique_md5,
            provider,
            COUNT(*) as record_count,
            SUM(cost_usd) as total_cost_usd,
            MIN(created_at) as oldest_record,
            MAX(created_at) as newest_record
        FROM api_call_log
        GROUP BY provider
        ORDER BY record_count DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(stats_sql).fetchall()

        # 安全处理日期字段
        def safe_date_format(date_value):
            if not date_value:
                return None
            try:
                if hasattr(date_value, 'isoformat'):
                    return date_value.isoformat()
                return str(date_value)
            except:
                return str(date_value)

        providers = []
        for row in rows:
            provider_info = {
                "provider": row.provider,
                "record_count": row.record_count,
                "total_cost": float(row.total_cost_usd or 0),
                "oldest": safe_date_format(row.oldest_record),
                "newest": safe_date_format(row.newest_record)
            }
            providers.append(provider_info)

        # 计算总计
        total_records = sum(row.record_count for row in rows) if rows else 0
        total_cost = sum(float(row.total_cost_usd or 0) for row in rows) if rows else 0.0

        # 获取所有provider用于调试
        all_providers_sql = text("SELECT DISTINCT provider FROM api_call_log")
        all_providers = [p[0] for p in conn.execute(all_providers_sql).fetchall()]

        stats = {
            "total_records": total_records,
            "unique_md5": rows[0].unique_md5 if rows else 0,
            "total_cost_usd": total_cost,
            "providers": providers,
            "all_providers": all_providers  # 新增：所有实际provider
        }
        return stats


def clear_old_cache(days: int = 7):
    """
    清除指定天数前的旧缓存

    Args:
        days: 保留最近多少天的缓存，默认7天
    """
    from sqlalchemy import text
    import datetime

    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    sql = text("""
        DELETE FROM api_call_log 
        WHERE created_at < :cutoff_date
    """)

    with engine.begin() as conn:
        result = conn.execute(sql, {"cutoff_date": cutoff_date})
        print(f"✅ 已清除 {result.rowcount} 条超过 {days} 天的缓存记录")
        return result.rowcount