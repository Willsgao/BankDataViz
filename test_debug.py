# -*- coding:utf-8 -*-
"""Debug test"""
import sys
sys.path.insert(0, r'F:\wills\codes\DocuVista')

from backend.services.dal import ExcelDataSource
from audit_engine import run_rule, load_rules

# 测试单条规则
ds = ExcelDataSource()
files = ds.get_file_list()
test_file = files[0]

rules = load_rules(r'F:\wills\codes\DocuVista\data\backend\config\audit_rules.json')
rule = rules[0]

print(f"Testing rule: {rule['id']} - {rule['name']}")
print(f"File ID: {test_file.id}")

# 获取所有sheets
all_sheets = ds.get_all_sheets_data(test_file.id)
print(f"Got {len(all_sheets)} sheets")

# 打印第一个sheet的信息
if all_sheets:
    sd = all_sheets[0]
    print(f"First sheet: {sd.name}")
    print(f"  Headers: {len(sd.headers)} rows")
    print(f"  Rows: {len(sd.rows)} rows")
    if sd.rows:
        print(f"  First row keys: {list(sd.rows[0].keys())[:5]}")

# 尝试提取关键词
keywords = []
for kw in rule['name'].replace('勾稽', '').replace('校验', '').split('、'):
    kw = kw.strip()
    if len(kw) >= 2:
        keywords.append(kw)
print(f"Keywords: {keywords}")

# 尝试执行规则
try:
    result = run_rule(rule, excel_path=None, sheet_mapping=None,
                     file_id=test_file.id, data_source=ds)
    print(f"Result: {result['status']}")
    print(f"Detail: {result['detail']}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()