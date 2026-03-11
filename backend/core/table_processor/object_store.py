# backend/services/table_processor/object_store.py

import os
import uuid
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

def extract_pdf_uuid_from_image_path(image_path: str) -> str:
    """从图片路径中提取PDF UUID - 最简洁版"""
    import re
    match = re.search(r'filtered_tables[\\/]([a-f0-9-]{36})[\\/]tables', image_path)
    return match.group(1) if match else None

# 初始化配置
config = get_config()
STORE_TYPE = config['store_type']
BUCKET = config['bucket']
LOCAL_ROOT = config['local_root']

# 确保目录存在（使用正确的路径）
LOCAL_ROOT.mkdir(parents=True, exist_ok=True)

print(f"[object_store] 配置: type={STORE_TYPE}, local_root={LOCAL_ROOT}")


def _local_path(key: str, pdf_uuid: str = None) -> Path:
    """生成本地文件路径 - 保持原有逻辑，仅添加可选UUID支持"""
    if pdf_uuid and _is_valid_uuid(pdf_uuid):
        # 🔥🔥🔥 新增：如果提供了有效的UUID，使用UUID子目录
        uuid_dir = LOCAL_ROOT / pdf_uuid
        uuid_dir.mkdir(parents=True, exist_ok=True)
        return uuid_dir / key
    else:
        # ✅✅✅ 保持原有逻辑不变
        return LOCAL_ROOT / key


def _is_valid_uuid(uuid_str: str) -> bool:
    """检查是否为有效的UUID"""
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False


def _find_object_by_key(key: str) -> Path:
    """通过key查找对象文件 - 保持原有逻辑不变"""
    # 1. 首先尝试传统路径
    traditional_path = LOCAL_ROOT / key
    if traditional_path.exists():
        return traditional_path

    # 2. 尝试旧的obj_cache路径（兼容性处理）
    old_path = Path("obj_cache") / key
    if old_path.exists():
        return old_path

    raise FileNotFoundError(f"对象不存在: {key}")


def put_object(key: str, body: bytes, pdf_uuid: str = None):
    """保存对象，支持PDF UUID文件夹和类型子目录"""
    if STORE_TYPE == "local":
        # 🔥🔥🔥 修改：在key中添加类型前缀
        if key.startswith("llm/"):
            # llm类型：pdf_uuid/llm/文件名
            if pdf_uuid and _is_valid_uuid(pdf_uuid):
                file_path = LOCAL_ROOT / pdf_uuid / "llm" / key.replace("llm/", "")
            else:
                file_path = LOCAL_ROOT / "llm" / key.replace("llm/", "")
        elif key.startswith("ocr/"):
            # ocr类型：pdf_uuid/ocr/文件名
            if pdf_uuid and _is_valid_uuid(pdf_uuid):
                file_path = LOCAL_ROOT / pdf_uuid / "ocr" / key.replace("ocr/", "")
            else:
                file_path = LOCAL_ROOT / "ocr" / key.replace("ocr/", "")
        else:
            # 其他类型：pdf_uuid/文件名
            if pdf_uuid and _is_valid_uuid(pdf_uuid):
                file_path = LOCAL_ROOT / pdf_uuid / key
            else:
                file_path = LOCAL_ROOT / key

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(body)

        print(f"[object_store] 保存到: {file_path} [PDF UUID: {pdf_uuid}]")

    else:  # s3
        import boto3
        boto3.client('s3').put_object(Bucket=BUCKET, Key=key, Body=body)
        print(f"[object_store] 保存到S3: {BUCKET}/{key}")



def get_object(key: str, pdf_uuid: str = None) -> bytes:
    """获取对象，支持PDF UUID文件夹和类型子目录"""
    try:
        if STORE_TYPE == "local":
            # 🔥🔥🔥 修改：添加类型子目录支持
            if key.startswith("llm/"):
                if pdf_uuid and _is_valid_uuid(pdf_uuid):
                    file_path = LOCAL_ROOT / pdf_uuid / "llm" / key.replace("llm/", "")
                else:
                    file_path = LOCAL_ROOT / "llm" / key.replace("llm/", "")
            elif key.startswith("ocr/"):
                if pdf_uuid and _is_valid_uuid(pdf_uuid):
                    file_path = LOCAL_ROOT / pdf_uuid / "ocr" / key.replace("ocr/", "")
                else:
                    file_path = LOCAL_ROOT / "ocr" / key.replace("ocr/", "")
            else:
                if pdf_uuid and _is_valid_uuid(pdf_uuid):
                    file_path = LOCAL_ROOT / pdf_uuid / key
                else:
                    file_path = LOCAL_ROOT / key

            if file_path.exists():
                return file_path.read_bytes()
            else:
                raise FileNotFoundError(f"文件不存在: {file_path}")

        else:  # s3
            import boto3
            return boto3.client('s3').get_object(Bucket=BUCKET, Key=key)["Body"].read()

    except Exception as e:
        error_msg = f"获取对象失败 [key={key}, pdf_uuid={pdf_uuid}]: {e}"
        print(f"[object_store] {error_msg}")
        raise FileNotFoundError(error_msg)


def object_exists(key: str, pdf_uuid: str = None) -> bool:
    """检查对象是否存在 - 保持原有接口，仅添加可选UUID参数"""
    if STORE_TYPE == "local":
        # 🔥🔥🔥 新增：如果提供了UUID，先检查UUID路径
        if pdf_uuid and _is_valid_uuid(pdf_uuid):
            uuid_path = LOCAL_ROOT / pdf_uuid / key
            if uuid_path.exists():
                return True

        # ✅✅✅ 保持原有逻辑不变
        try:
            _find_object_by_key(key)
            return True
        except FileNotFoundError:
            return False
    else:
        try:
            import boto3
            boto3.client('s3').head_object(Bucket=BUCKET, Key=key)
            return True
        except:
            return False


# 🔥🔥🔥 新增：PDF UUID相关的工具函数（不影响现有功能）
def get_pdf_storage_path(pdf_uuid: str) -> Path:
    """获取PDF的存储根路径 - 新增功能"""
    if not _is_valid_uuid(pdf_uuid):
        raise ValueError(f"无效的UUID格式: {pdf_uuid}")
    return LOCAL_ROOT / pdf_uuid


def list_pdf_objects(pdf_uuid: str) -> list:
    """列出PDF相关的所有存储对象 - 新增功能"""
    pdf_path = get_pdf_storage_path(pdf_uuid)
    if not pdf_path.exists():
        return []

    objects = []
    for file_path in pdf_path.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(pdf_path)
            objects.append({
                'relative_path': str(relative_path),
                'full_path': str(file_path),
                'size': file_path.stat().st_size
            })

    return objects


def migrate_object_to_pdf_uuid(key: str, pdf_uuid: str) -> bool:
    """将对象迁移到PDF UUID目录 - 新增功能"""
    try:
        if not _is_valid_uuid(pdf_uuid):
            return False

        # 查找现有对象
        old_path = _find_object_by_key(key)
        new_path = LOCAL_ROOT / pdf_uuid / key

        # 确保目标目录存在
        new_path.parent.mkdir(parents=True, exist_ok=True)

        # 复制文件（不删除原文件，保持兼容性）
        import shutil
        shutil.copy2(old_path, new_path)

        print(f"📦📦 迁移对象到PDF UUID目录: {old_path} -> {new_path}")
        return True

    except Exception as e:
        print(f"❌❌ 迁移对象失败: {e}")
        return False


# ✅✅✅ 保持原有接口的完全兼容性（不修改任何现有调用）
def put_object_legacy(key: str, body: bytes):
    """传统接口 - 完全向后兼容"""
    return put_object(key, body)


def get_object_legacy(key: str) -> bytes:
    """传统接口 - 完全向后兼容"""
    return get_object(key)


def object_exists_legacy(key: str) -> bool:
    """传统接口 - 完全向后兼容"""
    return object_exists(key)


# ✅✅✅ 保持模块级别的函数别名（确保现有导入不受影响）
put_object_legacy = put_object
get_object_legacy = get_object
object_exists_legacy = object_exists