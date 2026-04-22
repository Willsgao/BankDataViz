import os, glob
root = r'F:\wills\codes\DocuVista\frontend\src'
for f in glob.glob(os.path.join(root, '**', '*.vue'), recursive=True):
    try:
        with open(f, encoding='utf-8', errors='ignore') as fp:
            for i, line in enumerate(fp, 1):
                if 'disk_name' in line.lower():
                    rel = os.path.relpath(f, root)
                    print(f"{rel}:{i}: {line.rstrip()}")
    except Exception as e:
        print(f"Error: {e}")
