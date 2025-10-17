#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
PDF → PNG 转换服务
作者：IronmanJay
日期：2025-07-28
"""

from __future__ import annotations

import time
import logging
from pathlib import Path
from typing import List

# 需要提前安装：
#   pip install pdf2image pillow
from pdf2image import convert_from_path
from backend.service.table_page_detector import detect_table_pages

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def background_convert(pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict):
    """
    线程池内执行：
    1. 72 DPI 快速 YOLO 筛表格页
    2. 仅表格页 300 DPI，其余 150 DPI
    3. 逐页回写进度
    """
    from backend.service.table_page_detector import detect_table_pages   # 延迟导入避免循环

    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        # ---- ① 72 DPI 预览 + 找表格页 ----
        preview_imgs = convert_from_path(pdf_path, dpi=72)
        table_pages = set(detect_table_pages(pdf_path, 72))   # 返回 0-based 页码
        total = len(preview_imgs)
        progress_dict[job_id]["total"] = total

        # ---- ② 逐页生成：表格页 300 DPI，其余 150 DPI ----
        for idx in range(1, total + 1):
            page_0b = idx - 1
            if page_0b in table_pages:
                img = convert_from_path(pdf_path, dpi=300,
                                        first_page=idx, last_page=idx)[0]
            else:
                img = convert_from_path(pdf_path, dpi=150,
                                        first_page=idx, last_page=idx)[0]

            png_name = f"{pdf_path.stem}_{idx:03d}.png"
            img.save(out_dir / png_name, "PNG")

            # ---- ③ 实时进度 ----
            progress_dict[job_id]["finished"] = idx
            progress_dict[job_id]["percent"]  = round(idx / total * 100)
            time.sleep(0.02)          # 可选：避免进度刷太快

    except Exception as e:
        logger.exception("background_convert 失败")
        progress_dict[job_id]["error"]   = str(e)
        progress_dict[job_id]["percent"] = -1


def background_convert_table_only1(
    pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
):
    from backend.service.table_page_detector import detect_table_pages
    from PIL import Image
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed

    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        t0 = time.time()
        total = PdfConvertService._get_page_count(pdf_path)
        progress_dict[job_id]["total"] = total
        t1 = time.time()
        print("t1 - t0:", t1 - t0)

        # 预先把 72 DPI 缩图全部拿到，避免多次 poppler 调用
        images_72 = convert_from_path(pdf_path, dpi=72)
        images_75 = [im.copy().resize((im.width // 4, im.height // 4), Image.LANCZOS) for im in images_72]
        table_pages = set(detect_table_pages(pdf_path, 75, images=images_75))
        t2 = time.time()
        print("YOLO 判表耗时:", t2 - t1, "表格页:", sorted(table_pages))

        # 并发渲染：全部 300 DPI，不再降采样
        def render_page(page_0b: int):
            idx = page_0b + 1
            img = convert_from_path(pdf_path, dpi=300, first_page=idx, last_page=idx)[0]
            ext = 'png' #if page_0b in table_pages else 'png'
            fmt = 'PNG' #if ext == 'png' else 'PNG'
            out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.{ext}"
            img.save(out_path, fmt, quality=95 if fmt == 'JPEG' else None)
            return idx

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as exe:
            futures = {exe.submit(render_page, p): p for p in range(total)}
            for fut in as_completed(futures):
                idx = fut.result()
                progress_dict[job_id]["finished"] = idx
                progress_dict[job_id]["percent"]  = round(idx / total * 100)

        t5 = time.time()
        print("总耗时:", t5 - t0)

    except Exception as e:
        logger.exception(f"[{job_id}] stream_safe 失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1



def background_convert_table_only2(
    pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
):
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pdf2image import convert_from_path
    import logging
    logger = logging.getLogger(__name__)

    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:

        # print("os.cpu_count():", os.cpu_count())

        # ① 毫秒级拿总页数
        total = PdfConvertService._get_page_count(pdf_path)
        progress_dict[job_id]["total"] = total

        # ② 一次性 300 DPI 转图（使用 pdftocairo，中文兼容最好）
        images_300 = convert_from_path(
            pdf_path,
            dpi=300,
            use_pdftocairo=True,
            fmt="png"
        )

        # ③ 并发保存 PNG
        def render_page(page_0b: int):
            idx = page_0b + 1
            img = images_300[page_0b]
            out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.png"
            img.save(out_path, "PNG")
            return idx

        # os.cpu_count()
        with ThreadPoolExecutor(max_workers=1) as exe:
            futures = {exe.submit(render_page, p): p for p in range(total)}
            for fut in as_completed(futures):
                idx = fut.result()
                progress_dict[job_id]["finished"] = idx
                progress_dict[job_id]["percent"] = round(idx / total * 100)

        logger.info(f"[{job_id}] 全部保存完成，共 {total} 页")

    except Exception as e:
        logger.exception(f"[{job_id}] 转换失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1


def background_convert_table_only3(
    pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
):
    import os, subprocess, tempfile
    from pathlib import Path
    from PIL import Image
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import logging
    logger = logging.getLogger(__name__)

    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        # ① 毫秒级拿总页数
        total = PdfConvertService._get_page_count(pdf_path)
        progress_dict[job_id]["total"] = total

        # ② ✅ 手动 pdftocairo -level2 → 内存
        # ① 正常 300 dpi RGB，不用任何 cairo 花活
        images_300 = convert_from_path(
            pdf_path,
            dpi=300,
            use_pdftocairo=False,      # 用 poppler pdftoppm 即可
            fmt="png",
            thread_count=1,
        )

        # ② ✅ 直接内存加深对比度（自动色阶 + 30 % 对比度）
        from PIL import ImageOps, ImageEnhance
        def deepen(img: Image.Image) -> Image.Image:
            img = ImageOps.autocontrast(img, cutoff=2)      # 2 % 自动色阶
            img = ImageEnhance.Contrast(img).enhance(1.3)   # 再拉 30 % 对比
            return img
        images_300 = [deepen(im) for im in images_300]


        # ③ 单线程保存 + 进度
        for page_0b in range(total):
            idx = page_0b + 1
            img = images_300[page_0b]
            out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.png"
            img.save(out_path, "PNG")

            progress_dict[job_id]["finished"] = idx
            progress_dict[job_id]["percent"] = round(idx / total * 100)

        logger.info(f"[{job_id}] 全部保存完成，共 {total} 页")

    except Exception as e:
        logger.exception(f"[{job_id}] 转换失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1



def background_convert_table_only(
    pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
):
    import logging, tempfile, subprocess, shutil, os
    from pathlib import Path
    from PIL import Image, ImageOps, ImageEnhance
    from concurrent.futures import ProcessPoolExecutor, as_completed

    logger = logging.getLogger(__name__)
    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        # ① 总页数
        t0 = time.time()
        total = PdfConvertService._get_page_count(pdf_path)
        progress_dict[job_id]["total"] = total
        out_dir.mkdir(parents=True, exist_ok=True)

        t1 = time.time()
        print("t1 - t0:", t1 - t0)

        # ② 选 RAM-disk（Linux /dev/shm，Windows  fallback 到系统临时目录）
        ram = Path("/dev/shm") if os.path.exists("/dev/shm") else None
        with tempfile.TemporaryDirectory(dir=ram) as tmp:
            tmp = Path(tmp)
            # ②-1 一次性导出全部 300 dpi PNG（pdftoppm 自身多线程）
            subprocess.run([
                "pdftoppm", "-png", "-r", "300",
                str(pdf_path), str(tmp / "page")
            ], check=True)

            png_files = sorted(tmp.glob("page-*.png"))

            # ②-2 deepen 函数（纯 CPU，无 I/O）
            def deepen_and_save(args):
                png_path, out_path = args
                deepen = lambda im: ImageEnhance.Contrast(
                    ImageOps.autocontrast(im, cutoff=2)
                ).enhance(1.3)
                img = deepen(Image.open(png_path))
                # PNG 压缩级别 1 → 写盘快 3~5 倍，肉眼几乎无差异
                img.save(out_path, "PNG", compress_level=1)
                return out_path

            t2 = time.time()
            print("t2 - t1:", t2 - t1)

            # ②-3 进程池（CPU 核数，I/O 不占 GIL）
            tasks = [
                (png, out_dir / f"{pdf_path.stem}_{idx:03d}.png")
                for idx, png in enumerate(png_files, 1)
            ]
            with ProcessPoolExecutor(max_workers=os.cpu_count()) as exe:
                futures = {exe.submit(deepen_and_save, t): t[1] for t in tasks}
                for fut in as_completed(futures):
                    _ = fut.result()  # 抛异常
                    # 主线程只干一件事：刷进度
                    finished = len([f for f in futures if f.done()])
                    progress_dict[job_id]["finished"] = finished
                    progress_dict[job_id]["percent"]  = round(finished / total * 100)

        logger.info(f"[{job_id}] 全部保存完成，共 {total} 页")

    except Exception as e:
        logger.exception(f"[{job_id}] 转换失败")
        progress_dict[job_id]["error"]   = str(e)
        progress_dict[job_id]["percent"] = -1


class PdfConvertService:
    """
    将本地 PDF 文件逐页转成 PNG 图片。
    静态方法，无状态，方便单元测试与复用。
    """

    DEFAULT_DPI: int = 300          # 默认分辨率
    DEFAULT_FMT: str = "png"        # 只输出 PNG

    # -------------------- 公开接口 -------------------- #
    @staticmethod
    def _get_page_count(pdf_path: Path) -> int:
        """调用 pdfinfo 立即拿到总页数（毫秒级）"""
        import subprocess

        cmd = ["pdfinfo", str(pdf_path)]
        # out = subprocess.check_output(cmd, text=True, encoding="utf-8")

        out = subprocess.check_output(cmd, text=True, encoding="gbk")
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return int(line.split()[-1])
        raise RuntimeError("pdfinfo 未返回 Pages 字段")
    # ============== 结束 ==============


    @staticmethod
    def convert(
            pdf_path: str | Path,
            output_dir: str | Path,
            *,
            dpi: int = 150,
            prefix: str | None = None,
    ) -> List[Path]:
        """
        流式逐页 + 线程池版
        370 页 150 DPI 实测 65 s，峰值内存 < 200 MB
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        pdf_path, output_dir = Path(pdf_path), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        prefix = prefix or pdf_path.stem

        # ① 先拿总页数（几乎 0 内存）
        # page_total = len(convert_from_path(pdf_path, dpi=1, first_page=1, last_page=1))
        page_total = PdfConvertService._get_page_count(pdf_path)

        # ② 单页渲染函数
        def render_page(page: int) -> Path:
            img = convert_from_path(pdf_path, dpi=dpi, first_page=page, last_page=page)[0]
            png_path = output_dir / f"{prefix}_{page:03d}.png"
            img.save(png_path, "PNG")
            return png_path

        # ③ 线程池并发（4 核即可）
        png_paths = [None] * page_total
        with ThreadPoolExecutor(max_workers=4) as exe:
            futures = {exe.submit(render_page, p): p - 1 for p in range(1, page_total + 1)}
            for f in as_completed(futures):
                png_paths[futures[f]] = f.result()

        logger.info("流式+并行完成，共 %d 张", len(png_paths))
        return png_paths


    # -------------------- 辅助方法（可选） -------------------- #

    @staticmethod
    def convert_and_overwrite(
        pdf_path: str | Path,
        output_dir: str | Path,
        *,
        dpi: int = DEFAULT_DPI,
        prefix: str | None = None,
    ) -> List[Path]:
        """
        同 convert，但在写入前先清空 output_dir 里所有同名前缀的 PNG。
        用于希望“覆盖上一次结果”的场景。
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        if prefix is None:
            prefix = pdf_path.stem

        # 先删除旧图
        for old_png in output_dir.glob(f"{prefix}_*.png"):
            old_png.unlink(missing_ok=True)
            logger.debug(f"已删除旧图：{old_png}")

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
        1. 72 DPI 过 YOLO 找表格页
        2. 只对表格页转 300 DPI
        3. 其余页转 150 DPI（可选，保持目录完整）
        返回生成的 PNG 路径列表
        """
        pdf_path, out_dir = Path(pdf_path), Path(out_dir)
        print("********pdf_path, out_dir:", pdf_path, out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        table_pages = set(detect_table_pages(pdf_path, preview_dpi))
        print("table_pages:", table_pages)
        images = convert_from_path(pdf_path, dpi=150)  # 先统一 150 DPI
        png_paths = []
        for idx, img in enumerate(images, 1):
            print("idx--------------->:", idx)
            if idx - 1 in table_pages:  # 表格页重新 300 DPI
                img = convert_from_path(pdf_path, dpi=table_dpi, first_page=idx, last_page=idx)[0]
            png_name = f"{pdf_path.stem}_{idx:03d}.png"
            png_path = out_dir / png_name
            print("png_path--------------->:", png_path)
            img.save(png_path, "PNG")
            png_paths.append(png_path)

        return png_paths


# -------------------- 简单自测 -------------------- #
if __name__ == "__main__":
    import traceback, time
    from pathlib import Path

    test_pdf = Path(r"E:\Datas\bank_data\images\601939建设银行2024年年度报告.pdf")
    out_dir = test_pdf.parent / "pngs"
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    try:
        paths = PdfConvertService.convert(test_pdf, out_dir, dpi=150)
        print("测试完成，已生成：", *paths, sep="\n  ")
    except Exception as e:
        print("测试失败：")
        traceback.print_exc()      # ← 关键：打印完整堆栈
    print("耗时：", time.time() - t0, "s")
