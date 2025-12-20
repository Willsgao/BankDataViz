"""
表格处理模块
"""
import uuid
import threading
from pathlib import Path
from datetime import datetime
from flask import jsonify, send_from_directory


def execute_single_step_handler(step_name, output_dir, request):
    """分步执行表格处理"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        pdf_folder = data.get('pdf_folder')
        png_names = data.get('png_names', [])
        previous_context = data.get('previous_context', {})

        if not pdf_folder or not isinstance(png_names, list):
            return jsonify({
                "success": False,
                "error": "参数错误：需提供pdf_folder和png_names"
            }), 400

        from backend.service.layout_service import execute_single_step
        result_context = execute_single_step(
            step_name=step_name,
            pdf_folder=pdf_folder,
            png_names=png_names,
            output_root=output_dir,
            previous_context=previous_context
        )

        return jsonify({
            "success": True,
            "step": step_name,
            "context": result_context,
            "message": f"步骤 {step_name} 执行完成"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"分步执行失败: {str(e)}"
        }), 500


def get_available_steps():
    """获取可用的处理步骤列表"""
    try:
        from backend.service.layout_service import processing_pipeline
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


def submit_table_processing_task(pdf_folder, joined_tables_dir, request, progress_tracker):
    """提交表格处理任务"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        png_names = data.get('png_names', [])
        bank_name = data.get('bank_name', '')

        if not pdf_folder or not isinstance(png_names, list) or len(png_names) == 0:
            return jsonify({
                "success": False,
                "error": "参数错误：需提供非空的pdf_folder和png_names列表"
            }), 400

        missing_images = []
        valid_images = []
        for png_name in png_names:
            image_path = Path(joined_tables_dir) / pdf_folder / png_name
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

        job_id = uuid.uuid4().hex
        progress_tracker.init_table_job(job_id, {
            "pdf_folder": pdf_folder,
            "png_names": png_names,
            "bank_name": bank_name,
            "status": "pending",
            "total_images": len(valid_images)
        })

        thread = threading.Thread(
            target=_process_tables_async,
            args=(job_id, pdf_folder, valid_images, bank_name, progress_tracker),
            daemon=True
        )
        thread.start()

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
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"接口处理失败: {str(e)}"
        }), 500


def get_table_results(pdf_folder, progress_tracker):
    """查询表格处理结果列表"""
    try:
        folder_tasks = progress_tracker.get_folder_tasks(pdf_folder)

        from backend.utils.config import tableconfig
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

        return jsonify({
            "success": True,
            "pdf_folder": pdf_folder,
            "data": {
                "tasks": folder_tasks,
                "excel_files": excel_files,
                "task_count": len(folder_tasks),
                "excel_count": len(excel_files)
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"查询失败: {str(e)}"
        }), 500


def download_excel_file(pdf_folder, filename):
    """下载表格处理结果Excel文件"""
    try:
        from backend.utils.config import tableconfig
        file_path = Path(tableconfig.output_dir) / pdf_folder / filename

        if not file_path.exists():
            return jsonify({"success": False, "error": "文件不存在"}), 404

        if not filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                "success": False,
                "error": "仅支持Excel文件下载"
            }), 400

        return send_from_directory(
            directory=str(file_path.parent),
            path=filename,
            as_attachment=True,
            download_name=f"表格处理结果_{pdf_folder}_{filename}"
        )
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"下载失败: {str(e)}"
        }), 500


def _process_tables_async(job_id, pdf_folder, valid_images, bank_name, progress_tracker):
    """内部异步处理函数"""
    try:
        progress_tracker.update_table_job(job_id, {
            "status": "processing",
            "stage": "starting",
            "progress": 5
        })

        from backend.utils.config import tableconfig
        output_dir = Path(tableconfig.output_dir) / pdf_folder
        output_dir.mkdir(parents=True, exist_ok=True)

        from backend.src.services.table_processor.end_to_end_pipeline import batch_example
        result = batch_example(
            image_paths=valid_images,
            output_dir=str(output_dir),
            bank_name=bank_name
        )

        if result.get('success') and 'results' in result:
            results = []
            excel_files = []
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

            success_count = sum(1 for r in results if r.get('success'))
            progress_tracker.update_table_job(job_id, {
                "stage": "completed",
                "status": "completed",
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
                    "total_time": result.get('stats', {}).get('processing_time', 0)
                }
            })
        else:
            progress_tracker.update_table_job(job_id, {
                "status": "failed",
                "stage": "failed",
                "error": "处理失败，未返回有效结果",
                "end_time": datetime.now().isoformat()
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        progress_tracker.update_table_job(job_id, {
            "status": "failed",
            "stage": "failed",
            "error": str(e),
            "end_time": datetime.now().isoformat()
        })