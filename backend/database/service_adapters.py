"""
服务类数据库适配器 - 第三步：为服务类提供统一的数据库连接
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib
import uuid

# 导入统一的数据库配置
from . import get_db_connection, get_database_path, get_upload_folder, get_main_root


class FileUploadServiceAdapter:
    """
    FileUploadService 的适配器
    保持完全相同的接口，但内部使用新的统一数据库管理器
    """

    def __init__(self):
        # 使用统一配置
        self.db_path = get_database_path()
        self.upload_dir = Path(get_main_root()) / get_upload_folder()

        # 确保上传目录存在
        if not self.upload_dir.exists():
            print(f"📁📁📁📁 创建上传目录: {self.upload_dir}")
            self.upload_dir.mkdir(parents=True, exist_ok=True)

        print(f"🔄 FileUploadServiceAdapter 初始化完成")

    def allowed_file(self, filename):
        """完全复制原始方法"""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

    def calculate_file_hash(self, file_content):
        """完全复制原始方法"""
        return hashlib.md5(file_content).hexdigest()

    def generate_deterministic_uuid(self, file_content):
        """完全复制原始方法"""
        md5_hash = hashlib.md5(file_content).hexdigest()
        try:
            return uuid.UUID(hex=md5_hash)
        except ValueError:
            return uuid.uuid3(uuid.NAMESPACE_URL, md5_hash)

    def generate_smart_uuid(self, file_content, raw_filename=None, file_size=None):
        """完全复制原始方法"""
        if file_size is None:
            file_size = len(file_content)

        if raw_filename is None:
            md5_hash = hashlib.md5(file_content).hexdigest()
            return uuid.UUID(hex=md5_hash)

        # 1. 先检查是否银行标准命名
        if self.is_standard_bank_filename(raw_filename):
            combined = f"{raw_filename}_{file_size}".encode('utf-8')
            print(f"🏦🏦 银行文档模式: {raw_filename} (大小: {file_size} bytes)")
        else:
            combined = file_content
            print(f"📄📄 普通文档模式: 基于内容 (大小: {file_size} bytes)")

        md5_hash = hashlib.md5(combined).hexdigest()
        return uuid.UUID(hex=md5_hash)

    def is_standard_bank_filename(self, filename):
        """完全复制原始方法"""
        import re
        patterns = [
            r'\d{4}-\d{2}-\d{2}-\d{6}\.(SH|SZ)-',
            r'.*银行.*\d{4}.*报告',
            r'.*银行.*财务报表',
            r'.*银行.*报.*',
        ]

        for pattern in patterns:
            if re.search(pattern, filename):
                return True
        return False

    def extract_bank_name(self, filename):
        """完全复制原始方法"""
        try:
            from backend.src.services.table_processor.get_bank_name import SimpleBankNameExtractor
            extractor = SimpleBankNameExtractor()
            bank_name = extractor.extract_bank_name(filename)
            return bank_name if bank_name else ""
        except Exception as e:
            print(f"⚠️ 银行名称提取失败: {e}")
            return ""

    def check_table_columns(self):
        """完全复制原始方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
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
                    'last_uploaded': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'bank_name': 'TEXT'
                }

                for col_name, col_type in new_columns.items():
                    if col_name not in existing_cols:
                        print(f"🔧🔧🔧🔧 添加缺失列: {col_name} {col_type}")
                        try:
                            c.execute(f"ALTER TABLE files ADD COLUMN {col_name} {col_type}")
                            conn.commit()
                            print(f"✅ 列 {col_name} 添加成功")
                        except Exception as e:
                            print(f"⚠️ 添加列 {col_name} 失败: {e}")

        except Exception as e:
            print(f"❌❌❌❌ 检查表结构失败: {e}")

    def get_existing_file(self, file_hash, raw_filename=None):
        """完全复制原始方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                # 优先检查完全匹配
                if raw_filename:
                    c.execute("""
                        SELECT id, filename, raw_filename, upload_count, created_at, file_size, bank_name
                        FROM files 
                        WHERE file_hash = ? AND raw_filename = ? AND deleted = 0 AND file_hash IS NOT NULL
                        LIMIT 1
                    """, (file_hash, raw_filename))

                    exact_match = c.fetchone()
                    if exact_match:
                        print(f"✅✅ 找到完全匹配文件: {raw_filename}")
                        return exact_match

                # 检查内容相同的文件
                c.execute("""
                    SELECT id, filename, raw_filename, upload_count, created_at, file_size, bank_name
                    FROM files 
                    WHERE file_hash = ? AND deleted = 0 AND file_hash IS NOT NULL
                    LIMIT 1
                """, (file_hash,))

                return c.fetchone()
        except Exception as e:
            print(f"❌❌❌❌❌❌❌❌ 查询重复文件失败: {e}")
            return None

    def increment_upload_count(self, file_id, bank_name=""):
        """完全复制原始方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                if bank_name:
                    c.execute("""
                        UPDATE files 
                        SET upload_count = upload_count + 1, 
                            last_uploaded = CURRENT_TIMESTAMP,
                            bank_name = ?
                        WHERE id = ?
                    """, (bank_name, file_id))
                    print(f"🏦🏦🏦🏦 更新银行名称: {bank_name}")
                else:
                    c.execute("""
                        UPDATE files 
                        SET upload_count = upload_count + 1, 
                            last_uploaded = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (file_id,))

                conn.commit()
                return True
        except Exception as e:
            print(f"❌❌❌❌ 更新上传次数失败: {e}")
            return False

    def save_new_file(self, file_content, raw_filename, file_hash, bank_name="", file_size=None):
        """完全复制原始方法，只修改连接方式"""
        if file_size is None:
            file_size = len(file_content)

        # 生成智能UUID
        file_id = self.generate_smart_uuid(file_content, raw_filename, file_size)

        ext = os.path.splitext(raw_filename)[1].lower()
        disk_filename = f"{file_id}{ext}"
        file_path = self.upload_dir / disk_filename

        # 确保上传目录存在
        if not self.upload_dir.exists():
            print(f"📁📁📁📁 创建上传目录: {self.upload_dir}")
            self.upload_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件到磁盘
        print(f"💾💾💾💾 保存新文件到: {file_path}")
        try:
            file_path.write_bytes(file_content)
        except Exception as e:
            print(f"❌❌❌❌ 文件保存失败: {e}")
            return None

        # 保存到数据库
        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                file_type = ext[1:] if ext.startswith('.') else ext
                file_size = len(file_content)

                c.execute("""
                    INSERT INTO files 
                    (filename, file_type, raw_filename, deleted, file_hash, file_size, upload_count, bank_name) 
                    VALUES (?, ?, ?, 0, ?, ?, 1, ?)
                """, (disk_filename, file_type, raw_filename, file_hash, file_size, bank_name))

                new_id = c.lastrowid
                conn.commit()

                print(f"✅ 数据库插入成功 - 新记录ID: {new_id}")
                print(f"🏦🏦🏦🏦 银行名称已保存: {bank_name}")
                print(f"🆔🆔🆔🆔🆔🆔 确定性UUID: {file_id}")

                return {
                    "id": new_id,
                    "file_id": str(file_id),
                    "disk_filename": disk_filename,
                    "file_type": file_type,
                    "file_size": file_size,
                    "file_hash": file_hash,
                    "bank_name": bank_name
                }

        except Exception as e:
            print(f"❌❌❌❌ 数据库插入失败: {e}")
            # 删除已保存的文件
            if file_path.exists():
                file_path.unlink()
            return None

    def process_upload(self, file, raw_filename):
        """完全复制原始方法，只修改连接方式"""
        print("=" * 50)
        print("🔄🔄🔄🔄🔄🔄🔄🔄 开始处理文件上传...")
        print(f"📄📄📄📄📄📄📄📄 原始文件名: {raw_filename}")

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

        print(f"📄📄📄📄📄📄📄📄 文件大小: {file_size} bytes")
        print(f"🔢🔢🔢🔢🔢🔢🔢🔢 文件哈希: {file_hash}")

        # 3. 提取银行名称
        bank_name = self.extract_bank_name(raw_filename)
        print(f"🏦🏦🏦🏦🏦🏦🏦🏦 识别到的银行名称: {bank_name if bank_name else '无'}")

        # 4. 确保数据库表结构完整
        self.check_table_columns()

        # 5. 检查重复
        existing_file = self.get_existing_file(file_hash, raw_filename)

        if existing_file:
            return self._handle_duplicate(existing_file, raw_filename, file_size, file_hash, bank_name)
        else:
            return self._handle_new_file(file_content, raw_filename, file_hash, bank_name)

    def _handle_duplicate(self, existing_file, raw_filename, file_size, file_hash, bank_name=""):
        """完全复制原始方法"""
        print("🔄🔄🔄🔄🔄🔄🔄🔄 发现重复文件")

        file_id = existing_file[0]
        disk_filename = existing_file[1]
        existing_raw_name = existing_file[2]
        upload_count = existing_file[3] + 1
        created_at = existing_file[4]
        existing_file_size = existing_file[5]
        existing_bank_name = existing_file[6]

        existing_file_id = disk_filename.split('.')[0] if '.' in disk_filename else disk_filename

        print(f"   数据库ID: {file_id}")
        print(f"   文件ID: {existing_file_id}")
        print(f"   磁盘文件名: {disk_filename}")
        print(f"   已有上传次数: {upload_count - 1}")
        print(f"   匹配类型: {'完全匹配（名称+内容）' if existing_raw_name == raw_filename else '内容匹配'}")

        # 更新上传次数
        update_bank_name = bank_name if bank_name and bank_name != existing_bank_name else ""
        if not self.increment_upload_count(file_id, update_bank_name):
            print("⚠️ 更新上传次数失败，但继续处理...")

        # 添加文件映射（只有在不是完全匹配时才需要添加新映射）
        if existing_raw_name != raw_filename:
            ext = os.path.splitext(raw_filename)[1].lower()
            try:
                from backend.service.file_mapping_service import file_mapping_service
                file_mapping_service.add_mapping(existing_file_id, raw_filename, ext[1:].lower())
                print(f"✅ 新文件名映射添加成功")
            except Exception as e:
                print(f"⚠️ 文件映射添加失败: {e}")
        else:
            print(f"✅ 完全匹配，无需添加新映射")

        # 构建响应
        response = {
            "success": True,
            "id": file_id,
            "filename": raw_filename,
            "file_type": os.path.splitext(raw_filename)[1][1:].lower(),
            "disk_name": disk_filename,
            "file_id": existing_file_id,
            "file_hash": file_hash[:12],
            "file_size": file_size,
            "upload_count": upload_count,
            "bank_name": bank_name or existing_bank_name,
            "created_at": created_at,
            "message": "文件已存在（内容相同），直接使用现有文件",
            "duplicate": True,
            "exact_match": existing_raw_name == raw_filename
        }

        print(f"✅ 重复文件处理完成")
        print("=" * 50)
        return response

    def _handle_new_file(self, file_content, raw_filename, file_hash, bank_name=""):
        """完全复制原始方法"""
        print("🆕🆕🆕🆕🆕🆕🆕🆕🆕 处理新文件")

        file_size = len(file_content)
        result = self.save_new_file(file_content, raw_filename, file_hash, bank_name, file_size)

        if not result:
            return {
                "success": False,
                "error": "文件保存失败",
                "status_code": 500
            }

        # 添加文件映射
        ext = os.path.splitext(raw_filename)[1].lower()
        try:
            from backend.service.file_mapping_service import file_mapping_service
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
            "bank_name": bank_name,
            "message": "新文件上传成功",
            "duplicate": False
        }

        print(f"✅ 新文件上传完成")
        print("=" * 50)
        return response


class FileManagementServiceAdapter:
    """
    FileManagementService 的适配器
    """

    def __init__(self):
        self.db_path = get_database_path()
        self.upload_dir = Path(get_main_root()) / get_upload_folder()
        print(f"🔄 FileManagementServiceAdapter 初始化完成")

    def get_file_stats(self):
        """完全复制原始方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                # 总文件数
                c.execute("SELECT COUNT(*) FROM files WHERE deleted = 0")
                total_files = c.fetchone()[0]

                # 总文件大小
                c.execute("SELECT SUM(file_size) FROM files WHERE deleted = 0 AND file_size IS NOT NULL")
                total_size = c.fetchone()[0] or 0

                # 去重后的文件数
                c.execute("""
                    SELECT COUNT(DISTINCT file_hash) 
                    FROM files 
                    WHERE deleted = 0 AND file_hash IS NOT NULL
                """)
                unique_files = c.fetchone()[0]

                # 平均上传次数
                c.execute("SELECT AVG(upload_count) FROM files WHERE deleted = 0")
                avg_uploads = c.fetchone()[0] or 0

                # 最近24小时上传
                c.execute("""
                    SELECT COUNT(*) 
                    FROM files 
                    WHERE deleted = 0 
                    AND created_at > datetime('now', '-1 day')
                """)
                recent_24h = c.fetchone()[0]

                return {
                    "total_files": total_files,
                    "unique_files": unique_files,
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
                    "duplicate_count": total_files - unique_files,
                    "storage_savings_bytes": total_size - (total_size / max(avg_uploads, 1)) if total_size else 0,
                    "avg_upload_count": round(avg_uploads, 2),
                    "recent_24h_uploads": recent_24h,
                    "storage_efficiency": round(unique_files / total_files * 100, 2) if total_files > 0 else 100
                }

        except Exception as e:
            print(f"❌❌ 获取文件统计失败: {e}")
            return None

    def find_duplicates(self, limit=20):
        """完全复制原始方法，只修改连接方式"""
        try:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()

                c.execute("""
                    SELECT 
                        file_hash,
                        COUNT(*) as file_count,
                        GROUP_CONCAT(raw_filename, '|') as filenames,
                        SUM(file_size) as total_size,
                        MAX(created_at) as last_upload,
                        MIN(created_at) as first_upload,
                        GROUP_CONCAT(id) as file_ids
                    FROM files 
                    WHERE deleted = 0 
                      AND file_hash IS NOT NULL 
                      AND file_hash != ''
                    GROUP BY file_hash 
                    HAVING COUNT(*) > 1
                    ORDER BY total_size DESC, file_count DESC
                    LIMIT ?
                """, (limit,))

                duplicates = []
                for row in c.fetchall():
                    filenames = row['filenames'].split('|')
                    file_ids = list(map(int, row['file_ids'].split(',')))

                    potential_saving = row['total_size'] - (row['total_size'] / row['file_count'])

                    duplicates.append({
                        "hash": row['file_hash'],
                        "hash_short": row['file_hash'][:12] + "...",
                        "file_count": row['file_count'],
                        "filenames": filenames,
                        "total_size_bytes": row['total_size'],
                        "total_size_mb": round(row['total_size'] / (1024 * 1024), 2),
                        "potential_saving_bytes": potential_saving,
                        "potential_saving_mb": round(potential_saving / (1024 * 1024), 2),
                        "first_upload": row['first_upload'],
                        "last_upload": row['last_upload'],
                        "file_ids": file_ids,
                        "efficiency_percent": round(100 / row['file_count'], 2)
                    })

                return duplicates

        except Exception as e:
            print(f"❌❌ 查找重复文件失败: {e}")
            return []

    # 其他方法类似实现...


# 创建服务适配器实例
file_upload_service_adapter = FileUploadServiceAdapter()
file_management_service_adapter = FileManagementServiceAdapter()

print("✅ 第三步完成：创建了服务类的数据库适配器")