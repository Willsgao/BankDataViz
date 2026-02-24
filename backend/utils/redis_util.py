# backend/utils/redis_util.py
"""
Redis兼容性工具函数
支持Redis 3.x版本的兼容操作
"""

import time
import redis
from typing import Dict, Any, Optional
import json


def redis_hset_compatible_old(client: redis.Redis, key: str, mapping: Dict[str, Any]) -> bool:
    """
    兼容Redis 3.x的HSET函数

    参数:
        client: Redis客户端实例
        key: Redis键名
        mapping: 字典，包含字段名和值

    返回:
        bool: 操作是否成功

    示例:
        redis_hset_compatible(redis_client, "mykey", {"field1": "value1", "field2": "value2"})
    """
    if not client or not key or not mapping:
        return False

    try:
        # 方法1：尝试使用Redis 4.0+的新语法
        try:
            client.hset(key, mapping=mapping)
            return True
        except Exception as e1:
            error_msg = str(e1)
            if "wrong number of arguments" in error_msg or "ERR" in error_msg:
                # 方法2：Redis 3.x版本，使用管道批量设置
                try:
                    pipe = client.pipeline()
                    for field, value in mapping.items():
                        # 确保值是字符串
                        if not isinstance(value, (str, bytes, int, float)):
                            value = str(value)
                        pipe.hset(key, field, value)
                    pipe.execute()
                    return True
                except Exception as e2:
                    # 方法3：管道失败，回退到逐个设置
                    print(f"⚠️ Redis管道操作失败，回退到逐个设置: {e2}")
                    for field, value in mapping.items():
                        try:
                            if not isinstance(value, (str, bytes, int, float)):
                                value = str(value)
                            client.hset(key, field, value)
                        except Exception as e3:
                            print(f"⚠️ Redis HSET字段失败 {field}: {e3}")
                    return True
            else:
                # 其他错误，重新抛出
                raise e1

    except Exception as e:
        print(f"❌ Redis HSET兼容函数失败: {e}")
        raise


# 在 redis_util.py 中添加更健壮的错误处理
def redis_hset_compatible(client: redis.Redis, key: str, mapping: Dict[str, Any], max_retries: int = 3) -> bool:
    """
    更健壮的Redis HSET兼容函数，支持重试
    """
    for attempt in range(max_retries):
        try:
            return redis_hset_compatible_old(client, key, mapping)
        except redis.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                print(f"🔄 Redis连接错误，尝试重连 ({attempt+1}/{max_retries}): {e}")
                time.sleep(1)  # 等待1秒后重试
                try:
                    client.ping()  # 测试连接
                except:
                    pass
            else:
                print(f"❌ Redis连接失败，达到最大重试次数: {e}")
                raise
        except Exception as e:
            print(f"❌ Redis HSET失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5)  # 短暂等待后重试
            else:
                raise
    return False


def redis_hgetall_safe(client: redis.Redis, key: str) -> Dict[str, Any]:
    """
    安全的HGETALL函数，返回字符串类型的字典
    """
    try:
        result = client.hgetall(key)
        if result:
            # 将bytes转换为字符串
            return {k.decode('utf-8') if isinstance(k, bytes) else k:
                        v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in result.items()}
        return {}
    except Exception as e:
        print(f"⚠️ Redis HGETALL失败: {e}")
        return {}


def get_redis_client(config: dict = None) -> Optional[redis.Redis]:
    """
    获取Redis客户端
    """
    if config is None:
        config = {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'decode_responses': False,
            'socket_connect_timeout': 10,
            'socket_timeout': 10
        }

    try:
        client = redis.Redis(**config)
        client.ping()  # 测试连接
        return client
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return None

