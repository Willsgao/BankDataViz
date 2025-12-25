# -*- coding:utf-8 -*-
# -*- coding:utf-8 -*-
"""
文件管理服务类
提供文件查询、统计、清理等功能
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from backend.utils.constants import DATABASE, UPLOAD_FOLDER, MAIN_ROOT


class FileManagementService:
    """文件管理服务"""

    def __init__(self):
        self.db_path = DATABASE
        self.upload_dir = Path(MAIN_ROOT) / UPLOAD_FOLDER

    def get_file_stats(self):
        """获取文件统计信息"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # 总文件数
            c.execute("SELECT COUNT(*) FROM files WHERE deleted = 0")
            total_files = c.fetchone()[0]

            # 总文件大小
            c.execute("SELECT SUM(file_size) FROM files WHERE deleted = 0 AND file_size IS NOT NULL")
            total_size = c.fetchone()[0] or 0

            # 去重后的文件数（按哈希）
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
            print(f"❌ 获取文件统计失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def find_duplicates(self, limit=20):
        """查找重复文件"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 返回字典格式
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

                # 计算可节省的空间（保留一份，删除其他副本）
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
                    "efficiency_percent": round(100 / row['file_count'], 2)  # 存储效率
                })

            return duplicates

        except Exception as e:
            print(f"❌ 查找重复文件失败: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_file_info(self, file_id):
        """获取文件详细信息"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # 根据输入可能是数据库ID或文件ID（UUID）
            if len(str(file_id)) < 10:  # 假设是数字ID
                c.execute("""
                    SELECT f.*, 
                           (SELECT COUNT(*) FROM files WHERE file_hash = f.file_hash AND deleted = 0) as duplicate_count
                    FROM files f
                    WHERE f.id = ? AND f.deleted = 0
                """, (file_id,))
            else:  # 假设是UUID格式的文件ID
                c.execute("""
                    SELECT f.*,
                           (SELECT COUNT(*) FROM files WHERE file_hash = f.file_hash AND deleted = 0) as duplicate_count
                    FROM files f
                    WHERE f.filename LIKE ? AND f.deleted = 0
                """, (f"{file_id}%",))

            file_data = c.fetchone()

            if file_data:
                # 获取同哈希的其他文件
                c.execute("""
                    SELECT id, raw_filename, created_at, upload_count
                    FROM files
                    WHERE file_hash = ? AND deleted = 0 AND id != ?
                    ORDER BY created_at
                """, (file_data['file_hash'], file_data['id']))

                same_hash_files = [
                    dict(row) for row in c.fetchall()
                ]

                # 检查物理文件是否存在
                physical_path = self.upload_dir / file_data['filename']
                physical_exists = physical_path.exists()
                physical_size = physical_path.stat().st_size if physical_exists else 0

                return {
                    "file_info": dict(file_data),
                    "same_hash_files": same_hash_files,
                    "physical_file": {
                        "exists": physical_exists,
                        "path": str(physical_path),
                        "size_bytes": physical_size,
                        "size_match": physical_size == file_data['file_size']
                    }
                }

            return None

        except Exception as e:
            print(f"❌ 获取文件信息失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def find_orphaned_files(self, days_threshold=30):
        """查找孤立文件（长时间未被引用的）"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # 查找上传次数为1且超过指定天数的文件
            c.execute("""
                SELECT f.*,
                       julianday('now') - julianday(f.created_at) as days_old
                FROM files f
                WHERE f.deleted = 0 
                  AND f.upload_count = 1
                  AND f.created_at < datetime('now', ?)
                ORDER BY f.file_size DESC
            """, (f"-{days_threshold} days",))

            orphaned_files = []
            total_size = 0

            for row in c.fetchall():
                file_info = dict(row)

                # 检查是否被其他表引用（如果有的话）
                # 这里可以添加检查其他业务表引用的逻辑

                orphaned_files.append(file_info)
                total_size += file_info.get('file_size', 0)

            return {
                "orphaned_files": orphaned_files,
                "count": len(orphaned_files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "days_threshold": days_threshold
            }

        except Exception as e:
            print(f"❌ 查找孤立文件失败: {e}")
            return {"orphaned_files": [], "count": 0, "total_size_bytes": 0}
        finally:
            if conn:
                conn.close()

    def cleanup_file(self, file_id, delete_physical=False):
        """清理文件（逻辑删除或物理删除）"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # 获取文件信息
            c.execute("SELECT filename, file_hash, upload_count FROM files WHERE id = ?", (file_id,))
            file_info = c.fetchone()

            if not file_info:
                return {"success": False, "error": "文件不存在"}

            filename, file_hash, upload_count = file_info

            # 如果有多个引用，只做逻辑删除
            if upload_count > 1:
                # 减少引用计数
                c.execute("UPDATE files SET upload_count = upload_count - 1 WHERE id = ?", (file_id,))
                action = "decremented"
                message = f"文件有 {upload_count} 个引用，已减少引用计数"
            else:
                # 只有1个引用，可以逻辑删除
                c.execute("UPDATE files SET deleted = 1 WHERE id = ?", (file_id,))
                action = "soft_deleted"
                message = "文件已逻辑删除"

            conn.commit()

            # 如果需要物理删除
            physical_deleted = False
            if delete_physical:
                physical_path = self.upload_dir / filename
                if physical_path.exists():
                    try:
                        physical_path.unlink()
                        physical_deleted = True
                        message += "，物理文件已删除"
                    except Exception as e:
                        message += f"，但物理文件删除失败: {e}"

            return {
                "success": True,
                "action": action,
                "physical_deleted": physical_deleted,
                "message": message,
                "file_id": file_id
            }

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ 清理文件失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if conn:
                conn.close()


# 创建全局实例
file_management_service = FileManagementService()