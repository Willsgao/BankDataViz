# backend/init_file_mapping.py
import os
from pathlib import Path
import sys
import sqlite3

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.file_mapping_service import file_mapping_service
from backend.utils.constants import UPLOAD_FOLDER, DATABASE


def init_existing_files_mapping():
    """为现有文件创建映射（从数据库获取原始中文名）"""

    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 获取所有未删除的文件
    c.execute("SELECT filename, raw_filename, file_type FROM files WHERE deleted = 0")
    db_files = c.fetchall()
    conn.close()

    file_count = 0
    for row in db_files:
        disk_filename = row['filename']  # 磁盘上的文件名
        raw_filename = row['raw_filename']  # 原始中文文件名
        file_type = row['file_type']

        # 提取文件ID（去掉扩展名）
        if '.' in disk_filename:
            file_id = disk_filename.split('.')[0]

            # 检查文件是否实际存在
            file_path = Path(UPLOAD_FOLDER) / disk_filename
            if file_path.exists():
                # 添加到映射（使用原始中文名）
                file_mapping_service.add_mapping(file_id, raw_filename, file_type)
                print(f"添加文件映射: {file_id} -> {raw_filename}")
                file_count += 1
            else:
                print(f"警告: 文件不存在: {disk_filename}")
        else:
            print(f"警告: 文件名格式不正确: {disk_filename}")

    print(f"映射初始化完成，共处理 {file_count} 个文件")


if __name__ == "__main__":
    init_existing_files_mapping()