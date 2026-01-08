"""
PDF → PNG 转图蓝图（主接口文件）
"""

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
from pathlib import Path
import tempfile
import time
import shutil
from flask import Blueprint, request, jsonify, send_file  # 确保有 send_file


# 初始化输出目录
PNG_OUTPUT_DIR = Path(MAIN_ROOT) / PNG_OUTPUT_ROOT
PNG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

convert_bp = Blueprint('convert', __name__)

# 初始化管理器
db_manager = database_handler.NewDatabaseManager(DATABASE_PATH)
progress_tracker = progress_manager.ProgressManager()

# ---------------- 1. 提交异步转图 ----------------
@convert_bp.post('/api/convert-pdf-async/<path:pdf_name>')
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
@convert_bp.get('/api/progress/<job_id>')
def api_progress(job_id: str):
    return progress_tracker.get_progress(job_id)

# ---------------- 3. 列出某 PDF 的所有 PNG ----------------
@convert_bp.get('/api/png-list/<pdf_folder>')
def api_png_list(pdf_folder: str):
    print("pdf_folder, PNG_OUTPUT_DIR:::")
    print(pdf_folder, PNG_OUTPUT_DIR)
    return image_operations.get_png_list(pdf_folder, PNG_OUTPUT_DIR)

# ---------------- 4. 单张 PNG 访问 ----------------
@convert_bp.get('/api/png/<pdf_folder>/<png_name>')
def api_serve_png(pdf_folder: str, png_name: str):
    return image_operations.serve_png(pdf_folder, png_name, PNG_OUTPUT_DIR)

# ---------------- 5. 旋转并保存 ----------------
@convert_bp.post('/api/png/rotate/<pdf_folder>/<png_name>')
def rotate_png(pdf_folder: str, png_name: str):
    return image_operations.rotate_and_save(
        pdf_folder,
        png_name,
        PNG_OUTPUT_DIR,
        request
    )

# ---------------- 6. 保存前端裁剪子图 ----------------
@convert_bp.post('/api/save-rotated-sub/<folder>/<png_name>')
def save_rotated_sub(folder: str, png_name: str):
    return image_operations.save_rotated_subimage(
        folder,
        png_name,
        PNG_OUTPUT_DIR,
        request
    )

# ---------------- 7. 单张 PNG 版面分区 ----------------
@convert_bp.get('/api/layout/<pdf_folder>/<png_name>')
def api_layout(pdf_folder: str, png_name: str):
    return image_operations.detect_layout(
        pdf_folder,
        png_name,
        PNG_OUTPUT_DIR
    )

# ---------------- 8. 批量切割图表 ----------------
@convert_bp.route('/api/batch-cut-table/<task_id>', methods=['POST', 'OPTIONS'])
def batch_cut_table(task_id):
    return image_operations.batch_cut_tables_handler(
        task_id,
        PNG_OUTPUT_DIR,
        request
    )

# ---------------- 9. 文件夹图片列表 ----------------
@convert_bp.get('/api/api/folder-images/<path:folder_path>')
def api_folder_images(folder_path: str):
    return image_operations.get_folder_images(folder_path, STATIC_DIR)

# ---------------- 10. 静态文件服务 ----------------
@convert_bp.route('/api/JOINED_TABLES_DIR/<path:filename>')
def serve_static_png(filename):
    return image_operations.serve_static_image(filename, JOINED_TABLES_DIR)

# ---------------- 11. 分步执行表格处理 ----------------
@convert_bp.route('/api/step-process/<step_name>', methods=['POST', 'OPTIONS'])
def api_step_process(step_name: str):
    return table_processor.execute_single_step_handler(
        step_name,
        PNG_OUTPUT_DIR,
        request
    )

# ---------------- 12. 获取可用步骤列表 ----------------
@convert_bp.get('/api/available-steps')
def api_available_steps():
    return table_processor.get_available_steps()

# ---------------- 13. 提交表格处理任务 ----------------
@convert_bp.route('/api/process-tables/<pdf_folder>', methods=['POST', 'OPTIONS'])
def api_process_tables(pdf_folder: str):
    # INPUT_TABLES_ROOT = FILTERED_TABLES_DIR / "tables"
    return table_processor.submit_table_processing_task(
        pdf_folder,
        FILTERED_TABLES_DIR,
        request,
        progress_tracker
    )

# ---------------- 14. 查询表格处理任务状态 ----------------
@convert_bp.get('/api/table-progress/<job_id>')
def api_table_progress(job_id: str):
    return progress_tracker.get_table_progress(job_id)

# ---------------- 15. 查询表格处理结果列表 ----------------
@convert_bp.get('/api/table-results/<pdf_folder>')
def api_table_results(pdf_folder: str):
    return table_processor.get_table_results(
        pdf_folder,
        progress_tracker
    )

# ---------------- 16. 下载表格处理结果Excel文件 ----------------
@convert_bp.route('/api/download-table/<pdf_folder>/<filename>', methods=['GET'])
def api_download_table(pdf_folder: str, filename: str):
    return table_processor.download_excel_file(pdf_folder, filename)

# ---------------- 17. 清理表格处理任务 ----------------
@convert_bp.delete('/api/cleanup-table-jobs')
def api_cleanup_table_jobs():
    return progress_tracker.cleanup_old_jobs()

# ---------------- 18. 查询所有表格处理历史记录 ----------------
@convert_bp.get('/api/table-history')
def api_table_history():
    return database_handler.load_processing_history()

# ---------------- 19. 查询单个任务详情 ----------------
@convert_bp.get('/api/table-task/<job_id>')
def api_table_task_detail(job_id: str):
    return database_handler.get_task_detail(job_id, progress_tracker)

# ---------------- 工具函数 ----------------
def _map_to_disk(filename: str) -> str | None:
    """保留此函数以便向后兼容"""
    return utils.map_to_disk(filename, db_manager)


# ---------------- 20. 表格图片预筛选 API ----------------
@convert_bp.route('/api/screen-table-images/<pdf_folder>', methods=['POST', 'OPTIONS'])
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

        # ---------------- 0. 缓存检查 ----------------
        output_dir = Path(FILTERED_TABLES_DIR) / pdf_folder
        tables_dir = output_dir / "tables"
        no_tables_dir = output_dir / "no_tables"

        # 若已存在分类结果，直接返回缓存
        if tables_dir.exists() or no_tables_dir.exists():
            cached_tables = [f.name for f in tables_dir.glob("*.png")] if tables_dir.exists() else []
            cached_no_tables = [f.name for f in no_tables_dir.glob("*.png")] if no_tables_dir.exists() else []

            if cached_tables or cached_no_tables:
                return jsonify({
                    "success": True,
                    "cached": True,
                    "message": "使用已有筛选结果",
                    "classified_data": {
                        "tables": [
                            {"name": n, "relative_path": f"filtered_tables/{pdf_folder}/tables/{n}",
                             "type": "tables", "cached": True}
                            for n in cached_tables
                        ],
                        "no_tables": [
                            {"name": n, "relative_path": f"filtered_tables/{pdf_folder}/no_tables/{n}",
                             "type": "no_tables", "cached": True}
                            for n in cached_no_tables
                        ],
                        "uncertain": []
                    },
                    "stats": {
                        "tables_count": len(cached_tables),
                        "no_tables_count": len(cached_no_tables),
                        "uncertain_count": 0,
                        "total": len(cached_tables) + len(cached_no_tables)
                    }
                })

        # ---------------- 1. 构建图片路径列表（原有代码） ----------------
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

            # 1. 获取检测结果中的置信度信息
            detection_info = {}
            if hasattr(report, 'detection_results'):
                for result in report.detection_results:
                    if hasattr(result, 'image_name') and hasattr(result, 'confidence'):
                        img_name = Path(result.image_name).name
                        detection_info[img_name] = {
                            'confidence': result.confidence,
                            'processing_time': getattr(result, 'processing_time', 0.0)
                        }

            # 2. 获取有表格的图片实际路径 - 基于检测结果
            tables_images = []
            tables_dir = output_dir / "tables"

            # 确保 report.has_table_images 存在
            if hasattr(report, 'has_table_images') and tables_dir.exists():
                for img_name in report.has_table_images:
                    img_file = tables_dir / img_name
                    if img_file.exists():
                        info = detection_info.get(img_name, {})
                        tables_images.append({
                            "name": img_name,
                            "path": str(img_file),  # 绝对路径
                            "relative_path": f"filtered_tables/{pdf_folder}/tables/{img_name}",
                            "web_url": f"/static/filtered_tables/{pdf_folder}/tables/{img_name}",
                            "type": "tables",
                            "source_dir": str(pdf_folder_path),
                            "confidence": info.get('confidence', 0.9),
                            "processing_time": info.get('processing_time', 0.0),
                            "detected_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                            "size": img_file.stat().st_size,
                            "modified_at": img_file.stat().st_mtime
                        })
                    else:
                        print(f"⚠️ 警告: 有表格图片 {img_name} 在目录中不存在")

            # 3. 获取无表格的图片实际路径 - 基于检测结果
            no_tables_images = []
            no_tables_dir = output_dir / "no_tables"

            # 确保 report.no_table_images 存在
            if hasattr(report, 'no_table_images') and no_tables_dir.exists():
                for img_name in report.no_table_images:
                    img_file = no_tables_dir / img_name
                    if img_file.exists():
                        info = detection_info.get(img_name, {})
                        no_tables_images.append({
                            "name": img_name,
                            "path": str(img_file),  # 绝对路径
                            "relative_path": f"filtered_tables/{pdf_folder}/no_tables/{img_name}",
                            "web_url": f"/static/filtered_tables/{pdf_folder}/no_tables/{img_name}",
                            "type": "no_tables",
                            "source_dir": str(pdf_folder_path),
                            "confidence": info.get('confidence', 0.9),
                            "processing_time": info.get('processing_time', 0.0),
                            "detected_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                            "size": img_file.stat().st_size,
                            "modified_at": img_file.stat().st_mtime
                        })
                    else:
                        print(f"⚠️ 警告: 无表格图片 {img_name} 在目录中不存在")

            # 4. 检查是否有不确定的图片
            uncertain_images = []
            if hasattr(report, 'uncertain_images') and report.uncertain_images:
                for img_name in report.uncertain_images:
                    # 不确定的图片可能在原始目录
                    img_file = pdf_folder_path / img_name
                    if img_file.exists():
                        info = detection_info.get(img_name, {})
                        uncertain_images.append({
                            "name": img_name,
                            "path": str(img_file),
                            "relative_path": f"pdf2pngs/{pdf_folder}/{img_name}",
                            "web_url": f"/static/pdf2pngs/{pdf_folder}/{img_name}",
                            "type": "uncertain",
                            "source_dir": str(pdf_folder_path),
                            "confidence": info.get('confidence', 0.5),
                            "processing_time": info.get('processing_time', 0.0),
                            "detected_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                            "size": img_file.stat().st_size,
                            "modified_at": img_file.stat().st_mtime
                        })

            # 5. 构建响应数据
            response_data = {
                "success": True,
                "pdf_folder": pdf_folder,
                "total_images": len(image_paths),
                "has_table_count": len(tables_images),  # 使用实际数量
                "no_table_count": len(no_tables_images),  # 使用实际数量
                "uncertain_count": len(uncertain_images),  # 新增
                "output_dir": str(output_dir),
                "output_relative_path": f"filtered_tables/{pdf_folder}",
                "tables_dir": str(tables_dir),
                "tables_relative_dir": f"filtered_tables/{pdf_folder}/tables",
                "no_tables_dir": str(no_tables_dir),
                "no_tables_relative_dir": f"filtered_tables/{pdf_folder}/no_tables",
                "screening_report": report.to_dict(),
                "has_table_images": report.has_table_images,  # 原始检测结果
                "no_table_images": report.no_table_images,  # 原始检测结果
                "uncertain_images": getattr(report, 'uncertain_images', []),  # 原始检测结果
                "classified_data": {
                    "tables": tables_images,
                    "no_tables": no_tables_images,
                    "uncertain": uncertain_images
                },
                "stats": {
                    "tables_count": len(tables_images),
                    "no_tables_count": len(no_tables_images),
                    "uncertain_count": len(uncertain_images),
                    "total": len(image_paths)
                }
            }

            return jsonify(response_data)

        except Exception as e:
            print(f"💥 筛选过程异常: {e}")
            import traceback
            traceback.print_exc()
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
@convert_bp.get('/api/screen-results/<pdf_folder>')
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
@convert_bp.route('/api/batch-screen-folders', methods=['POST', 'OPTIONS'])
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
@convert_bp.delete('/api/cleanup-screening-temp')
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


# ---------------- 24. 图片分类 API ----------------
# convert_apis.py - 修改 api_get_classified_images 函数
@convert_bp.route('/api/classified-images/<pdf_folder>', methods=['GET'])
def api_get_classified_images(pdf_folder: str):
    """
    API: 获取已分类的图片列表
    功能: 返回指定PDF文件夹中已分类的图片列表
    """
    try:
        # 验证PDF文件夹存在
        pdf_folder_path = PNG_OUTPUT_DIR / pdf_folder
        if not pdf_folder_path.exists():
            return jsonify({
                "success": False,
                "error": f"PDF文件夹不存在: {pdf_folder}"
            }), 404

        # 检查筛选输出目录
        output_dir = Path(FILTERED_TABLES_DIR) / pdf_folder
        tables_dir = output_dir / "tables"
        no_tables_dir = output_dir / "no_tables"

        # 检查是否有筛选结果
        if not output_dir.exists():
            return jsonify({
                "success": True,
                "data": {
                    "tables": [],
                    "no_tables": [],
                    "uncertain": []
                },
                "message": "尚未进行图片筛选",
                "stats": {
                    "tables_count": 0,
                    "no_tables_count": 0,
                    "uncertain_count": 0,
                    "total": 0
                }
            })

        # 构建分类图片数据
        classified_data = {
            "tables": [],
            "no_tables": [],
            "uncertain": []
        }

        # 读取有表格图片
        if tables_dir.exists():
            for img_file in tables_dir.glob("*.png"):
                classified_data["tables"].append({
                    "name": img_file.name,
                    "path": str(img_file),
                    "relative_path": f"filtered_tables/{pdf_folder}/tables/{img_file.name}",
                    "url": f"/filtered-tables-image/{pdf_folder}/tables/{img_file.name}",
                    "type": "tables",
                    "size": img_file.stat().st_size,
                    "modified_at": img_file.stat().st_mtime
                })

        # 读取无表格图片
        if no_tables_dir.exists():
            for img_file in no_tables_dir.glob("*.png"):
                classified_data["no_tables"].append({
                    "name": img_file.name,
                    "path": str(img_file),
                    "relative_path": f"filtered_tables/{pdf_folder}/no_tables/{img_file.name}",
                    "url": f"/filtered-tables-image/{pdf_folder}/no_tables/{img_file.name}",
                    "type": "no_tables",
                    "size": img_file.stat().st_size,
                    "modified_at": img_file.stat().st_mtime
                })


        # 计算统计信息
        stats = {
            "tables_count": len(classified_data["tables"]),
            "no_tables_count": len(classified_data["no_tables"]),
            "uncertain_count": len(classified_data["uncertain"]),
            "total": len(classified_data["tables"]) + len(classified_data["no_tables"]) + len(classified_data["uncertain"])
        }

        response_data = {
            "success": True,
            "data": classified_data,  # 将数据包装在 data 字段中
            "stats": stats,
            "directories": {
                "tables_dir": str(tables_dir),
                "no_tables_dir": str(no_tables_dir),
                "output_dir": str(output_dir)
            }
        }

        result = jsonify(response_data)
        print("Content-Type:", result.headers.get('Content-Type'))
        print("resultresult")
        print(result.get_json())

        # 关键修复：返回标准格式
        return result

    except Exception as e:
        import traceback
        print(f"💥 获取分类图片失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"获取分类图片失败: {str(e)}"
        }), 500


# ---------------- 25. 移动单张图片 API ----------------
@convert_bp.route('/api/move-screened-image/<pdf_folder>', methods=['POST'])
def api_move_screened_image(pdf_folder: str):
    """
    API: 移动单张图片到不同分类
    功能: 将有表格/无表格的图片移动到另一个分类
    """
    try:
        # 解析请求数据
        data = request.get_json() or {}
        image_name = data.get('image_name')
        from_type = data.get('from_type')  # 'tables' 或 'no_tables'
        to_type = data.get('to_type')  # 'tables' 或 'no_tables'
        move_physically = data.get('move_physically', True)

        # 验证参数
        if not image_name:
            return jsonify({
                "success": False,
                "error": "请提供图片名称 (image_name)"
            }), 400

        if not from_type or not to_type:
            return jsonify({
                "success": False,
                "error": "请提供来源分类和目标分类 (from_type, to_type)"
            }), 400

        if from_type not in ['tables', 'no_tables', 'uncertain']:
            return jsonify({
                "success": False,
                "error": "来源分类必须是 'tables', 'no_tables' 或 'uncertain'"
            }), 400

        if to_type not in ['tables', 'no_tables', 'uncertain']:
            return jsonify({
                "success": False,
                "error": "目标分类必须是 'tables', 'no_tables' 或 'uncertain'"
            }), 400

        if from_type == to_type:
            return jsonify({
                "success": False,
                "error": "来源分类和目标分类不能相同"
            }), 400

        # 构建目录路径
        output_dir = Path(FILTERED_TABLES_DIR) / pdf_folder
        from_dir = output_dir / from_type
        to_dir = output_dir / to_type

        # 确保目录存在
        to_dir.mkdir(parents=True, exist_ok=True)

        # 构建完整文件路径
        from_path = from_dir / image_name
        to_path = to_dir / image_name

        # 检查源文件是否存在
        if not from_path.exists():
            return jsonify({
                "success": False,
                "error": f"源文件不存在: {from_path}"
            }), 404

        print(f"📂 移动图片: {image_name}")
        print(f"   从: {from_path}")
        print(f"   到: {to_path}")

        # 处理文件名冲突（如果目标文件已存在）
        counter = 1
        final_to_path = to_path
        while final_to_path.exists():
            stem = Path(image_name).stem
            suffix = Path(image_name).suffix
            new_name = f"{stem}_{counter}{suffix}"
            final_to_path = to_dir / new_name
            counter += 1

            if counter > 100:
                return jsonify({
                    "success": False,
                    "error": "生成唯一文件名失败"
                }), 500

        moved = False
        actual_to_name = final_to_path.name

        # 物理移动文件
        if move_physically:
            try:
                # 复制文件到新位置
                shutil.copy2(str(from_path), str(final_to_path))

                # 可选：删除源文件（如果需要）
                # from_path.unlink()

                moved = True
                print(f"✅ 文件已复制到: {final_to_path}")

            except Exception as e:
                print(f"❌ 文件移动失败: {e}")
                return jsonify({
                    "success": False,
                    "error": f"文件移动失败: {str(e)}"
                }), 500
        else:
            # 仅逻辑移动（更新记录）
            moved = True
            print(f"📝 逻辑移动: {image_name} -> {to_type}")

        # 构建响应
        response_data = {
            "success": True,
            "message": f"图片已成功移动到{to_type}分类",
            "data": {
                "original_name": image_name,
                "actual_name": actual_to_name,
                "from_type": from_type,
                "to_type": to_type,
                "from_path": str(from_path),
                "to_path": str(final_to_path),
                "moved_physically": move_physically,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            },
            "file_info": {
                "new_name": actual_to_name,
                "new_path": str(final_to_path),
                "new_url": f"/api/filtered-tables/{pdf_folder}/{to_type}/{actual_to_name}"
            }
        }

        # 如果是物理移动且成功，可以尝试删除源文件
        if moved and move_physically:
            try:
                from_path.unlink()
                print(f"🗑️  已删除源文件: {from_path}")
                response_data["data"]["source_deleted"] = True
            except Exception as e:
                print(f"⚠️  删除源文件失败（可忽略）: {e}")
                response_data["data"]["source_deleted"] = False
                response_data["data"]["delete_error"] = str(e)

        return jsonify(response_data)

    except Exception as e:
        import traceback
        print(f"💥 移动图片失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"移动图片失败: {str(e)}"
        }), 500

# ---------------- 26. 批量移动图片 API ----------------
@convert_bp.route('/api/batch-move-images/<pdf_folder>', methods=['POST'])
def api_batch_move_images(pdf_folder: str):
    """
    API: 批量移动图片
    功能: 批量将多张图片移动到指定分类
    """
    try:
        # 解析请求数据
        data = request.get_json() or {}
        images = data.get('images', [])  # 图片名称列表
        to_type = data.get('to_type')  # 目标分类
        move_physically = data.get('move_physically', True)

        # 验证参数
        if not images:
            return jsonify({
                "success": False,
                "error": "请提供要移动的图片列表 (images)"
            }), 400

        if not to_type or to_type not in ['tables', 'no_tables', 'uncertain']:
            return jsonify({
                "success": False,
                "error": "请提供有效的目标分类 (to_type)"
            }), 400

        # 构建目录路径
        output_dir = Path(FILTERED_TABLES_DIR) / pdf_folder
        to_dir = output_dir / to_type

        # 确保目标目录存在
        to_dir.mkdir(parents=True, exist_ok=True)

        print(f"📦 批量移动 {len(images)} 张图片到 {to_type} 分类")

        results = []
        success_count = 0
        failed_count = 0

        # 遍历所有图片，确定它们当前所在的分类
        for image_name in images:
            try:
                # 查找图片当前所在位置
                found = False
                current_type = None
                current_path = None

                # 在所有分类目录中查找
                for category in ['tables', 'no_tables', 'uncertain']:
                    category_dir = output_dir / category
                    if category_dir.exists():
                        image_path = category_dir / image_name
                        if image_path.exists():
                            found = True
                            current_type = category
                            current_path = image_path
                            break

                if not found:
                    results.append({
                        "image_name": image_name,
                        "success": False,
                        "error": "图片不存在",
                        "current_type": None
                    })
                    failed_count += 1
                    continue

                # 如果已经在目标分类，跳过
                if current_type == to_type:
                    results.append({
                        "image_name": image_name,
                        "success": True,
                        "skipped": True,
                        "message": "图片已在目标分类",
                        "current_type": current_type,
                        "to_type": to_type
                    })
                    success_count += 1
                    continue

                # 构建目标路径
                to_path = to_dir / image_name

                # 处理文件名冲突
                counter = 1
                final_to_path = to_path
                while final_to_path.exists():
                    stem = Path(image_name).stem
                    suffix = Path(image_name).suffix
                    new_name = f"{stem}_{counter}{suffix}"
                    final_to_path = to_dir / new_name
                    counter += 1

                # 移动文件
                if move_physically:
                    # 复制到新位置
                    shutil.copy2(str(current_path), str(final_to_path))

                    # 删除源文件
                    try:
                        current_path.unlink()
                        source_deleted = True
                    except Exception as e:
                        source_deleted = False
                        delete_error = str(e)

                # 记录结果
                result = {
                    "image_name": image_name,
                    "success": True,
                    "from_type": current_type,
                    "to_type": to_type,
                    "from_path": str(current_path),
                    "to_path": str(final_to_path),
                    "actual_name": final_to_path.name,
                    "moved_physically": move_physically,
                    "source_deleted": source_deleted if move_physically else None,
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                }

                if move_physically and not source_deleted:
                    result["warning"] = "源文件删除失败"
                    result["delete_error"] = delete_error

                results.append(result)
                success_count += 1

                print(f"  ✅ {image_name}: {current_type} -> {to_type}")

            except Exception as e:
                print(f"  ❌ {image_name}: 移动失败 - {e}")
                results.append({
                    "image_name": image_name,
                    "success": False,
                    "error": str(e),
                    "current_type": current_type if 'current_type' in locals() else None
                })
                failed_count += 1

        # 构建响应
        return jsonify({
            "success": True,
            "message": f"批量移动完成: 成功 {success_count} 个, 失败 {failed_count} 个",
            "summary": {
                "total": len(images),
                "success": success_count,
                "failed": failed_count,
                "target_type": to_type
            },
            "results": results,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        import traceback
        print(f"💥 批量移动失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"批量移动失败: {str(e)}"
        }), 500

#
# ---------------- 27. 重新检测图片 API ----------------
@convert_bp.route('/api/re-screen-image/<pdf_folder>', methods=['POST'])
def api_re_screen_image(pdf_folder: str):
    """
    API: 重新检测单张图片
    功能: 对单张图片重新进行表格检测
    """
    try:
        # 解析请求数据
        data = request.get_json() or {}
        image_name = data.get('image_name')
        current_type = data.get('current_type')
        use_llm = data.get('use_llm', True)
        force_redetect = data.get('force_redetect', False)

        # 验证参数
        if not image_name:
            return jsonify({
                "success": False,
                "error": "请提供图片名称 (image_name)"
            }), 400

        # 构建图片路径
        output_dir = Path(FILTERED_TABLES_DIR) / pdf_folder

        # 尝试在所有分类目录中找到图片
        image_path = None
        found_type = None

        for category in ['tables', 'no_tables', 'uncertain']:
            category_dir = output_dir / category
            if category_dir.exists():
                potential_path = category_dir / image_name
                if potential_path.exists():
                    image_path = potential_path
                    found_type = category
                    break

        if not image_path:
            return jsonify({
                "success": False,
                "error": f"图片不存在: {image_name}"
            }), 404

        print(f"🔄 重新检测图片: {image_name}")
        print(f"   当前分类: {found_type}")
        print(f"   使用LLM: {use_llm}")

        # 导入表格检测模块
        try:
            from backend.api.convert.table_detection_screening import TableScreeningPipeline
        except ImportError as e:
            return jsonify({
                "success": False,
                "error": f"表格检测模块导入失败: {str(e)}"
            }), 500

        # 创建筛选管道
        pipeline = TableScreeningPipeline()

        # 重新检测图片
        try:
            # 使用传统检测器直接检测
            from backend.api.convert.table_detection_screening import TraditionalTableDetector

            detector = TraditionalTableDetector()
            screening_result, confidence, features = detector.detect(str(image_path))

            # 如果需要，使用LLM进行判断
            detected_type = 'no_tables'
            llm_used = False

            if screening_result.name == 'HAS_TABLE':
                detected_type = 'tables'
            elif screening_result.name == 'UNCERTAIN' and use_llm:
                # 使用LLM判断
                from backend.api.convert.table_detection_screening import LLMTableDetector
                llm_detector = LLMTableDetector()
                has_table, llm_confidence = llm_detector.detect_with_llm(str(image_path))
                detected_type = 'tables' if has_table else 'no_tables'
                llm_used = True
                confidence = llm_confidence if has_table else 1 - llm_confidence
            elif screening_result.name == 'NO_TABLE':
                detected_type = 'no_tables'

            print(f"   🔍 检测结果: {detected_type} (置信度: {confidence:.2f})")

            # 构建响应
            response_data = {
                "success": True,
                "message": f"重新检测完成: {detected_type}",
                "data": {
                    "image_name": image_name,
                    "original_type": found_type,
                    "detected_type": detected_type,
                    "confidence": float(confidence),
                    "features": features,
                    "llm_used": llm_used,
                    "force_redetect": force_redetect,
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                },
                "recommendation": {
                    "move_required": detected_type != found_type,
                    "action": f"移动到{detected_type}" if detected_type != found_type else "无需移动"
                }
            }

            return jsonify(response_data)

        except Exception as e:
            print(f"❌ 重新检测失败: {e}")
            return jsonify({
                "success": False,
                "error": f"重新检测失败: {str(e)}"
            }), 500

    except Exception as e:
        import traceback
        print(f"💥 重新检测API失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"重新检测失败: {str(e)}"
        }), 500

# ---------------- 28. 获取统计信息 ------ API ----------------
@convert_bp.route('/api/screening-statistics/<pdf_folder>', methods=['GET'])
def api_get_screening_statistics(pdf_folder: str):
    """
    API: 获取筛选统计信息
    功能: 返回指定PDF文件夹的筛选统计信息
    """
    try:
        # 构建目录路径
        output_dir = Path(FILTERED_TABLES_DIR) / pdf_folder
        tables_dir = output_dir / "tables"
        no_tables_dir = output_dir / "no_tables"

        # 检查是否有筛选结果
        if not output_dir.exists():
            return jsonify({
                "success": True,
                "data": {
                    "has_screening": False,
                    "message": "尚未进行图片筛选",
                    "stats": {
                        "tables_count": 0,
                        "no_tables_count": 0,
                        "uncertain_count": 0,
                        "total": 0
                    }
                }
            })

        # 计算统计信息
        tables_count = len(list(tables_dir.glob("*.png"))) if tables_dir.exists() else 0
        no_tables_count = len(list(no_tables_dir.glob("*.png"))) if no_tables_dir.exists() else 0
        total = tables_count + no_tables_count

        # 如果有历史记录文件，可以读取更多统计信息
        accuracy = None
        false_positives = 0
        false_negatives = 0

        # 检查是否有审计日志
        audit_log = Path("false_negatives.log")
        if audit_log.exists():
            try:
                with open(audit_log, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if pdf_folder in content:
                        # 简单统计漏检数量
                        false_negatives = content.count(pdf_folder)
            except:
                pass

        # 构建响应
        stats = {
            "tables_count": tables_count,
            "no_tables_count": no_tables_count,
            "uncertain_count": 0,  # 如果有不确定分类可以添加
            "total": total,
            "tables_percentage": (tables_count / total * 100) if total > 0 else 0,
            "no_tables_percentage": (no_tables_count / total * 100) if total > 0 else 0,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "estimated_accuracy": accuracy,
            "last_updated": time.strftime('%Y-%m-%d %H:%M:%S')
        }

        return jsonify({
            "success": True,
            "data": stats,
            "directories": {
                "tables_dir": str(tables_dir),
                "no_tables_dir": str(no_tables_dir),
                "output_dir": str(output_dir)
            }
        })

    except Exception as e:
        import traceback
        print(f"💥 获取统计信息失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"获取统计信息失败: {str(e)}"
        }), 500



# ---------------- 25.5. 提供筛选分类图片 API ----------------
@convert_bp.route('/filtered-tables-image/<pdf_folder>/<category>/<filename>')
def api_filtered_tables_image(pdf_folder: str, category: str, filename: str):
    """
    API: 提供筛选分类后的图片
    功能: 返回筛选后的分类图片文件（tables/no_tables）
    """
    try:
        print(f"🔍 请求图片: pdf_folder={pdf_folder}, category={category}, filename={filename}")

        # 验证分类
        if category not in ['tables', 'no_tables', 'uncertain']:
            return jsonify({
                "success": False,
                "error": f"无效的分类: {category}"
            }), 400

        # 构建文件路径
        output_dir = Path(FILTERED_TABLES_DIR) / pdf_folder
        image_path = output_dir / category / filename

        print(f"📤 提供筛选图片路径: {image_path}")
        print(f"📤 路径是否存在: {image_path.exists()}")

        if not image_path.exists():
            # 列出目录内容帮助调试
            if output_dir.exists():
                print(f"📁 目录内容: {list(output_dir.glob('*'))}")
            if (output_dir / category).exists():
                print(f"📁 {category}目录内容: {list((output_dir / category).glob('*'))}")

            return jsonify({
                "success": False,
                "error": f"筛选图片不存在: {filename}, 路径: {image_path}"
            }), 404

        # 返回图片文件
        print(f"✅ 成功找到图片，准备发送: {image_path}")
        return send_file(str(image_path), mimetype='image/png')

    except Exception as e:
        import traceback
        print(f"💥 提供筛选图片失败: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"提供筛选图片失败: {str(e)}"
        }), 500






