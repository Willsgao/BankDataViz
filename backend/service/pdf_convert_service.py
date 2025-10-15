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

    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        # ① 一次性 300 DPI（仅一次 poppler）
        t0 = time.time()
        images_300 = convert_from_path(pdf_path, dpi=300)
        total = len(images_300)
        progress_dict[job_id]["total"] = total
        t1 = time.time()
        print("images_300:", t1 - t0)
        logger.info(f"[{job_id}] 300 DPI 一次渲染完成：{t1 - t0:.2f}s")

        # ② 内存缩图 75 DPI 给 YOLO（零 IO）
        images_75 = [img.copy().resize((img.width // 4, img.height // 4), Image.LANCZOS) for img in images_300]
        table_pages = set(detect_table_pages(pdf_path, 75, images=images_75))
        t2 = time.time()
        print("images_75:", t2 - t1)
        logger.info(f"[{job_id}] YOLO 筛表完成：{t2 - t1:.2f}s，发现表格页：{sorted(table_pages)}")

        # ③ 直接用原图保存（不再渲染）
        for idx, img in enumerate(images_300, 1):
            page_0b = idx - 1
            if page_0b not in table_pages:
                # 非表格页：内存降采样 150 DPI 保存（仍清晰）
                img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)

            png_path = out_dir / f"{pdf_path.stem}_{idx:03d}.png"
            img.save(png_path, "PNG")

            progress_dict[job_id]["finished"] = idx
            progress_dict[job_id]["percent"] = round(idx / total * 100)

        t3 = time.time()
        print("progress_dict:", t3 - t2)
        logger.info(f"[{job_id}] 全部保存完成：{t3 - t2:.2f}s，总耗时：{t3 - t0:.2f}s")

    except Exception as e:
        logger.exception(f"[{job_id}] 异步转换失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1


def background_convert_table_only2(
    pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
):
    from backend.service.table_page_detector import detect_table_pages
    from PIL import Image

    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        # ① 毫秒级拿总页数
        t0 = time.time()
        total = PdfConvertService._get_page_count(pdf_path)
        progress_dict[job_id]["total"] = total
        t1 = time.time()
        print("progress_dict:", t1 - t0)
        table_pages = set()
        print("len_table_pages:", len(table_pages))
        for idx in range(1, total + 1):
            t00 = time.time()
            # ② 流式：只渲染当前页（300 DPI）
            img_300 = convert_from_path(pdf_path, dpi=300,
                                        first_page=idx, last_page=idx)[0]

            # ③ 内存缩到 75 DPI 给 YOLO 判表（用完即扔）
            img_75 = img_300.resize((img_300.width // 4, img_300.height // 4),
                                    Image.LANCZOS)
            if detect_table_pages(pdf_path, 75, images=[img_75]):
                table_pages.add(idx - 1)          # 0-based

            # ④ 非表格页降采样到 150 DPI，全部 PNG
            if idx - 1 not in table_pages:
                img_300 = img_300.resize((img_300.width // 2, img_300.height // 2),
                                         Image.LANCZOS)  # 150 DPI

            out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.png"
            img_300.save(out_path, 'PNG')

            # ⑤ 实时进度
            progress_dict[job_id]["finished"] = idx
            progress_dict[job_id]["percent"] = round(idx / total * 100)
            t01 = time.time()

            # print("odx-time:", t01 - t00)
        t2 = time.time()
        print("耗时:", t2 - t1, t2 - t0)
    except Exception as e:
        logger.exception(f"[{job_id}] 异步转换失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1


def background_convert_table_only3(
    pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
):
    from backend.service.table_page_detector import detect_table_pages
    from PIL import Image
    from concurrent.futures import ThreadPoolExecutor, as_completed

    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        t0 = time.time()
        # ① 72 DPI 一次性拿全本（毫秒级）
        images_72 = convert_from_path(pdf_path, dpi=72)
        total = len(images_72)
        progress_dict[job_id]["total"] = total

        # ② 内存 75 DPI 给 YOLO 批量判表
        images_75 = [img.copy().resize((img.width // 4, img.height // 4), Image.LANCZOS)
                     for img in images_72]
        table_pages = set(detect_table_pages(pdf_path, 75, images=images_75))
        t1 = time.time()
        logger.info(f"[{job_id}] YOLO 筛表完成：{t1 - t0:.1f}s，表格页：{sorted(table_pages)}")

        # ③ 线程池：只对表格页二次 300 DPI 渲染
        need_300 = {idx for idx in table_pages}   # 0-based

        def render_if_table(page_0b: int) -> tuple[int, Image.Image]:
            if page_0b in need_300:
                img = convert_from_path(pdf_path, dpi=300,
                                        first_page=page_0b + 1, last_page=page_0b + 1)[0]
            else:
                img = images_72[page_0b].copy()
                # 非表格页 150 DPI 灰度 PNG
                img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)  # 72→144 ≈150
                img = img.convert('L')
            return page_0b, img

        with ThreadPoolExecutor(max_workers=4) as exe:
            futures = [exe.submit(render_if_table, p) for p in range(total)]
            for fut in as_completed(futures):
                page_0b, img = fut.result()
                idx = page_0b + 1
                ext, fmt = ('png', 'PNG') if page_0b in need_300 else ('jpg', 'JPEG')
                out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.{ext}"
                img.save(out_path, fmt, quality=90 if fmt == 'JPEG' else None)

                progress_dict[job_id]["finished"] = idx
                progress_dict[job_id]["percent"] = round(idx / total * 100)

        t2 = time.time()
        logger.info(f"[{job_id}] 全部保存完成：{t2 - t1:.1f}s，总耗时：{t2 - t0:.1f}s")

    except Exception as e:
        logger.exception(f"[{job_id}]  ultra 失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1


def background_convert_table_only4(
    pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
):
    from backend.service.table_page_detector import detect_table_pages
    from PIL import Image
    from concurrent.futures import ThreadPoolExecutor, as_completed

    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        # ① 先拿总页数（毫秒级）
        t0 = time.time()
        total = PdfConvertService._get_page_count(pdf_path)
        progress_dict[job_id]["total"] = total
        t1 = time.time()
        print("t1 - t0:", t1 - t0)

        # ② 分批 72 DPI，每批 50 页，避免一次性爆内存
        batch = 50
        images_72 = []
        for start in range(1, total + 1, batch):
            end = min(start + batch - 1, total)
            images_72 += convert_from_path(pdf_path, dpi=72, first_page=start, last_page=end)
        t2 = time.time()
        print("t2 - t1:", t2 - t1)

        # ③ 内存 75 DPI 给 YOLO
        images_75 = [img.copy().resize((img.width // 4, img.height // 4), Image.LANCZOS)
                     for img in images_72]
        table_pages = set(detect_table_pages(pdf_path, 75, images=images_75))

        # ④ 并行二次渲染（仅表格页 300 DPI）
        need_300 = {idx for idx in table_pages}
        t3 = time.time()
        print("t3 - t2:", t3 - t2)

        def render_if_table(page_0b: int) -> tuple[int, Image.Image]:
            if page_0b in need_300:
                img = convert_from_path(pdf_path, dpi=300,
                                        first_page=page_0b + 1, last_page=page_0b + 1)[0]
            else:
                src = images_72[page_0b]
                img = src.copy().resize((src.width * 2, src.height * 2), Image.LANCZOS).convert('L')
            return page_0b, img

        with ThreadPoolExecutor(max_workers=4) as exe:
            futures = [exe.submit(render_if_table, p) for p in range(total)]
            for fut in as_completed(futures):
                page_0b, img = fut.result()
                idx = page_0b + 1
                ext = 'png' if page_0b in need_300 else 'jpg'
                fmt = 'PNG' if ext == 'png' else 'JPEG'
                out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.{ext}"
                img.save(out_path, fmt, quality=90 if fmt == 'JPEG' else None)
                progress_dict[job_id]["finished"] = idx
                progress_dict[job_id]["percent"] = round(idx / total * 100)

        t4 = time.time()
        print("t4 - t3:", t4 - t3)

        print("总耗时：", t4 - t0)


    except Exception as e:
        logger.exception(f"[{job_id}] ultra_safe 失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1


def background_convert_table_only(
    pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict
):
    from backend.service.table_page_detector import detect_table_pages
    from PIL import Image

    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}

    try:
        t0 = time.time()
        total = PdfConvertService._get_page_count(pdf_path)
        progress_dict[job_id]["total"] = total
        t1 = time.time()
        print("t1 - t0:", t1 - t0)

        for idx in range(1, total + 1):
            page_0b = idx - 1

            t2 = time.time()

            # ① 流式 72 DPI 判表（只渲染当前页）
            img_72 = convert_from_path(pdf_path, dpi=72, first_page=idx, last_page=idx)[0]
            img_75 = img_72.copy().resize((img_72.width // 4, img_72.height // 4), Image.LANCZOS)
            is_table = bool(detect_table_pages(pdf_path, 75, images=[img_75]))

            t3 = time.time()
            print("t3 - t2:", t3 - t2)

            # ② 按需二次渲染
            if is_table:
                img = convert_from_path(pdf_path, dpi=300, first_page=idx, last_page=idx)[0]
            else:
                img = img_72.resize((img_72.width * 2, img_72.height * 2), Image.LANCZOS).convert('L')

            ext = 'png' if is_table else 'jpg'
            fmt = 'PNG' if ext == 'png' else 'JPEG'
            out_path = out_dir / f"{pdf_path.stem}_{idx:03d}.{ext}"
            img.save(out_path, fmt, quality=90)

            progress_dict[job_id]["finished"] = idx
            progress_dict[job_id]["percent"] = round(idx / total * 100)
            t4 = time.time()
            print("t4 - t3:", t4 - t3)

        t5 = time.time()
        print("t5 - t0:", t5 - t0)



    except Exception as e:
        logger.exception(f"[{job_id}] stream_safe 失败")
        progress_dict[job_id]["error"] = str(e)
        progress_dict[job_id]["percent"] = -1


class PdfConvertService:
    """
    将本地 PDF 文件逐页转成 PNG 图片。
    静态方法，无状态，方便单元测试与复用。
    """

    DEFAULT_DPI: int = 150          # 默认分辨率
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
