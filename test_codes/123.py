"""
PDF → PNG 转图蓝图
"""
import uuid
import io
import base64
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_from_directory
# from backend.models.database_manager import OldDatabaseManager
from backend.models.unified_db import DatabaseManager as OldDatabaseManager
from backend.service.pdf_convert_service import background_convert_table_only
from backend.service.layout_service import batch_cut_tables, execute_single_step, processing_pipeline

from backend.utils.constants import (
    MAIN_ROOT, UPLOAD_FOLDER, PNG_OUTPUT_ROOT, DATABASE,  # 原有的
    UPLOAD_DIR, PNG_OUTPUT_DIR, DATABASE_PATH, STATIC_DIR, JOINED_TABLES_DIR  # 新增的
)
from sqlite3 import Cursor, Connection  # 需导入对应类型（假设使用sqlite3）

# 分步提取数据
from backend.src.services.table_processor.end_to_end_pipeline import (
    create_pipeline,
    batch_example
)
from backend.utils.config import tableconfig
import threading

# 确保输出目录存在 - 修正：使用正确的路径组合
PNG_OUTPUT_DIR = Path(MAIN_ROOT) / PNG_OUTPUT_ROOT
PNG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"🔍 输出目录设置为: {PNG_OUTPUT_DIR}")
print(f"🔍 输出目录是否存在: {PNG_OUTPUT_DIR.exists()}")

convert_bp = Blueprint('convert', __name__)
db = OldDatabaseManager(DATABASE_PATH)


# ---------------- 1. 提交异步转图 ----------------
@convert_bp.post('/convert-pdf-async/<path:pdf_name>')
def api_convert_pdf_async(pdf_name: str):
    """接收中文或 UUID 文件名 → 返回 jobId"""
    print(f"🔍 转图API被调用，参数: {pdf_name}")

    real_name = _map_to_disk(pdf_name)
    if not real_name:
        print(f"❌ PDF 不存在: {pdf_name}")
        return jsonify({"error": "PDF 不存在"}), 404

    # 修正：PDF路径需要包含MAIN_ROOT
    # pdf_path = Path(MAIN_ROOT) / UPLOAD_FOLDER / real_name
    pdf_path = UPLOAD_DIR / real_name
    print(f"📁 完整PDF路径: {pdf_path}")
    print(f"📁 PDF是否存在: {pdf_path.exists()}")

    if not pdf_path.exists():
        print(f"❌ 物理文件不存在: {pdf_path}")
        return jsonify({"error": "物理文件不存在"}), 404

    out_dir = Path(PNG_OUTPUT_DIR) / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    print("XXXXXXXXout_dirXXXXXXXXX", out_dir)

    # 缓存命中直接返回
    existing = sorted(p.name for p in out_dir.glob("*.png"))
    if existing:
        return jsonify({"hitCache": True, "total": len(existing),
                        "pngs": existing, "folder": pdf_path.stem})

    job_id = uuid.uuid4().hex
    from backend.api.convert_apis import PROGRESS
    PROGRESS[job_id] = {"total": 0, "finished": 0, "percent": 0}
    background_convert_table_only(pdf_path, out_dir, job_id, PROGRESS)


    return jsonify({"jobId": job_id, "message": "任务已提交"})


# ---------------- 2. 轮询进度 ----------------
PROGRESS = {}     # 内存进度表

# 扩展PROGRESS字典以支持表格处理
TABLE_PROCESSING_JOBS = {}  # 专门存储表格处理任务状态

# 表格处理状态定义
TABLE_PROCESSING_STAGES = {
    'pending': '等待处理',
    'ocr': 'OCR识别中',
    'llm': 'LLM分析中',
    'reconstruction': '表格重构中',
    'exporting': '导出Excel中',
    'completed': '处理完成',
    'failed': '处理失败'
}

# 在现有的输出目录基础上添加
TABLE_OUTPUT_DIR = Path(tableconfig.output_dir)  # 从配置获取
print("TABLE_OUTPUT_DIR:", TABLE_OUTPUT_DIR)
TABLE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 新增数据库导入
import sqlite3
from contextlib import closing

# 表格处理记录表结构
TABLE_PROCESSING_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS table_processing_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE,
    pdf_folder TEXT,
    bank_name TEXT,
    status TEXT,
    stage TEXT,
    progress INTEGER,
    total_images INTEGER,
    processed_images INTEGER,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    excel_files TEXT,  -- JSON数组存储Excel文件路径
    start_time DATETIME,
    end_time DATETIME,
    error_message TEXT,
    raw_result TEXT,   -- JSON格式的原始结果
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""


def init_table_processing_db():
    """初始化表格处理数据库表"""
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(TABLE_PROCESSING_RECORDS_TABLE)
        conn.commit()
        print("✅ 表格处理记录表初始化完成")



# 数据库函数
def save_table_processing_record(job_info):
    """保存表格处理记录到数据库"""
    try:
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            cursor = conn.cursor()

            # 检查记录是否存在
            cursor.execute("SELECT id FROM table_processing_records WHERE job_id = ?",
                           (job_info.get('job_id'),))
            exists = cursor.fetchone()

            excel_files_json = json.dumps(job_info.get('excel_files', []))
            raw_result_json = json.dumps(job_info)

            if exists:
                # 更新现有记录
                cursor.execute("""
                    UPDATE table_processing_records 
                    SET status = ?, stage = ?, progress = ?,
                        processed_images = ?, success_count = ?, failed_count = ?,
                        excel_files = ?, end_time = ?, error_message = ?,
                        raw_result = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                """, (
                    job_info.get('status'),
                    job_info.get('stage'),
                    job_info.get('progress', 0),
                    job_info.get('processed_images', 0),
                    job_info.get('success_count', 0),
                    job_info.get('failed_count', 0),
                    excel_files_json,
                    job_info.get('end_time'),
                    job_info.get('error'),
                    raw_result_json,
                    job_info.get('job_id')
                ))
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO table_processing_records 
                    (job_id, pdf_folder, bank_name, status, stage, progress,
                     total_images, processed_images, success_count, failed_count,
                     excel_files, start_time, end_time, error_message, raw_result)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_info.get('job_id'),
                    job_info.get('pdf_folder'),
                    job_info.get('bank_name'),
                    job_info.get('status'),
                    job_info.get('stage'),
                    job_info.get('progress', 0),
                    job_info.get('total_images', 0),
                    job_info.get('processed_images', 0),
                    job_info.get('success_count', 0),
                    job_info.get('failed_count', 0),
                    excel_files_json,
                    job_info.get('start_time'),
                    job_info.get('end_time'),
                    job_info.get('error'),
                    raw_result_json
                ))

            conn.commit()
            print(f"💾 表格处理记录已保存到数据库 - Job ID: {job_info.get('job_id')}")

    except Exception as e:
        print(f"❌ 保存表格处理记录失败: {e}")


def load_table_processing_records(pdf_folder=None, limit=100):
    """从数据库加载表格处理记录"""
    try:
        with closing(sqlite3.connect(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if pdf_folder:
                cursor.execute("""
                    SELECT * FROM table_processing_records 
                    WHERE pdf_folder = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (pdf_folder, limit))
            else:
                cursor.execute("""
                    SELECT * FROM table_processing_records 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))

            records = []
            for row in cursor.fetchall():
                record = dict(row)
                # 解析JSON字段
                if record.get('excel_files'):
                    try:
                        record['excel_files'] = json.loads(record['excel_files'])
                    except:
                        record['excel_files'] = []
                if record.get('raw_result'):
                    try:
                        record['raw_result'] = json.loads(record['raw_result'])
                    except:
                        record['raw_result'] = {}

                records.append(record)

            return records

    except Exception as e:
        print(f"❌ 加载表格处理记录失败: {e}")
        return []


def process_tables_async(job_id, pdf_folder, valid_images, bank_name):
    try:
        print(f"🚀 开始异步处理表格 - Job ID: {job_id}")

        # 初始化数据库
        init_table_processing_db()

        # 更新内存和数据库状态
        update_job_progress(job_id, {
            "status": "processing",
            "stage": "starting",
            "progress": 5
        })

        # ========== 真实处理逻辑 ==========
        output_dir = Path(tableconfig.output_dir) / pdf_folder
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"📁 输出目录: {output_dir}")

        # 创建进度回调函数
        def progress_callback(image_index, total_images, stage):
            """进度回调函数"""
            progress = 10 + (image_index / total_images * 80)  # 10%-90%
            update_job_progress(job_id, {
                "stage": stage,
                "progress": int(progress),
                "processed_images": image_index + 1,
                "current_stage": stage,
                "current_image": Path(valid_images[image_index]).name if image_index < len(valid_images) else ""
            })
            print(f"📊 处理进度: {stage} - {image_index + 1}/{total_images} ({int(progress)}%)")

        # 处理每张图片
        results = []
        excel_files = []

        for i, image_path in enumerate(valid_images):
            image_name = Path(image_path).name

            # 更新进度
            progress_callback(i, len(valid_images), "ocr")

            try:
                print(f"🖼️ 处理图片 {i + 1}/{len(valid_images)}: {image_name}")

                # 1. OCR识别
                update_job_progress(job_id, {
                    "current_image": image_name,
                    "current_stage": "ocr"
                })

                # 2. LLM分析
                progress_callback(i, len(valid_images), "llm")
                update_job_progress(job_id, {
                    "current_image": image_name,
                    "current_stage": "llm"
                })

                # 3. 表格重构
                progress_callback(i, len(valid_images), "reconstruction")
                update_job_progress(job_id, {
                    "current_image": image_name,
                    "current_stage": "reconstruction"
                })

                # 这里可以调用单张图片处理函数
                # 暂时用模拟数据
                excel_filename = f"table_result_{i + 1}.xlsx"
                excel_path = output_dir / excel_filename

                # 模拟生成Excel文件
                import pandas as pd
                df = pd.DataFrame({
                    '提取时间': [datetime.now().isoformat()],
                    '图片名称': [image_name],
                    '银行名称': [bank_name],
                    '状态': ['处理成功']
                })
                df.to_excel(excel_path, index=False)

                results.append({
                    "image_path": image_name,
                    "success": True,
                    "output_file": str(excel_path),
                    "processing_time": 2.5  # 模拟处理时间
                })
                excel_files.append(str(excel_path))

                print(f"✅ 图片处理完成: {image_name}")

            except Exception as img_error:
                print(f"❌ 图片处理失败 {image_name}: {img_error}")
                results.append({
                    "image_path": image_name,
                    "success": False,
                    "error": str(img_error)
                })

        # 处理完成
        success_count = sum(1 for r in results if r.get('success'))

        update_job_progress(job_id, {
            "status": "completed",
            "stage": "completed",
            "progress": 100,
            "processed_images": len(valid_images),
            "success_count": success_count,
            "failed_count": len(valid_images) - success_count,
            "results": results,
            "excel_files": excel_files,
            "end_time": datetime.now().isoformat(),
            "summary": {
                "total_images": len(valid_images),
                "successful": success_count,
                "failed": len(valid_images) - success_count,
                "excel_files_count": len(excel_files)
            }
        })

        print(f"✅ 表格处理任务完成 - Job ID: {job_id}")

    except Exception as e:
        print(f"❌ 表格处理任务失败 - Job ID: {job_id}, 错误: {e}")
        import traceback
        traceback.print_exc()

        update_job_progress(job_id, {
            "status": "failed",
            "stage": "failed",
            "error": str(e),
            "end_time": datetime.now().isoformat()
        })


def update_job_progress(job_id, updates):
    """更新任务进度（同时更新内存和数据库）"""
    if job_id in TABLE_PROCESSING_JOBS:
        TABLE_PROCESSING_JOBS[job_id].update(updates)

        # 保存到数据库
        job_info = TABLE_PROCESSING_JOBS[job_id].copy()
        job_info['job_id'] = job_id
        save_table_processing_record(job_info)



















@convert_bp.get('/progress/<job_id>')
def api_progress(job_id: str):
    return jsonify(PROGRESS.get(job_id, {"state": "unknown", "percent": 0}))


# ---------------- 3. 列出某 PDF 的所有 PNG ----------------
@convert_bp.get('/png-list/<pdf_folder>')
def api_png_list(pdf_folder: str):
    out_dir = Path(PNG_OUTPUT_DIR) / pdf_folder

    if not out_dir.exists():
        return jsonify({"error": "PNG folder not found"}), 404
    pngs = sorted(p.name for p in out_dir.glob("*.png"))
    return jsonify({"total": len(pngs), "pngs": pngs})


# ---------------- 4. 单张 PNG 访问 ----------------
@convert_bp.get('/png/<pdf_folder>/<png_name>')
def api_serve_png(pdf_folder: str, png_name: str):
    return send_from_directory(Path(PNG_OUTPUT_DIR) / pdf_folder, png_name)


# ---------------- 5. 旋转并保存 ----------------
@convert_bp.post('/png/rotate/<pdf_folder>/<png_name>')
def rotate_png(pdf_folder: str, png_name: str):
    angle = request.json.get('angle', 90)
    png_path = Path(PNG_OUTPUT_DIR) / pdf_folder / png_name
    if not png_path.exists():
        return jsonify({"error": "PNG not found"}), 404

    from PIL import Image
    img = Image.open(png_path)
    rotated = img.rotate(-angle, expand=True)
    rotated.save(png_path)
    return jsonify({"message": "rotated and saved"})


# ---------------- 6. 保存前端裁剪子图 ----------------
@convert_bp.post('/save-rotated-sub/<folder>/<png_name>')
def save_rotated_sub(folder: str, png_name: str):
    try:
        data = request.get_json()
        img_bytes = base64.b64decode(data['image'])
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        save_dir = Path(PNG_OUTPUT_DIR) / folder
        save_dir.mkdir(exist_ok=True)
        img.save(save_dir / png_name, format='PNG')
        return jsonify({'code': 0, 'msg': 'saved'})
    except Exception as e:
        return jsonify({'code': 1, 'msg': str(e)}), 500


# ---------------- 工具：中文/UUID → 磁盘名 ----------------
def _map_to_disk(filename: str) -> str | None:
    """返回磁盘文件名；若文件不存在或已软删则返回 None"""
    print(f"[DEBUG] 数据库路径: {db.db_path}")
    print(f"🔍 _map_to_disk 查找文件: {filename}")

    conn: Connection | None = db.connect()
    if not conn:
        print("❌ 数据库连接失败")
        return None
    try:
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


# ---------------- 7. 单张 PNG 版面分区 ----------------
@convert_bp.get('/layout/<pdf_folder>/<png_name>')
def api_layout(pdf_folder: str, png_name: str):
    """
    对已经转图完成的单张 PNG 做版面检测
    返回：{ json: <原始 layout>, table_zones: [[x1,y1,x2,y2], ...] }
    """
    png_path = Path(PNG_OUTPUT_DIR) / pdf_folder / png_name
    print("png_path111111::", png_path)
    if not png_path.exists():
        return jsonify({"error": "PNG not found"}), 404
    print("png_path22222222::", png_path)
    try:
        from backend.service.layout_service import layout_detect
        result = layout_detect(png_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- 8. 批量切割图表 版面分区 ----------------
@convert_bp.route('/batch-cut-table/<task_id>', methods=['POST', 'OPTIONS'])
def batch_cut_table(task_id):
    """
    批量裁切图片中的表格 - 修正类型错误
    """
    print("开始处理批量裁切请求")

    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        pdf_folder = data.get('pdf_folder')
        png_names = data.get('png_names', [])
        print(f"批量裁切参数 - pdf_folder: {pdf_folder}, png_names: {png_names}")

        # 参数校验
        if not pdf_folder or not isinstance(png_names, list) or len(png_names) == 0:
            return jsonify({
                "success": False,
                "error": "参数错误：需提供非空的pdf_folder和png_names列表"
            }), 400

        # # 调用服务层批量裁切逻辑
        # batch_result = batch_cut_tables(
        #     pdf_folder=pdf_folder,
        #     png_names=png_names,
        #     output_root=PNG_OUTPUT_DIR
        # )

        steps = data.get('steps')  # 新增：支持指定步骤
        batch_result = batch_cut_tables(
            pdf_folder=pdf_folder,
            png_names=png_names,
            output_root=PNG_OUTPUT_DIR,
            steps=steps  # 新增步骤参数
        )

        print(f"批量裁切完成，结果类型: {type(batch_result)}")
        print(f"批量裁切结果: {batch_result}")

        # 直接返回 batch_result，不要做任何额外的处理
        # batch_cut_tables 已经返回了正确格式的数据
        return jsonify(batch_result)

    except Exception as e:
        print(f"批量裁切接口处理失败: {str(e)}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": f"接口处理失败: {str(e)}"
        }), 500



@convert_bp.get('/api/folder-images/<path:folder_path>')
def api_folder_images(folder_path: str):
    """获取文件夹中的图片列表"""
    # 修正：使用正确的静态文件目录路径
    # folder_dir = Path(MAIN_ROOT) / "backend" / "static" / folder_path
    folder_dir = STATIC_DIR / folder_path
    if not folder_dir.exists():
        return jsonify({"success": False, "error": "文件夹不存在"}), 404

    images = []
    for img_file in sorted(folder_dir.glob("*.png")):
        images.append({
            "name": img_file.name,
            "url": f"/static/{folder_path}/{img_file.name}"
        })

    return jsonify({
        "success": True,
        "data": {
            "images": images,
            "total": len(images)
        }
    })


# ---------------- 9. 静态文件服务（修正） ----------------
@convert_bp.route('/JOINED_TABLES_DIR/<path:filename>')
def serve_static_png(filename):
    """提供 /static/converted/ 路径的图片访问"""
    try:
        # filename 格式: folder/image.png
        parts = filename.split('/')
        if len(parts) < 2:
            return jsonify({"error": "Invalid filename format"}), 400

        folder = parts[0]
        png_name = parts[1]

        # 修正：使用正确的输出目录
        # target_dir = PNG_OUTPUT_DIR / folder
        target_dir = JOINED_TABLES_DIR / folder  # 用 joined_tables 目录

        print(f"🔍 静态文件服务 - 查找路径: {target_dir}")
        print(f"🔍 静态文件服务 - 文件名: {png_name}")
        print(f"🔍 静态文件服务 - 目录是否存在: {target_dir.exists()}")

        if target_dir.exists():
            return send_from_directory(str(target_dir), png_name)
        else:
            print(f"❌ 目录不存在: {target_dir}")
            return jsonify({"error": "Directory not found"}), 404

    except Exception as e:
        print(f"❌ 静态图片服务错误: {e}")
        return jsonify({"error": "File not found"}), 404


# ---------------- 10. 分步执行表格处理 ----------------
@convert_bp.route('/step-process/<step_name>', methods=['POST', 'OPTIONS'])
def api_step_process(step_name: str):
    """
    分步执行表格处理
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        pdf_folder = data.get('pdf_folder')
        png_names = data.get('png_names', [])
        previous_context = data.get('previous_context', {})

        # 参数校验
        if not pdf_folder or not isinstance(png_names, list):
            return jsonify({
                "success": False,
                "error": "参数错误：需提供pdf_folder和png_names"
            }), 400

        # 执行单个步骤
        result_context = execute_single_step(
            step_name=step_name,
            pdf_folder=pdf_folder,
            png_names=png_names,
            output_root=PNG_OUTPUT_DIR,
            previous_context=previous_context
        )

        return jsonify({
            "success": True,
            "step": step_name,
            "context": result_context,
            "message": f"步骤 {step_name} 执行完成"
        })

    except Exception as e:
        print(f"❌ 分步执行失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"分步执行失败: {str(e)}"
        }), 500


# ---------------- 11. 获取可用步骤列表 ----------------
@convert_bp.get('/available-steps')
def api_available_steps():
    """获取可用的处理步骤列表"""
    try:
        steps = processing_pipeline.get_available_steps()
        return jsonify({
            "success": True,
            "data": {
                "steps": steps,
                "count": len(steps)
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ---------------- 12. 提交表格处理任务 ----------------
@convert_bp.route('/process-tables/<pdf_folder>', methods=['POST', 'OPTIONS'])
def api_process_tables(pdf_folder: str):
    """
    提交表格处理任务
    参数: {
        "png_names": ["table1.png", "table2.png"],
        "bank_name": "中国建设银行",
        "process_mode": "full"  # full/ocr_only/llm_only
    }
    """
    print(f"📋 接收到表格处理请求 - PDF文件夹: {pdf_folder}")

    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        # 1. 解析请求数据
        data = request.get_json()
        png_names = data.get('png_names', [])
        bank_name = data.get('bank_name', '')
        process_mode = data.get('process_mode', 'full')

        print(f"📋 处理参数 - PNG数量: {len(png_names)}, 银行: {bank_name}, 模式: {process_mode}")

        # 2. 参数校验
        if not pdf_folder or not isinstance(png_names, list) or len(png_names) == 0:
            return jsonify({
                "success": False,
                "error": "参数错误：需提供非空的pdf_folder和png_names列表"
            }), 400

        # 3. 检查图片是否存在
        missing_images = []
        valid_images = []
        for png_name in png_names:
            # 检查在joined_tables目录中是否存在
            image_path = JOINED_TABLES_DIR / pdf_folder / png_name
            if image_path.exists():
                valid_images.append(str(image_path))
            else:
                missing_images.append(png_name)

        if missing_images:
            return jsonify({
                "success": False,
                "error": f"以下图片不存在: {missing_images}",
                "missing": missing_images
            }), 404

        print(f"✅ 找到 {len(valid_images)} 个有效图片文件")

        # 4. 创建任务ID和状态跟踪
        job_id = uuid.uuid4().hex
        TABLE_PROCESSING_JOBS[job_id] = {
            "pdf_folder": pdf_folder,
            "png_names": png_names,
            "bank_name": bank_name,
            "process_mode": process_mode,
            "status": "pending",
            "stage": "pending",
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "total_images": len(valid_images),
            "processed_images": 0,
            "results": [],
            "error": None
        }

        print(f"✅ 创建表格处理任务 - Job ID: {job_id}")

        # 5. 在后台异步执行处理
        def process_tables_async():
            try:
                print(f"🚀 开始异步处理表格 - Job ID: {job_id}")

                # 更新状态为处理中
                TABLE_PROCESSING_JOBS[job_id].update({
                    "status": "processing",
                    "stage": "starting",
                    "progress": 5
                })

                # ========== 真实处理逻辑开始 ==========

                # 1. OCR阶段
                TABLE_PROCESSING_JOBS[job_id].update({
                    "stage": "ocr",
                    "progress": 20
                })
                print(f"🔍 开始OCR识别 - Job ID: {job_id}")

                # 2. LLM分析阶段
                TABLE_PROCESSING_JOBS[job_id].update({
                    "stage": "llm",
                    "progress": 50
                })
                print(f"🤖 开始LLM分析 - Job ID: {job_id}")

                # 3. 表格重构阶段
                TABLE_PROCESSING_JOBS[job_id].update({
                    "stage": "reconstruction",
                    "progress": 70
                })
                print(f"🔧 开始表格重构 - Job ID: {job_id}")

                # 4. 调用真实的表格处理管道
                try:
                    # 确定输出目录
                    output_dir = Path(tableconfig.output_dir) / pdf_folder
                    output_dir.mkdir(parents=True, exist_ok=True)

                    print(f"📁 输出目录: {output_dir}")

                    # 调用批量处理函数
                    print(f"📊 开始处理 {len(valid_images)} 张图片...")
                    result = batch_example(
                        image_paths=valid_images,
                        output_dir=str(output_dir),
                        bank_name=bank_name
                    )

                    print(f"✅ 表格处理完成，结果: {result.get('success', False)}")

                    # 5. 收集处理结果
                    results = []
                    excel_files = []

                    if result.get('success') and 'results' in result:
                        for res in result['results']:
                            if res.get('success'):
                                results.append({
                                    "image_path": Path(res.get('image_path', '')).name,
                                    "success": True,
                                    "output_file": res.get('output_file', ''),
                                    "processing_time": res.get('processing_time', 0)
                                })
                                if res.get('output_file'):
                                    excel_files.append(res['output_file'])

                    # 6. 更新任务状态
                    TABLE_PROCESSING_JOBS[job_id].update({
                        "stage": "completed",
                        "status": "completed",
                        "progress": 100,
                        "processed_images": len(valid_images),
                        "success_count": sum(1 for r in results if r.get('success')),
                        "failed_count": len(valid_images) - sum(1 for r in results if r.get('success')),
                        "results": results,
                        "excel_files": excel_files,
                        "end_time": datetime.now().isoformat(),
                        "summary": {
                            "total_images": len(valid_images),
                            "successful": sum(1 for r in results if r.get('success')),
                            "failed": len(valid_images) - sum(1 for r in results if r.get('success')),
                            "total_time": result.get('stats', {}).get('processing_time', 0)
                        }
                    })

                    print(f"✅ 表格处理任务完成 - Job ID: {job_id}")
                    print(
                        f"📊 处理统计: 成功 {TABLE_PROCESSING_JOBS[job_id]['success_count']}, 失败 {TABLE_PROCESSING_JOBS[job_id]['failed_count']}")

                except Exception as process_error:
                    print(f"❌ 表格处理过程异常 - Job ID: {job_id}, 错误: {process_error}")
                    import traceback
                    traceback.print_exc()

                    TABLE_PROCESSING_JOBS[job_id].update({
                        "status": "failed",
                        "stage": "failed",
                        "error": f"处理过程异常: {str(process_error)}",
                        "end_time": datetime.now().isoformat()
                    })

            except Exception as e:
                print(f"❌ 表格处理任务整体失败 - Job ID: {job_id}, 错误: {e}")
                import traceback
                traceback.print_exc()

                TABLE_PROCESSING_JOBS[job_id].update({
                    "status": "failed",
                    "stage": "failed",
                    "error": str(e),
                    "end_time": datetime.now().isoformat()
                })

        # 启动异步线程
        thread = threading.Thread(target=process_tables_async, daemon=True)
        thread.start()

        # 6. 返回任务ID
        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": "表格处理任务已提交",
            "data": {
                "total_images": len(valid_images),
                "pdf_folder": pdf_folder,
                "bank_name": bank_name
            }
        })

    except Exception as e:
        print(f"❌ 表格处理接口异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"接口处理失败: {str(e)}"
        }), 500


# ---------------- 13. 查询表格处理任务状态 ----------------
@convert_bp.get('/table-progress/<job_id>')
def api_table_progress(job_id: str):
    """
    查询表格处理任务状态
    """
    print(f"📊 查询表格处理进度 - Job ID: {job_id}")

    if job_id not in TABLE_PROCESSING_JOBS:
        return jsonify({
            "success": False,
            "error": "任务不存在或已过期",
            "job_id": job_id
        }), 404

    job_info = TABLE_PROCESSING_JOBS[job_id]

    # 计算进度百分比
    progress = job_info.get("progress", 0)
    if job_info["status"] == "completed":
        progress = 100
    elif job_info["status"] == "failed":
        progress = 0

    return jsonify({
        "success": True,
        "job_id": job_id,
        "status": job_info["status"],
        "stage": job_info["stage"],
        "progress": progress,
        "data": {
            "pdf_folder": job_info.get("pdf_folder"),
            "total_images": job_info.get("total_images", 0),
            "processed_images": job_info.get("processed_images", 0),
            "bank_name": job_info.get("bank_name", ""),
            "start_time": job_info.get("start_time"),
            "end_time": job_info.get("end_time"),
            "error": job_info.get("error")
        }
    })


# ---------------- 14. 查询表格处理结果列表 ----------------
@convert_bp.get('/table-results/<pdf_folder>')
def api_table_results(pdf_folder: str):
    """
    查询某个PDF文件夹的所有表格处理结果
    """
    print(f"📋 查询表格处理结果 - PDF文件夹: {pdf_folder}")

    try:
        # 1. 查找该文件夹的所有任务
        folder_tasks = []
        for job_id, job_info in TABLE_PROCESSING_JOBS.items():
            if job_info.get("pdf_folder") == pdf_folder:
                folder_tasks.append({
                    "job_id": job_id,
                    "status": job_info.get("status", "unknown"),
                    "stage": job_info.get("stage", "unknown"),
                    "progress": job_info.get("progress", 0),
                    "start_time": job_info.get("start_time"),
                    "end_time": job_info.get("end_time"),
                    "total_images": job_info.get("total_images", 0),
                    "processed_images": job_info.get("processed_images", 0),
                    "bank_name": job_info.get("bank_name", ""),
                    "summary": job_info.get("summary", {})
                })

        # 2. 查找该文件夹生成的Excel文件
        output_dir = Path(tableconfig.output_dir) / pdf_folder
        excel_files = []

        if output_dir.exists():
            for excel_file in output_dir.glob("*.xlsx"):
                excel_files.append({
                    "filename": excel_file.name,
                    "path": str(excel_file),
                    "size": excel_file.stat().st_size,
                    "modified_time": datetime.fromtimestamp(excel_file.stat().st_mtime).isoformat(),
                    "download_url": f"/download-table/{pdf_folder}/{excel_file.name}"
                })

        # 3. 返回结果
        return jsonify({
            "success": True,
            "pdf_folder": pdf_folder,
            "data": {
                "tasks": folder_tasks,
                "excel_files": excel_files,
                "task_count": len(folder_tasks),
                "excel_count": len(excel_files),
                "output_dir": str(output_dir)
            }
        })

    except Exception as e:
        print(f"❌ 查询表格处理结果异常: {e}")
        return jsonify({
            "success": False,
            "error": f"查询失败: {str(e)}"
        }), 500


# ---------------- 15. 下载表格处理结果Excel文件 ----------------
@convert_bp.route('/download-table/<pdf_folder>/<filename>', methods=['GET'])
def api_download_table(pdf_folder: str, filename: str):
    """
    下载表格处理生成的Excel文件
    """
    print(f"📥 请求下载Excel文件 - {pdf_folder}/{filename}")

    try:
        # 1. 构造文件路径
        file_path = Path(tableconfig.output_dir) / pdf_folder / filename

        # 2. 安全性检查
        if not file_path.exists():
            return jsonify({
                "success": False,
                "error": "文件不存在"
            }), 404

        # 确保文件在允许的目录内
        allowed_dir = Path(tableconfig.output_dir).resolve()
        file_path_resolved = file_path.resolve()

        if not str(file_path_resolved).startswith(str(allowed_dir)):
            return jsonify({
                "success": False,
                "error": "非法文件路径"
            }), 403

        # 3. 检查文件类型
        if not filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                "success": False,
                "error": "仅支持Excel文件下载"
            }), 400

        # 4. 提供文件下载
        return send_from_directory(
            directory=str(file_path.parent),
            path=filename,
            as_attachment=True,
            download_name=f"表格处理结果_{pdf_folder}_{filename}"
        )

    except Exception as e:
        print(f"❌ 下载Excel文件异常: {e}")
        return jsonify({
            "success": False,
            "error": f"下载失败: {str(e)}"
        }), 500


# ---------------- 16. 清理表格处理任务（开发调试用） ----------------
@convert_bp.delete('/cleanup-table-jobs')
def api_cleanup_table_jobs():
    """
    清理表格处理任务（仅用于开发调试）
    """
    try:
        # 只清理已完成或失败超过1小时的任务
        now = datetime.now()
        jobs_to_remove = []

        for job_id, job_info in TABLE_PROCESSING_JOBS.items():
            if job_info.get("status") in ["completed", "failed"]:
                end_time_str = job_info.get("end_time")
                if end_time_str:
                    try:
                        end_time = datetime.fromisoformat(end_time_str)
                        if (now - end_time).total_seconds() > 3600:  # 1小时
                            jobs_to_remove.append(job_id)
                    except:
                        jobs_to_remove.append(job_id)

        # 清理任务
        for job_id in jobs_to_remove:
            del TABLE_PROCESSING_JOBS[job_id]

        return jsonify({
            "success": True,
            "message": f"清理了 {len(jobs_to_remove)} 个旧任务",
            "remaining_jobs": len(TABLE_PROCESSING_JOBS)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"清理失败: {str(e)}"
        }), 500

