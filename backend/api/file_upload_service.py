import hashlib, uuid, os
from pathlib import Path
from backend.service.file_mapping_service import file_mapping_service
from backend.utils.constants import MAIN_ROOT, UPLOAD_FOLDER

def process_upload(file_obj, raw_filename):
    """幂等上传：同内容文件只存一份"""
    # 1. 把文件读出来计算哈希（内存友好版：分块 1 MB）
    file_obj.seek(0)
    h = hashlib.md5()
    for chunk in iter(lambda: file_obj.read(1024*1024), b''):
        h.update(chunk)
    file_hash = h.hexdigest()          # 32 位小写 MD5
    file_obj.seek(0)                   # 重置指针，后面真正落盘

    # 2. 用哈希查是否已存在
    exist = file_mapping_service.get_by_hash(file_hash)
    if exist:
        # 已存在 → 直接返回旧记录
        return {
            'success': True,
            'file_id': exist['file_id'],
            'disk_name': exist['disk_name'],
            'raw_filename': exist['raw_filename'],
            'message': '文件已存在，使用已有记录'
        }

    # 3. 不存在 → 正常保存
    ext = Path(raw_filename).suffix.lower()
    file_id = str(uuid.uuid4())
    disk_name = file_id + ext
    upload_path = Path(MAIN_ROOT) / UPLOAD_FOLDER / disk_name

    # 4. 落盘 + 写库
    file_obj.save(upload_path)
    file_mapping_service.add_mapping(file_id, raw_filename, disk_name, ext[1:], file_hash=file_hash)

    return {
        'success': True,
        'file_id': file_id,
        'disk_name': disk_name,
        'raw_filename': raw_filename
    }