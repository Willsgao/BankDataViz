import pandas as pd
import json
import numpy as np
from collections import defaultdict
from sklearn.cluster import DBSCAN
import re
from typing import List, Dict, Any, Tuple


class RobustTableExtractor:
    """
    鲁棒表格提取器 - 针对缺失表格线的OCR数据进行表格重建
    结合多维度密度聚类和基于对齐模式的区域检测
    """

    def __init__(self, row_threshold=15, col_threshold=50, min_table_elements=10):
        """
        初始化参数
        Args:
            row_threshold: 行聚类阈值(像素)
            col_threshold: 列聚类阈值(像素)
            min_table_elements: 最小表格元素数量
        """
        self.row_threshold = row_threshold
        self.col_threshold = col_threshold
        self.min_table_elements = min_table_elements

    def load_ocr_data(self, json_file_path: str) -> List[Dict]:
        """
        从JSON文件加载OCR数据
        Args:
            json_file_path: JSON文件路径
        Returns:
            OCR数据列表
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                ocr_data = json.load(file)
            words_data = ocr_data.get('words_result', [])
            print(f"成功加载 {len(words_data)} 个OCR数据项")
            return words_data
        except Exception as e:
            print(f"加载OCR数据失败: {e}")
            return []

    def extract_text_features(self, text: str) -> Dict[str, Any]:
        """
        提取文本特征用于聚类
        Args:
            text: 输入文本
        Returns:
            文本特征字典
        """
        # 清理文本
        cleaned_text = re.sub(r'[\(\)\.,;，。；]', '', text.strip())

        # 特征提取
        features = {
            'is_numeric': bool(re.match(r'^[-+]?[0-9]*\.?[0-9]+$', cleaned_text)),
            'is_percentage': '%' in text,
            'is_money': any(char in text for char in ['¥', '$', '€', '￥']),
            'has_parentheses': '(' in text and ')' in text,
            'text_length': len(cleaned_text),
            'digit_ratio': sum(c.isdigit() for c in cleaned_text) / len(cleaned_text) if cleaned_text else 0,
            'has_chinese': bool(re.search(r'[\u4e00-\u9fff]', text)),
        }
        return features

    def multi_dimension_clustering(self, words_data: List[Dict]) -> List[Dict]:
        """
        方案1: 多维度密度聚类 + 结构一致性验证
        Args:
            words_data: OCR数据
        Returns:
            过滤后的表格元素
        """
        if len(words_data) < self.min_table_elements:
            return words_data

        print("开始多维度密度聚类...")

        # 准备三维特征: [x_center, y_center, feature_score]
        features = []
        feature_weights = []

        for item in words_data:
            # 位置特征
            bbox = item['location']
            x_center = bbox['left'] + bbox['width'] / 2
            y_center = bbox['top'] + bbox['height'] / 2

            # 文本特征
            text_features = self.extract_text_features(item['words'])

            # 特征评分 (表格区域通常有特定的特征组合)
            feature_score = 0
            feature_score += 2 if text_features['is_numeric'] else 0
            feature_score += 1 if text_features['has_parentheses'] else 0
            feature_score += 0.5 if text_features['digit_ratio'] > 0.3 else 0
            feature_score -= 1 if text_features['has_chinese'] and text_features['text_length'] > 8 else 0

            features.append([x_center, y_center, feature_score])
            feature_weights.append(feature_score)

        features = np.array(features)

        # 使用DBSCAN进行密度聚类
        # 调整参数以适应不同的表格密度
        clustering = DBSCAN(
            eps=80,  # 邻域半径
            min_samples=3  # 最小样本数
        ).fit(features)

        labels = clustering.labels_

        # 分析聚类结果
        unique_labels, counts = np.unique(labels[labels >= 0], return_counts=True)

        if len(unique_labels) == 0:
            print("未找到有效聚类，返回所有数据")
            return words_data

        # 选择主要聚类 (基于元素数量和特征质量)
        cluster_scores = []
        for label in unique_labels:
            cluster_indices = np.where(labels == label)[0]
            cluster_size = len(cluster_indices)

            # 计算聚类质量分数 (大小 + 平均特征分)
            avg_feature_score = np.mean([feature_weights[i] for i in cluster_indices])
            cluster_score = cluster_size * (1 + avg_feature_score)
            cluster_scores.append((label, cluster_score))

        # 选择最佳聚类
        best_label = max(cluster_scores, key=lambda x: x[1])[0]

        # 提取主要聚类中的元素
        table_elements = [words_data[i] for i in range(len(words_data))
                          if labels[i] == best_label]

        print(f"多维度聚类后保留 {len(table_elements)} 个元素")
        return table_elements

    def detect_column_boundaries(self, words_data: List[Dict]) -> List[float]:
        """
        方案2: 基于对齐模式的列边界检测
        Args:
            words_data: OCR数据
        Returns:
            检测到的列边界位置列表
        """
        print("开始列边界检测...")

        # 收集所有左边界和右边界位置
        left_positions = []
        right_positions = []

        for item in words_data:
            bbox = item['location']
            left_positions.append(bbox['left'])
            right_positions.append(bbox['left'] + bbox['width'])

        # 对位置进行聚类以找到常见的列边界
        def cluster_positions(positions, threshold=20):
            if not positions:
                return []
            positions = sorted(positions)
            clusters = []
            current_cluster = [positions[0]]

            for pos in positions[1:]:
                if pos - current_cluster[-1] <= threshold:
                    current_cluster.append(pos)
                else:
                    clusters.append(current_cluster)
                    current_cluster = [pos]

            if current_cluster:
                clusters.append(current_cluster)

            return [np.mean(cluster) for cluster in clusters]

        # 检测左边界和右边界的聚集点
        left_clusters = cluster_positions(left_positions, self.col_threshold)
        right_clusters = cluster_positions(right_positions, self.col_threshold)

        # 合并左右边界，形成列分隔线
        all_boundaries = sorted(left_clusters + right_clusters)

        # 过滤掉过于接近的边界
        filtered_boundaries = []
        for boundary in all_boundaries:
            if not filtered_boundaries or boundary - filtered_boundaries[-1] > 30:
                filtered_boundaries.append(boundary)

        print(f"检测到 {len(filtered_boundaries)} 个列边界: {filtered_boundaries}")
        return filtered_boundaries

    def detect_row_structure(self, words_data: List[Dict]) -> List[float]:
        """
        检测行结构
        Args:
            words_data: OCR数据
        Returns:
            行中心位置列表
        """
        # 收集所有行的垂直中心位置
        y_centers = []
        for item in words_data:
            bbox = item['location']
            y_center = bbox['top'] + bbox['height'] / 2
            y_centers.append(y_center)

        # 对行位置进行聚类
        y_centers = sorted(y_centers)
        row_clusters = []
        current_cluster = [y_centers[0]]

        for y in y_centers[1:]:
            if y - current_cluster[-1] <= self.row_threshold:
                current_cluster.append(y)
            else:
                row_clusters.append(current_cluster)
                current_cluster = [y]

        if current_cluster:
            row_clusters.append(current_cluster)

        # 返回每行的平均中心位置
        row_centers = [np.mean(cluster) for cluster in row_clusters]
        print(f"检测到 {len(row_centers)} 行")
        return row_centers

    def build_table_from_alignment(self, words_data: List[Dict]) -> List[List[str]]:
        """
        基于对齐模式重建表格
        Args:
            words_data: 过滤后的表格元素
        Returns:
            重建的表格数据
        """
        print("基于对齐模式重建表格...")

        # 检测列边界和行结构
        column_boundaries = self.detect_column_boundaries(words_data)
        row_centers = self.detect_row_structure(words_data)

        if not column_boundaries or not row_centers:
            print("无法检测到有效的表格结构")
            return []

        # 创建空的表格结构
        table = [['' for _ in range(len(column_boundaries))]
                 for _ in range(len(row_centers))]

        # 将元素分配到表格单元格中
        for item in words_data:
            bbox = item['location']
            x_center = bbox['left'] + bbox['width'] / 2
            y_center = bbox['top'] + bbox['height'] / 2

            # 找到对应的行
            row_idx = min(range(len(row_centers)),
                          key=lambda i: abs(row_centers[i] - y_center))

            # 找到对应的列
            col_idx = min(range(len(column_boundaries)),
                          key=lambda i: abs(column_boundaries[i] - x_center))

            # 将文本分配到单元格（处理合并单元格情况）
            if not table[row_idx][col_idx]:
                table[row_idx][col_idx] = item['words']
            else:
                # 如果单元格已有内容，追加（可能是同一单元格的多个文本块）
                table[row_idx][col_idx] += ' ' + item['words']

        return table

    def validate_table_structure(self, table: List[List[str]]) -> bool:
        """
        验证表格结构的合理性
        Args:
            table: 重建的表格
        Returns:
            是否合理的表格
        """
        if not table or len(table) < 2:
            return False

        # 检查行的一致性（每行应该有相似数量的非空单元格）
        non_empty_counts = [sum(1 for cell in row if cell.strip()) for row in table]
        avg_non_empty = np.mean(non_empty_counts)

        # 如果大多数行都远低于平均非空单元格数，可能不是有效表格
        if avg_non_empty < 2:
            return False

        # 检查列的一致性
        col_counts = []
        for col_idx in range(len(table[0])):
            non_empty_in_col = sum(1 for row in table if row[col_idx].strip())
            col_counts.append(non_empty_in_col)

        # 至少应该有2列有较多数据
        if sum(1 for count in col_counts if count > len(table) * 0.3) < 2:
            return False

        return True

    def extract_table(self, json_file_path: str, output_file: str = None) -> pd.DataFrame:
        """
        主函数：从OCR JSON数据中提取表格
        Args:
            json_file_path: 输入JSON文件路径
            output_file: 输出Excel文件路径
        Returns:
            提取的表格DataFrame
        """
        print("开始表格提取流程...")

        # 1. 加载原始数据
        words_data = self.load_ocr_data(json_file_path)
        if not words_data:
            print("没有可处理的数据")
            return None

        # 2. 多维度密度聚类过滤
        filtered_elements = self.multi_dimension_clustering(words_data)

        if len(filtered_elements) < self.min_table_elements:
            print(f"过滤后元素数量({len(filtered_elements)})不足，尝试使用原始数据")
            filtered_elements = words_data

        # 3. 基于对齐模式重建表格
        table_data = self.build_table_from_alignment(filtered_elements)

        if not table_data:
            print("表格重建失败")
            return None

        # 4. 验证表格结构
        if not self.validate_table_structure(table_data):
            print("表格结构验证失败，但继续处理")

        # 5. 创建DataFrame并保存
        try:
            # 尝试自动识别表头
            df = self.auto_detect_header(table_data)

            if output_file:
                df.to_excel(output_file, index=False)
                print(f"表格已保存至: {output_file}")

            return df

        except Exception as e:
            print(f"创建DataFrame失败: {e}")
            return None

    def auto_detect_header(self, table_data: List[List[str]]) -> pd.DataFrame:
        """
        自动检测表头
        Args:
            table_data: 表格数据
        Returns:
            带有正确表头的DataFrame
        """
        if len(table_data) < 2:
            return pd.DataFrame(table_data)

        # 分析第一行的特征
        first_row = table_data[0]
        first_row_features = []

        for cell in first_row:
            features = self.extract_text_features(cell)
            # 表头通常包含较多中文，较少数字
            header_score = features['has_chinese'] - features['digit_ratio']
            first_row_features.append(header_score)

        avg_header_score = np.mean(first_row_features)

        # 如果第一行看起来像表头，则使用它作为列名
        if avg_header_score > 0.3 and len(table_data) > 1:
            df = pd.DataFrame(table_data[1:], columns=first_row)
        else:
            df = pd.DataFrame(table_data)
            # 生成默认列名
            df.columns = [f'列_{i + 1}' for i in range(len(table_data[0]))]

        return df


# 使用示例
if __name__ == "__main__":
    # 初始化提取器
    extractor = RobustTableExtractor(
        row_threshold=15,
        col_threshold=50,
        min_table_elements=8
    )

    # 提取表格
    json_file_path = "data1.json"  # 替换为实际文件路径
    output_file = "OCR_区域结果_1.xlsx"

    df = extractor.extract_table(json_file_path, output_file)

    if df is not None:
        print("表格提取成功!")
        print(f"表格形状: {df.shape}")
        print("\n前5行数据:")
        print(df.head())
    else:
        print("表格提取失败")