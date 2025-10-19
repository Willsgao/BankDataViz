#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
PDF → PNG 转换服务（流式 + 表格页高 DPI）
author : you
date   : 2025-10-17  最新融合版
"""
from __future__ import annotations

import time, logging, os, tempfile, subprocess, shutil
from pathlib import Path
from typing import List

from pdf2image import convert_from_path
from backend.service.table_page_detector import detect_table_page   # 单页接口

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# ① 后台任务：流式 + 表格页 300 DPI，其余 150 DPI
# ------------------------------------------------------------------
def background_convert(
    pdf_path: Path,
    out_dir: Path,
    job_id: str,
    progress_dict: dict,
    *,
    preview_dpi: int = 72,
    table_dpi: int = 300,
    normal_dpi: int = 150,
) -> None:
    """
    线程池内执行：
    1. 逐页 72 dpi 预览 → 单页接口 detect_table_page 判表格
    2. 根据结果决定正式 dpi（表格页 300，其余 150）
    3. 逐页正式渲染并立即释放，峰值内存≈1 张图
    """
    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        # 毫秒级拿总页数
        total = PdfConvertService._get_page_count(pdf_path)
        progress_dict[job_id]["total"] = total

        table_flags: List[bool] = []
        # ---- ① 预览：逐页 72 dpi，立即释放 ----
        for page_0b in range(total):
            img = convert_from_path(
                pdf_path, dpi=preview_dpi, first_page=page_0b + 1, last_page=page_0b + 1
            )[0]
            box = detect_table_page(pdf_path, page_0b, dpi=preview_dpi)
            table_flags.append(box is not None)
            del img  # 立即释放

        # ---- ② 正式渲染 ----
        for page_0b in range(total):
            dpi = table_dpi if table_flags[page_0b] else normal_dpi
            img = convert_from_path(
                pdf_path, dpi=dpi, first_page=page_0b + 1, last_page=page_0b + 1
            )[0]
            png_path = out_dir / f"{pdf_path.stem}_{page_0b + 1:03d}.png"
            img.save(png_path, "PNG")
            del img  # 立即释放

            # 实时进度
            progress_dict[job_id]["finished"] = page_0b + 1
            progress_dict[job_id]["percent"] = round((page_0b + 1) / total * 100)

        logger.info(f"[{job_id}] 全部完成，共 {total} 页，表格页：{sum(table_flags)} 张")
    except Exception as e:
        logger.exception(f"[{job_id}] 转换失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1





# ------------------------------------------------------------------
# ② 后台任务：仅转表格页，300 DPI，PyMuPDF 截图式流式
# ------------------------------------------------------------------
def background_convert_table_only(
    pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
) -> None:
    """
    流式 + detect_table_page 单页判表 + 仅表格页 300 dpi
    内存峰值 ≈ 1 张 300 dpi 图片；彻底摆脱 poppler
    """
    import os, time, logging
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import fitz  # PyMuPDF
    from PIL import Image, ImageOps, ImageEnhance
    from backend.service.table_page_detector import detect_table_page

    logger = logging.getLogger(__name__)
    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        t0 = time.time()
        total = PdfConvertService._get_page_count(pdf_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        progress_dict[job_id]["total"] = total

        # ① 逐页 72 dpi 判表（PyMuPDF 渲染）
        doc = fitz.open(pdf_path)
        table_pages: set[int] = set()
        for page_0b in range(total):
            page = doc.load_page(page_0b)
            pix = page.get_pixmap(dpi=72, colorspace=fitz.csRGB)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if detect_table_page(pdf_path, page_0b, dpi=72) is not None:
                table_pages.add(page_0b)
            del img, pix
        doc.close()
        t1 = time.time()
        logger.info(f"[{job_id}] 判表完成，表格页：{sorted(table_pages)}，耗时：{t1 - t0:.2f}s")

        # ② 并发渲染：仅表格页 300 dpi， deepen 增强
        def render_if_table(page_0b: int):
            idx = page_0b + 1
            if page_0b not in table_pages:
                return idx          # 跳过非表格页
            doc = fitz.open(pdf_path)          # 每个 worker 独立 doc，线程安全
            page = doc.load_page(page_0b)
            pix = page.get_pixmap(dpi=300, colorspace=fitz.csRGB)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            # 可选：加深对比度
            img = ImageOps.autocontrast(img, cutoff=2)
            img = ImageEnhance.Contrast(img).enhance(1.3)
            out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.png"
            img.save(out_path, "PNG", compress_level=1)
            del img, pix
            doc.close()
            return idx

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as exe:
            futures = {exe.submit(render_if_table, p): p for p in range(total)}
            for fut in as_completed(futures):
                finished = fut.result()
                progress_dict[job_id]["finished"] = finished
                progress_dict[job_id]["percent"] = round(finished / total * 100)

        t2 = time.time()
        logger.info(f"[{job_id}] 全部完成，总耗时：{t2 - t0:.2f}s")

    except Exception as e:
        logger.exception(f"[{job_id}] 转换失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1



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
        from concurrent.futures import ThreadPoolExecutor, as_completed

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
        from backend.service.table_page_detector import detect_table_pages

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
        from concurrent.futures import ThreadPoolExecutor
        import threading, queue

        progress = {}
        background_convert(test_pdf, out_dir, "job-001", progress)
        print("测试完成，最终进度：", progress["job-001"])

        # ② 也可以直接调工具类
        # paths = PdfConvertService.convert(test_pdf, out_dir, dpi=150)
    except Exception as e:
        traceback.print_exc()
    print("耗时：", time.time() - t0, "s")