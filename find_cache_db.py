import os
for root, dirs, files in os.walk(r'F:\wills\codes\DocuVista'):
    if 'venv' in root or '__pycache__' in root or '.git' in root:
        continue
    for f in files:
        if f == 'cache_gateway.py':
            path = os.path.join(root, f)
            with open(path, encoding='utf-8') as fp:
                for i, line in enumerate(fp, 1):
                    if 'connect' in line.lower() and ('sqlite' in line.lower() or 'database' in line.lower() or 'db' in line.lower()):
                        print(f'{i}: {line.rstrip()}')
