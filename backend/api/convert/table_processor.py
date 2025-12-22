"""
表格处理模块 - 业务逻辑层
职责：封装表格处理业务逻辑，不包含API响应
"""
from flask import jsonify
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.utils.constants import DATABASE_PATH, FILTERED_TABLES_DIR
# from backend.models.new_database import NewDatabaseManager
from backend.models.unified_db import NewDatabaseManager
from backend.src.services.table_processor.table_rebuilder import TableReconstructor
from backend.src.services.table_processor.ocr_gateway import TableOCRService
from backend.src.services.table_processor.llm_table_structure_parser import EnhancedFinancialTableAnalyzer


# ========== 1. 导入表格处理管道 ==========
try:
    from backend.src.services.table_processor.end_to_end_pipeline import batch_example
    from backend.utils.config import tableconfig
    PIPELINE_AVAILABLE = True
    print("✅ 表格处理管道导入成功")
except ImportError as e:
    print(f"⚠️ 表格处理管道导入失败: {e}")
    PIPELINE_AVAILABLE = False


class TableProcessingService:
    """表格处理服务类 - 纯业务逻辑"""

    def __init__(self):
        self.output_base_dir = self._get_output_dir()

    def _get_output_dir(self) -> Path:
        """获取输出目录"""
        try:
            output_dir = Path(tableconfig.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir
        except:
            # 回退到默认目录
            default_dir = Path("data/backend/outputs")
            default_dir.mkdir(parents=True, exist_ok=True)
            return default_dir

    def validate_images(self, pdf_folder: str, png_names: list, png_output_dir) -> tuple:
        """
        验证图片是否存在（只检查前几条数据）
        返回: (是否全部存在, 有效图片路径列表, 缺失图片名称列表)
        """
        missing_images = []
        valid_images = []

        # 只检查前5条数据（可以根据需要调整数量）
        check_count = min(5, len(png_names))
        check_names = png_names[:check_count]

        print(f"🔍 验证图片 - 文件夹: {pdf_folder}")
        print(f"📄 总图片数: {len(png_names)}, 只检查前 {check_count} 条")

        # 确保 png_output_dir 是 Path 对象
        if isinstance(png_output_dir, str):
            from pathlib import Path
            png_output_dir = Path(png_output_dir)
            print(f"✅ 路径对象: {png_output_dir}")

        # 检查PDF子目录
        pdf_folder_path = png_output_dir / pdf_folder
        print(f"📁 检查子目录: {pdf_folder_path}")

        if not pdf_folder_path.exists():
            print(f"❌ 子目录不存在")
            # 为了测试，我们假设只有目录不存在这一个问题
            # 实际上可能所有图片都不存在，但这里只检查前几条
            for png_name in check_names:
                missing_images.append(png_name)
            return False, [], check_names  # 只返回检查过的图片

        # 验证前几条图片
        for i, png_name in enumerate(check_names):
            print(f"  检查图片 {i + 1}/{check_count}: {png_name}")

            try:
                # 清理可能的路径前缀
                if '/' in png_name:
                    png_name = png_name.split('/')[-1]
                    print(f"    🔧 清理后: {png_name}")

                # 检查扩展名
                if not png_name.lower().endswith('.png'):
                    if '.' not in png_name:
                        png_name = f"{png_name}.png"
                        print(f"    🔧 添加扩展名: {png_name}")

                # 构建完整路径
                image_path = pdf_folder_path / png_name
                print(f"    📁 完整路径: {image_path}")

                # 检查文件是否存在
                if image_path.exists():
                    valid_images.append(str(image_path))
                    print(f"    ✅ 文件存在")
                else:
                    missing_images.append(png_name)
                    print(f"    ❌ 文件不存在")

                    # 列出目录中的实际文件（前3个）作为参考
                    if i == 0:  # 只在第一个文件缺失时列出参考
                        actual_files = list(pdf_folder_path.glob("*.png"))[:3]
                        if actual_files:
                            print(f"    🔍 目录中实际文件示例: {[f.name for f in actual_files]}")

            except Exception as e:
                print(f"    💥 检查出错: {e}")
                missing_images.append(png_name)

        print(f"📊 验证结果 (前{check_count}条):")
        print(f"  - 有效图片: {len(valid_images)} 张")
        print(f"  - 缺失图片: {len(missing_images)} 张")

        if missing_images:
            print(f"  - 缺失的图片: {missing_images}")

        # 如果前几条都不存在，说明整个列表可能都有问题
        if len(missing_images) == check_count:
            print(f"⚠️  前{check_count}条图片都不存在，可能整个列表都有问题")
            return False, [], png_names  # 返回所有缺失

        # 如果前几条存在，说明格式正确，返回成功（假设其他图片也存在）
        if len(valid_images) == check_count:
            print(f"✅ 前{check_count}条验证通过，格式正确")
            # 这里可以只返回前几条验证过的，或者扩展验证全部
            return True, valid_images, []

        # 部分存在的情况
        print(f"⚠️  部分图片存在，格式可能需要调整")
        return False, valid_images, missing_images


    def process_images(self, pdf_folder: str, valid_images: List[str],
                      bank_name: str = "") -> Dict[str, Any]:
        """
        处理图片表格 - 核心业务逻辑
        返回: 处理结果字典（不包含API响应）
        """
        print(f"📊 开始处理表格 - 文件夹: {pdf_folder}, 图片数: {len(valid_images)}")

        if not PIPELINE_AVAILABLE:
            return {
                "success": False,
                "error": "表格处理管道不可用",
                "total_images": len(valid_images)
            }

        try:
            # 创建输出目录
            output_dir = self.output_base_dir / pdf_folder
            output_dir.mkdir(parents=True, exist_ok=True)

            print(f"📁 输出目录: {output_dir}")

            # 调用批量处理函数
            result = batch_example(
                image_paths=valid_images,
                output_dir=str(output_dir),
                bank_name=bank_name
            )

            # 解析结果
            return self._parse_processing_result(result, valid_images)

        except Exception as e:
            print(f"❌ 表格处理失败: {e}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e),
                "total_images": len(valid_images)
            }

    def _parse_processing_result(self, raw_result: Dict[str, Any],
                               valid_images: List[str]) -> Dict[str, Any]:
        """解析处理结果"""
        if not raw_result.get('success', False):
            return {
                "success": False,
                "error": raw_result.get('error', '未知错误'),
                "total_images": len(valid_images)
            }

        # 提取成功的结果和Excel文件
        results = []
        excel_files = []
        success_count = 0

        for res in raw_result.get('results', []):
            if res.get('success'):
                success_count += 1
                results.append({
                    "image_path": Path(res.get('image_path', '')).name,
                    "success": True,
                    "output_file": res.get('output_file', ''),
                    "processing_time": res.get('processing_time', 0)
                })
                if res.get('output_file'):
                    excel_files.append(res['output_file'])

        # 统计信息
        stats = raw_result.get('stats', {})

        return {
            "success": True,
            "total_images": len(valid_images),
            "success_count": success_count,
            "failed_count": len(valid_images) - success_count,
            "processing_time": stats.get('processing_time', 0),
            "excel_files": excel_files,
            "raw_results": results,
            "raw_stats": stats
        }

    def get_excel_files(self, pdf_folder: str) -> List[Dict[str, Any]]:
        """获取指定文件夹的Excel文件列表"""
        output_dir = self.output_base_dir / pdf_folder
        excel_files = []

        if output_dir.exists():
            for excel_file in output_dir.glob("*.xlsx"):
                excel_files.append({
                    "filename": excel_file.name,
                    "path": str(excel_file),
                    "size": excel_file.stat().st_size,
                    "modified_time": datetime.fromtimestamp(
                        excel_file.stat().st_mtime
                    ).isoformat(),
                    "relative_download_path": f"{pdf_folder}/{excel_file.name}"
                })

        return excel_files

    def get_excel_file_path(self, pdf_folder: str, filename: str) -> Optional[Path]:
        """获取Excel文件路径"""
        file_path = self.output_base_dir / pdf_folder / filename

        # 安全检查
        try:
            file_path_resolved = file_path.resolve()
            base_dir_resolved = self.output_base_dir.resolve()

            # 确保文件在输出目录内（防止路径遍历攻击）
            if str(file_path_resolved).startswith(str(base_dir_resolved)):
                return file_path if file_path.exists() else None
        except:
            pass

        return None


# ========== 2. 异步处理包装器 ==========
def create_table_processing_task(pdf_folder: str, valid_images: List[str],
                               bank_name: str = "") -> Dict[str, Any]:
    """
    创建表格处理任务（供异步调用）
    返回任务信息，不启动线程
    """
    job_id = str(uuid.uuid4())

    return {
        "job_id": job_id,
        "pdf_folder": pdf_folder,
        "valid_images": valid_images,
        "bank_name": bank_name,
        "total_images": len(valid_images),
        "created_at": datetime.now().isoformat()
    }


def execute_table_processing(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行表格处理（供线程调用）
    返回处理结果
    """
    service = TableProcessingService()

    result = service.process_images(
        pdf_folder=task_info["pdf_folder"],
        valid_images=task_info["valid_images"],
        bank_name=task_info.get("bank_name", "")
    )

    # 合并任务信息和处理结果
    final_result = {
        **task_info,
        **result,
        "completed_at": datetime.now().isoformat()
    }

    return final_result


# ========== 3. 创建全局服务实例 ==========
table_processing_service = TableProcessingService()


# ========== 4. API 接口函数 ==========
def submit_table_processing_task(pdf_folder, png_output_dir, request, progress_tracker):
    """API: 提交表格处理任务"""

    try:
        # 1. 解析请求
        if request.method == 'OPTIONS':
            return jsonify({"status": "ok"}), 200

        data = request.get_json()
        png_names = data.get('png_names', [])
        bank_name = data.get('bank_name', '')
        table_type = data.get('table_type', 'financial')  # 添加表格类型参数

        # 2. 参数校验
        if not pdf_folder or not png_names:
            return jsonify({
                "success": False,
                "error": "参数错误：需提供pdf_folder和png_names"
            }), 400

        print(f"📥 接收表格处理请求:")
        print(f"  - PDF文件夹: {pdf_folder}")
        print(f"  - 图片数量: {len(png_names)}")
        print(f"  - 银行名称: {bank_name}")
        print(f"  - 表格类型: {table_type}")

        # 3. 验证图片存在
        service = TableProcessingService()

        # 🔧 关键修复：确保 png_output_dir 是 Path 对象
        from pathlib import Path
        if isinstance(png_output_dir, str):
            png_output_dir = Path(png_output_dir)
            print(f"  ✅ 已将字符串转换为Path对象: {png_output_dir}")

        print(f"  - PNG输出目录: {png_output_dir}")
        print(f"  - 目录是否存在: {png_output_dir.exists()}")

        # 检查子目录是否存在
        pdf_folder_path = png_output_dir / pdf_folder / "tables"
        print(f"  - PDF子目录: {pdf_folder_path}")
        print(f"  - 子目录是否存在: {pdf_folder_path.exists()}")

        if pdf_folder_path.exists():
            print(f"  - 子目录中的文件: {list(pdf_folder_path.glob('*.png'))[:5]}...")

        all_valid, valid_images, missing_images = service.validate_images(
            pdf_folder, png_names, png_output_dir
        )

        if not all_valid:
            missing_count = len(missing_images)
            error_msg = f"发现 {missing_count} 张图片不存在"
            if missing_count <= 5:
                error_msg += f": {missing_images}"
            else:
                error_msg += f"，前5张: {missing_images[:5]}..."

            print(f"❌ 图片验证失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg,
                "missing": missing_images,
                "missing_count": missing_count
            }), 404

        print(f"✅ 图片验证通过: 找到 {len(valid_images)} 张有效图片")

        # 4. 创建任务
        job_id = str(uuid.uuid4())
        task_info = {
            "job_id": job_id,
            "pdf_folder": pdf_folder,
            "valid_images": valid_images,
            "bank_name": bank_name,
            "table_type": table_type,  # 添加表格类型
            "total_images": len(valid_images),
            "created_at": datetime.now().isoformat(),
            "status": "submitted"
        }

        print(f"🎯 创建任务: {job_id}")

        # 5. 初始化进度
        progress_tracker.init_table_job(job_id, task_info)

        # 6. 异步处理
        def async_process():
            try:
                print(f"🔄 开始异步处理任务: {job_id}")

                # 更新状态
                progress_tracker.update_table_job(job_id, {
                    "status": "processing",
                    "stage": "starting",
                    "progress": 10,
                    "message": "开始处理图片..."
                })

                # 🔧 根据表格类型选择处理方法
                print(f"📊 表格类型: {table_type}")

                result = service.process_images(pdf_folder, valid_images, bank_name)

                print(f"✅ 任务处理完成: {job_id}, 结果: {result.get('success', False)}")

                # 更新完成状态
                final_status = {
                    "status": "completed" if result.get("success") else "failed",
                    "stage": "completed",
                    "progress": 100,
                    "end_time": datetime.now().isoformat(),
                    "message": "处理完成" if result.get("success") else "处理失败"
                }

                # 如果有额外结果，添加到状态中
                if result:
                    final_status.update(result)

                progress_tracker.update_table_job(job_id, final_status)

                print(f"📁 任务状态已更新: {job_id}")

            except Exception as e:
                import traceback
                print(f"💥 异步处理异常: {e}")
                traceback.print_exc()

                progress_tracker.update_table_job(job_id, {
                    "status": "failed",
                    "stage": "failed",
                    "error": str(e),
                    "end_time": datetime.now().isoformat(),
                    "message": f"处理失败: {str(e)}"
                })

        thread = threading.Thread(target=async_process, daemon=True)
        thread.start()

        print(f"🚀 异步线程已启动: {job_id}")

        # 7. 返回响应
        response_data = {
            "success": True,
            "job_id": job_id,
            "task_id": job_id,  # 为了兼容性，也返回task_id
            "message": "表格处理任务已提交",
            "data": {
                "total_images": len(valid_images),
                "pdf_folder": pdf_folder,
                "table_type": table_type,
                "bank_name": bank_name
            }
        }

        print(f"📤 返回响应: {response_data}")

        return jsonify(response_data)

    except Exception as e:
        import traceback
        print(f"💥 提交任务异常: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"请求处理失败: {str(e)}"
        }), 500


def get_table_results(pdf_folder, progress_tracker):
    """API: 查询表格处理结果"""
    from flask import jsonify

    try:
        # 1. 获取内存中的任务
        folder_tasks = progress_tracker.get_folder_tasks(pdf_folder)

        # 2. 获取Excel文件
        service = TableProcessingService()
        excel_files = service.get_excel_files(pdf_folder)

        # 3. 返回结果
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
    """API: 下载Excel文件"""
    from flask import send_from_directory, jsonify

    try:
        service = TableProcessingService()
        file_path = service.get_excel_file_path(pdf_folder, filename)

        if not file_path or not file_path.exists():
            return jsonify({
                "success": False,
                "error": "文件不存在"
            }), 404

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




def get_available_steps():
    """API: 获取可用步骤"""
    from flask import jsonify
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


import concurrent.futures
from threading import Semaphore
from typing import List, Dict, Any


class HighVolumeTableProcessor:
    """高容量表格处理器 - 处理上百张图片"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            'max_ocr_workers': 4,  # OCR线程数（I/O密集型）
            'max_llm_workers': 2,  # LLM线程数（GPU限制）
            'max_reconstruct_workers': 3,  # 重构线程数
            'batch_size': 10,  # 批次大小，控制内存
            'queue_size': 50  # 队列缓冲
        }

        # 资源限制信号量
        self.gpu_semaphore = Semaphore(self.config['max_llm_workers'])

    def process_hundred_images(self, image_paths: List[str], bank_name: str = "") -> Dict[str, Any]:
        """
        处理上百张图片的优化方案
        """
        total_images = len(image_paths)
        print(f"🚀 开始处理 {total_images} 张图片")

        # 1. 分批处理，避免内存爆炸
        batches = self._create_batches(image_paths, self.config['batch_size'])

        all_results = []

        with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.config['max_ocr_workers'] +
                            self.config['max_llm_workers'] +
                            self.config['max_reconstruct_workers']
        ) as executor:

            # 提交批次任务
            future_to_batch = {}
            for batch_idx, batch_images in enumerate(batches):
                future = executor.submit(
                    self._process_batch_pipeline,
                    batch_images, batch_idx, bank_name
                )
                future_to_batch[future] = batch_idx

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                    print(f"✅ 批次 {batch_idx + 1}/{len(batches)} 处理完成")
                except Exception as e:
                    print(f"❌ 批次 {batch_idx} 处理失败: {e}")

        # 汇总统计
        return self._aggregate_results(all_results, total_images)

    def _create_batches(self, image_paths: List[str], batch_size: int) -> List[List[str]]:
        """创建批次"""
        return [image_paths[i:i + batch_size]
                for i in range(0, len(image_paths), batch_size)]

    def _process_batch_pipeline(self, batch_images: List[str],
                                batch_idx: int, bank_name: str) -> List[Dict[str, Any]]:
        """
        批次内的流水线处理
        """
        batch_results = []

        # 阶段1: OCR识别（并行）
        ocr_results = []
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(self.config['max_ocr_workers'], len(batch_images))
        ) as ocr_executor:
            ocr_futures = {
                ocr_executor.submit(self._ocr_recognize, img_path): img_path
                for img_path in batch_images
            }

            for future in concurrent.futures.as_completed(ocr_futures):
                img_path = ocr_futures[future]
                try:
                    ocr_result = future.result()
                    ocr_results.append((img_path, ocr_result))
                except Exception as e:
                    print(f"❌ OCR失败 {img_path}: {e}")
                    ocr_results.append((img_path, {'success': False, 'error': str(e)}))

        # 阶段2: LLM分析（受GPU限制）
        llm_results = []
        for img_path, ocr_result in ocr_results:
            if ocr_result.get('success'):
                # 使用信号量限制并发
                with self.gpu_semaphore:
                    llm_result = self._llm_analyze(img_path, ocr_result)
                    llm_results.append((img_path, ocr_result, llm_result))
            else:
                llm_results.append((img_path, ocr_result, {'success': False, 'error': 'OCR失败'}))

        # 阶段3: 表格重构（并行）
        for img_path, ocr_result, llm_result in llm_results:
            if llm_result.get('success'):
                try:
                    reconstruct_result = self._table_reconstruct(
                        ocr_result, llm_result, img_path, bank_name
                    )
                    batch_results.append({
                        'image_path': img_path,
                        'success': reconstruct_result.get('success', False),
                        'output_file': reconstruct_result.get('output_file'),
                        'processing_time': reconstruct_result.get('processing_time', 0)
                    })
                except Exception as e:
                    batch_results.append({
                        'image_path': img_path,
                        'success': False,
                        'error': str(e)
                    })
            else:
                batch_results.append({
                    'image_path': img_path,
                    'success': False,
                    'error': llm_result.get('error', 'LLM分析失败')
                })

        return batch_results

    def _ocr_recognize(self, image_path: str) -> Dict[str, Any]:
        """OCR识别"""
        ocr_service = TableOCRService()
        return ocr_service.recognize_table(image_path)

    def _llm_analyze(self, image_path: str, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """LLM分析（GPU密集型）"""
        analyzer = EnhancedFinancialTableAnalyzer()
        return analyzer.analyze_image(image_path, ocr_result)

    def _table_reconstruct(self, ocr_result: Dict[str, Any],
                           llm_result: Dict[str, Any],
                           image_path: str, bank_name: str) -> Dict[str, Any]:
        """表格重构"""
        reconstructor = TableReconstructor()

        # 生成输出文件路径
        from pathlib import Path
        image_name = Path(image_path).stem
        output_dir = Path("data/backend/outputs/large_batch")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = str(output_dir / f"{image_name}_reconstructed.xlsx")

        success = reconstructor.process_all_tables(
            ocr_result=ocr_result,
            llm_result=llm_result,
            output_file=output_file,
            image_path=image_path,
            bank_name=bank_name
        )

        return {
            'success': success,
            'output_file': output_file if success else None
        }

    def _aggregate_results(self, all_results: List[Dict], total_images: int) -> Dict[str, Any]:
        """汇总结果"""
        successful = sum(1 for r in all_results if r.get('success'))
        failed = total_images - successful

        return {
            'success': failed == 0,
            'total_images': total_images,
            'successful': successful,
            'failed': failed,
            'results': all_results,
            'summary': {
                'success_rate': f"{(successful / total_images * 100):.1f}%",
                'failed_images': [
                    r['image_path'] for r in all_results
                    if not r.get('success')
                ]
            }
        }


def process_large_batch(pdf_folder: str, image_paths: List[str],
                        bank_name: str = "") -> Dict[str, Any]:
    """
    处理大批量图片的接口
    """
    processor = HighVolumeTableProcessor({
        'max_ocr_workers': 6,
        'max_llm_workers': 2,  # 根据GPU显存调整
        'max_reconstruct_workers': 4,
        'batch_size': 15,
        'queue_size': 30
    })

    return processor.process_hundred_images(image_paths, bank_name)

def _ensure_table_processing_db():
    """确保表格处理数据库表存在"""
    global _table_processing_db_initialized

    if _table_processing_db_initialized:
        return True

    try:

        db_handler = NewDatabaseManager(DATABASE_PATH)
        db_handler.init_table_processing_db()
        _table_processing_db_initialized = True
        return True
    except Exception as e:
        print(f"⚠️ 数据库表初始化失败，但继续处理: {e}")
        return False


# def update_job_progress(job_id, updates):
def update_job_progress(job_id, updates, progress_tracker):
    """更新任务进度"""
    if job_id in progress_tracker.TABLE_PROCESSING_JOBS:
        progress_tracker.TABLE_PROCESSING_JOBS[job_id].update(updates)

        # 保存到数据库
        try:
            from backend.utils.constants import DATABASE_PATH
            db_handler = NewDatabaseManager(DATABASE_PATH)
            job_info = progress_tracker.TABLE_PROCESSING_JOBS[job_id].copy()
            job_info['job_id'] = job_id
            db_handler.save_table_processing_record(job_info)
        except Exception as e:
            print(f"⚠️ 保存进度到数据库失败: {e}")

_table_processing_db_initialized = False

def process_tables_async(job_id, pdf_folder, valid_images, bank_name):
    """
    异步处理表格的完整实现
    """
    print(f"🚀 开始异步处理表格 - Job ID: {job_id}")
    print(f"📊 图片数量: {len(valid_images)} 张")

    try:
        # 确保数据库表存在
        _ensure_table_processing_db()

        # 更新进度为开始
        update_job_progress(job_id, {
            "status": "processing",
            "stage": "starting",
            "progress": 5,
            "total_images": len(valid_images)
        })

        # ========== 智能选择处理器 ==========
        results = []
        excel_files = []

        if len(valid_images) > 20:
            print("🔧 使用高容量处理器（批量>20）")

            # 创建高容量处理器
            processor = HighVolumeTableProcessor({
                'max_ocr_workers': min(8, len(valid_images) // 3),
                'max_llm_workers': 2,
                'max_reconstruct_workers': 4,
                'batch_size': 15
            })

            # 定义进度回调
            def progress_callback(processed, total, stage):
                progress = 10 + (processed / total * 80)  # 10%-90%
                update_job_progress(job_id, {
                    "stage": stage,
                    "progress": int(progress),
                    "processed_images": processed,
                    "current_stage": stage,
                    "current_image": f"批次处理中 ({processed}/{total})"
                })
                print(f"📊 处理进度: {stage} - {processed}/{total} ({int(progress)}%)")

            # 执行处理
            batch_result = processor.process_hundred_images(
                valid_images, bank_name, progress_callback
            )

            # 解析结果
            if batch_result.get('success'):
                for res in batch_result.get('results', []):
                    if res.get('success'):
                        results.append({
                            "image_path": Path(res.get('image_path', '')).name,
                            "success": True,
                            "output_file": res.get('output_file', ''),
                            "processing_time": res.get('processing_time', 0)
                        })
                        if res.get('output_file'):
                            excel_files.append(res['output_file'])
                    else:
                        results.append({
                            "image_path": Path(res.get('image_path', '')).name,
                            "success": False,
                            "error": res.get('error', '处理失败')
                        })

        else:
            print("🔧 使用标准处理器（批量≤20）")

            # 创建标准处理器
            service = TableProcessingService()

            # 逐张处理（可改为小批量并行）
            for i, image_path in enumerate(valid_images):
                image_name = Path(image_path).name

                # 更新进度
                progress = 10 + (i / len(valid_images) * 80)
                update_job_progress(job_id, {
                    "stage": "processing",
                    "progress": int(progress),
                    "processed_images": i,
                    "current_image": image_name,
                    "current_stage": "processing"
                })

                try:
                    # 处理单张图片
                    print(f"🖼️ 处理图片 {i + 1}/{len(valid_images)}: {image_name}")

                    # 这里应该是处理单张的逻辑
                    # 暂时调用批量处理，传入单张图片
                    result = service.process_images(
                        pdf_folder, [image_path], bank_name
                    )

                    if result.get('success'):
                        # 解析单张结果
                        for res in result.get('raw_results', []):
                            if res.get('success'):
                                results.append({
                                    "image_path": image_name,
                                    "success": True,
                                    "output_file": res.get('output_file', ''),
                                    "processing_time": res.get('processing_time', 0)
                                })
                                if res.get('output_file'):
                                    excel_files.append(res['output_file'])
                    else:
                        results.append({
                            "image_path": image_name,
                            "success": False,
                            "error": result.get('error', '处理失败')
                        })

                except Exception as img_error:
                    print(f"❌ 图片处理失败 {image_name}: {img_error}")
                    results.append({
                        "image_path": image_name,
                        "success": False,
                        "error": str(img_error)
                    })

        # ========== 处理完成 ==========
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
        print(f"📊 成功: {success_count}, 失败: {len(valid_images) - success_count}")

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



def execute_single_step_handler(step_name, output_dir, request):
    """分步执行表格处理 - 真正的分步实现"""

    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        pdf_folder = data.get('pdf_folder')
        png_names = data.get('png_names', [])
        previous_context = data.get('previous_context', {})

        if not pdf_folder or not png_names:
            return jsonify({
                "success": False,
                "error": "参数错误：需提供pdf_folder和png_names"
            }), 400

        # 根据步骤名称执行不同的逻辑
        if step_name == "ocr":
            result = execute_ocr_step(pdf_folder, png_names, output_dir)
        elif step_name == "llm":
            result = execute_llm_step(pdf_folder, png_names, previous_context, output_dir)
        elif step_name == "reconstruct":
            result = execute_reconstruct_step(pdf_folder, png_names, previous_context, output_dir)
        elif step_name == "export":
            result = execute_export_step(pdf_folder, png_names, previous_context, output_dir)
        else:
            return jsonify({
                "success": False,
                "error": f"不支持的步骤: {step_name}"
            }), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"分步执行失败: {str(e)}"
        }), 500


def execute_ocr_step(pdf_folder, png_names, output_dir):
    """执行OCR步骤"""
    try:
        results = {}
        ocr_service = TableOCRService()

        for png_name in png_names:
            # 构建图片路径
            from backend.utils.constants import JOINED_TABLES_DIR
            image_path = JOINED_TABLES_DIR / pdf_folder / png_name

            if not image_path.exists():
                results[png_name] = {"success": False, "error": "图片不存在"}
                continue

            # 执行OCR
            ocr_result = ocr_service.recognize_table(str(image_path))
            results[png_name] = {
                "success": True,
                "result": ocr_result,
                "tables_count": len(ocr_result.get('tables_result', []))
            }

        return {
            "success": True,
            "step": "ocr",
            "results": results,
            "message": f"OCR识别完成，处理{len(png_names)}张图片"
        }

    except Exception as e:
        return {
            "success": False,
            "step": "ocr",
            "error": str(e)
        }


def execute_llm_step(pdf_folder, png_names, previous_context, output_dir):
    """执行LLM分析步骤"""
    try:

        # 检查是否有OCR结果
        ocr_results = previous_context.get('ocr_results', {})
        if not ocr_results:
            return {
                "success": False,
                "step": "llm",
                "error": "需要先执行OCR步骤"
            }

        results = {}
        analyzer = EnhancedFinancialTableAnalyzer()

        for png_name in png_names:
            # 获取OCR结果
            ocr_result = ocr_results.get(png_name, {}).get('result')
            if not ocr_result:
                results[png_name] = {"success": False, "error": "没有OCR结果"}
                continue

            # 构建图片路径
            from backend.utils.constants import JOINED_TABLES_DIR
            image_path = JOINED_TABLES_DIR / pdf_folder / png_name

            # 执行LLM分析
            llm_result = analyzer.analyze_image(str(image_path), ocr_result)

            if llm_result.get('success'):
                results[png_name] = {
                    "success": True,
                    "result": llm_result,
                    "tables_count": llm_result['processing_stats']['visual_tables_count']
                }
            else:
                results[png_name] = {
                    "success": False,
                    "error": llm_result.get('error', 'LLM分析失败')
                }

        return {
            "success": True,
            "step": "llm",
            "results": results,
            "message": f"LLM分析完成，处理{len(png_names)}张图片"
        }

    except Exception as e:
        return {
            "success": False,
            "step": "llm",
            "error": str(e)
        }


def execute_reconstruct_step(pdf_folder, png_names, previous_context, output_dir):
    """执行表格重构步骤"""
    try:

        # 检查前置结果
        ocr_results = previous_context.get('ocr_results', {})
        llm_results = previous_context.get('llm_results', {})

        if not ocr_results or not llm_results:
            return {
                "success": False,
                "step": "reconstruct",
                "error": "需要先执行OCR和LLM步骤"
            }

        results = {}
        reconstructor = TableReconstructor()

        for png_name in png_names:
            # 获取前置结果
            ocr_result = ocr_results.get(png_name, {}).get('result')
            llm_result = llm_results.get(png_name, {}).get('result')

            if not ocr_result or not llm_result:
                results[png_name] = {"success": False, "error": "缺少前置结果"}
                continue

            # 生成输出文件路径
            from pathlib import Path
            output_path = Path(output_dir) / pdf_folder
            output_path.mkdir(parents=True, exist_ok=True)
            excel_file = str(output_path / f"{Path(png_name).stem}_reconstructed.xlsx")

            effect_png_dir = FILTERED_TABLES_DIR / pdf_folder / png_name
            print("effect_png_dir::::", effect_png_dir)
            # 执行表格重构
            success = reconstructor.process_all_tables(
                ocr_result=ocr_result,
                llm_result=llm_result,
                output_file=excel_file,
                final_output_file=excel_file,
                image_path=str(effect_png_dir),
                bank_name=""
            )

            if success:
                results[png_name] = {
                    "success": True,
                    "output_file": excel_file,
                    "message": "表格重构成功"
                }
            else:
                results[png_name] = {
                    "success": False,
                    "error": "表格重构失败"
                }

        return {
            "success": True,
            "step": "reconstruct",
            "results": results,
            "message": f"表格重构完成"
        }

    except Exception as e:
        return {
            "success": False,
            "step": "reconstruct",
            "error": str(e)
        }


def execute_export_step(pdf_folder, png_names, previous_context, output_dir):
    """执行数据导出步骤"""
    # 在实际中，重构步骤通常已经生成Excel文件
    # 所以导出步骤可能只是文件整理或格式转换
    reconstruct_results = previous_context.get('reconstruct_results', {})

    excel_files = []
    for png_name in png_names:
        result = reconstruct_results.get(png_name, {})
        if result.get('success') and result.get('output_file'):
            excel_files.append(result['output_file'])

    return {
        "success": True,
        "step": "export",
        "excel_files": excel_files,
        "message": f"导出完成，生成{len(excel_files)}个Excel文件"
    }

