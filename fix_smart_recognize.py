import re

with open('backend/api/smart_recognize.py', 'r', encoding='utf-8') as f:
    content = f.read()

fixed = 0

# 1. 修正全角引号为半角引号
replacements = {
    '\u201c': '"',   # 左双引号
    '\u201d': '"',   # 右双引号
    '\u2018': "'",   # 左单引号
    '\u2019': "'",   # 右单引号
}
for old, new in replacements.items():
    if old in content:
        content = content.replace(old, new)
        fixed += 1
        print(f"修正了全角引号: {repr(old)} -> {repr(new)}")

# 2. 修正 clean_ed -> cleaned 的拼写错误
# 只修正变量名，不修正注释或字符串中的内容
lines = content.split('\n')
new_lines = []
for line in lines:
    # 修正变量名 clean_ed 为 cleaned (只修正 Python 标识符)
    new_line = re.sub(r'\bclean_ed\b', 'cleaned', line)
    if new_line != line:
        fixed += 1
    new_lines.append(new_line)

content = '\n'.join(new_lines)

if fixed:
    with open('backend/api/smart_recognize.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"共修正了 {fixed} 处问题")
else:
    print("未发现需要修正的问题")

# 验证语法
try:
    import ast
    ast.parse(content)
    print("✅ 语法检查通过")
except SyntaxError as e:
    print(f"❌ 语法错误: {e}")
