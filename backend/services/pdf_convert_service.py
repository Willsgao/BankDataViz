#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
PDF → PNG 转换服务（流式 + 表格页高 DPI）
author : you
date   : 2025-10-17  最新融合版
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from pdf2image import convert_from_path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from PIL import Image, ImageEnhance

# ------------ 精准 + 高效 ------------
import fitz, os, logging
from backend.services.table_page_detector import detect_table_page
from concurrent.futures import ProcessPoolExecutor

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# ② 后台任务：仅转表格页，300 DPI，PyMuPDF 截图式流式
# ------------------------------------------------------------------
def background_convert(
        pdf_path: Path,
        out_dir: Path,
        job_id: str,
        progress_dict: dict,
        *,
        preview_dpi: int = 72,
        table_dpi: int = 300,
        normal_dpi: int = 200,  # 提高普通页DPI
) -> None:
    """分级 DPI + 优化的渲染，确保清晰不变黑"""
    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        # 1. 单进程快速判表（72 dpi 足够）
        doc = fitz.open(pdf_path)
        total = doc.page_count
        progress_dict[job_id]["total"] = total
        table_pages = {p for p in range(total)
                       if detect_table_page(pdf_path, p, preview_dpi)}
        doc.close()
        logger.info(f"[{job_id}] 表格页：{sorted(table_pages)}")

        # 2. 多进程渲染（优化渲染参数）
        def render_one(p: int) -> None:
            dpi = table_dpi if p in table_pages else normal_dpi
            doc = fitz.open(pdf_path)  # 独立句柄
            page = doc.load_page(p)
            mat = fitz.Matrix(dpi / 72, dpi / 72)

            # 关键优化：使用正确的渲染参数避免黑色
            pix = page.get_pixmap(
                matrix=mat,
                colorspace="rgb",  # 使用字符串而非fitz.csRGB
                alpha=False  # 禁用alpha通道
            )

            out_path = out_dir / f"{pdf_path.stem}_{p + 1:03d}.png"
            pix.save(str(out_path))
            doc.close()
            return p

        with ProcessPoolExecutor(max_workers=min(os.cpu_count(), 4)) as exe:
            for p in exe.map(render_one, range(total)):
                progress_dict[job_id]["finished"] = p + 1
                progress_dict[job_id]["percent"] = round((p + 1) / total * 100)

        logger.info(f"[{job_id}] 全部完成，共 {total} 页")
    except Exception as e:
        logger.exception(f"[{job_id}] 转换失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1



def background_convert_all_pages(
        pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict,
        dpi: int = 200  # 统一DPI
) -> None:
    """
    将PDF所有页面转换为PNG（不区分表格页）
    专为pdf_converter.py的convert_pdf_async函数设计
    """

    logger = logging.getLogger(__name__)

    # 1. 初始化进度
    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0, "status": "processing"}

    try:
        start_time = time.time()

        # 2. 获取PDF总页数（使用PyMuPDF，避免Poppler路径问题）
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()

        progress_dict[job_id]["total"] = total_pages
        logger.info(f"[{job_id}] 开始转换: {pdf_path.name}, 总页数: {total_pages}")

        # 3. 确保输出目录存在
        out_dir.mkdir(parents=True, exist_ok=True)

        # 4. 多线程并发转换所有页面
        def convert_page(page_0b: int) -> bool:
            """转换单个页面"""
            idx = page_0b + 1  # 转换为1-based页码

            try:
                # 每个线程独立打开文档（线程安全）
                doc = fitz.open(pdf_path)
                page = doc.load_page(page_0b)

                # 计算缩放矩阵
                zoom = dpi / 72
                matrix = fitz.Matrix(zoom, zoom)

                # 渲染页面为图片
                pix = page.get_pixmap(
                    matrix=matrix,
                    colorspace="rgb",
                    alpha=False
                )

                # 保存为PNG
                out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.png"
                pix.save(str(out_path))

                # 清理资源
                del pix, page
                doc.close()

                return True

            except Exception as e:
                logger.error(f"[{job_id}] 页面{idx}转换失败: {e}")
                return False

        # 5. 并发处理（控制并发数，避免资源耗尽）
        max_workers = min(os.cpu_count() or 4, 6)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有页面的转换任务
            future_to_page = {
                executor.submit(convert_page, page_num): page_num
                for page_num in range(total_pages)
            }

            # 处理结果
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]

                try:
                    success = future.result(timeout=60)  # 每页最多60秒

                    if success:
                        completed += 1
                        progress_dict[job_id]["finished"] = completed
                        progress_dict[job_id]["percent"] = round(completed / total_pages * 100)

                        # 每10页或最后1页打印进度
                        if completed % 10 == 0 or completed == total_pages:
                            logger.info(
                                f"[{job_id}] 进度: {completed}/{total_pages} ({progress_dict[job_id]['percent']}%)")
                    else:
                        logger.warning(f"[{job_id}] 页面{page_num + 1}转换失败，但继续处理其他页面")

                except Exception as e:
                    logger.error(f"[{job_id}] 页面{page_num + 1}处理异常: {e}")
                    # 继续处理其他页面

        # 6. 完成处理
        elapsed_time = time.time() - start_time
        logger.info(f"[{job_id}] 转换完成! 总页数: {total_pages}, 耗时: {elapsed_time:.1f}秒")

        progress_dict[job_id].update({
            "status": "completed",
            "elapsed_time": elapsed_time,
            "avg_time_per_page": elapsed_time / total_pages if total_pages > 0 else 0
        })

    except Exception as e:
        logger.exception(f"[{job_id}] PDF转换失败")
        progress_dict[job_id].update({
            "status": "error",
            "error": str(e),
            "percent": -1
        })


def background_convert_table_only(
        pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
) -> None:
    """
    兼容性包装器：调用新的全页面转换函数
    保持原有函数签名，但实际转换为所有页面
    """
    # 直接调用全页面转换函数
    background_convert_all_pages(pdf_path, out_dir, job_id, progress_dict, dpi=200)


def _process_missing_pages_only(
        pdf_path: Path,
        out_dir: Path,
        pages_to_process: list,
        job_id: str,
        progress_dict: dict
) -> None:
    """只处理缺失的页面"""
    logger.info(f"[{job_id}] 🚀 开始处理缺失的 {len(pages_to_process)} 页")

    try:
        total = progress_dict[job_id]["total"]
        base_finished = progress_dict[job_id]["finished"]  # 已缓存的数量

        # 确保输出目录存在
        out_dir.mkdir(parents=True, exist_ok=True)

        # 只检测需要处理的页面中的表格页
        doc = fitz.open(pdf_path)
        table_pages = set()

        logger.info(f"[{job_id}] 🔍 检测缺失页面中的表格...")

        for page_0b in pages_to_process:
            try:
                page = doc.load_page(page_0b)
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(72 / 72, 72 / 72),
                    colorspace="rgb",
                    alpha=False
                )
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                if detect_table_page(pdf_path, page_0b, dpi=72) is not None:
                    table_pages.add(page_0b)

                del img, pix, page

            except Exception as e:
                logger.warning(f"[{job_id}] 页面{page_0b}检测失败: {e}")
                continue

        doc.close()

        # 只转换表格页
        pages_to_convert = [p for p in pages_to_process if p in table_pages]

        if not pages_to_convert:
            logger.info(f"[{job_id}] ℹ️ 缺失页面中没有表格页，无需转换")
            progress_dict[job_id]["status"] = "completed"
            progress_dict[job_id]["finished"] = total
            progress_dict[job_id]["percent"] = 100
            return

        logger.info(f"[{job_id}] ✅ 缺失页面中有 {len(pages_to_convert)} 个表格页需要转换")

        # 分批处理这些页面
        batch_size = 50
        batches = [pages_to_convert[i:i + batch_size] for i in range(0, len(pages_to_convert), batch_size)]

        completed = base_finished

        for batch_idx, batch in enumerate(batches):
            logger.info(f"[{job_id}] 🔄 处理批次 {batch_idx + 1}/{len(batches)} ({len(batch)}页)")

            batch_doc = fitz.open(pdf_path)
            for page_0b in batch:
                idx = page_0b + 1
                try:
                    page = batch_doc.load_page(page_0b)
                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(300 / 72, 300 / 72),
                        colorspace="rgb",
                        alpha=False
                    )
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                    # 图像增强
                    try:
                        brightness = ImageEnhance.Brightness(img).enhance(1.05)
                        enhanced_img = ImageEnhance.Contrast(brightness).enhance(1.15)
                        img = enhanced_img
                    except Exception:
                        pass

                    out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.png"
                    img.save(out_path, "PNG", compress_level=3)

                    del img, pix, page

                    # 更新进度
                    completed += 1
                    progress_dict[job_id]["finished"] = completed
                    progress_dict[job_id]["percent"] = round(completed / total * 100)

                except Exception as e:
                    logger.error(f"[{job_id}] ❌ 页面{idx}转换失败: {e}")
                    # 跳过失败的页面，继续处理

            batch_doc.close()

            # 每批完成后强制GC
            import gc
            gc.collect()

            # 每批处理完记录日志
            logger.info(f"[{job_id}] 📊 进度: {completed}/{total} ({progress_dict[job_id]['percent']}%)")

        logger.info(f"[{job_id}] 🎉 缺失页面处理完成")
        progress_dict[job_id]["status"] = "completed"

    except Exception as e:
        logger.exception(f"[{job_id}] 处理缺失页面失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1
        progress_dict[job_id]["status"] = "error"


# ------------------------------------------------------------------
# ③ PdfConvertService 工具类保持原样
# ------------------------------------------------------------------
class PdfConvertService:
    DEFAULT_DPI: int = 300
    DEFAULT_FMT: str = "png"

    @staticmethod
    def _get_page_count(pdf_path: Path) -> int:
        import subprocess

        out = subprocess.check_output(["pdfinfo", str(pdf_path)], text=True, encoding="gbk")
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return int(line.split()[-1])
        raise RuntimeError("pdfinfo 未返回 Pages 字段")

    @staticmethod
    def convert(
            pdf_path: str | Path,
            output_dir: str | Path,
            *,
            dpi: int = 150,
            prefix: str | None = None,
    ) -> List[Path]:

        pdf_path, output_dir = Path(pdf_path), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        prefix = prefix or pdf_path.stem
        total = PdfConvertService._get_page_count(pdf_path)

        def render_page(page: int) -> Path:
            img = convert_from_path(pdf_path, dpi=dpi, first_page=page, last_page=page)[0]
            png_path = output_dir / f"{prefix}_{page:03d}.png"
            img.save(png_path, "PNG")
            return png_path

        png_paths = [None] * total
        with ThreadPoolExecutor(max_workers=4) as exe:
            futures = {exe.submit(render_page, p): p - 1 for p in range(1, total + 1)}
            for f in as_completed(futures):
                png_paths[futures[f]] = f.result()

        logger.info("流式+并行完成，共 %d 张", len(png_paths))
        return png_paths

    @staticmethod
    def convert_and_overwrite(
            pdf_path: str | Path,
            output_dir: str | Path,
            *,
            dpi: int = 150,
            prefix: str | None = None,
    ) -> List[Path]:
        pdf_path, output_dir = Path(pdf_path), Path(output_dir)
        if prefix is None:
            prefix = pdf_path.stem
        for old_png in output_dir.glob(f"{prefix}_*.png"):
            old_png.unlink(missing_ok=True)
        return PdfConvertService.convert(pdf_path, output_dir, dpi=dpi, prefix=prefix)

    @staticmethod
    def convert_table_pages_only(
            pdf_path: Path,
            out_dir: Path,
            *,
            preview_dpi: int = 72,
            table_dpi: int = 300,
    ) -> list[Path]:
        """
        保持原逻辑，但内部已自动改用 detect_table_page 单页接口
        （detect_table_pages 本身也已改成流式，内存安全）
        """
        from backend.services.table_page_detector import detect_table_pages

        pdf_path, out_dir = Path(pdf_path), Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        table_pages = set(detect_table_pages(pdf_path, preview_dpi))  # 已流式
        images = convert_from_path(pdf_path, dpi=150)
        png_paths = []
        for idx, img in enumerate(images, 1):
            if idx - 1 in table_pages:
                img = convert_from_path(pdf_path, dpi=table_dpi, first_page=idx, last_page=idx)[0]
            png_path = out_dir / f"{pdf_path.stem}_{idx:03d}.png"
            img.save(png_path, "PNG")
            png_paths.append(png_path)
        return png_paths


# -------------------- 简单自测 -------------------- #
if __name__ == "__main__":
    import traceback, time

    test_pdf = Path(r"E:\Datas\bank_data\images\601939建设银行2024年年度报告.pdf")
    out_dir = test_pdf.parent / "pngs"
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    try:
        # ① 快速测试最新流式逻辑
        # import threading, queue

        progress = {}
        background_convert_table_only(test_pdf, out_dir, "job-001", progress)
        print("测试完成，最终进度：", progress["job-001"])

        # ② 也可以直接调工具类
        # paths = PdfConvertService.convert(test_pdf, out_dir, dpi=150)
    except Exception as e:
        traceback.print_exc()
    print("耗时：", time.time() - t0, "s")