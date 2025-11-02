# backend/api/visualization_api.py
import os
import pandas as pd
import numpy as np
import json
from flask import Blueprint, request, jsonify
from pathlib import Path
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 创建蓝图
visualization_bp = Blueprint('visualization', __name__)


def convert_excel_url_to_path(excel_url):
    """
    将Excel URL转换为本地文件路径
    """
    try:
        # 移除URL前缀，获取相对路径
        if excel_url.startswith('/api/excel-data/'):
            relative_path = excel_url.replace('/api/excel-data/', 'static/excel_data/')
        elif excel_url.startswith('/static/excel_data/'):
            relative_path = excel_url.replace('/static/excel_data/', 'static/excel_data/')
        else:
            # 如果已经是相对路径，直接使用
            relative_path = excel_url

        # 清理查询参数
        if '?' in relative_path:
            relative_path = relative_path.split('?')[0]

        # 构建完整路径
        file_path = Path(relative_path)

        # 如果文件不存在，尝试在项目根目录查找
        if not file_path.exists():
            file_path = Path(".") / relative_path

        logger.info(f"Excel文件路径转换: {excel_url} -> {file_path}")
        return str(file_path)

    except Exception as e:
        logger.error(f"Excel路径转换失败: {e}")
        return None


@visualization_bp.route('/api/visualization/data', methods=['GET'])
def get_visualization_data():
    """
    获取可视化分析数据
    """
    try:
        excel_url = request.args.get('excel_url')
        if not excel_url:
            return jsonify({
                "success": False,
                "error": "缺少excel_url参数"
            }), 400

        # 转换URL为文件路径
        file_path = convert_excel_url_to_path(excel_url)

        if not file_path or not os.path.exists(file_path):
            return jsonify({
                "success": False,
                "error": f"Excel文件不存在: {file_path}"
            }), 404

        logger.info(f"开始生成可视化数据: {file_path}")

        # 生成可视化数据
        visualization_data = generate_visualization_data(file_path)

        return jsonify({
            "success": True,
            "data": visualization_data
        })

    except Exception as e:
        logger.error(f"生成可视化数据失败: {e}")
        return jsonify({
            "success": False,
            "error": f"生成可视化数据失败: {str(e)}"
        }), 500


def generate_visualization_data(file_path):
    """
    生成前端可视化所需的数据
    """
    try:
        # 读取Excel文件的所有工作表
        excel_data = pd.read_excel(file_path, sheet_name=None)
        result = {}

        for sheet_name, df in excel_data.items():
            logger.info(f"处理工作表: {sheet_name}, 形状: {df.shape}")

            # 清理数据：移除完全为空的行和列
            df_clean = df.dropna(how='all').dropna(axis=1, how='all')

            # 基础统计信息
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
            categorical_cols = df_clean.select_dtypes(include=['object']).columns.tolist()

            # 数值列统计
            numeric_stats = {}
            for col in numeric_cols:
                try:
                    numeric_stats[col] = {
                        'mean': float(df_clean[col].mean()),
                        'median': float(df_clean[col].median()),
                        'std': float(df_clean[col].std()),
                        'min': float(df_clean[col].min()),
                        'max': float(df_clean[col].max()),
                        'count': int(df_clean[col].count()),
                        'missing': int(df_clean[col].isnull().sum())
                    }
                except Exception as e:
                    logger.warning(f"处理数值列 {col} 失败: {e}")
                    continue

            # 分类列统计
            categorical_stats = {}
            for col in categorical_cols:
                try:
                    value_counts = df_clean[col].value_counts().head(10)  # 只取前10个
                    categorical_stats[col] = {
                        'value_counts': value_counts.to_dict(),
                        'unique_count': int(df_clean[col].nunique()),
                        'top_value': value_counts.index[0] if len(value_counts) > 0 else None,
                        'top_count': int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                        'missing': int(df_clean[col].isnull().sum())
                    }
                except Exception as e:
                    logger.warning(f"处理分类列 {col} 失败: {e}")
                    continue

            # 相关性矩阵（只计算数值列）
            correlation_matrix = {}
            if len(numeric_cols) > 1:
                try:
                    corr_df = df_clean[numeric_cols].corr()
                    # 将NaN替换为0，将numpy类型转换为Python原生类型
                    correlation_matrix = corr_df.fillna(0).astype(float).to_dict()
                except Exception as e:
                    logger.warning(f"计算相关性矩阵失败: {e}")

            # 缺失值统计
            missing_data = df_clean.isnull().sum().to_dict()

            # 数据质量评分
            quality_score = calculate_data_quality_score(df_clean)

            result[sheet_name] = {
                'basic_info': {
                    'rows': len(df_clean),
                    'columns': len(df_clean.columns),
                    'numeric_columns': numeric_cols,
                    'categorical_columns': categorical_cols,
                    'total_cells': len(df_clean) * len(df_clean.columns),
                    'file_path': file_path
                },
                'numeric_stats': numeric_stats,
                'categorical_stats': categorical_stats,
                'correlation_matrix': correlation_matrix,
                'missing_data': missing_data,
                'quality_score': quality_score,
                'sample_data': get_sample_data(df_clean)  # 获取样本数据用于预览
            }

        logger.info(f"可视化数据生成完成，共 {len(result)} 个工作表")
        return result

    except Exception as e:
        logger.error(f"生成可视化数据异常: {e}")
        raise e


def calculate_data_quality_score(df):
    """
    计算数据质量评分 (0-100分)
    """
    try:
        total_score = 100

        # 1. 缺失值扣分 (最多扣40分)
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        missing_rate = missing_cells / total_cells if total_cells > 0 else 0
        total_score -= missing_rate * 40

        # 2. 重复行扣分 (最多扣20分)
        duplicate_rate = df.duplicated().mean()
        total_score -= duplicate_rate * 20

        # 3. 数据类型多样性加分 (最多加10分)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        type_diversity = min(1.0, (len(numeric_cols) + len(categorical_cols)) / max(1, len(df.columns)))
        total_score += type_diversity * 10

        # 4. 数据量加分 (最多加10分)
        data_volume_score = min(1.0, len(df) / 1000)  # 每1000行加1分，最多10分
        total_score += data_volume_score * 10

        return max(0, min(100, int(total_score)))

    except Exception as e:
        logger.warning(f"计算数据质量评分失败: {e}")
        return 50  # 默认分数


def get_sample_data(df, sample_size=5):
    """
    获取样本数据用于前端预览
    """
    try:
        if len(df) == 0:
            return []

        # 取前几行作为样本
        sample_df = df.head(sample_size)
        # 转换NaN为None，确保JSON序列化
        sample_data = sample_df.where(pd.notnull(sample_df), None).to_dict('records')
        return sample_data

    except Exception as e:
        logger.warning(f"获取样本数据失败: {e}")
        return []


@visualization_bp.route('/api/visualization/export', methods=['POST'])
def export_visualization_report():
    """
    导出可视化分析报告
    """
    try:
        data = request.get_json()
        excel_url = data.get('excel_url')
        analysis_data = data.get('analysis_data')

        if not excel_url:
            return jsonify({
                "success": False,
                "error": "缺少excel_url参数"
            }), 400

        # 这里可以实现导出PDF或Excel报告的功能
        # 暂时返回成功响应
        return jsonify({
            "success": True,
            "message": "导出功能开发中",
            "download_url": None
        })

    except Exception as e:
        logger.error(f"导出可视化报告失败: {e}")
        return jsonify({
            "success": False,
            "error": f"导出失败: {str(e)}"
        }), 500


@visualization_bp.route('/api/visualization/health', methods=['GET'])
def health_check():
    """
    健康检查接口
    """
    return jsonify({
        "success": True,
        "message": "Visualization API is healthy",
        "timestamp": pd.Timestamp.now().isoformat()
    })