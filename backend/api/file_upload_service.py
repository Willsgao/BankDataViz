import hashlib, uuid, os
from pathlib import Path
from backend.service.file_mapping_service import file_mapping_service
from backend.utils.constants import MAIN_ROOT, UPLOAD_FOLDER


# file_upload_service.py - 增强版本
def process_upload(file_obj, raw_filename):
    """幂等上传：同内容文件只存一份"""
    try:
        # 1. 计算哈希
        file_obj.seek(0)
        h = hashlib.md5()
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b''):
            h.update(chunk)
        file_hash = h.hexdigest()
        file_obj.seek(0)

        # 2. 用哈希查是否已存在（包括已删除的）
        exist = file_mapping_service.get_by_hash(file_hash, include_deleted=True)

        if exist:
            # 检查是否已删除
            if exist.get('deleted', 0) == 1:
                # 恢复已删除的文件
                file_mapping_service.restore_file(exist['file_id'])
                return {
                    'success': True,
                    'file_id': exist['file_id'],
                    'disk_name': exist['disk_name'],
                    'raw_filename': exist['raw_filename'],
                    'message': '文件已恢复（之前被删除）',
                    'is_new': False,
                    'was_deleted': True
                }
            else:
                # 文件已存在且未删除
                return {
                    'success': True,
                    'file_id': exist['file_id'],
                    'disk_name': exist['disk_name'],
                    'raw_filename': exist['raw_filename'],
                    'message': '文件已存在，使用已有记录',
                    'is_new': False,
                    'was_deleted': False
                }

        # 3. 全新文件
        ext = Path(raw_filename).suffix.lower()
        file_id = str(uuid.uuid4())
        disk_name = file_id + ext
        upload_path = Path(MAIN_ROOT) / UPLOAD_FOLDER / disk_name

        # 保存文件
        file_obj.save(upload_path)

        # 记录文件大小
        file_size = upload_path.stat().st_size

        # 添加到映射
        file_mapping_service.add_mapping(
            file_id=file_id,
            raw_filename=raw_filename,
            disk_name=disk_name,
            file_type=ext[1:],
            file_hash=file_hash,
            file_size=file_size
        )

        return {
            'success': True,
            'file_id': file_id,
            'disk_name': disk_name,
            'raw_filename': raw_filename,
            'message': '上传成功',
            'is_new': True,
            'file_size': file_size
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'status_code': 500
        }

