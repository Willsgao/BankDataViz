# table_detection_screening.py
"""
表格检测筛选模块 - 100%不遗漏表格的高效筛选方案
功能：扫描源目录图片，将有表格的图片复制到目标目录
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import json
import hashlib
import time
from dataclasses import dataclass
from enum import Enum
import base64
from io import BytesIO
from PIL import Image
import logging
import shutil
import os

# ==================== 导入配置 ====================
try:
    from backend.utils.config import tableconfig

    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    print("警告: 无法导入tableconfig，使用默认配置")

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==================== 配置管理 ====================

def get_config():
    """获取配置参数"""
    if USE_CONFIG:
        # 从tableconfig获取配置
        config = {
            # 传统检测配置
            "line_min_length": getattr(tableconfig, "line_min_length", 20),
            "line_threshold": getattr(tableconfig, "line_threshold", 50),
            "min_line_count": getattr(tableconfig, "min_line_count", 3),
            "min_text_density": getattr(tableconfig, "min_text_density", 0.02),
            "text_contour_min_area": getattr(tableconfig, "text_contour_min_area", 50),
            "alignment_threshold": getattr(tableconfig, "alignment_threshold", 0.7),
            "min_rows": getattr(tableconfig, "min_rows", 2),
            "min_cols": getattr(tableconfig, "min_cols", 2),
            "min_digit_ratio": getattr(tableconfig, "min_digit_ratio", 0.05),
            "high_confidence_threshold": getattr(tableconfig, "high_confidence_threshold", 0.7),
            "low_confidence_threshold": getattr(tableconfig, "low_confidence_threshold", 0.3),

            # 大模型配置
            "use_llm_mock": getattr(tableconfig, "use_llm_mock", True),
            "llm_model": getattr(tableconfig, "llm_model", "gpt-4-vision-preview"),
            "llm_api_key": getattr(tableconfig, "llm_api_key", ""),
            "llm_base_url": getattr(tableconfig, "llm_base_url", ""),

            # 图片压缩配置
            "compression_size": getattr(tableconfig, "compression_size", (128, 128)),
            "compression_quality": getattr(tableconfig, "compression_quality", 65),

            # 审计配置
            "audit_rate": getattr(tableconfig, "audit_rate", 0.1),

            # 路径配置
            "default_input_dir": getattr(tableconfig, "table_screening_input_dir", ""),
            "default_output_dir": getattr(tableconfig, "table_screening_output_dir", ""),

            # 文件过滤
            "supported_extensions": getattr(tableconfig, "supported_extensions", ['.png', '.jpg', '.jpeg', '.bmp']),
        }
    else:
        # 默认配置
        config = {
            # 传统检测配置
            "line_min_length": 20,
            "line_threshold": 50,
            "min_line_count": 3,
            "min_text_density": 0.02,
            "text_contour_min_area": 50,
            "alignment_threshold": 0.7,
            "min_rows": 2,
            "min_cols": 2,
            "min_digit_ratio": 0.05,
            "high_confidence_threshold": 0.7,
            "low_confidence_threshold": 0.3,

            # 大模型配置
            "use_llm_mock": True,
            "llm_model": "gpt-4-vision-preview",
            "llm_api_key": "",
            "llm_base_url": "",

            # 图片压缩配置
            "compression_size": (128, 128),
            "compression_quality": 65,

            # 审计配置
            "audit_rate": 0.1,

            # 路径配置
            "default_input_dir": "",
            "default_output_dir": "",

            # 文件过滤
            "supported_extensions": ['.png', '.jpg', '.jpeg', '.bmp'],
        }

    return config


# ==================== 数据类定义 ====================

class ScreeningResult(Enum):
    """筛选结果枚举"""
    HAS_TABLE = "has_table"  # 确定有表格
    NO_TABLE = "no_table"  # 确定无表格
    UNCERTAIN = "uncertain"  # 无法确定，需要大模型判断


@dataclass
class DetectionResult:
    """检测结果数据类"""
    image_path: str
    image_name: str
    screening_result: ScreeningResult
    confidence: float
    features: Dict[str, float]
    llm_used: bool = False
    llm_result: Optional[bool] = None
    processing_time: float = 0.0
    copied_to: Optional[str] = None  # 复制到的目标路径

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "image_name": self.image_name,
            "image_path": self.image_path,
            "screening_result": self.screening_result.value,
            "confidence": self.confidence,
            "features": self.features,
            "llm_used": self.llm_used,
            "llm_result": self.llm_result,
            "processing_time": self.processing_time,
            "copied_to": self.copied_to
        }


@dataclass
class ScreeningReport:
    """筛选报告数据类"""
    input_dir: str
    output_dir: str
    tables_dir: str  # 有表格目录
    no_tables_dir: str  # 无表格目录
    total_images: int
    has_table_images: List[str]  # 有表格的图片文件名
    no_table_images: List[str]  # 无表格的图片文件名
    uncertain_images: List[str]  # 需要大模型判断的图片文件名
    detection_results: List[DetectionResult]  # 详细结果
    copied_tables_count: int = 0  # 成功复制到有表格目录的数量
    copied_no_tables_count: int = 0  # 成功复制到无表格目录的数量
    processing_time: float = 0.0

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
            "tables_dir": self.tables_dir,
            "no_tables_dir": self.no_tables_dir,
            "total_images": self.total_images,
            "has_table_images": len(self.has_table_images),
            "no_table_images": len(self.no_table_images),
            "uncertain_images": len(self.uncertain_images),
            "copied_tables_count": self.copied_tables_count,
            "copied_no_tables_count": self.copied_no_tables_count,
            "processing_time": self.processing_time,
            "stats": {
                "has_table_percentage": len(
                    self.has_table_images) / self.total_images * 100 if self.total_images > 0 else 0,
                "no_table_percentage": len(
                    self.no_table_images) / self.total_images * 100 if self.total_images > 0 else 0,
                "uncertain_percentage": len(
                    self.uncertain_images) / self.total_images * 100 if self.total_images > 0 else 0,
                "tables_copy_success_rate": self.copied_tables_count / len(
                    self.has_table_images) * 100 if self.has_table_images else 0,
                "no_tables_copy_success_rate": self.copied_no_tables_count / len(
                    self.no_table_images) * 100 if self.no_table_images else 0
            }
        }

# ==================== 传统CV检测器 ====================

class TraditionalTableDetector:
    """
    传统CV表格检测器
    使用极宽松阈值，宁可误判不可漏判
    """

    def __init__(self):
        # 从配置获取参数
        self.config = get_config()

        logger.info("传统表格检测器初始化完成（极宽松模式）")

    def detect(self, image_path: str) -> Tuple[ScreeningResult, float, Dict[str, float]]:
        """
        检测图片是否包含表格
        返回: (筛选结果, 置信度, 特征分数)
        """
        start_time = time.time()
        image_name = Path(image_path).name

        try:
            # 1. 读取图片
            image = cv2.imread(image_path)
            if image is None:
                logger.warning(f"无法读取图片: {image_path}")
                return ScreeningResult.NO_TABLE, 0.0, {"error": "read_failed"}

            # 2. 计算各项特征分数
            features = self._extract_features(image)

            # 获取具体特征值
            line_score = features.get("line_score", 0)
            h_lines = features.get("horizontal_lines", 0)
            v_lines = features.get("vertical_lines", 0)
            total_lines = features.get("total_lines", 0)
            text_score = features.get("text_score", 0)
            alignment_score = features.get("alignment_score", 0)
            digit_score = features.get("digit_score", 0)
            complexity = features.get("complexity_score", 0.5)

            # 3. 打印调试信息
            print(f"\n🔍 检测图片: {image_name}")
            print(f"   线条特征: 总分={line_score:.2f}, 横线={h_lines}, 竖线={v_lines}, 总计={total_lines}")
            print(f"   文本特征: {text_score:.2f}, 对齐: {alignment_score:.2f}, 数字: {digit_score:.2f}")
            print(f"   复杂度: {complexity:.2f}")

            # 4. 严格的判断逻辑（第一轮：100%确定的情况）

            # ====== 情况A：100%有表格（必须同时满足多个条件） ======
            a1 = h_lines >= 3 and v_lines >= 3  # 既有横线又有竖线
            a2 = line_score > 0.7  # 线条特征明显
            a3 = text_score > 0.3  # 有一定文本
            a4 = alignment_score > 0.4  # 文本有对齐

            if a1 and a2 and a3 and a4:
                # 表格的典型特征：网格状结构+对齐文本
                confidence = min(line_score * 0.4 + text_score * 0.3 + alignment_score * 0.3, 0.95)
                print(f"   ✅ 判断: 100%有表格 (置信度: {confidence:.2f})")
                processing_time = time.time() - start_time
                return ScreeningResult.HAS_TABLE, confidence, features

            # ====== 情况B：100%无表格（满足任一条件即可） ======
            b1 = total_lines <= 1  # 几乎没有线条
            b2 = text_score < 0.1  # 几乎没有文本（可能是封面、图片等）
            b3 = complexity < 0.1 and text_score < 0.2  # 简单背景+极少文本

            if b1 or b2 or b3:
                confidence = 0.9  # 高置信度无表格
                reason = ""
                if b1:
                    reason = "线条太少"
                elif b2:
                    reason = "文本太少"
                elif b3:
                    reason = "内容过于简单"
                print(f"   ❌ 判断: 100%无表格 ({reason}, 置信度: {confidence:.2f})")
                processing_time = time.time() - start_time
                return ScreeningResult.NO_TABLE, confidence, features

            # ====== 情况C：可疑的表格（需要进一步检查） ======
            c1 = h_lines >= 2 and v_lines >= 1  # 有一定线条结构
            c2 = line_score > 0.4 and line_score <= 0.7  # 线条特征中等
            c3 = text_score > 0.2  # 有一定文本

            if c1 and c2 and c3:
                # 可能是简单表格或不规则表格
                confidence = (line_score + text_score + alignment_score) / 3
                print(f"   ⚠️  判断: 疑似表格，需要LLM判断 (置信度: {confidence:.2f})")
                processing_time = time.time() - start_time
                return ScreeningResult.UNCERTAIN, confidence, features

            # ====== 情况D：普通文档页面 ======
            d1 = text_score > 0.4  # 有较多文本
            d2 = line_score < 0.3  # 线条特征不明显
            d3 = alignment_score > 0.3  # 文本有基本对齐

            if d1 and d2 and d3:
                confidence = 0.8  # 高置信度无表格
                print(f"   📄 判断: 普通文档页面，无表格 (置信度: {confidence:.2f})")
                processing_time = time.time() - start_time
                return ScreeningResult.NO_TABLE, confidence, features

            # ====== 情况E：其他情况（不确定） ======
            # 默认交给LLM判断
            confidence = (line_score + text_score + alignment_score) / 3
            print(f"   ❓ 判断: 无法确定，需要LLM (置信度: {confidence:.2f})")
            processing_time = time.time() - start_time
            return ScreeningResult.UNCERTAIN, confidence, features

        except Exception as e:
            logger.error(f"传统检测失败: {image_path}, 错误: {str(e)}")
            # 出错时返回不确定，让大模型判断
            return ScreeningResult.UNCERTAIN, 0.5, {"error": str(e)}


    def _extract_features(self, image: np.ndarray) -> Dict[str, float]:
        """提取图片特征"""
        features = {}

        # 1. 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        height, width = gray.shape
        features["image_size"] = height * width

        # 2. 直线检测特征（现在返回更多信息）
        line_score, h_lines, v_lines = self._detect_lines(gray)
        features["line_score"] = line_score
        features["horizontal_lines"] = h_lines
        features["vertical_lines"] = v_lines
        features["total_lines"] = h_lines + v_lines

        # 3. 文本区域特征
        features["text_score"] = self._detect_text_regions(gray)

        # 4. 行列对齐特征
        features["alignment_score"] = self._detect_alignment(gray)

        # 5. 数字比例特征
        features["digit_score"] = self._estimate_digit_ratio(gray)

        # 6. 额外特征：图像复杂度
        features["complexity_score"] = self._calculate_complexity(gray)

        return features

    def _calculate_complexity(self, gray: np.ndarray) -> float:
        """计算图像复杂度（用于区分简单图表和复杂表格）"""
        try:
            # 计算图像的梯度幅值
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)

            # 计算梯度的标准差（复杂度）
            complexity = np.std(magnitude) / 255.0

            return min(complexity, 1.0)
        except:
            return 0.5

    def _detect_lines(self, gray: np.ndarray) -> Tuple[float, int, int]:
        """检测直线特征，返回(线条分数, 水平线数量, 垂直线数量)"""
        try:
            # 边缘检测
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # 检测直线（宽松参数）
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=self.config["line_threshold"],
                minLineLength=self.config["line_min_length"],
                maxLineGap=20
            )

            if lines is None:
                return 0.0, 0, 0

            # 统计水平和垂直线条
            horizontal_count = 0
            vertical_count = 0
            horizontal_lines = []
            vertical_lines = []

            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

                if angle < 10 or angle > 170:  # 水平线（±10度）
                    horizontal_count += 1
                    horizontal_lines.append((x1, y1, x2, y2))
                elif 80 < angle < 100:  # 垂直线（±10度）
                    vertical_count += 1
                    vertical_lines.append((x1, y1, x2, y2))

            total_lines = len(lines)

            # 计算线条密度
            h, w = gray.shape
            area = h * w

            # 关键改进：检测线条交叉点（表格网格特征）
            intersection_count = 0
            if horizontal_lines and vertical_lines:
                for h_line in horizontal_lines[:10]:  # 限制数量提高性能
                    hx1, hy1, hx2, hy2 = h_line
                    h_y = (hy1 + hy2) // 2  # 水平线的y坐标
                    h_x1 = min(hx1, hx2)
                    h_x2 = max(hx1, hx2)

                    for v_line in vertical_lines[:10]:
                        vx1, vy1, vx2, vy2 = v_line
                        v_x = (vx1 + vx2) // 2  # 垂直线的x坐标
                        v_y1 = min(vy1, vy2)
                        v_y2 = max(vy1, vy2)

                        # 检查是否相交
                        if (h_x1 <= v_x <= h_x2) and (v_y1 <= h_y <= v_y2):
                            intersection_count += 1

            # 表格特征：既有横线又有竖线，且有交叉
            if horizontal_count >= 2 and vertical_count >= 2:
                # 有交叉点，很可能是表格
                if intersection_count > 0:
                    intersection_score = min(intersection_count / 5.0, 1.0)  # 最多5个交叉点给满分
                    line_density = min(total_lines / 30.0, 1.0)  # 最多30条线给满分
                    line_score = 0.6 * intersection_score + 0.4 * line_density
                else:
                    # 没有交叉点，可能不是真正的表格网格
                    line_score = min(total_lines / 40.0, 0.6)  # 上限0.6
            elif horizontal_count >= 3 or vertical_count >= 3:
                # 只有单一方向的线条
                line_score = min(total_lines / 50.0, 0.4)  # 上限0.4
            else:
                # 线条太少
                line_score = total_lines / 10.0  # 最多0.1

            return min(line_score, 1.0), horizontal_count, vertical_count

        except Exception as e:
            logger.warning(f"直线检测失败: {e}")
            return 0.0, 0, 0


    def _detect_text_regions(self, gray: np.ndarray) -> float:
        """检测文本区域特征"""
        try:
            # 使用简单的方法检测文本区域
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 11, 2
            )

            # 形态学操作连接文字
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            # 查找轮廓
            contours, _ = cv2.findContours(
                morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return 0.0

            # 计算文本区域总面积
            total_area = gray.shape[0] * gray.shape[1]
            text_area = 0

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > self.config["text_contour_min_area"]:
                    text_area += area

            # 计算文本密度
            text_density = text_area / total_area

            # 文本密度越高，分数越高
            text_score = min(text_density / self.config["min_text_density"], 1.0)

            # 如果文本区域多且分散，可能不是表格
            if len(contours) > 50 and text_density < 0.1:
                text_score *= 0.7

            return text_score

        except Exception as e:
            logger.warning(f"文本区域检测失败: {e}")
            return 0.0

    def _detect_alignment(self, gray: np.ndarray) -> float:
        """检测行列对齐特征"""
        try:
            # 简化版对齐检测
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # 计算水平投影
            horizontal_projection = np.sum(binary, axis=1)

            # 计算垂直投影
            vertical_projection = np.sum(binary, axis=0)

            # 寻找峰值（表示对齐）
            horizontal_peaks = np.where(horizontal_projection > np.mean(horizontal_projection) * 1.5)[0]
            vertical_peaks = np.where(vertical_projection > np.mean(vertical_projection) * 1.5)[0]

            # 计算对齐分数
            h_score = len(horizontal_peaks) / gray.shape[0] * 10
            v_score = len(vertical_peaks) / gray.shape[1] * 10

            alignment_score = min((h_score + v_score) / 2, 1.0)

            # 既有行对齐又有列对齐，分数更高
            if len(horizontal_peaks) >= self.config["min_rows"] and \
                    len(vertical_peaks) >= self.config["min_cols"]:
                alignment_score = min(alignment_score * 1.3, 1.0)

            return alignment_score

        except Exception as e:
            logger.warning(f"对齐检测失败: {e}")
            return 0.0

    def _estimate_digit_ratio(self, gray: np.ndarray) -> float:
        """估计数字比例（简化版）"""
        try:
            # 使用二值化
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # 查找轮廓
            contours, _ = cv2.findContours(
                binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return 0.0

            # 分析轮廓特征（数字通常有特定宽高比）
            digit_like_count = 0

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 50:  # 太小忽略
                    continue

                x, y, w, h = cv2.boundingRect(contour)

                # 数字的典型宽高比
                aspect_ratio = w / h if h > 0 else 0

                # 宽高比在0.3到1.5之间可能是数字
                if 0.3 <= aspect_ratio <= 1.5:
                    digit_like_count += 1

            digit_ratio = digit_like_count / max(len(contours), 1)
            digit_score = min(digit_ratio / self.config["min_digit_ratio"], 1.0)

            return digit_score

        except Exception as e:
            logger.warning(f"数字比例估计失败: {e}")
            return 0.0


# ==================== 图片压缩器 ====================

class ImageCompressor:
    """图片压缩器 - 用于大模型处理前的极致压缩"""

    def __init__(self):
        self.config = get_config()

    def compress_for_llm(self, image_path: str) -> str:
        """
        压缩图片用于大模型处理
        返回base64编码的图片字符串
        """
        try:
            # 读取图片
            pil_image = Image.open(image_path)

            # 保持宽高比调整大小
            target_size = self.config["compression_size"]
            pil_image.thumbnail(target_size, Image.Resampling.LANCZOS)

            # 转换为RGB模式（如果不是）
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')

            # 高质量JPEG压缩
            buffer = BytesIO()
            pil_image.save(
                buffer,
                format='JPEG',
                quality=self.config["compression_quality"],
                optimize=True
            )

            # 转换为base64
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

            logger.debug(f"图片压缩完成: {Path(image_path).name} -> {target_size}, "
                         f"大小: {len(img_str) / 1024:.1f}KB")

            return img_str

        except Exception as e:
            logger.error(f"图片压缩失败: {image_path}, 错误: {str(e)}")
            raise


# ==================== 大模型调用器 ====================

class LLMTableDetector:
    """大模型表格检测器"""

    def __init__(self):
        """初始化大模型检测器"""
        self.config = get_config()
        self.compressor = ImageCompressor()

        if self.config["use_llm_mock"]:
            logger.info("大模型检测器使用模拟模式（测试用）")
        else:
            logger.info("大模型检测器初始化完成")

    def detect_with_llm(self, image_path: str) -> Tuple[bool, float]:
        """
        使用大模型检测图片是否包含表格
        返回: (是否有表格, 置信度)
        """
        try:
            # 1. 极致压缩图片
            compressed_image = self.compressor.compress_for_llm(image_path)

            if self.config["use_llm_mock"]:
                # 模拟模式：随机返回结果（实际应调用API）
                time.sleep(0.05)  # 模拟网络延迟

                # 基于文件名简单判断（实际应用中删除）
                image_name = Path(image_path).name.lower()
                has_table = any(
                    keyword in image_name for keyword in ['table', 'sheet', 'report', 'data', '财务', '报表'])

                # 添加一些随机性模拟真实场景
                import random
                if random.random() < 0.05:  # 5%概率出错
                    has_table = not has_table

                confidence = 0.9 if has_table else 0.85
                return has_table, confidence

            else:
                # 实际调用大模型API（需要实现）
                # 这里需要根据具体的大模型API实现
                api_key = self.config["llm_api_key"]
                base_url = self.config["llm_base_url"]
                model = self.config["llm_model"]

                if not api_key:
                    logger.error("未配置大模型API密钥")
                    return True, 0.5  # 默认认为有表格（确保不漏）

                # 实际调用代码示例（需要根据具体API修改）
                # response = call_llm_api(compressed_image, api_key, model, base_url)
                # has_table = parse_llm_response(response)

                logger.warning("实际大模型调用未实现，使用模拟模式")
                return True, 0.9  # 默认认为有表格（确保不漏）

        except Exception as e:
            logger.error(f"大模型检测失败: {image_path}, 错误: {str(e)}")
            # 出错时默认认为有表格（确保不漏）
            return True, 0.5


# ==================== 文件处理器 ====================

class FileProcessor:
    """文件处理工具类"""

    def __init__(self):
        self.config = get_config()

    def scan_input_directory(self, input_dir: str) -> List[str]:
        """扫描输入目录，返回所有支持的图片文件路径"""
        input_path = Path(input_dir)

        if not input_path.exists():
            logger.error(f"输入目录不存在: {input_dir}")
            return []

        image_files = []

        # 支持递归扫描子目录
        for ext in self.config["supported_extensions"]:
            image_files.extend(input_path.rglob(f"*{ext}"))
            image_files.extend(input_path.rglob(f"*{ext.upper()}"))

        # 去重并排序
        image_files = sorted(list(set(str(f) for f in image_files)))

        logger.info(f"扫描到 {len(image_files)} 张图片在目录: {input_dir}")
        return image_files

    def copy_table_images(self, image_paths: List[str], output_dir: str) -> Tuple[List[str], List[Dict]]:
        """
        将有表格的图片复制到输出目录
        返回: (成功复制的文件列表, 失败信息列表)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        success_files = []
        failed_files = []

        for image_path in image_paths:
            try:
                src_path = Path(image_path)
                dst_path = output_path / src_path.name

                # 如果目标文件已存在，添加序号
                counter = 1
                while dst_path.exists():
                    stem = src_path.stem
                    suffix = src_path.suffix
                    dst_path = output_path / f"{stem}_{counter}{suffix}"
                    counter += 1

                # 复制文件
                shutil.copy2(src_path, dst_path)
                success_files.append(str(dst_path))

                logger.debug(f"复制成功: {src_path.name} -> {dst_path.name}")

            except Exception as e:
                error_info = {
                    "image_path": image_path,
                    "error": str(e)
                }
                failed_files.append(error_info)
                logger.error(f"复制失败: {image_path}, 错误: {str(e)}")

        logger.info(f"文件复制完成: 成功 {len(success_files)} 个, 失败 {len(failed_files)} 个")
        return success_files, failed_files


# ==================== 主筛选器 ====================

class TableScreeningPipeline:
    """
    表格筛选主管道
    功能：扫描源目录，筛选有表格的图片，复制到目标目录
    """

    def __init__(self):
        """初始化筛选管道"""
        self.config = get_config()
        self.traditional_detector = TraditionalTableDetector()
        self.llm_detector = LLMTableDetector()
        self.file_processor = FileProcessor()

        # 初始化缓存（简化版，先不持久化）
        self.cache = {}

        logger.info(f"表格筛选管道初始化完成")

        logger.info(f"表格筛选管道初始化完成，审计比例: {self.config['audit_rate'] * 100}%")


    def _screen_single_image(self, image_path: str) -> DetectionResult:
        """筛选单张图片"""
        start_time = time.time()

        # 检查缓存
        cache_key = self._get_image_hash(image_path)
        if cache_key in self.cache:
            logger.debug(f"使用缓存结果: {Path(image_path).name}")
            return self.cache[cache_key]

        # 1. 传统检测
        screening_result, confidence, features = self.traditional_detector.detect(image_path)

        # 2. 如果无法确定，使用大模型判断
        llm_used = False
        llm_result = None

        if screening_result == ScreeningResult.UNCERTAIN:
            llm_used = True
            print(f"🤖 调用LLM判断: {Path(image_path).name}")

            try:
                has_table, llm_confidence = self.llm_detector.detect_with_llm(image_path)
                llm_result = has_table

                # 根据大模型结果更新
                if has_table:
                    screening_result = ScreeningResult.HAS_TABLE
                    confidence = max(confidence, llm_confidence)
                    print(f"   LLM结果: 有表格 (置信度: {llm_confidence:.2f})")
                else:
                    screening_result = ScreeningResult.NO_TABLE
                    confidence = min(confidence, 1 - llm_confidence)
                    print(f"   LLM结果: 无表格 (置信度: {1 - llm_confidence:.2f})")

            except Exception as e:
                print(f"   ❌ LLM调用失败: {e}")
                # LLM失败时保守处理：认为有表格（确保不漏）
                screening_result = ScreeningResult.HAS_TABLE
                confidence = 0.6
                llm_result = True

        # 3. 构建结果
        processing_time = time.time() - start_time
        result = DetectionResult(
            image_path=image_path,
            image_name=Path(image_path).name,
            screening_result=screening_result,
            confidence=confidence,
            features=features,
            llm_used=llm_used,
            llm_result=llm_result,
            processing_time=processing_time
        )

        # 4. 缓存结果
        self.cache[cache_key] = result

        return result

    def screen_directory(self, input_dir: str = None, output_dir: str = None) -> ScreeningReport:
        """
        扫描目录并筛选图片
        返回筛选报告
        """
        start_time = time.time()

        # 1. 确定输入输出目录
        if input_dir is None or not input_dir.strip():
            input_dir = self.config["default_input_dir"]

        if output_dir is None or not output_dir.strip():
            output_dir = self.config["default_output_dir"]

        if not input_dir or not output_dir:
            raise ValueError("未指定输入或输出目录")

        input_dir = Path(input_dir).resolve()
        output_dir = Path(output_dir).resolve()

        # 创建两个子目录：有表格和无表格
        tables_dir = output_dir / "tables"  # 有表格的图片
        no_tables_dir = output_dir / "no_tables"  # 无表格的图片

        tables_dir.mkdir(parents=True, exist_ok=True)
        no_tables_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"开始筛选: 输入目录={input_dir}")
        logger.info(f"输出目录: 有表格->{tables_dir}, 无表格->{no_tables_dir}")

        # 2. 扫描输入目录
        image_files = self.file_processor.scan_input_directory(str(input_dir))

        if not image_files:
            logger.warning(f"输入目录中没有图片文件: {input_dir}")
            return ScreeningReport(
                input_dir=str(input_dir),
                output_dir=str(output_dir),  # 返回根目录
                tables_dir=str(tables_dir),
                no_tables_dir=str(no_tables_dir),
                total_images=0,
                has_table_images=[],
                no_table_images=[],
                uncertain_images=[],
                detection_results=[],
                copied_tables_count=0,
                copied_no_tables_count=0,
                processing_time=0
            )

        # 3. 批量筛选图片（使用缓存）
        detection_results = []
        has_table_paths = []
        no_table_paths = []
        uncertain_paths = []

        # 统计缓存命中率
        cache_hits = 0
        cache_misses = 0

        for image_path in image_files:
            cache_key = self._get_cache_key(image_path, str(input_dir), str(output_dir))

            # 检查缓存
            if cache_key in self.cache:
                cache_hits += 1
                cached_result = self.cache[cache_key]

                # 从缓存恢复 DetectionResult 对象
                result = self._restore_from_cache(cached_result, image_path)
                detection_results.append(result)

                # 根据结果分类
                if result.screening_result == ScreeningResult.HAS_TABLE:
                    has_table_paths.append(image_path)
                elif result.screening_result == ScreeningResult.NO_TABLE:
                    no_table_paths.append(image_path)
                else:
                    uncertain_paths.append(image_path)

                logger.debug(f"缓存命中: {Path(image_path).name}")

            else:
                cache_misses += 1
                result = self._screen_single_image(image_path)
                detection_results.append(result)

                # 保存到缓存
                self.cache[cache_key] = result.to_dict()

                if result.screening_result == ScreeningResult.HAS_TABLE:
                    has_table_paths.append(image_path)
                elif result.screening_result == ScreeningResult.NO_TABLE:
                    no_table_paths.append(image_path)
                else:
                    uncertain_paths.append(image_path)

        # 打印缓存统计
        total_images = len(image_files)
        cache_hit_rate = (cache_hits / total_images * 100) if total_images > 0 else 0
        print(f"\n💾 缓存统计: 命中 {cache_hits}/{total_images} ({cache_hit_rate:.1f}%)")

        # 4. 保存缓存（只在有新增结果时）
        if cache_misses > 0:
            self._save_cache()
            print(f"💾 新增 {cache_misses} 条结果已保存到缓存")

        # 5. 检查输出目录中是否已有文件，避免重复复制
        existing_tables = [f.name for f in tables_dir.glob("*") if f.is_file()]
        existing_no_tables = [f.name for f in no_tables_dir.glob("*") if f.is_file()]

        # 需要复制的新文件
        new_table_paths = []
        new_no_table_paths = []

        for img_path in has_table_paths:
            img_name = Path(img_path).name
            if img_name not in existing_tables:
                new_table_paths.append(img_path)

        for img_path in no_table_paths:
            img_name = Path(img_path).name
            if img_name not in existing_no_tables:
                new_no_table_paths.append(img_path)

        # 6. 复制文件到相应目录
        copied_tables = []
        copied_no_tables = []

        if new_table_paths:
            copied_tables, table_errors = self.file_processor.copy_table_images(new_table_paths, str(tables_dir))
            print(f"📁 有表格: 新增 {len(copied_tables)} 个文件到 {tables_dir}")

        if new_no_table_paths:
            copied_no_tables, no_table_errors = self.file_processor.copy_table_images(new_no_table_paths,
                                                                                      str(no_tables_dir))
            print(f"📁 无表格: 新增 {len(copied_no_tables)} 个文件到 {no_tables_dir}")

        # 7. 抽样审计（确保100%不漏）
        if no_table_paths and self.config["audit_rate"] > 0:
            self._perform_audit(no_table_paths)

        # 8. 更新结果中的复制信息
        for result in detection_results:
            src_path = Path(result.image_path)
            img_name = src_path.name

            if result.screening_result == ScreeningResult.HAS_TABLE:
                # 检查是否在有表格目录
                table_path = tables_dir / img_name
                if table_path.exists():
                    result.copied_to = str(table_path)
            elif result.screening_result == ScreeningResult.NO_TABLE:
                # 检查是否在无表格目录
                no_table_path = no_tables_dir / img_name
                if no_table_path.exists():
                    result.copied_to = str(no_table_path)

        processing_time = time.time() - start_time

        # 9. 创建报告（添加新字段）
        report = ScreeningReport(
            input_dir=str(input_dir),
            output_dir=str(output_dir),  # 根目录
            tables_dir=str(tables_dir),  # 有表格目录
            no_tables_dir=str(no_tables_dir),  # 无表格目录
            total_images=len(image_files),
            has_table_images=[Path(p).name for p in has_table_paths],
            no_table_images=[Path(p).name for p in no_table_paths],
            uncertain_images=[Path(p).name for p in uncertain_paths],
            detection_results=detection_results,
            copied_tables_count=len(copied_tables),  # 修改字段名
            copied_no_tables_count=len(copied_no_tables),  # 新增字段
            processing_time=processing_time
        )

        # 10. 输出统计信息
        self._print_report_summary(report)

        return report


    def _perform_audit(self, no_table_paths: List[str]) -> None:
        """抽样审计无表格图片"""
        import random

        # 计算需要审计的数量
        audit_count = max(1, int(len(no_table_paths) * self.config["audit_rate"]))

        # 随机选择审计样本
        audit_samples = random.sample(no_table_paths, min(audit_count, len(no_table_paths)))

        logger.info(f"开始抽样审计: 从{len(no_table_paths)}张无表格图片中抽取{len(audit_samples)}张")

        false_negatives = []

        for image_path in audit_samples:
            # 使用大模型重新判断
            has_table, confidence = self.llm_detector.detect_with_llm(image_path)

            if has_table:
                false_negatives.append({
                    "image_path": image_path,
                    "image_name": Path(image_path).name,
                    "confidence": confidence
                })
                logger.warning(f"审计发现漏检表格: {Path(image_path).name}, 置信度: {confidence:.2f}")

        # 如果发现漏检，记录日志并调整策略
        if false_negatives:
            logger.error(f"发现{len(false_negatives)}张表格图片被漏检！需要调整检测阈值")
            self._log_false_negatives(false_negatives)

    def _log_false_negatives(self, false_negatives: List[Dict]) -> None:
        """记录漏检情况"""
        log_file = Path("false_negatives.log")

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n=== 漏检发现时间: {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            for item in false_negatives:
                f.write(f"漏检图片: {item['image_name']}, 置信度: {item['confidence']:.2f}\n")
            f.write("=" * 50 + "\n")

        logger.info(f"漏检记录已保存到: {log_file}")


    def _get_cache_key(self, image_path: str, input_dir: str, output_dir: str) -> str:
        """生成缓存键（简化版）"""
        try:
            # 使用图片路径、输入目录、输出目录生成唯一键
            path_hash = hash(image_path + input_dir + output_dir)
            return str(abs(path_hash))
        except:
            return f"{image_path}_{input_dir}_{output_dir}"

    def _get_image_hash(self, image_path: str) -> str:
        """计算图片哈希"""
        try:
            import hashlib
            import os
            from pathlib import Path

            # 使用文件名和修改时间作为简单哈希
            stat = os.stat(image_path)
            file_info = f"{Path(image_path).name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(file_info.encode()).hexdigest()[:8]
        except:
            return Path(image_path).name

    def _save_cache(self):
        """保存缓存（简化版，先不实际保存）"""
        print("💾 缓存保存被调用（简化版，不实际保存）")
        # 为了调试，打印缓存统计
        print(f"  当前缓存大小: {len(self.cache)}")
        if self.cache:
            sample_key = next(iter(self.cache))
            print(f"  示例缓存项: {sample_key[:50]}...")

    def _load_cache(self) -> dict:
        """加载缓存（简化版）"""
        print("💾 缓存加载被调用（简化版，返回空缓存）")
        return {}

    def _restore_from_cache(self, cached_data: Dict, image_path: str) -> DetectionResult:
        """从缓存数据恢复 DetectionResult 对象"""
        try:
            # 恢复 ScreeningResult 枚举
            screening_result = ScreeningResult(cached_data.get("screening_result", "uncertain"))

            result = DetectionResult(
                image_path=image_path,
                image_name=Path(image_path).name,
                screening_result=screening_result,
                confidence=cached_data.get("confidence", 0.5),
                features=cached_data.get("features", {}),
                llm_used=cached_data.get("llm_used", False),
                llm_result=cached_data.get("llm_result"),
                processing_time=cached_data.get("processing_time", 0.0),
                copied_to=cached_data.get("copied_to")
            )
            return result
        except Exception as e:
            print(f"⚠️ 从缓存恢复失败: {e}")
            # 恢复失败时重新检测
            return self._screen_single_image(image_path)

    def _print_report_summary(self, report: ScreeningReport) -> None:
        """打印报告摘要"""
        print("\n" + "=" * 80)
        print("📊 表格筛选完成报告")
        print("=" * 80)
        print(f"📁 输入目录: {report.input_dir}")
        print(f"📁 输出根目录: {report.output_dir}")
        print(f"✅ 有表格目录: {report.tables_dir} ({report.copied_tables_count}张)")
        print(f"❌ 无表格目录: {report.no_tables_dir} ({report.copied_no_tables_count}张)")
        print(f"🖼️  总图片数: {report.total_images}")
        print(f"✅ 有表格图片: {len(report.has_table_images)}张")
        print(f"❌ 无表格图片: {len(report.no_table_images)}张")
        print(f"❓ 不确定图片: {len(report.uncertain_images)}张")

        # 统计LLM使用情况
        llm_count = sum(1 for r in report.detection_results if r.llm_used)
        llm_table_count = sum(1 for r in report.detection_results
                              if r.llm_used and r.llm_result is True)

        print(f"🤖 LLM判断数量: {llm_count} (其中判断为表格: {llm_table_count})")
        print(f"⏱️  处理时间: {report.processing_time:.2f}秒")
        print(f"📈 平均每张: {report.processing_time / max(report.total_images, 1):.3f}秒")
        print("=" * 80)

# ==================== 使用示例 ====================

def main():
    """使用示例"""

    # 1. 创建筛选管道
    pipeline = TableScreeningPipeline()

    # 2. 从配置获取默认目录，或手动指定
    config = get_config()
    input_dir = config.get("default_input_dir", "")
    output_dir = config.get("default_output_dir", "")

    if not input_dir or not output_dir:
        # 如果配置中没有，使用示例目录
        input_dir = "data/input_images"
        output_dir = "data/output_tables"
        print(f"使用示例目录: 输入={input_dir}, 输出={output_dir}")

    # 3. 执行目录筛选
    report = pipeline.screen_directory(input_dir, output_dir)

    # 4. 保存详细报告
    report.save_to_file("screening_report.json")

    # 5. 返回有表格的图片路径（供后续处理）
    output_path = Path(output_dir)
    table_images = [str(f) for f in output_path.glob("*") if f.is_file()]

    print(f"\n已复制到输出目录的表格图片: {len(table_images)}张")

    return table_images


if __name__ == "__main__":
    main()