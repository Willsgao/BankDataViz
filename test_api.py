# -*- coding:utf-8 -*-
"""测试新增的DAL API"""
import sys
sys.path.insert(0, r'F:\wills\codes\DocuVista')

def test_dal_apis():
    print("=" * 50)
    print("Testing DAL APIs")
    print("=" * 50)
    
    # 测试1: list_files_dal
    print("\n[Test 1] list_files_dal...")
    try:
        from backend.services.dal import ExcelDataSource
        ds = ExcelDataSource()
        files = ds.get_file_list()
        print(f"  Found {len(files)} files")
        for f in files:
            print(f"    - {f.id}: {f.name}")
        if files:
            test_file = files[1]  # 使用包含资本充足率的文件
            print(f"  Using test file: {test_file.id}")
    except Exception as e:
        print(f"  FAILED: {e}")
        return False
    
    # 测试2: get_sheets_dal
    print("\n[Test 2] get_sheets_dal...")
    try:
        sheets = ds.get_sheet_names(test_file.id)
        print(f"  Found {len(sheets)} sheets")
        for s in sheets[:5]:
            print(f"    - {s}")
    except Exception as e:
        print(f"  FAILED: {e}")
        return False
    
    # 测试3: get_sheet_summary
    print("\n[Test 3] get_sheet_summary...")
    try:
        test_sheet = 'P005_1_T_监管并表关键审慎监管指标表'
        if test_sheet in sheets:
            summary = ds.get_sheet_summary(test_file.id, test_sheet)
            print(f"  Sheet: {summary.name}")
            print(f"  Rows: {summary.row_count}, Cols: {summary.col_count}")
            print(f"  Headers: {summary.header_preview[:2]}")
        else:
            print(f"  Sheet '{test_sheet}' not found, using first sheet")
            summary = ds.get_sheet_summary(test_file.id, sheets[0])
            print(f"  Sheet: {summary.name}")
    except Exception as e:
        print(f"  FAILED: {e}")
        return False
    
    # 测试4: get_sheet_data
    print("\n[Test 4] get_sheet_data...")
    try:
        sheet_data = ds.get_sheet_data(test_file.id, summary.name)
        print(f"  Headers: {len(sheet_data.headers)} rows")
        print(f"  Data rows: {len(sheet_data.rows)}")
        if sheet_data.rows:
            print(f"  First row (first 5 cols): {list(sheet_data.rows[0].items())[:5]}")
    except Exception as e:
        print(f"  FAILED: {e}")
        return False
    
    # 测试5: 字段分析
    print("\n[Test 5] Field analysis...")
    try:
        from audit_engine import load_rules
        rules = load_rules(r'F:\wills\codes\DocuVista\data\backend\config\audit_rules.json')
        test_rule = rules[0]
        print(f"  Testing rule: {test_rule['id']} - {test_rule['name']}")
        
        # 检查规则需要哪些字段
        needed_fields = []
        if 'formula' in test_rule:
            formula = test_rule['formula']
            for part in ['numerator', 'denominator', 'result_field']:
                f = formula.get(part, {})
                if isinstance(f, dict):
                    needed_fields.append(f.get('field', ''))
                elif f:
                    needed_fields.append(str(f))
        print(f"  Needed fields: {needed_fields}")
        
        # 在Sheet中查找
        for nf in needed_fields:
            found = False
            for row in sheet_data.rows[:20]:
                for col_key, val in row.items():
                    if val and nf in str(val):
                        found = True
                        print(f"    FOUND: '{nf}' in cell: {str(val)[:50]}...")
                        break
                if found:
                    break
            if not found:
                print(f"    NOT FOUND: '{nf}'")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 50)
    print("Phase 3 API TEST PASSED!")
    print("=" * 50)
    return True


if __name__ == '__main__':
    test_dal_apis()