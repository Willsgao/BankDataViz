"""
PDF → PNG 转图蓝图（主接口文件）
"""
from flask import Blueprint, request

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
    UPLOAD_DIR, PNG_OUTPUT_DIR, DATABASE_PATH,
    STATIC_DIR, JOINED_TABLES_DIR, FILTERED_TABLES_DIR
)

# 需要在文件开头添加必要的导入
import json
import time
from pathlib import Path
from flask import jsonify

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


# 在 convert_apis.py 中添加以下代码


# ---------------- 20. 表格图片预筛选 API ----------------
@convert_bp.route('/screen-table-images/<pdf_folder>', methods=['POST', 'OPTIONS'])
def api_screen_table_images(pdf_folder: str):
    """
    API: 表格图片预筛选
    功能: 对指定的PNG图片进行表格筛选
    """
    try:
        # 处理OPTIONS预检请求
        if request.method == 'OPTIONS':
            return jsonify({"status": "ok"}), 200

        # 解析请求参数
        data = request.get_json() or {}
        png_names = data.get('png_names', [])
        filter_only = data.get('filter_only', False)

        # 验证参数
        if not png_names:
            return jsonify({
                "success": False,
                "error": "请提供要筛选的图片列表 (png_names)"
            }), 400

        # 验证PDF文件夹存在
        pdf_folder_path = PNG_OUTPUT_DIR / pdf_folder
        if not pdf_folder_path.exists():
            return jsonify({
                "success": False,
                "error": f"PDF文件夹不存在: {pdf_folder}"
            }), 404

        # 构建图片路径列表
        image_paths = []
        missing_images = []

        for png_name in png_names:
            # 清理路径前缀，确保有.png扩展名
            if '/' in png_name:
                png_name = png_name.split('/')[-1]
            if not png_name.lower().endswith('.png'):
                if '.' not in png_name:
                    png_name = f"{png_name}.png"

            image_path = pdf_folder_path / png_name
            if image_path.exists():
                image_paths.append(str(image_path))
            else:
                missing_images.append(png_name)

        if missing_images:
            return jsonify({
                "success": False,
                "error": f"以下图片不存在: {missing_images[:5]}...",
                "missing_count": len(missing_images)
            }), 404

        if not image_paths:
            return jsonify({
                "success": False,
                "error": "没有有效的图片路径"
            }), 400

        # 导入表格筛选模块
        try:
            from backend.api.convert.table_detection_screening import TableScreeningPipeline
        except ImportError as e:
            return jsonify({
                "success": False,
                "error": f"表格筛选模块导入失败: {str(e)}"
            }), 500

        # 设置输出目录
        output_dir = Path(FILTERED_TABLES_DIR) / pdf_folder
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"📊 开始表格图片筛选: {pdf_folder}, 图片数量: {len(image_paths)}")

        try:
            # 创建筛选管道并执行
            pipeline = TableScreeningPipeline()
            report = pipeline.screen_directory(
                input_dir=str(pdf_folder_path),  # 直接使用原始图片目录
                output_dir=str(output_dir)
            )

            # 构建响应数据
            response_data = {
                "success": True,
                "pdf_folder": pdf_folder,
                "total_images": len(image_paths),
                "has_table_count": len(report.has_table_images),
                "no_table_count": len(report.no_table_images),
                "output_dir": str(output_dir),
                "tables_dir": str(output_dir / "tables"),
                "no_tables_dir": str(output_dir / "no_tables"),
                "screening_report": report.to_dict(),
                "has_table_images": report.has_table_images,
                "no_table_images": report.no_table_images
            }

            # 如果只需要有表格的图片列表
            if filter_only:
                response_data["filtered_images"] = report.has_table_images

            print(f"✅ 表格筛选完成: 有表格{len(report.has_table_images)}张，无表格{len(report.no_table_images)}张")
            return jsonify(response_data)

        except Exception as e:
            print(f"💥 筛选过程异常: {e}")
            return jsonify({
                "success": False,
                "error": f"筛选过程失败: {str(e)}"
            }), 500

    except Exception as e:
        import traceback
        print(f"💥 表格筛选API异常: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"表格筛选失败: {str(e)}"
        }), 500

# ---------------- 21. 获取筛选结果详情 API ----------------
@convert_bp.get('/screen-results/<pdf_folder>')
def api_get_screen_results(pdf_folder: str):
    """
    API: 获取上次筛选结果
    功能: 获取指定PDF文件夹的上次表格筛选结果
    查询参数:
    - result_file: 可选，指定结果文件路径
    """
    try:
        # 查找可能的结果文件
        result_file = request.args.get('result_file')

        if not result_file:
            # 尝试查找默认位置的结果文件
            result_dir = PNG_OUTPUT_DIR / pdf_folder / "screening_results"
            if result_dir.exists():
                result_files = list(result_dir.glob("*.json"))
                if result_files:
                    result_file = str(max(result_files, key=lambda x: x.stat().st_mtime))

        if not result_file or not Path(result_file).exists():
            return jsonify({
                "success": False,
                "error": "未找到筛选结果文件",
                "suggestion": "请先执行表格筛选"
            }), 404

        # 读取结果文件
        import json
        with open(result_file, 'r', encoding='utf-8') as f:
            result_data = json.load(f)

        return jsonify({
            "success": True,
            "pdf_folder": pdf_folder,
            "result_file": result_file,
            "data": result_data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"读取筛选结果失败: {str(e)}"
        }), 500


# ---------------- 22. 批量筛选多个文件夹 API ----------------
@convert_bp.route('/batch-screen-folders', methods=['POST', 'OPTIONS'])
def api_batch_screen_folders():
    """
    API: 批量筛选多个PDF文件夹
    功能: 批量扫描多个PDF文件夹，筛选有表格的图片
    请求参数 (JSON):
    {
        "pdf_folders": ["folder1", "folder2", ...],
        "output_base_dir": "path/to/output",  # 输出基础目录
        "parallel": false  # 是否并行处理，默认false
    }
    """
    try:
        if request.method == 'OPTIONS':
            return jsonify({"status": "ok"}), 200

        data = request.get_json() or {}
        pdf_folders = data.get('pdf_folders', [])
        output_base_dir = data.get('output_base_dir')
        parallel = data.get('parallel', False)

        if not pdf_folders:
            return jsonify({
                "success": False,
                "error": "请提供要筛选的PDF文件夹列表"
            }), 400

        # 验证所有文件夹都存在
        missing_folders = []
        for folder in pdf_folders:
            folder_path = PNG_OUTPUT_DIR / folder
            if not folder_path.exists():
                missing_folders.append(folder)

        if missing_folders:
            return jsonify({
                "success": False,
                "error": f"以下PDF文件夹不存在: {', '.join(missing_folders[:5])}",
                "missing_count": len(missing_folders)
            }), 404

        # 导入筛选模块
        try:
            from backend.src.services.table_screening.table_detection_screening import (
                TableScreeningPipeline
            )
        except ImportError as e:
            return jsonify({
                "success": False,
                "error": f"表格筛选模块导入失败: {str(e)}"
            }), 500

        results = []

        # 设置输出基础目录
        if output_base_dir:
            output_base_path = Path(output_base_dir)
            output_base_path.mkdir(parents=True, exist_ok=True)
        else:
            # 使用临时目录
            import tempfile
            output_base_path = Path(tempfile.mkdtemp(prefix="batch_screening_"))

        # 逐个处理文件夹
        for folder in pdf_folders:
            try:
                print(f"📁 处理文件夹: {folder}")

                # 获取文件夹中PNG图片
                folder_path = PNG_OUTPUT_DIR / folder
                png_files = list(folder_path.glob("*.png"))

                if not png_files:
                    results.append({
                        "pdf_folder": folder,
                        "success": False,
                        "error": "文件夹中没有PNG图片",
                        "image_count": 0
                    })
                    continue

                # 创建临时目录
                import tempfile
                import shutil

                temp_input_dir = tempfile.mkdtemp(prefix=f"screening_{folder}_")
                temp_output_dir = output_base_path / folder
                temp_output_dir.mkdir(parents=True, exist_ok=True)

                try:
                    # 复制图片到临时目录
                    for png_file in png_files:
                        shutil.copy2(png_file, temp_input_dir)

                    # 执行筛选
                    pipeline = TableScreeningPipeline()
                    report = pipeline.screen_directory(
                        input_dir=temp_input_dir,
                        output_dir=str(temp_output_dir)
                    )

                    # 保存报告
                    report_file = temp_output_dir / "screening_report.json"
                    report.save_to_file(str(report_file))

                    results.append({
                        "pdf_folder": folder,
                        "success": True,
                        "image_count": len(png_files),
                        "has_table_count": len(report.has_table_images),
                        "no_table_count": len(report.no_table_images),
                        "uncertain_count": len(report.uncertain_images),
                        "report_path": str(report_file),
                        "output_dir": str(temp_output_dir),
                        "processing_time": report.processing_time
                    })

                    print(f"✅ 完成: {folder} - "
                          f"有表格{len(report.has_table_images)}/{len(png_files)}张")

                finally:
                    # 清理临时输入目录
                    shutil.rmtree(temp_input_dir, ignore_errors=True)

            except Exception as e:
                import traceback
                print(f"❌ 处理文件夹失败 {folder}: {e}")
                traceback.print_exc()

                results.append({
                    "pdf_folder": folder,
                    "success": False,
                    "error": str(e),
                    "image_count": 0
                })

        # 汇总统计
        total_folders = len(pdf_folders)
        successful_folders = sum(1 for r in results if r.get('success'))
        total_images = sum(r.get('image_count', 0) for r in results)
        total_has_table = sum(r.get('has_table_count', 0) for r in results)

        return jsonify({
            "success": True,
            "batch_id": f"batch_{int(time.time())}",
            "summary": {
                "total_folders": total_folders,
                "successful_folders": successful_folders,
                "failed_folders": total_folders - successful_folders,
                "total_images": total_images,
                "total_has_table": total_has_table,
                "has_table_percentage": total_has_table / total_images * 100 if total_images > 0 else 0
            },
            "results": results,
            "output_base_dir": str(output_base_path)
        })

    except Exception as e:
        import traceback
        print(f"💥 批量筛选API异常: {e}")
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": f"批量筛选失败: {str(e)}"
        }), 500


# ---------------- 23. 清理筛选临时文件 API ----------------
@convert_bp.delete('/cleanup-screening-temp')
def api_cleanup_screening_temp():
    """
    API: 清理筛选临时文件
    功能: 清理表格筛选过程中产生的临时文件
    查询参数:
    - older_than_hours: 可选，清理多少小时前的文件，默认24
    - pdf_folder: 可选，只清理指定PDF文件夹的临时文件
    """
    try:
        older_than_hours = float(request.args.get('older_than_hours', 24))
        pdf_folder = request.args.get('pdf_folder')

        import tempfile
        import os
        import time
        import shutil

        temp_dir = tempfile.gettempdir()
        deleted_count = 0
        deleted_size = 0

        # 查找表格筛选相关的临时目录
        for item in Path(temp_dir).iterdir():
            if item.is_dir():
                dir_name = item.name

                # 匹配表格筛选的临时目录模式
                is_screening_dir = (
                        dir_name.startswith("table_screening_") or
                        dir_name.startswith("filtered_tables_") or
                        dir_name.startswith("screening_") or
                        dir_name.startswith("batch_screening_")
                )

                # 如果指定了PDF文件夹，进一步过滤
                if pdf_folder and pdf_folder not in dir_name:
                    continue

                if is_screening_dir:
                    # 检查目录创建时间
                    try:
                        dir_mtime = item.stat().st_mtime
                        hours_old = (time.time() - dir_mtime) / 3600

                        if hours_old > older_than_hours:
                            # 计算目录大小
                            dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())

                            # 删除目录
                            shutil.rmtree(item, ignore_errors=True)
                            deleted_count += 1
                            deleted_size += dir_size

                            print(
                                f"🗑️  清理临时目录: {dir_name} ({dir_size / 1024 / 1024:.1f}MB, {hours_old:.1f}小时前)")
                    except Exception as e:
                        print(f"⚠️  清理目录失败 {dir_name}: {e}")

        return jsonify({
            "success": True,
            "message": f"清理完成，删除了{deleted_count}个临时目录，释放空间{deleted_size / 1024 / 1024:.1f}MB",
            "deleted_count": deleted_count,
            "deleted_size_mb": deleted_size / 1024 / 1024,
            "older_than_hours": older_than_hours
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"清理临时文件失败: {str(e)}"
        }), 500

