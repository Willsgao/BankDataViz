# -*- coding:utf-8 -*-
"""测试规则引擎"""
import sys
import os
sys.path.insert(0, r'F:\wills\codes\DocuVista')

def test_audit_engine():
    print("=" * 50)
    print("Testing Audit Engine with DAL")
    print("=" * 50)
    
    # 1. 导入模块
    print("\n[Step 1] Import modules...")
    try:
        from backend.services.dal import ExcelDataSource
        from backend.services.audit_engine import run_audit, load_rules
        print("  Import OK")
    except Exception as e:
        print(f"  Import FAILED: {e}")
        return False
    
    # 2. 创建数据源
    print("\n[Step 2] Create data source...")
    try:
        ds = ExcelDataSource()
        files = ds.get_file_list()
        print(f"  Found {len(files)} files")
    except Exception as e:
        print(f"  FAILED: {e}")
        return False
    
    # 3. 找到包含资本充足率数据的文件
    target_file = None
    for f in files:
        sheets = ds.get_sheet_names(f.id)
        for s in sheets:
            if '资本充足率' in s or '审慎监管' in s:
                target_file = f
                print(f"  Found target file with capital adequacy sheets: {f.id}")
                print(f"    Sheet: {s}")
                break
        if target_file:
            break
    
    if not target_file:
        print("  No suitable file found, using first file")
        target_file = files[0]
    
    # 4. 加载规则
    print("\n[Step 3] Load rules...")
    rules = load_rules()
    print(f"  Loaded {len(rules)} rules")
    
    # 5. 执行勾稽（使用DAL模式）
    print("\n[Step 4] Run audit with DAL mode...")
    try:
        result = run_audit(
            file_id=target_file.id,
            file_name=target_file.name,
            rule_ids=[r['id'] for r in rules],  # 测试所有规则
            data_source=ds
        )
        print(f"\n  Result Summary:")
        print(f"    Status: {result['status']}")
        print(f"    Total: {result['total']}, Pass: {result['pass_count']}, Fail: {result['fail_count']}, Warn: {result['warn_count']}")
        
        # 打印详细结果
        print("\n  Detailed results:")
        for r in result['results']:
            status_icon = {'pass': '[PASS]', 'fail': '[FAIL]', 'warn': '[WARN]'}.get(r['status'], '[???]')
            print(f"\n    {status_icon} {r['rule_id']}: {r['rule_name']}")
            print(f"         Sheet: {r['sheet_name']}")
            if r['detail']:
                print(f"         {r['detail'][:80]}...")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 50)
    print("Phase 2 TEST PASSED!")
    print("=" * 50)
    return True


if __name__ == '__main__':
    test_audit_engine()