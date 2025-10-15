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

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)



def background_convert(pdf_path: Path, out_dir: Path, job_id: str, progress_dict: dict):
    """
    在线程池里跑，逐页更新进度。
    progress_dict 由外部传进来，避免直接 import app.PROGRESS
    """
    progress_dict[job_id] = {"total": 0, "finished": 0, "percent": 0}
    try:
        images = convert_from_path(pdf_path, dpi=300)
        total = len(images)
        progress_dict[job_id]["total"] = total
        for idx, img in enumerate(images, 1):
            png_name = f"{pdf_path.stem}_{idx:03d}.png"
            img.save(out_dir / png_name, "PNG")
            progress_dict[job_id]["finished"] = idx
            progress_dict[job_id]["percent"]  = round(idx / total * 100)
            time.sleep(0.1)          # 模拟耗时，可删
    except Exception as e:
        progress_dict[job_id]["error"] = str(e)
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
    def convert(
        pdf_path: str | Path,
        output_dir: str | Path,
        *,
        dpi: int = DEFAULT_DPI,
        prefix: str | None = None,
    ) -> List[Path]:
        """
        将一份 PDF 的所有页面转成 PNG 文件。

        参数
        ----
        pdf_path : PDF 源文件路径
        output_dir : PNG 输出目录（若不存在则自动创建）
        dpi : 渲染分辨率，默认 150
        prefix : 输出文件名前缀，默认使用 PDF 文件名（不含扩展名）

        返回
        ----
        List[Path] : 实际生成的 PNG 文件路径列表，顺序同 PDF 页序
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)

        # 参数校验
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")
        if not pdf_path.suffix.lower() == ".pdf":
            raise ValueError(f"文件扩展名不是 .pdf：{pdf_path}")

        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)

        # 文件名前缀
        if prefix is None:
            prefix = pdf_path.stem

        logger.info(f"开始转换 PDF → PNG：{pdf_path.name} | 输出目录：{output_dir}")

        # 真正转图
        try:
            images = convert_from_path(pdf_path, dpi=dpi, fmt=PdfConvertService.DEFAULT_FMT)
        except Exception as exc:
            logger.exception("pdf2image 转换失败")
            raise RuntimeError(f"PDF 转换失败：{exc}") from exc

        # 逐页保存
        png_paths: List[Path] = []
        for page_index, img in enumerate(images, start=1):
            png_name = f"{prefix}_{page_index:03d}.{PdfConvertService.DEFAULT_FMT}"
            png_path = output_dir / png_name
            img.save(png_path, "PNG")
            png_paths.append(png_path)
            logger.debug(f"已生成：{png_path}")

        logger.info(f"转换完成，共生成 {len(png_paths)} 张 PNG")
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


# -------------------- 简单自测 -------------------- #
if __name__ == "__main__":
    import shutil
    from pathlib import Path

    # 1. 输入：已有的真实 PDF
    test_pdf = Path(r"F:\wills\codes\test_data\2024-04-24-1921038.IB-19禾城农商二级01-浙江禾城农村商业银行股份有限公司2023年年度报告.pdf")

    # 2. 输出：单独建一个子目录放 PNG
    out_dir = test_pdf.parent / "pngs"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        paths = PdfConvertService.convert(test_pdf, out_dir, dpi=150)
        print("测试完成，已生成：")
        for p in paths:
            print("  ", p)
    except Exception as e:
        print("测试失败：", e)

