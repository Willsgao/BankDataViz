# -*- coding:utf-8 -*-
"""
同步版：单张/批量图片 → 版面检测 + 表格区域提取 + 表格裁切
最终适配方案：
1. 彻底移除所有不支持的参数（use_gpu等）
2. 仅保留PaddleOCR 3.3.0支持的必要参数
3. 适配魔搭社区模型格式，确保无冗余校验
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Union, Optional
from PIL import Image, UnidentifiedImageError
from paddleocr import LayoutDetection

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 环境配置（通过环境变量控制GPU，不传入代码参数）
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # 强制CPU运行

# 权重目录与模型参数
WEIGHT_DIR = Path(__file__).resolve().parent.parent / "weights" / "PP-DocLayout-M" # "PP-DocLayout_plus-L"
DEFAULT_CONFIDENCE_THRESHOLD = 0.5

# 全局复用模型
_model: Optional[LayoutDetection] = None


def _validate_model_dir():
    """校验模型目录（仅保留魔搭社区存在的文件）"""
    required_files = ["inference.pdiparams", "inference.yml", "inference.json"]
    missing = []
    if not WEIGHT_DIR.exists():
        raise FileNotFoundError(f"模型目录不存在: {WEIGHT_DIR}")
    for file in required_files:
        if not (WEIGHT_DIR / file).exists():
            missing.append(file)
    if missing:
        raise FileNotFoundError(f"模型文件缺失: {missing}，请检查目录")


def _get_model():
    """获取模型，仅传入PaddleOCR支持的参数"""
    global _model
    if _model is None:
        print(f"当前模型目录: {WEIGHT_DIR.resolve()}")
        _validate_model_dir()

        # 关键修改：仅保留model_name和model_dir两个必要参数
        # 移除所有可能不支持的参数（use_gpu、enable_mkldnn等）
        _model = LayoutDetection(
            model_name="PP-DocLayout-M", #"PP-DocLayout_plus-L",
            model_dir=str(WEIGHT_DIR)
        )
    return _model


def layout_detect(
        png_path: Union[str, Path],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> Dict[str, Union[Dict, List[Dict]]]:
    path = Path(png_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"不是文件路径: {path}")

    model = _get_model()
    try:
        detection_results = model.predict(
            str(path),
            batch_size=1,
            layout_nms=True
        )
        if not detection_results:
            raise RuntimeError("版面检测未返回结果")

        json_data = detection_results[0].json
        table_zones = []
        for idx, obj in enumerate(json_data.get("layout", [])):
            if (obj["type"].lower() == "table" and
                    obj.get("score", 0.0) >= confidence_threshold):
                table_zones.append({
                    "table_id": idx,
                    "bbox": [int(round(x)) for x in obj["bbox"]],
                    "confidence": round(obj.get("score", 0.0), 4)
                })
        logger.info(f"图片 {path.name} 检测到 {len(table_zones)} 个有效表格")
        return {"json": json_data, "table_zones": table_zones}

    except Exception as e:
        logger.error(f"图片检测失败: {str(e)}")
        raise


def cut_tables_from_image(
        png_path: Union[str, Path],
        output_dir: Union[str, Path],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> List[Dict[str, Union[int, str, List[int], float]]]:
    png_path = Path(png_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    detect_result = layout_detect(png_path, confidence_threshold)
    table_zones = detect_result["table_zones"]
    if not table_zones:
        logger.info(f"图片 {png_path.name} 未检测到表格")
        return []

    try:
        with Image.open(png_path) as img:
            img_width, img_height = img.size
            cut_results = []

            for table in table_zones:
                table_idx = table["table_id"]
                x1, y1, x2, y2 = table["bbox"]

                x1_clamped = max(0, min(int(x1), img_width))
                y1_clamped = max(0, min(int(y1), img_height))
                x2_clamped = max(0, min(int(x2), img_width))
                y2_clamped = max(0, min(int(y2), img_height))

                if x2_clamped - x1_clamped <= 0 or y2_clamped - y1_clamped <= 0:
                    logger.warning(f"表格 {table_idx} 区域无效，跳过")
                    continue

                try:
                    table_img = img.crop((x1_clamped, y1_clamped, x2_clamped, y2_clamped))
                    cut_filename = f"{png_path.stem}_table_{table_idx}.png"
                    cut_path = output_dir / cut_filename
                    table_img.save(cut_path)

                    cut_results.append({
                        "table_index": table_idx,
                        "bbox": [x1, y1, x2, y2],
                        "clamped_bbox": [x1_clamped, y1_clamped, x2_clamped, y2_clamped],
                        "cut_png_path": str(cut_path),
                        "confidence": table["confidence"]
                    })
                except Exception as e:
                    logger.error(f"表格 {table_idx} 裁切失败: {str(e)}")
                    continue

            return cut_results

    except UnidentifiedImageError:
        raise ValueError(f"无法识别的图片格式: {png_path}")
    except Exception as e:
        logger.error(f"图片处理失败: {str(e)}")
        raise


def batch_cut_tables(
        pdf_folder: Union[str, Path],
        png_names: List[str],
        output_root: Union[str, Path],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> List[Dict[str, Union[str, bool, int, List[Dict]]]]:
    output_root = Path(output_root).resolve()
    pdf_folder = Path(pdf_folder)
    results = []

    for png_name in png_names:
        original_png_path = output_root / pdf_folder / png_name
        logger.info(f"开始处理: {original_png_path}")

        try:
            cuts = cut_tables_from_image(
                png_path=original_png_path,
                output_dir=output_root / pdf_folder,
                confidence_threshold=confidence_threshold
            )
            results.append({
                "png_name": png_name,
                "success": True,
                "table_count": len(cuts),
                "cuts": cuts
            })
        except Exception as e:
            logger.error(f"处理 {png_name} 失败", exc_info=True)
            results.append({
                "png_name": png_name,
                "success": False,
                "error": str(e),
                "table_count": 0,
                "cuts": []
            })

    logger.info(f"批量处理完成，总处理 {len(png_names)} 张，成功 {sum(1 for r in results if r['success'])} 张")
    return results


if __name__ == "__main__":
    try:
        test_output_root = Path(".") / "test_output"
        test_pdf_folder = "test_pngs"
        (Path(test_pdf_folder)).mkdir(exist_ok=True)
        test_output_root.mkdir(exist_ok=True)

        test_png_names = [
            f for f in os.listdir(test_pdf_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]

        if test_png_names:
            batch_results = batch_cut_tables(
                pdf_folder=test_pdf_folder,
                png_names=test_png_names,
                output_root=test_output_root,
                confidence_threshold=0.6
            )
            logger.info(f"调试结果: {batch_results}")
        else:
            logger.warning(f"未在 {test_pdf_folder} 找到图片")
    except Exception as e:
        logger.critical("调试失败", exc_info=True)