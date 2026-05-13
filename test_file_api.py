"""测试 /api/file 接口"""
import requests
try:
    r = requests.get(
        'http://localhost:5000/api/file/731b28f5-2bd0-141b-129f-c2ee7fda72a2.pdf',
        timeout=5
    )
    print('Status:', r.status_code)
    print('Content-Type:', r.headers.get('Content-Type', 'N/A'))
    print('Content-Length:', len(r.content))
    print('First 100 bytes:', r.content[:100])
except Exception as e:
    print('Error:', e)
