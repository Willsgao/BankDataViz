import cv2
import numpy as np
from typing import Tuple


class MorphologyTableDetector:
    """基于图像形态学的表格检测"""

    def __init__(self):
        # 形态学核
        self.kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        self.kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
        self.kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    def detect(self, image_path: str) -> bool:
        """检测图片中是否有表格"""
        try:
            # 1. 读取并预处理
            img = cv2.imread(image_path)
            if img is None:
                return True  # 保守处理

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            # 2. 自适应二值化
            binary = cv2.adaptiveThreshold(gray, 255,
                                           cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY_INV, 11, 2)

            # 3. 形态学操作提取表格线
            # 提取水平线
            horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                          self.kernel_horizontal, iterations=2)

            # 提取垂直线
            vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                        self.kernel_vertical, iterations=2)

            # 4. 计算线条密度
            horizontal_density = np.sum(horizontal > 0) / (h * w)
            vertical_density = np.sum(vertical > 0) / (h * w)

            # 5. 检测闭合矩形（表格单元格）
            table_mask = cv2.bitwise_or(horizontal, vertical)
            dilated = cv2.dilate(table_mask, self.kernel_small, iterations=1)

            # 查找轮廓（查找闭合区域）
            contours, _ = cv2.findContours(dilated, cv2.RETR_TREE,
                                           cv2.CHAIN_APPROX_SIMPLE)

            # 6. 判断标准
            has_horizontal_lines = horizontal_density > 0.002  # 水平线密度阈值
            has_vertical_lines = vertical_density > 0.002  # 垂直线密度阈值
            has_closed_cells = len(contours) > 5  # 闭合区域数量

            # 表格特征：既有水平垂直线，又有闭合单元格
            is_table = (has_horizontal_lines and has_vertical_lines) or \
                       (has_closed_cells and (has_horizontal_lines or has_vertical_lines))

            return is_table

        except Exception as e:
            print(f"Morphology检测错误: {e}")
            return True


class HoughProjectionTableDetector:
    """基于霍夫变换和投影分析的表格检测"""

    def __init__(self):
        self.hough_threshold = 80
        self.min_line_length = 30
        self.max_line_gap = 20

    def detect(self, image_path: str) -> bool:
        """检测图片中是否有表格"""
        try:
            # 1. 读取并预处理
            img = cv2.imread(image_path)
            if img is None:
                return True

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            # 2. 边缘检测
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # 3. 霍夫直线检测
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                                    threshold=self.hough_threshold,
                                    minLineLength=self.min_line_length,
                                    maxLineGap=self.max_line_gap)

            if lines is None or len(lines) < 5:
                return False  # 线条太少，不可能是表格

            # 4. 分析直线方向
            horizontal_lines = 0
            vertical_lines = 0
            line_lengths = []

            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                line_lengths.append(length)

                # 计算角度
                if x2 - x1 == 0:
                    angle = 90
                else:
                    angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

                # 判断水平或垂直
                if angle < 15 or angle > 165:  # 水平线
                    horizontal_lines += 1
                elif 75 < angle < 105:  # 垂直线
                    vertical_lines += 1

            # 5. 投影分析（检测网格状结构）
            # 水平投影
            horizontal_proj = np.sum(edges, axis=1)
            vertical_proj = np.sum(edges, axis=0)

            # 检测投影的峰值（表格线的特征）
            h_peaks = self._find_peaks(horizontal_proj, min_distance=10)
            v_peaks = self._find_peaks(vertical_proj, min_distance=10)

            # 6. 判断标准
            has_enough_lines = horizontal_lines >= 2 and vertical_lines >= 2
            has_grid_structure = len(h_peaks) >= 3 and len(v_peaks) >= 3
            avg_line_length = np.mean(line_lengths) if line_lengths else 0

            # 表格特征：有交叉的直线，并且有网格状结构
            is_table = has_enough_lines and has_grid_structure and avg_line_length > 20

            return is_table

        except Exception as e:
            print(f"Hough检测错误: {e}")
            return True

    def _find_peaks(self, signal: np.ndarray, min_distance: int = 10) -> list:
        """查找信号峰值"""
        peaks = []
        for i in range(1, len(signal) - 1):
            if signal[i] > signal[i - 1] and signal[i] > signal[i + 1] and signal[i] > 10:
                # 检查与已有峰值的距离
                if not peaks or (i - peaks[-1]) > min_distance:
                    peaks.append(i)
        return peaks


class ConnectedComponentsTableDetector:
    """基于连通区域和结构分析的表格检测"""

    def __init__(self):
        self.min_cell_area_ratio = 0.0005  # 单元格最小面积占比
        self.max_cell_area_ratio = 0.05  # 单元格最大面积占比

    def detect(self, image_path: str) -> bool:
        """检测图片中是否有表格"""
        try:
            # 1. 读取并预处理
            img = cv2.imread(image_path)
            if img is None:
                return True

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            img_area = h * w

            # 2. 二值化
            _, binary = cv2.threshold(gray, 0, 255,
                                      cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # 3. 形态学操作，增强表格结构
            kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
            kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))

            horizontal = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_h)
            vertical = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_v)

            table_structure = cv2.bitwise_or(horizontal, vertical)

            # 4. 查找连通区域（潜在的表格单元格）
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                table_structure, connectivity=8
            )

            if num_labels < 2:  # 只有背景
                return False

            # 5. 分析连通区域特征
            cell_count = 0
            cell_areas = []
            cell_aspect_ratios = []

            for i in range(1, num_labels):  # 跳过背景
                x, y, cell_w, cell_h, area = stats[i]

                # 过滤过大或过小的区域
                area_ratio = area / img_area
                if self.min_cell_area_ratio < area_ratio < self.max_cell_area_ratio:
                    # 计算宽高比（表格单元格通常有特定比例）
                    aspect_ratio = cell_w / cell_h if cell_h > 0 else 0

                    cell_count += 1
                    cell_areas.append(area)
                    cell_aspect_ratios.append(aspect_ratio)

            # 6. 检测矩形排列（表格特征）
            has_grid_layout = self._detect_grid_layout(labels, cell_count)

            # 7. 判断标准
            has_enough_cells = cell_count >= 6
            has_uniform_cells = False

            if cell_areas:
                # 检查单元格面积的一致性（表格通常有均匀的单元格）
                area_std = np.std(cell_areas) / np.mean(cell_areas) if np.mean(cell_areas) > 0 else 1
                has_uniform_cells = area_std < 0.8  # 面积变化不大

            # 表格特征：有多个单元格，排列成网格状，面积相对均匀
            is_table = has_enough_cells and has_grid_layout and has_uniform_cells

            return is_table

        except Exception as e:
            print(f"连通区域检测错误: {e}")
            return True

    def _detect_grid_layout(self, labels: np.ndarray, cell_count: int) -> bool:
        """检测网格状排列"""
        if cell_count < 4:
            return False

        # 提取所有非零像素的坐标
        rows, cols = np.where(labels > 0)

        if len(rows) < 10:
            return False

        # 计算行和列的直方图（网格会有明显的峰值）
        row_hist = np.histogram(rows, bins=10)[0]
        col_hist = np.histogram(cols, bins=10)[0]

        # 检查是否有明显的行和列模式
        row_peaks = np.sum(row_hist > np.mean(row_hist) * 1.5)
        col_peaks = np.sum(col_hist > np.mean(col_hist) * 1.5)

        # 网格结构应该有明显的行和列
        return row_peaks >= 3 and col_peaks >= 3


class TripleFastTableDetector:
    """三重快速表格检测器"""

    def __init__(self):
        self.detectors = [
            MorphologyTableDetector(),  # 形态学方法
            HoughProjectionTableDetector(),  # 霍夫变换方法
            ConnectedComponentsTableDetector()  # 连通区域方法
        ]

    def detect_with_voting(self, image_path: str, threshold: int = 2) -> Tuple[bool, list]:
        """
        三重投票检测
        threshold: 认为无表格的阈值（需要多少个检测器认为无表格）
        """
        results = []

        for i, detector in enumerate(self.detectors):
            try:
                has_table = detector.detect(image_path)
                results.append(has_table)
                print(f"检测器{i + 1}: {'有表格' if has_table else '无表格'}")
            except Exception as e:
                print(f"检测器{i + 1}出错: {e}")
                results.append(True)  # 出错时保守处理

        # 统计投票
        yes_votes = sum(results)
        no_votes = len(results) - yes_votes

        # 决策：只有大多数检测器认为无表格才排除
        final_decision = no_votes < threshold  # 认为有表格

        return final_decision, results

    def batch_detect(self, image_paths: list, threshold: int = 2) -> Tuple[list, list]:
        """批量检测"""
        table_images = []
        non_table_images = []

        for img_path in image_paths:
            print(f"\n检测: {img_path}")
            has_table, results = self.detect_with_voting(img_path, threshold)

            if has_table:
                table_images.append((img_path, results))
                print(f"结论: 可能有表格")
            else:
                non_table_images.append((img_path, results))
                print(f"结论: 无表格")

        print(f"\n检测完成!")
        print(f"可能有表格: {len(table_images)} 张")
        print(f"无表格: {len(non_table_images)} 张")

        return table_images, non_table_images


# 使用示例
if __name__ == "__main__":
    import glob

    # 初始化检测器
    detector = TripleFastTableDetector()

    # 获取图片列表
    image_paths = glob.glob("images/*.jpg") + glob.glob("images/*.png")

    # 批量检测
    table_images, non_table_images = detector.batch_detect(image_paths[:10], threshold=2)

    # 输出结果
    print("\n可能有表格的图片:")
    for img_path, _ in table_images:
        print(f"  {img_path}")

    print("\n无表格的图片:")
    for img_path, _ in non_table_images:
        print(f"  {img_path}")