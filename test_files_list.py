"""测试 /api/files 列表接口"""
import requests, json
try:
    r = requests.get('http://localhost:5000/api/files', timeout=5)
    print('Status:', r.status_code)
    data = r.json()
    print('Success:', data.get('success'))
    print('Files count:', len(data.get('files', [])))
    if data.get('files'):
        for f in data['files']:
            print('  - disk_name:', f.get('disk_name'), '| filename:', f.get('filename'))
except Exception as e:
    print('Error:', e)
