import sys
sys.path.insert(0, 'F:/wills/codes/DocuVista/backend')

from pathlib import Path

LOCAL_OBJECT_STORE = Path('F:/wills/codes/DocuVista/data/backend/obj_cache')

# 假设 s3_key 是这样的（不带 ocr/ 前缀）
s3_key = "014_b65309b3868f628c75ed783d2b09c3c.json.gz"

# 假设 pdf_uuid
pdf_uuid = "23ca8b0f-2236-00a8-9f19-08195e029986"

print("=== 测试路径匹配 ===")
print(f"s3_key: {s3_key}")
print(f"pdf_uuid: {pdf_uuid}")
print()

# 路径1：新路径（带 uuid 和 ocr/ 子目录）
path1 = LOCAL_OBJECT_STORE / pdf_uuid / "ocr" / s3_key
print(f"1. 新路径(uuid/ocr/): {path1}")
print(f"   存在: {path1.exists()}")
print()

# 路径2：旧路径（带 uuid 但不带 ocr/ 子目录）
path2 = LOCAL_OBJECT_STORE / pdf_uuid / s3_key
print(f"2. 旧路径(uuid/直接): {path2}")
print(f"   存在: {path2.exists()}")
print()

# 列出 obj_cache 目录下的实际文件
print("=== obj_cache 目录内容 ===")
for f in (LOCAL_OBJECT_STORE / pdf_uuid / "ocr").glob("*"):
    print(f"  {f.name[:50]}...")
    break
print()

# 确认实际文件存在
print("=== 实际文件路径 ===")
actual = LOCAL_OBJECT_STORE / pdf_uuid / "ocr" / s3_key
print(f"完整路径: {actual}")
print(f"文件存在: {actual.exists()}")
