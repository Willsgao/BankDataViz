# -*- coding:utf-8 -*-
"""测试 Excel 上传修复"""
import sys
sys.path.insert(0, 'F:/wills/codes/DocuVista')

from backend.models.unified_db import UnifiedDatabaseManager

# 初始化数据库管理器
db_mgr = UnifiedDatabaseManager()

# 测试保存 Excel 文件记录
file_info = {
    'filename': 'test.xlsx',
    'disk_name': 'test_uuid.xlsx',
    'file_path': 'F:/wills/codes/DocuVista/data/backend/static/excel_uploads/test_uuid.xlsx',
    'file_size': 1024,
    'uploader_id': 1,
    'uploader_name': 'Test User',
    'description': 'Test upload'
}

success, result = db_mgr.save_excel_file(file_info)
print(f"Save result: success={success}, result={result}")

if success:
    print("[OK] Excel 文件记录保存成功！")
else:
    print(f"[FAIL] 保存失败: {result}")
