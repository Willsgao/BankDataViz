"""
PDF → PNG 转图蓝图（主接口文件）
"""
from flask import Blueprint, request
from pathlib import Path

# 导入拆分后的模块
from backend.api.convert import (
    pdf_converter,           # 正确
    image_operations,        # 正确
    table_processor,         # 正确
    database_handler,        # 正确
    progress_manager,        # 正确
    utils                   # 正确
)

# 从常量导入
from backend.utils.constants import (
    MAIN_ROOT, PNG_OUTPUT_ROOT,
    UPLOAD_DIR, PNG_OUTPUT_DIR, DATABASE_PATH, STATIC_DIR, JOINED_TABLES_DIR
)

# 初始化输出目录
PNG_OUTPUT_DIR = Path(MAIN_ROOT) / PNG_OUTPUT_ROOT
PNG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

convert_bp = Blueprint('convert', __name__)

# 初始化管理器
db_manager = database_handler.NewDatabaseManager(DATABASE_PATH)
progress_tracker = progress_manager.ProgressManager()

# ---------------- 1. 提交异步转图 ----------------
@convert_bp.post('/convert-pdf-async/<path:pdf_name>')
def api_convert_pdf_async(pdf_name: str):
    """接收中文或 UUID 文件名 → 返回 jobId"""
    return pdf_converter.convert_pdf_async(
        pdf_name,
        UPLOAD_DIR,
        PNG_OUTPUT_DIR,
        db_manager,
        progress_tracker
    )

# ---------------- 2. 轮询进度 ----------------
@convert_bp.get('/progress/<job_id>')
def api_progress(job_id: str):
    return progress_tracker.get_progress(job_id)

# ---------------- 3. 列出某 PDF 的所有 PNG ----------------
@convert_bp.get('/png-list/<pdf_folder>')
def api_png_list(pdf_folder: str):
    return image_operations.get_png_list(pdf_folder, PNG_OUTPUT_DIR)

# ---------------- 4. 单张 PNG 访问 ----------------
@convert_bp.get('/png/<pdf_folder>/<png_name>')
def api_serve_png(pdf_folder: str, png_name: str):
    return image_operations.serve_png(pdf_folder, png_name, PNG_OUTPUT_DIR)

# ---------------- 5. 旋转并保存 ----------------
@convert_bp.post('/png/rotate/<pdf_folder>/<png_name>')
def rotate_png(pdf_folder: str, png_name: str):
    return image_operations.rotate_and_save(
        pdf_folder,
        png_name,
        PNG_OUTPUT_DIR,
        request
    )

# ---------------- 6. 保存前端裁剪子图 ----------------
@convert_bp.post('/save-rotated-sub/<folder>/<png_name>')
def save_rotated_sub(folder: str, png_name: str):
    return image_operations.save_rotated_subimage(
        folder,
        png_name,
        PNG_OUTPUT_DIR,
        request
    )

# ---------------- 7. 单张 PNG 版面分区 ----------------
@convert_bp.get('/layout/<pdf_folder>/<png_name>')
def api_layout(pdf_folder: str, png_name: str):
    return image_operations.detect_layout(
        pdf_folder,
        png_name,
        PNG_OUTPUT_DIR
    )

# ---------------- 8. 批量切割图表 ----------------
@convert_bp.route('/batch-cut-table/<task_id>', methods=['POST', 'OPTIONS'])
def batch_cut_table(task_id):
    return image_operations.batch_cut_tables_handler(
        task_id,
        PNG_OUTPUT_DIR,
        request
    )

# ---------------- 9. 文件夹图片列表 ----------------
@convert_bp.get('/api/folder-images/<path:folder_path>')
def api_folder_images(folder_path: str):
    return image_operations.get_folder_images(folder_path, STATIC_DIR)

# ---------------- 10. 静态文件服务 ----------------
@convert_bp.route('/JOINED_TABLES_DIR/<path:filename>')
def serve_static_png(filename):
    return image_operations.serve_static_image(filename, JOINED_TABLES_DIR)

# ---------------- 11. 分步执行表格处理 ----------------
@convert_bp.route('/step-process/<step_name>', methods=['POST', 'OPTIONS'])
def api_step_process(step_name: str):
    return table_processor.execute_single_step_handler(
        step_name,
        PNG_OUTPUT_DIR,
        request
    )

# ---------------- 12. 获取可用步骤列表 ----------------
@convert_bp.get('/available-steps')
def api_available_steps():
    return table_processor.get_available_steps()

# ---------------- 13. 提交表格处理任务 ----------------
@convert_bp.route('/process-tables/<pdf_folder>', methods=['POST', 'OPTIONS'])
def api_process_tables(pdf_folder: str):
    return table_processor.submit_table_processing_task(
        pdf_folder,
        PNG_OUTPUT_ROOT,
        request,
        progress_tracker
    )

# ---------------- 14. 查询表格处理任务状态 ----------------
@convert_bp.get('/table-progress/<job_id>')
def api_table_progress(job_id: str):
    return progress_tracker.get_table_progress(job_id)

# ---------------- 15. 查询表格处理结果列表 ----------------
@convert_bp.get('/table-results/<pdf_folder>')
def api_table_results(pdf_folder: str):
    return table_processor.get_table_results(
        pdf_folder,
        progress_tracker
    )

# ---------------- 16. 下载表格处理结果Excel文件 ----------------
@convert_bp.route('/download-table/<pdf_folder>/<filename>', methods=['GET'])
def api_download_table(pdf_folder: str, filename: str):
    return table_processor.download_excel_file(pdf_folder, filename)

# ---------------- 17. 清理表格处理任务 ----------------
@convert_bp.delete('/cleanup-table-jobs')
def api_cleanup_table_jobs():
    return progress_tracker.cleanup_old_jobs()

# ---------------- 18. 查询所有表格处理历史记录 ----------------
@convert_bp.get('/table-history')
def api_table_history():
    return database_handler.load_processing_history()

# ---------------- 19. 查询单个任务详情 ----------------
@convert_bp.get('/table-task/<job_id>')
def api_table_task_detail(job_id: str):
    return database_handler.get_task_detail(job_id, progress_tracker)

# ---------------- 工具函数 ----------------
def _map_to_disk(filename: str) -> str | None:
    """保留此函数以便向后兼容"""
    return utils.map_to_disk(filename, db_manager)