import os, sqlite3
for root, dirs, files in os.walk(r'F:\wills\codes\DocuVista'):
    if any(x in root for x in ['venv', '__pycache__', '.git', 'node_modules']):
        continue
    for f in files:
        if f.endswith('.db'):
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            rel = os.path.relpath(path, r'F:\wills\codes\DocuVista')
            try:
                conn = sqlite3.connect(path)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cur.fetchall()]
                conn.close()
                print(f"{rel}: {size} bytes, tables={tables}")
            except Exception as e:
                print(f"{rel}: {size} bytes, ERROR: {e}")
