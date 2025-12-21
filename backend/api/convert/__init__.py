"""
convert 模块
"""
from .pdf_converter import convert_pdf_async  # 删除了 _map_to_disk_file
from .image_operations import (
    get_png_list, serve_png, rotate_and_save, save_rotated_subimage,
    detect_layout, batch_cut_tables_handler, get_folder_images,
    serve_static_image
)
from .database_handler import (
    NewDatabaseManager, load_processing_history,
    get_task_detail  # 删除了 _calculate_duration
)
from .progress_manager import ProgressManager
from .utils import calculate_duration

# ========== 新增：导入 table_processor 的函数 ==========
from .table_processor import (
    submit_table_processing_task,
    get_table_results,
    download_excel_file,
    execute_single_step_handler,
    get_available_steps
)

__all__ = [
    # 图片相关
    'convert_pdf_async',
    'get_png_list',
    'serve_png',
    'rotate_and_save',
    'save_rotated_subimage',
    'detect_layout',
    'batch_cut_tables_handler',
    'get_folder_images',
    'serve_static_image',

    # 数据库相关
    'NewDatabaseManager',
    'load_processing_history',
    'get_task_detail',

    # 进度管理
    'ProgressManager',  # 删除了重复的

    # 工具函数
    'calculate_duration',

    # 新增：表格处理相关
    'submit_table_processing_task',
    'get_table_results',
    'download_excel_file',
    'execute_single_step_handler',
    'get_available_steps'
]