import re

def extract_pdf_uuid_from_image_path(image_path: str) -> str:
    """从图片路径中提取PDF UUID - 最简洁版"""
    match = re.search(r'filtered_tables[\\/]([a-f0-9-]{36})[\\/]tables', image_path)
    return match.group(1) if match else None

# 测试几个可能的图片路径
test_paths = [
    r"F:\wills\codes\DocuVista\data\backend\static\filtered_tables\23ca8b0f-2236-00a8-9f19-08195e029986\tables\table_014.png",
    r"F:/wills/codes/DocuVista/data/backend/static/filtered_tables/23ca8b0f-2236-00a8-9f19-08195e029986/tables/table_014.png",
    r"data/backend/static/filtered_tables/23ca8b0f-2236-00a8-9f19-08195e029986/tables/table_014.png",
    # Windows 反斜杠
    r"backend\static\filtered_tables\23ca8b0f-2236-00a8-9f19-08195e029986\tables\table_014.png",
    # Unix 正斜杠
    r"backend/static/filtered_tables/23ca8b0f-2236-00a8-9f19-08195e029986/tables/table_014.png",
]

print("=== 测试 extract_pdf_uuid_from_image_path ===\n")

for path in test_paths:
    uuid = extract_pdf_uuid_from_image_path(path)
    print(f"路径: {path}")
    print(f"提取的 UUID: {uuid}")
    print("-" * 60)
