# -*- coding:utf-8 -*-
"""
文件上传服务类
集中处理文件上传、去重、映射等逻辑
"""

import os
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from backend.utils.constants import UPLOAD_FOLDER, DATABASE, MAIN_ROOT, ALLOWED_EXTENSIONS
from backend.service.file_mapping_service import file_mapping_service


class FileUploadService:
    """文件上传服务"""

    def __init__(self):
        self.db_path = DATABASE
        self.upload_dir = Path(MAIN_ROOT) / UPLOAD_FOLDER

    def allowed_file(self, filename):
        """检查文件类型是否允许"""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def calculate_file_hash(self, file_content):
        """计算文件的MD5哈希值"""
        return hashlib.md5(file_content).hexdigest()

    def check_table_columns(self):
        """确保数据库表有必要的列"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # 检查表结构
            c.execute("PRAGMA table_info(files)")
            columns = c.fetchall()
            existing_cols = {col[1] for col in columns}

            # 需要添加的列
            new_columns = {
                'file_hash': 'TEXT',
                'file_size': 'INTEGER',
                'upload_count': 'INTEGER DEFAULT 1',
                'last_uploaded': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }

            for col_name, col_type in new_columns.items():
                if col_name not in existing_cols:
                    print(f"🔧 添加缺失列: {col_name} {col_type}")
                    try:
                        c.execute(f"ALTER TABLE files ADD COLUMN {col_name} {col_type}")
                        conn.commit()
                        print(f"✅ 列 {col_name} 添加成功")
                    except Exception as e:
                        print(f"⚠️ 添加列 {col_name} 失败: {e}")

        except Exception as e:
            print(f"❌ 检查表结构失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def get_existing_file(self, file_hash):
        """根据哈希值检查文件是否已存在"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute("""
                SELECT id, filename, raw_filename, upload_count, created_at, file_size
                FROM files 
                WHERE file_hash = ? AND deleted = 0 AND file_hash IS NOT NULL
                LIMIT 1
            """, (file_hash,))

            return c.fetchone()
        except Exception as e:
            print(f"❌ 查询重复文件失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def increment_upload_count(self, file_id):
        """增加文件的上传次数"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute("""
                UPDATE files 
                SET upload_count = upload_count + 1, 
                    last_uploaded = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (file_id,))
            conn.commit()

            return True
        except Exception as e:
            print(f"❌ 更新上传次数失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def save_new_file(self, file_content, raw_filename, file_hash):
        """保存新文件到磁盘和数据库"""
        import uuid

        # 生成文件ID和存储路径
        ext = os.path.splitext(raw_filename)[1].lower()
        file_id = str(uuid.uuid4())
        disk_filename = f"{file_id}{ext}"
        file_path = self.upload_dir / disk_filename

        # 确保上传目录存在
        if not self.upload_dir.exists():
            print(f"📁 创建上传目录: {self.upload_dir}")
            self.upload_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件到磁盘
        print(f"💾 保存新文件到: {file_path}")
        try:
            file_path.write_bytes(file_content)
        except Exception as e:
            print(f"❌ 文件保存失败: {e}")
            return None

        # 保存到数据库
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            file_type = ext[1:] if ext.startswith('.') else ext
            file_size = len(file_content)

            c.execute("""
                INSERT INTO files 
                (filename, file_type, raw_filename, deleted, file_hash, file_size, upload_count) 
                VALUES (?, ?, ?, 0, ?, ?, 1)
            """, (disk_filename, file_type, raw_filename, file_hash, file_size))

            new_id = c.lastrowid
            conn.commit()

            print(f"✅ 数据库插入成功 - 新记录ID: {new_id}")

            return {
                "id": new_id,
                "file_id": file_id,
                "disk_filename": disk_filename,
                "file_type": file_type,
                "file_size": file_size,
                "file_hash": file_hash
            }

        except Exception as e:
            print(f"❌ 数据库插入失败: {e}")
            if conn:
                conn.rollback()

            # 删除已保存的文件
            if file_path.exists():
                file_path.unlink()

            return None
        finally:
            if conn:
                conn.close()

    def process_upload(self, file, raw_filename):
        """处理文件上传的主方法"""
        print("=" * 50)
        print("🔄 开始处理文件上传...")
        print(f"📄 原始文件名: {raw_filename}")

        # 1. 基础验证
        if not self.allowed_file(raw_filename):
            return {
                "success": False,
                "error": "文件类型不允许",
                "status_code": 400
            }

        # 2. 读取文件内容并计算哈希
        file_content = file.read()
        file.seek(0)  # 重置指针

        if len(file_content) == 0:
            return {
                "success": False,
                "error": "文件内容为空",
                "status_code": 400
            }

        file_size = len(file_content)
        file_hash = self.calculate_file_hash(file_content)

        print(f"📄 文件大小: {file_size} bytes")
        print(f"🔢 文件哈希: {file_hash}")

        # 3. 确保数据库表结构完整
        self.check_table_columns()

        # 4. 检查重复
        existing_file = self.get_existing_file(file_hash)

        if existing_file:
            # 处理重复文件
            return self._handle_duplicate(existing_file, raw_filename, file_size, file_hash)
        else:
            # 处理新文件
            return self._handle_new_file(file_content, raw_filename, file_hash)

    def _handle_duplicate(self, existing_file, raw_filename, file_size, file_hash):
        """处理重复文件"""
        print("🔄 发现重复文件")

        file_id = existing_file[0]
        disk_filename = existing_file[1]
        existing_raw_name = existing_file[2]
        upload_count = existing_file[3] + 1
        created_at = existing_file[4]
        existing_file_size = existing_file[5]

        # 提取file_id（去掉扩展名）
        existing_file_id = disk_filename.split('.')[0] if '.' in disk_filename else disk_filename

        print(f"   数据库ID: {file_id}")
        print(f"   文件ID: {existing_file_id}")
        print(f"   磁盘文件名: {disk_filename}")
        print(f"   已有上传次数: {upload_count - 1}")

        # 更新上传次数
        if not self.increment_upload_count(file_id):
            print("⚠️ 更新上传次数失败，但继续处理...")

        # 添加文件映射
        ext = os.path.splitext(raw_filename)[1].lower()
        try:
            file_mapping_service.add_mapping(existing_file_id, raw_filename, ext[1:].lower())
            print(f"✅ 重复文件映射添加成功")
        except Exception as e:
            print(f"⚠️ 文件映射添加失败: {e}")

        # 构建响应
        response = {
            "success": True,
            "id": file_id,
            "filename": raw_filename,
            "file_type": ext[1:] if ext.startswith('.') else ext,
            "disk_name": disk_filename,
            "file_id": existing_file_id,
            "file_hash": file_hash[:12],
            "file_size": file_size,
            "upload_count": upload_count,
            "created_at": created_at,
            "message": "文件已存在（内容相同），直接使用现有文件",
            "duplicate": True
        }

        print(f"✅ 重复文件处理完成")
        print("=" * 50)

        return response

    def _handle_new_file(self, file_content, raw_filename, file_hash):
        """处理新文件"""
        print("🆕 处理新文件")

        # 保存文件
        result = self.save_new_file(file_content, raw_filename, file_hash)

        if not result:
            return {
                "success": False,
                "error": "文件保存失败",
                "status_code": 500
            }

        # 添加文件映射
        ext = os.path.splitext(raw_filename)[1].lower()
        try:
            file_mapping_service.add_mapping(result["file_id"], raw_filename, ext[1:].lower())
            print(f"✅ 新文件映射添加成功")
        except Exception as e:
            print(f"⚠️ 文件映射添加失败: {e}")

        # 构建响应
        response = {
            "success": True,
            "id": result["id"],
            "filename": raw_filename,
            "file_type": result["file_type"],
            "disk_name": result["disk_filename"],
            "file_id": result["file_id"],
            "file_hash": file_hash[:12],
            "file_size": result["file_size"],
            "upload_count": 1,
            "message": "新文件上传成功",
            "duplicate": False
        }

        print(f"✅ 新文件上传完成")
        print("=" * 50)

        return response


# 创建全局实例
file_upload_service = FileUploadService()