# -*- coding: UTF-8 -*-
import sys
sys.path.insert(0, r'F:\wills\codes\DocuVista')
from pathlib import Path
from backend.services.table_region_detector import detect_tables

p = Path(r'F:\wills\codes\DocuVista\data\backend\static\uploads\731b28f5-2bd0-141b-129f-c2ee7fda72a2.pdf')
print('Testing detect_tables on', p)
result = detect_tables(p, dpi=150)
print('Success:', result.get('success'))
print('Pages:', result.get('total_pages'))
print('Total tables:', result.get('total_tables'))
for pg in result.get('pages', []):
    render_ok = pg.get('render') is not None
    print(f"  Page {pg['page_idx']}: {pg['table_count']} tables, render={render_ok}")
print('DONE')
