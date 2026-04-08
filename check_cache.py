import sys
sys.path.insert(0, 'F:/wills/codes/DocuVista/backend')

from core.table_processor.cache_gateway import get_cache_stats

stats = get_cache_stats()
print('总缓存记录:', stats['total_records'])

for p in stats['providers']:
    print(f"\nProvider: {p['provider']}, 记录数: {p['record_count']}")
    if p.get('sample'):
        print('示例 s3_key:', p['sample'][:5])
