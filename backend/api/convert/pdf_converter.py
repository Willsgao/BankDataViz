"""
PDF转图模块
"""
import uuid
from flask import jsonify

def convert_pdf_async(pdf_name, upload_dir, output_dir, db_manager, progress_tracker):
    """接收中文或 UUID 文件名 → 返回 jobId"""
    # 1. 文件名映射
    real_name = _map_to_disk_file(pdf_name, db_manager)
    if not real_name:
        return jsonify({"error": "PDF 不存在"}), 404

    # 2. 检查文件存在
    pdf_path = upload_dir / real_name
    if not pdf_path.exists():
        return jsonify({"error": "物理文件不存在"}), 404

    # 3. 创建输出目录
    out_dir = output_dir / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    # 4. 检查缓存
    existing = sorted(p.name for p in out_dir.glob("*.png"))
    if existing:
        return jsonify({
            "hitCache": True,
            "total": len(existing),
            "pngs": existing,
            "folder": pdf_path.stem
        })

    # 5. 提交后台任务
    job_id = uuid.uuid4().hex
    from backend.service.pdf_convert_service import background_convert_table_only
    progress_tracker.init_job(job_id)
    background_convert_table_only(pdf_path, out_dir, job_id, progress_tracker.PROGRESS)

    return jsonify({"jobId": job_id, "message": "任务已提交"})


def _map_to_disk_file(filename, db_manager):
    """内部文件名映射函数"""
    print(f"[DEBUG] 数据库路径: {db_manager.db_path}")
    print(f"🔍 _map_to_disk 查找文件: {filename}")

    conn = db_manager.connect()
    if not conn:
        print("❌ 数据库连接失败")
        return None

    try:
        from sqlite3 import Cursor
        c: Cursor = conn.cursor()
        c.execute(
            "SELECT filename FROM files "
            "WHERE (raw_filename = ? OR filename = ?) AND deleted = 0",
            (filename, filename)
        )
        row = c.fetchone()

        if row:
            print(f"✅ 找到文件映射: {filename} -> {row['filename']}")
            return row["filename"]
        else:
            print(f"❌ 未找到文件映射: {filename}")
            # 打印所有可用文件用于调试
            c.execute("SELECT filename, raw_filename, deleted FROM files")
            all_files = c.fetchall()
            print(f"📋 数据库中所有文件: {all_files}")
            return None
    except Exception as e:
        print(f"❌ 数据库查询错误: {e}")
        return None
    finally:
        conn.close()