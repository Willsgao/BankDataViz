"""
OCR 缓存路径匹配测试脚本
用于验证 s3_key 前缀处理和路径查找逻辑
"""
import re
import json
import gzip
from pathlib import Path

# ===== 1. 测试 UUID 提取函数 =====
def extract_pdf_uuid_from_image_path(image_path: str) -> str:
    """从图片路径中提取PDF UUID"""
    match = re.search(r'filtered_tables[\\/]([a-f0-9-]{36})[\\/]tables', image_path)
    return match.group(1) if match else None

def _is_valid_uuid(uuid_str: str) -> bool:
    """检查是否为有效的UUID"""
    import uuid
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False

# ===== 2. 测试数据（从 DB 查询结果模拟）=====
# 这是 DB 中存储的 s3_key 格式
TEST_S3_KEY = "ocr/014_b65309b3868f628c75ed7835e009d699.json.gz"

# 实际的缓存文件路径
LOCAL_OBJECT_STORE = Path('F:/wills/codes/DocuVista/data/backend/obj_cache')

# 测试图片路径
TEST_IMAGE_PATH = r"F:\wills\codes\DocuVista\data\backend\static\filtered_tables\23ca8b0f-2236-00a8-9f19-08195e029986\tables\table_014.png"

print("=" * 60)
print("OCR 缓存路径匹配测试")
print("=" * 60)

# ===== 3. 测试 UUID 提取 =====
print(f"\n[1] 测试 UUID 提取")
print(f"    图片路径: {TEST_IMAGE_PATH}")
uuid = extract_pdf_uuid_from_image_path(TEST_IMAGE_PATH)
print(f"    提取结果: {uuid}")
print(f"    UUID 有效: {_is_valid_uuid(uuid)}")

# ===== 4. 测试 s3_key 前缀处理 =====
print(f"\n[2] 测试 s3_key 前缀处理")
print(f"    原始 s3_key: {TEST_S3_KEY}")

key_without_prefix = TEST_S3_KEY
if TEST_S3_KEY.startswith("ocr/") or TEST_S3_KEY.startswith("llm/"):
    key_without_prefix = TEST_S3_KEY.split("/", 1)[1]

print(f"    去掉前缀后: {key_without_prefix}")

# ===== 5. 测试路径查找 =====
print(f"\n[3] 测试路径查找")
print(f"    LOCAL_OBJECT_STORE: {LOCAL_OBJECT_STORE}")

possible_paths = []

# 路径1：uuid/ocr/
if uuid and _is_valid_uuid(uuid):
    path1 = LOCAL_OBJECT_STORE / uuid / "ocr" / key_without_prefix
    possible_paths.append(("uuid/ocr/", path1))

# 路径2：uuid/直接
if uuid and _is_valid_uuid(uuid):
    path2 = LOCAL_OBJECT_STORE / uuid / key_without_prefix
    possible_paths.append(("uuid/直接", path2))

# 路径3：根目录
path3 = LOCAL_OBJECT_STORE / key_without_prefix
possible_paths.append(("根目录", path3))

# 路径4：根目录/ocr/
path4 = LOCAL_OBJECT_STORE / TEST_S3_KEY
possible_paths.append(("根目录/ocr/", path4))

print(f"\n    尝试的路径:")
for name, path in possible_paths:
    exists = path.exists()
    status = "✅ 存在" if exists else "❌ 不存在"
    print(f"    {status} [{name}]")
    print(f"           {path}")

# ===== 6. 测试文件读取 =====
print(f"\n[4] 测试文件内容读取")
for name, path in possible_paths:
    if path.exists():
        print(f"    ✅ 找到有效缓存: {path}")
        try:
            data = json.loads(gzip.decompress(path.read_bytes()))
            print(f"    ✅ JSON 解析成功，包含 keys: {list(data.keys())}")
            print(f"    🎉 测试通过！")
        except Exception as e:
            print(f"    ❌ 读取失败: {e}")
        break
else:
    print(f"    ❌ 没有找到有效的缓存文件")

print("\n" + "=" * 60)
