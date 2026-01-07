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


# 初始化配置
config = get_config()
STORE_TYPE = config['store_type']
BUCKET = config['bucket']
LOCAL_ROOT = config['local_root']

# 确保目录存在（使用正确的路径）
LOCAL_ROOT.mkdir(parents=True, exist_ok=True)

print(f"[object_store] 配置: type={STORE_TYPE}, local_root={LOCAL_ROOT}")


def _local_path(key: str, pdf_uuid: str = None) -> Path:
    """生成本地文件路径，支持PDF UUID文件夹"""
    if pdf_uuid and _is_valid_uuid(pdf_uuid):
        # 使用PDF UUID作为父目录
        return LOCAL_ROOT / pdf_uuid / key
    else:
        # 传统路径（保持向后兼容）
        return LOCAL_ROOT / key


def _is_valid_uuid(uuid_str: str) -> bool:
    """检查是否为有效的UUID"""
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False


def _find_object_by_key(key: str) -> Path:
    """通过key查找对象文件（支持多种路径模式）"""
    # 1. 首先尝试传统路径
    traditional_path = LOCAL_ROOT / key
    if traditional_path.exists():
        return traditional_path

    # 2. 在所有UUID目录中递归查找（向后兼容）
    if LOCAL_ROOT.exists():
        for item in LOCAL_ROOT.iterdir():
            if item.is_dir() and _is_valid_uuid(item.name):
                candidate_path = item / key
                if candidate_path.exists():
                    return candidate_path

    # 3. 尝试旧的obj_cache路径（兼容性处理）
    old_path = Path("obj_cache") / key
    if old_path.exists():
        return old_path

    raise FileNotFoundError(f"对象不存在: {key}")


def put_object(key: str, body: bytes, pdf_uuid: str = None):
    """保存对象，支持PDF UUID文件夹"""
    if STORE_TYPE == "local":
        # 确定文件路径
        file_path = _local_path(key, pdf_uuid)

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(body)

        # 调试信息
        if pdf_uuid:
            print(f"[object_store] 保存到PDF文件夹: {file_path} [PDF UUID: {pdf_uuid}]")
        else:
            print(f"[object_store] 保存到本地: {file_path}")

    else:  # s3
        import boto3
        boto3.client('s3').put_object(Bucket=BUCKET, Key=key, Body=body)
        print(f"[object_store] 保存到S3: {BUCKET}/{key}")


def get_object(key: str, pdf_uuid: str = None) -> bytes:
    """获取对象，支持PDF UUID文件夹"""
    try:
        if STORE_TYPE == "local":
            # 如果有PDF UUID，优先使用指定路径
            if pdf_uuid and _is_valid_uuid(pdf_uuid):
                file_path = _local_path(key, pdf_uuid)
                if file_path.exists():
                    return file_path.read_bytes()
                else:
                    print(f"[object_store] PDF UUID路径不存在: {file_path}, 尝试其他路径")

            # 查找对象（自动处理多种路径）
            file_path = _find_object_by_key(key)

            # 🔥🔥 关键修复：如果文件在旧路径，迁移到新路径
            if "obj_cache" in str(file_path):
                # 迁移到LOCAL_ROOT下的传统路径
                new_path = LOCAL_ROOT / key
                print(f"[object_store] 迁移旧文件: {file_path} -> {new_path}")
                new_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.rename(new_path)
                return new_path.read_bytes()

            return file_path.read_bytes()

        else:  # s3
            import boto3
            return boto3.client('s3').get_object(Bucket=BUCKET, Key=key)["Body"].read()

    except Exception as e:
        # 提供更清晰的错误信息
        error_msg = f"获取对象失败 [key={key}, pdf_uuid={pdf_uuid}, type={STORE_TYPE}]: {e}"
        print(f"[object_store] {error_msg}")
        raise FileNotFoundError(error_msg)


def object_exists(key: str, pdf_uuid: str = None) -> bool:
    """检查对象是否存在，支持PDF UUID文件夹"""
    if STORE_TYPE == "local":
        # 如果有PDF UUID，检查指定路径
        if pdf_uuid and _is_valid_uuid(pdf_uuid):
            file_path = _local_path(key, pdf_uuid)
            if file_path.exists():
                return True

        # 检查其他可能路径
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


# 新增功能：PDF相关的工具函数
def get_pdf_storage_path(pdf_uuid: str) -> Path:
    """获取PDF的存储根路径"""
    if not _is_valid_uuid(pdf_uuid):
        raise ValueError(f"无效的UUID格式: {pdf_uuid}")
    return LOCAL_ROOT / pdf_uuid


def list_pdf_objects(pdf_uuid: str) -> list:
    """列出PDF相关的所有存储对象"""
    pdf_path = get_pdf_storage_path(pdf_uuid)
    if not pdf_path.exists():
        return []

    objects = []
    for file_path in pdf_path.rglob("*"):
        if file_path.is_file():
            # 计算相对路径（相对于PDF存储根目录）
            relative_path = file_path.relative_to(pdf_path)
            objects.append({
                'relative_path': str(relative_path),
                'full_path': str(file_path),
                'size': file_path.stat().st_size
            })

    return objects


def get_pdf_storage_info(pdf_uuid: str) -> dict:
    """获取PDF存储信息"""
    pdf_path = get_pdf_storage_path(pdf_uuid)
    info = {
        'pdf_uuid': pdf_uuid,
        'storage_path': str(pdf_path),
        'exists': pdf_path.exists(),
        'ocr_files': [],
        'llm_files': []
    }

    if pdf_path.exists():
        # 查找OCR文件
        ocr_files = list(pdf_path.glob("ocr/*.json.gz"))
        info['ocr_files'] = [{
            'name': f.name,
            'path': str(f),
            'size': f.stat().st_size
        } for f in ocr_files]

        # 查找LLM文件
        llm_files = list(pdf_path.glob("llm/*.json.gz"))
        info['llm_files'] = [{
            'name': f.name,
            'path': str(f),
            'size': f.stat().st_size
        } for f in llm_files]

    return info


# 保持原有接口的完全兼容性
def put_object_legacy(key: str, body: bytes):
    """传统接口（完全向后兼容）"""
    return put_object(key, body)


def get_object_legacy(key: str) -> bytes:
    """传统接口（完全向后兼容）"""
    return get_object(key)