import pandas as pd
import json
from collections import defaultdict
import numpy as np


def load_ocr_data_from_json(json_file_path):
    """从JSON文件加载OCR数据"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"读取文件错误: {e}")
        return None


def cluster_positions(positions, threshold=20):
    """对位置进行聚类，将相近的位置归为同一组"""
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

    # 返回每个聚类的中心位置
    return [int(np.mean(cluster)) for cluster in clusters]


def build_table_structure(words_data, row_threshold=15, col_threshold=50):
    """基于坐标构建表格结构"""

    # 提取所有位置信息
    top_positions = [item['location']['top'] for item in words_data]
    left_positions = [item['location']['left'] for item in words_data]

    # 对行列位置进行聚类
    row_clusters = cluster_positions(top_positions, row_threshold)
    col_clusters = cluster_positions(left_positions, col_threshold)

    # 创建空的表格结构
    table = [['' for _ in range(len(col_clusters))] for _ in range(len(row_clusters))]

    # 将数据填充到表格中
    for item in words_data:
        top = item['location']['top']
        left = item['location']['left']
        words = item['words']

        # 找到最接近的行索引
        row_idx = min(range(len(row_clusters)), key=lambda i: abs(row_clusters[i] - top))
        # 找到最接近的列索引
        col_idx = min(range(len(col_clusters)), key=lambda i: abs(col_clusters[i] - left))

        # 填充数据（如果该位置已有数据，则追加）
        if table[row_idx][col_idx]:
            table[row_idx][col_idx] += ' ' + words
        else:
            table[row_idx][col_idx] = words

    return table, row_clusters, col_clusters


def advanced_table_detection(words_data):
    """更高级的表格检测算法"""

    # 按行分组
    rows_dict = defaultdict(list)
    for item in words_data:
        top = item['location']['top']
        rows_dict[top].append(item)

    # 对每行按left排序
    for top in rows_dict:
        rows_dict[top].sort(key=lambda x: x['location']['left'])

    # 获取所有行并按top排序
    sorted_tops = sorted(rows_dict.keys())

    # 动态检测列位置
    all_left_positions = []
    for items in rows_dict.values():
        for item in items:
            all_left_positions.append(item['location']['left'])

    # 使用更精确的列聚类
    unique_left_positions = sorted(set(all_left_positions))
    col_boundaries = []

    if unique_left_positions:
        col_boundaries.append(unique_left_positions[0])
        for i in range(1, len(unique_left_positions)):
            if unique_left_positions[i] - unique_left_positions[i - 1] > 30:  # 列间距阈值
                col_boundaries.append(unique_left_positions[i])

    # 构建表格
    table = []
    for top in sorted_tops:
        items = rows_dict[top]
        row_data = [''] * len(col_boundaries)

        for item in items:
            left = item['location']['left']
            words = item['words']

            # 找到对应的列索引
            col_idx = 0
            min_distance = float('inf')
            for i, boundary in enumerate(col_boundaries):
                distance = abs(left - boundary)
                if distance < min_distance and distance < 80:  # 列匹配阈值
                    min_distance = distance
                    col_idx = i

            if min_distance < 80:  # 确保在合理范围内
                if row_data[col_idx]:
                    row_data[col_idx] += ' ' + words
                else:
                    row_data[col_idx] = words

        # 跳过完全空的行
        if any(cell.strip() for cell in row_data):
            table.append(row_data)

    return table


def save_table_to_excel(table_data, output_file):
    """将表格数据保存为Excel"""
    try:
        df = pd.DataFrame(table_data)

        # 自动检测表头（第一行如果包含数字，可能不是表头）
        has_numbers_in_first_row = any(any(char.isdigit() for char in str(cell)) for cell in table_data[0])

        if not has_numbers_in_first_row and len(table_data) > 1:
            # 使用第一行作为列名
            df.columns = table_data[0]
            df = df[1:]  # 移除第一行
        else:
            # 生成默认列名
            df.columns = [f'Column_{i + 1}' for i in range(len(table_data[0]))]

        df.to_excel(output_file, index=False)
        print(f"表格已保存为: {output_file}")
        return df
    except Exception as e:
        print(f"保存Excel时出错: {e}")
        return None


def process_ocr_json_to_excel(json_file_path, output_file=None):
    """主处理函数：从JSON文件读取OCR数据并转换为Excel"""

    # 加载数据
    ocr_data = load_ocr_data_from_json(json_file_path)
    if not ocr_data:
        return None

    words_data = ocr_data.get('words_result', [])
    if not words_data:
        print("没有找到有效的数据")
        return None

    print(f"处理 {len(words_data)} 个数据项...")

    # 方法1：使用高级表格检测
    print("使用高级表格检测算法...")
    table_data = advanced_table_detection(words_data)

    # 如果方法1结果不理想，使用方法2
    if len(table_data) < 2:
        print("方法1结果不理想，尝试基础方法...")
        table_data, _, _ = build_table_structure(words_data)

    if table_data and len(table_data) > 0:
        print(f"检测到表格: {len(table_data)} 行 x {len(table_data[0])} 列")

        # 显示前几行预览
        for i, row in enumerate(table_data[:3]):
            print(f"行 {i}: {row}")

        # 保存为Excel
        df = save_table_to_excel(table_data, output_file)
        return df
    else:
        print("未能检测到有效的表格结构")
        return None


# 批量处理函数
import os
def batch_process_ocr_files(json_folder, output_folder=None):
    """批量处理多个JSON文件"""
    import glob

    if not output_folder:
        output_folder = json_folder

    json_files = glob.glob(os.path.join(json_folder, "*.json"))

    results = []
    for json_file in json_files:
        print(f"\n处理文件: {json_file}")
        output_file = os.path.join(output_folder,
                                   f"{os.path.splitext(os.path.basename(json_file))[0]}.xlsx")

        df = process_ocr_json_to_excel(json_file, output_file)
        if df is not None:
            results.append((json_file, output_file, df.shape))

    print(f"\n批量处理完成! 成功处理 {len(results)} 个文件")
    return results


# 使用示例
if __name__ == "__main__":
    # 单个文件处理
    json_file_path = "data1.json"  # 替换为您的JSON文件路径
    output_file = "OCR_结果_3.xlsx"
    df = process_ocr_json_to_excel(json_file_path, output_file)

    # 批量处理（取消注释使用）
    results = batch_process_ocr_files("path/to/json/folder")
    {
        "code": 1001,
        "log_id": "1993548000500162560",
        "message": "Create task successfully!",
        "result": {
            "task_id": "QNngaThB"
        },
        "success": true
    }
