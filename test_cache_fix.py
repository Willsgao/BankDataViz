import sys
sys.path.insert(0, 'F:/wills/codes/DocuVista/backend')

from pathlib import Path

LOCAL_OBJECT_STORE = Path('F:/wills/codes/DocuVista/data/backend/obj_cache')

# DB 中存储的 s3_key（带 ocr/ 前缀）
s3_key = "ocr/014_b65309b3868f628c75ed7835e009d699.json.gz"

# 假设 pdf_uuid
pdf_uuid = "23ca8b0f-2236-00a8-9f19-08195e029986"

print("=== 测试修复后的路径匹配 ===")
print(f"s3_key: {s3_key}")
print(f"pdf_uuid: {pdf_uuid}")
print()

# s3_key 可能带有 ocr/ 或 llm/ 前缀，需要去掉
key_without_prefix = s3_key
if s3_key.startswith("ocr/") or s3_key.startswith("llm/"):
    key_without_prefix = s3_key.split("/", 1)[1]  # 去掉前缀

print(f"key_without_prefix: {key_without_prefix}")
print()

# 1. 新路径：obj_cache/<uuid>/ocr/<key_without_prefix>
path1 = LOCAL_OBJECT_STORE / pdf_uuid / "ocr" / key_without_prefix
print(f"1. 新路径(uuid/ocr/): {path1}")
print(f"   存在: {path1.exists()}")
print()

# 2. 旧路径：obj_cache/<uuid>/<key_without_prefix>
path2 = LOCAL_OBJECT_STORE / pdf_uuid / key_without_prefix
print(f"2. 旧路径(uuid/直接): {path2}")
print(f"   存在: {path2.exists()}")
print()

# 3. 更旧的路径：obj_cache/<key_without_prefix>
path3 = LOCAL_OBJECT_STORE / key_without_prefix
print(f"3. 更旧路径(根目录): {path3}")
print(f"   存在: {path3.exists()}")
print()

# 4. 最旧的路径：obj_cache/<s3_key>
path4 = LOCAL_OBJECT_STORE / s3_key
print(f"4. 最旧路径(根目录/ocr/): {path4}")
print(f"   存在: {path4.exists()}")
print()

# 列出实际目录内容确认
print("=== 实际文件确认 ===")
actual = LOCAL_OBJECT_STORE / pdf_uuid / "ocr"
print(f"ocr 目录: {actual}")
if actual.exists():
    for f in actual.glob("014_*.gz"):
        print(f"  找到: {f.name}")
