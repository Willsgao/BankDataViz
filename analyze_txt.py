#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析txt文件结构，找出表格数据区域"""

with open('data/backend/static/excel_data/智能识别_20260505_1648_raw.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('=== 分析txt文件结构 ===')
print(f'总行数: {len(lines)}')
print()

# 找到所有包含tab字符的行
tab_lines = []
for i, line in enumerate(lines, 1):
    if '\t' in line:
        tab_lines.append(i)

print(f'包含tab字符的行数: {len(tab_lines)}')
if tab_lines:
    print(f'第一个tab行: 第{tab_lines[0]}行')
    print(f'最后一个tab行: 第{tab_lines[-1]}行')
print()

# 显示表格数据区域内的所有行
if tab_lines:
    start = tab_lines[0]
    end = tab_lines[-1]
    print(f'=== 表格数据区域（第{start}-{end}行）===')
    for i in range(start-1, min(end, len(lines))):
        line = lines[i].rstrip('\n')
        has_tab = '\t' in line
        marker = '>>' if has_tab else '  '
        print(f'{marker} 第{i+1:3d}行: {line[:80]}')
print()

# 显示所有不包含tab的行（可能是分组标题）
print('=== 表格数据区域内的非tab行（可能是分组标题）===')
if tab_lines:
    start = tab_lines[0]
    end = tab_lines[-1]
    for i in range(start-1, min(end, len(lines))):
        line = lines[i].rstrip('\n')
        has_tab = '\t' in line
        if not has_tab and line.strip():
            print(f'   第{i+1:3d}行: {line[:80]}')
