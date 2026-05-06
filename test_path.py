# -*- coding:utf-8 -*-
"""测试路径计算"""
import os

# 当前文件: backend/services/dal/excel_source.py
current_file = __file__
print(f"当前文件: {current_file}")

# 逐步获取父目录
d1 = os.path.dirname(current_file)
d2 = os.path.dirname(d1)
d3 = os.path.dirname(d2)
d4 = os.path.dirname(d3)

print(f"d1 (dal): {d1}")
print(f"d2 (services): {d2}")
print(f"d3 (backend): {d3}")
print(f"d4 (DocuVista?): {d4}")

# 实际项目结构:
# F:\wills\codes\DocuVista\
#   ├── backend/
#   │   └── services/
#   │       └── dal/
#   └── data/
#       └── backend/
#           └── static/
#               └── excel_data/

# 期望的 excel_data 路径:
expected = r'F:\wills\codes\DocuVista\data\backend\static\excel_data'
print(f"\n期望的 excel_data 路径: {expected}")
print(f"是否存在: {os.path.exists(expected)}")