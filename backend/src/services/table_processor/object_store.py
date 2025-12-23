# backend/services/table_processor/object_store.py
import os
from pathlib import Path


def get_config():
    """获取配置，优先使用tableconfig，环境变量作为备选"""
    try:
        from backend.configs.config import tableconfig

        # 从tableconfig获取配置
        local_store = getattr(tableconfig, 'LOCAL_OBJECT_STORE', None)
        store_type = getattr(tableconfig, 'OBJECT_STORE', 'local')
        bucket = getattr(tableconfig, 'OBJECT_STORE_BUCKET', '')

        # 如果tableconfig中没有，使用环境变量
        if local_store is None:
            local_store = os.getenv("LOCAL_OBJECT_STORE", "data/backend/obj_cache")

        return {
            'store_type': store_type or os.getenv("OBJECT_STORE", "local"),
            'bucket': bucket or os.getenv("OBJECT_STORE_BUCKET", ""),
            'local_root': Path(local_store)
        }
    except ImportError:
        # 如果导入失败，使用环境变量
        return {
            'store_type': os.getenv("OBJECT_STORE", "local"),
            'bucket': os.getenv("OBJECT_STORE_BUCKET", ""),
            'local_root': Path(os.getenv("LOCAL_OBJECT_STORE", "data/backend/obj_cache"))
        }


# 初始化配置
config = get_config()
STORE_TYPE = config['store_type']
BUCKET = config['bucket']
LOCAL_ROOT = config['local_root']

# 确保目录存在（使用正确的路径）
LOCAL_ROOT.mkdir(parents=True, exist_ok=True)

print(f"[object_store] 配置: type={STORE_TYPE}, local_root={LOCAL_ROOT}")


def _local_path(key: str) -> Path:
    """生成本地文件路径"""
    return LOCAL_ROOT / key


def put_object(key: str, body: bytes):
    """保存对象"""
    if STORE_TYPE == "local":
        # 确保目录存在
        file_path = _local_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(body)

        # 调试信息
        print(f"[object_store] 保存到本地: {file_path}")

    else:  # s3
        import boto3
        boto3.client('s3').put_object(Bucket=BUCKET, Key=key, Body=body)
        print(f"[object_store] 保存到S3: {BUCKET}/{key}")


def get_object(key: str) -> bytes:
    """获取对象"""
    try:
        if STORE_TYPE == "local":
            file_path = _local_path(key)

            # 🔥 关键修复：如果文件不存在，尝试从旧路径迁移
            if not file_path.exists():
                # 尝试旧的 obj_cache 路径（兼容性处理）
                old_path = Path("obj_cache") / key
                if old_path.exists():
                    print(f"[object_store] 迁移旧文件: {old_path} -> {file_path}")
                    # 确保新目录存在
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    # 移动文件
                    old_path.rename(file_path)
                else:
                    raise FileNotFoundError(f"缓存文件不存在: {file_path}")

            return file_path.read_bytes()

        else:  # s3
            import boto3
            return boto3.client('s3').get_object(Bucket=BUCKET, Key=key)["Body"].read()

    except Exception as e:
        # 提供更清晰的错误信息
        error_msg = f"获取对象失败 [key={key}, type={STORE_TYPE}]: {e}"
        print(f"[object_store] {error_msg}")
        raise FileNotFoundError(error_msg)


def object_exists(key: str) -> bool:
    """检查对象是否存在"""
    if STORE_TYPE == "local":
        file_path = _local_path(key)
        exists = file_path.exists()

        # 如果新路径不存在，检查旧路径（兼容性）
        if not exists:
            old_path = Path("obj_cache") / key
            exists = old_path.exists()

        return exists
    else:
        try:
            import boto3
            boto3.client('s3').head_object(Bucket=BUCKET, Key=key)
            return True
        except:
            return False