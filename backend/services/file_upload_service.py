# -*- coding:utf-8 -*-
"""
文件上传服务类
集中处理文件上传、去重、映射等逻辑
"""

import os
import sqlite3
import hashlib
import uuid  # 🆕 添加uuid导入
from pathlib import Path
from backend.utils.constants import UPLOAD_FOLDER, DATABASE, MAIN_ROOT, ALLOWED_EXTENSIONS
from backend.services.file_mapping_service import file_mapping_service

from backend.core.table_processor.get_bank_name import SimpleBankNameExtractor

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

    # 🆕 新增：基于文件内容生成确定性UUID
    def generate_deterministic_uuid(self, file_content):
        """确保跨服务一致性的UUID生成"""
        # 使用MD5哈希（32字符，正好符合UUID格式）
        md5_hash = hashlib.md5(file_content).hexdigest()
        print("哈希密码值:", md5_hash)

        print("md5_hash:", md5_hash)

        try:
            # 直接基于MD5哈希构造UUID（最可靠）
            return uuid.UUID(hex=md5_hash)
        except ValueError:
            # 备用方案：如果MD5格式有问题，使用uuid3
            return uuid.uuid3(uuid.NAMESPACE_URL, md5_hash)

    def generate_smart_uuid(self, file_content, raw_filename=None, file_size=None):
        """智能UUID生成策略"""

        # 参数处理
        if file_size is None:
            file_size = len(file_content)

        if raw_filename is None:
            # 如果没有文件名，回退到基于内容的UUID
            md5_hash = hashlib.md5(file_content).hexdigest()
            return uuid.UUID(hex=md5_hash)

        # 1. 先检查是否银行标准命名
        if self.is_standard_bank_filename(raw_filename):
            # 银行文档：使用文件名+文件大小（更稳定）
            combined = f"{raw_filename}_{file_size}".encode('utf-8')
            print(f"🏦 银行文档模式: {raw_filename} (大小: {file_size} bytes)")
        else:
            # 非标准命名：使用完整内容（确保唯一性）
            combined = file_content
            print(f"📄 普通文档模式: 基于内容 (大小: {file_size} bytes)")

        md5_hash = hashlib.md5(combined).hexdigest()
        return uuid.UUID(hex=md5_hash)

    def is_standard_bank_filename(self, filename):
        """判断是否为标准银行文档文件名"""
        patterns = [
            r'\d{4}-\d{2}-\d{2}-\d{6}\.(SH|SZ)-',  # 股票代码格式
            r'.*银行.*\d{4}.*报告',  # 银行年度报告
            r'.*银行.*财务报表',  # 财务报表
            r'.*银行.*报.*',  # 财务报表
        ]

        import re
        for pattern in patterns:
            if re.search(pattern, filename):
                return True
        return False


    def extract_bank_name(self, filename):
        """从文件名中提取银行名称"""
        try:
            extractor = SimpleBankNameExtractor()
            bank_name = extractor.extract_bank_name(filename)
            return bank_name if bank_name else ""
        except Exception as e:
            print(f"⚠️ 银行名称提取失败: {e}")
            return ""

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

            # 需要添加的列（添加 bank_name 字段）
            new_columns = {
                'file_hash': 'TEXT',
                'file_size': 'INTEGER',
                'upload_count': 'INTEGER DEFAULT 1',
                'last_uploaded': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'bank_name': 'TEXT'  # 新增银行名称字段
            }

            for col_name, col_type in new_columns.items():
                if col_name not in existing_cols:
                    print(f"🔧🔧 添加缺失列: {col_name} {col_type}")
                    try:
                        c.execute(f"ALTER TABLE files ADD COLUMN {col_name} {col_type}")
                        conn.commit()
                        print(f"✅ 列 {col_name} 添加成功")
                    except Exception as e:
                        print(f"⚠️ 添加列 {col_name} 失败: {e}")

        except Exception as e:
            print(f"❌❌ 检查表结构失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def get_existing_file(self, file_hash, raw_filename=None):
        """根据哈希值和文件名检查文件是否已存在"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # 优先检查完全匹配（文件名和内容都相同）
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

            # 如果没有完全匹配，检查内容相同的文件
            c.execute("""
                SELECT id, filename, raw_filename, upload_count, created_at, file_size, bank_name
                FROM files 
                WHERE file_hash = ? AND deleted = 0 AND file_hash IS NOT NULL
                LIMIT 1
            """, (file_hash,))

            return c.fetchone()
        except Exception as e:
            print(f"❌❌❌❌ 查询重复文件失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def increment_upload_count(self, file_id, bank_name=""):
        """增加文件的上传次数，可选更新银行名称"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            if bank_name:
                # 如果提供了银行名称，同时更新银行名称
                c.execute("""
                    UPDATE files 
                    SET upload_count = upload_count + 1, 
                        last_uploaded = CURRENT_TIMESTAMP,
                        bank_name = ?
                    WHERE id = ?
                """, (bank_name, file_id))
                print(f"🏦🏦 更新银行名称: {bank_name}")
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
            print(f"❌❌ 更新上传次数失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def save_new_file(self, file_content, raw_filename, file_hash, bank_name="", file_size=None):
        """保存新文件到磁盘和数据库"""
        # 生成确定性文件ID
        # 如果未提供file_size，从file_content计算
        if file_size is None:
            file_size = len(file_content)

        # 生成智能UUID
        file_id = self.generate_smart_uuid(file_content, raw_filename, file_size)

        #
        ext = os.path.splitext(raw_filename)[1].lower()
        disk_filename = f"{file_id}{ext}"
        file_path = self.upload_dir / disk_filename

        # 确保上传目录存在
        if not self.upload_dir.exists():
            print(f"📁📁 创建上传目录: {self.upload_dir}")
            self.upload_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件到磁盘
        print(f"💾💾 保存新文件到: {file_path}")
        try:
            file_path.write_bytes(file_content)
        except Exception as e:
            print(f"❌❌ 文件保存失败: {e}")
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
                (filename, file_type, raw_filename, deleted, file_hash, file_size, upload_count, bank_name) 
                VALUES (?, ?, ?, 0, ?, ?, 1, ?)
            """, (disk_filename, file_type, raw_filename, file_hash, file_size, bank_name))

            new_id = c.lastrowid
            conn.commit()

            print(f"✅ 数据库插入成功 - 新记录ID: {new_id}")
            print(f"🏦🏦 银行名称已保存: {bank_name}")
            print(f"🆔🆔 确定性UUID: {file_id}")  # 🆕 添加UUID日志

            return {
                "id": new_id,
                "file_id": str(file_id),  # 🆕 返回字符串格式的UUID
                "disk_filename": disk_filename,
                "file_type": file_type,
                "file_size": file_size,
                "file_hash": file_hash,
                "bank_name": bank_name
            }

        except Exception as e:
            print(f"❌❌ 数据库插入失败: {e}")
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
        print("🔄🔄🔄🔄 开始处理文件上传...")
        print(f"📄📄📄📄 原始文件名: {raw_filename}")

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

        print(f"📄📄📄📄 文件大小: {file_size} bytes")
        print(f"🔢🔢🔢🔢 文件哈希: {file_hash}")

        # 3. 提取银行名称
        bank_name = self.extract_bank_name(raw_filename)
        print(f"🏦🏦🏦🏦 识别到的银行名称: {bank_name if bank_name else '无'}")

        # 4. 确保数据库表结构完整
        self.check_table_columns()

        # 5. 检查重复（新增文件名参数）
        existing_file = self.get_existing_file(file_hash, raw_filename)

        if existing_file:
            # 处理重复文件
            return self._handle_duplicate(existing_file, raw_filename, file_size, file_hash, bank_name)
        else:
            # 处理新文件
            return self._handle_new_file(file_content, raw_filename, file_hash, bank_name)

    def _handle_duplicate(self, existing_file, raw_filename, file_size, file_hash, bank_name=""):
        """处理重复文件"""
        print("🔄🔄🔄🔄 发现重复文件")

        file_id = existing_file[0]
        disk_filename = existing_file[1]
        existing_raw_name = existing_file[2]
        upload_count = existing_file[3] + 1
        created_at = existing_file[4]
        existing_file_size = existing_file[5]
        existing_bank_name = existing_file[6]  # 新增的银行名称字段

        # 提取file_id（去掉扩展名）
        existing_file_id = disk_filename.split('.')[0] if '.' in disk_filename else disk_filename

        print(f"   数据库ID: {file_id}")
        print(f"   文件ID: {existing_file_id}")
        print(f"   磁盘文件名: {disk_filename}")
        print(f"   已有上传次数: {upload_count - 1}")
        print(f"   匹配类型: {'完全匹配（名称+内容）' if existing_raw_name == raw_filename else '内容匹配'}")

        # 更新上传次数（如果银行名称有更新，也一并更新）
        update_bank_name = bank_name if bank_name and bank_name != existing_bank_name else ""
        if not self.increment_upload_count(file_id, update_bank_name):
            print("⚠️ 更新上传次数失败，但继续处理...")

        # 添加文件映射（只有在不是完全匹配时才需要添加新映射）
        if existing_raw_name != raw_filename:
            ext = os.path.splitext(raw_filename)[1].lower()
            try:
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
            "exact_match": existing_raw_name == raw_filename  # 标识是否完全匹配
        }

        print(f"✅ 重复文件处理完成")
        print("=" * 50)

        return response

    def _handle_new_file(self, file_content, raw_filename, file_hash, bank_name=""):
        """处理新文件"""
        print("🆕🆕🆕 处理新文件")

        # # 保存文件
        # result = self.save_new_file(file_content, raw_filename, file_hash, bank_name)

        # 保存文件 - 需要传递file_size
        file_size = len(file_content)  # 新增这行
        result = self.save_new_file(file_content, raw_filename, file_hash, bank_name, file_size)  # 修改这行

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
            "bank_name": bank_name,  # 添加银行名称到响应
            "message": "新文件上传成功",
            "duplicate": False
        }

        print(f"✅ 新文件上传完成")
        print("=" * 50)

        return response

# 创建全局实例
file_upload_service = FileUploadService()
