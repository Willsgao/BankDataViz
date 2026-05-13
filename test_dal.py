# -*- coding:utf-8 -*-
"""测试数据访问层（DAL）"""
import sys
import os
sys.path.insert(0, r'F:\wills\codes\DocuVista')

from backend.services.dal import ExcelDataSource

def test_dal():
    print("=" * 50)
    print("Testing Data Access Layer (DAL)")
    print("=" * 50)
    
    # 1. Create data source
    print("\n[Step 1] Create data source...")
    ds = ExcelDataSource()
    print(f"  DataSource type: {type(ds).__name__}")
    print(f"  Excel directory: {ds.excel_data_root}")
    print(f"  Database: {ds.db_path}")
    
    # Check if directory exists
    if not os.path.exists(ds.excel_data_root):
        print(f"  Excel directory NOT EXISTS!")
        return False
    
    print("  Directory exists [OK]")
    
    # 2. Get file list
    print("\n[Step 2] Get file list...")
    files = ds.get_file_list()
    print(f"  Found {len(files)} files")
    for f in files[:5]:
        print(f"    - {f.id}: {f.name}")
    
    if not files:
        print("  (No files, skip remaining tests)")
        return True
    
    # 3. Get sheet names
    print("\n[Step 3] Get sheet names...")
    test_file = files[0]
    print(f"  Test file ID: {test_file.id}")
    sheet_names = ds.get_sheet_names(test_file.id)
    print(f"  Sheet count: {len(sheet_names)}")
    print(f"  Sheet list: {sheet_names[:5]}")
    
    if not sheet_names:
        print("  (No sheets, skip remaining tests)")
        return True
    
    # 4. Get sheet summary
    print("\n[Step 4] Get sheet summary...")
    test_sheet = sheet_names[0]
    summary = ds.get_sheet_summary(test_file.id, test_sheet)
    print(f"  Sheet: {summary.name}")
    print(f"  Row count: {summary.row_count}")
    print(f"  Col count: {summary.col_count}")
    print(f"  Header preview: {summary.header_preview[:2]}")
    
    # 5. Get full sheet data
    print("\n[Step 5] Get full sheet data...")
    sheet_data = ds.get_sheet_data(test_file.id, test_sheet)
    print(f"  Sheet: {sheet_data.name}")
    print(f"  Header rows: {len(sheet_data.headers)}")
    print(f"  Data rows: {len(sheet_data.rows)}")
    if sheet_data.rows:
        print(f"  First row (first 5 cols): {list(sheet_data.rows[0].items())[:5]}")
    
    # 6. Batch get all sheets
    print("\n[Step 6] Batch get all sheets...")
    all_sheets = ds.get_all_sheets_data(test_file.id)
    print(f"  Got {len(all_sheets)} sheets")
    
    print("\n" + "=" * 50)
    print("Phase 1 TEST PASSED!")
    print("=" * 50)
    return True


if __name__ == '__main__':
    try:
        test_dal()
    except Exception as e:
        print(f"\nTest FAILED: {e}")
        import traceback
        traceback.print_exc()