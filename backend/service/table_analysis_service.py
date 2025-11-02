# backend/services/table_analysis_service.py
import logging
import pandas as pd
import numpy as np
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from openai import AsyncOpenAI
import io
import base64

logger = logging.getLogger(__name__)


class TableAnalysisService:
    """表格数据统计分析和可视化服务"""

    def __init__(self, llm_client=None, model_id=None):
        self.llm_client = llm_client
        self.model_id = model_id

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

    async def analyze_table_data(self, df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """
        综合分析表格数据
        """
        try:
            # 基础统计分析
            basic_stats = self._get_basic_statistics(df)

            # 数据质量分析
            data_quality = self._analyze_data_quality(df)

            # 使用LLM进行智能分析
            llm_insights = await self._get_llm_insights(df, table_name)

            # 生成可视化图表
            visualizations = await self._generate_visualizations(df, table_name)

            return {
                "table_name": table_name,
                "basic_statistics": basic_stats,
                "data_quality": data_quality,
                "llm_insights": llm_insights,
                "visualizations": visualizations,
                "summary": await self._generate_summary(df, table_name, basic_stats, llm_insights)
            }

        except Exception as e:
            logger.error(f"表格数据分析失败: {e}")
            return {"error": str(e)}

    def _get_basic_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """基础统计分析"""
        stats = {
            "shape": {
                "rows": df.shape[0],
                "columns": df.shape[1]
            },
            "data_types": df.dtypes.astype(str).to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "numeric_columns": {},
            "categorical_columns": {}
        }

        # 数值列统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            stats["numeric_columns"][col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "sum": float(df[col].sum())
            }

        # 分类列统计
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            value_counts = df[col].value_counts()
            stats["categorical_columns"][col] = {
                "unique_count": int(value_counts.count()),
                "top_value": value_counts.index[0] if len(value_counts) > 0 else None,
                "top_count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0
            }

        return stats

    def _analyze_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """数据质量分析"""
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()

        return {
            "completeness": {
                "total_cells": total_cells,
                "missing_cells": missing_cells,
                "completeness_rate": (total_cells - missing_cells) / total_cells if total_cells > 0 else 0
            },
            "duplicates": {
                "duplicate_rows": int(df.duplicated().sum()),
                "duplicate_rate": df.duplicated().mean()
            },
            "data_issues": self._detect_data_issues(df)
        }

    def _detect_data_issues(self, df: pd.DataFrame) -> List[str]:
        """检测数据问题"""
        issues = []

        # 检查缺失值
        missing_cols = df.columns[df.isnull().any()].tolist()
        if missing_cols:
            issues.append(f"以下列存在缺失值: {', '.join(missing_cols)}")

        # 检查重复行
        if df.duplicated().any():
            issues.append(f"存在 {df.duplicated().sum()} 行重复数据")

        # 检查数值列的异常值
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = df[(df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)]
            if len(outliers) > 0:
                issues.append(f"列 '{col}' 存在 {len(outliers)} 个异常值")

        return issues

    async def _get_llm_insights(self, df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """使用LLM获取数据洞察"""
        if not self.llm_client:
            return {"insights": ["LLM客户端未配置，无法生成深度洞察"]}

        try:
            # 准备数据摘要
            data_summary = self._prepare_data_summary(df)

            prompt = f"""
请分析以下表格数据并提供洞察：

表格名称：{table_name}
数据摘要：
{data_summary}

请从以下角度提供分析：
1. 数据的主要特征和模式
2. 关键发现和趋势
3. 潜在的数据质量问题
4. 业务建议或下一步分析方向

请用简洁明了的中文回答。
"""

            response = await self.llm_client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3,
            )

            insights_text = response.choices[0].message.content.strip()

            # 解析LLM返回的洞察
            return {
                "text_insights": insights_text,
                "key_findings": self._extract_key_findings(insights_text)
            }

        except Exception as e:
            logger.error(f"LLM洞察分析失败: {e}")
            return {"error": f"LLM分析失败: {str(e)}"}

    def _prepare_data_summary(self, df: pd.DataFrame) -> str:
        """准备数据摘要"""
        summary = []
        summary.append(f"数据形状: {df.shape[0]} 行 × {df.shape[1]} 列")
        summary.append(f"列名: {', '.join(df.columns.tolist())}")

        # 数值列摘要
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            summary.append("数值列:")
            for col in numeric_cols:
                summary.append(f"  - {col}: 均值={df[col].mean():.2f}, 范围=[{df[col].min():.2f}, {df[col].max():.2f}]")

        # 分类列摘要
        categorical_cols = df.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            summary.append("分类列:")
            for col in categorical_cols:
                top_values = df[col].value_counts().head(3)
                summary.append(f"  - {col}: 唯一值={df[col].nunique()}, 常见值={dict(top_values)}")

        return "\n".join(summary)

    def _extract_key_findings(self, insights_text: str) -> List[str]:
        """从LLM返回文本中提取关键发现"""
        # 简单的关键词提取和句子分割
        sentences = insights_text.split('。')
        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        return key_sentences[:5]  # 返回前5个关键句子

    async def _generate_visualizations(self, df: pd.DataFrame, table_name: str) -> Dict[str, str]:
        """生成可视化图表"""
        visualizations = {}

        try:
            # 1. 数据概览图
            overview_plot = self._create_overview_plot(df, table_name)
            if overview_plot:
                visualizations["overview"] = overview_plot

            # 2. 数值分布图
            distribution_plots = self._create_distribution_plots(df)
            visualizations.update(distribution_plots)

            # 3. 相关性热力图（如果有多个数值列）
            correlation_plot = self._create_correlation_plot(df)
            if correlation_plot:
                visualizations["correlation"] = correlation_plot

            # 4. 分类数据图
            categorical_plots = self._create_categorical_plots(df)
            visualizations.update(categorical_plots)

        except Exception as e:
            logger.error(f"生成可视化图表失败: {e}")
            visualizations["error"] = f"图表生成失败: {str(e)}"

        return visualizations

    def _create_overview_plot(self, df: pd.DataFrame, table_name: str) -> Optional[str]:
        """创建数据概览图"""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle(f'{table_name} - 数据概览', fontsize=16)

            # 1. 数据类型分布
            dtypes_count = df.dtypes.value_counts()
            ax1.pie(dtypes_count.values, labels=dtypes_count.index, autopct='%1.1f%%')
            ax1.set_title('数据类型分布')

            # 2. 缺失值情况
            missing_data = df.isnull().sum()
            if missing_data.sum() > 0:
                missing_data[missing_data > 0].plot(kind='bar', ax=ax2)
                ax2.set_title('缺失值统计')
                ax2.tick_params(axis='x', rotation=45)
            else:
                ax2.text(0.5, 0.5, '无缺失值', ha='center', va='center', transform=ax2.transAxes)
                ax2.set_title('缺失值统计')

            # 3. 数据行数信息
            info_text = f"总行数: {len(df)}\n总列数: {len(df.columns)}\n重复行: {df.duplicated().sum()}"
            ax3.text(0.1, 0.5, info_text, fontsize=12, va='center')
            ax3.set_title('数据基本信息')
            ax3.axis('off')

            # 4. 数值列统计
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                numeric_info = f"数值列数量: {len(numeric_cols)}\n"
                for col in numeric_cols[:3]:  # 显示前3个数值列
                    numeric_info += f"{col}: {df[col].mean():.2f}±{df[col].std():.2f}\n"
                ax4.text(0.1, 0.5, numeric_info, fontsize=10, va='center')
            else:
                ax4.text(0.5, 0.5, '无数值列', ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title('数值列统计')
            ax4.axis('off')

            plt.tight_layout()
            return self._fig_to_base64(fig)

        except Exception as e:
            logger.error(f"创建概览图失败: {e}")
            return None

    def _create_distribution_plots(self, df: pd.DataFrame) -> Dict[str, str]:
        """创建数值分布图"""
        plots = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            try:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
                fig.suptitle(f'{col} - 分布分析')

                # 直方图
                df[col].hist(bins=20, ax=ax1, alpha=0.7)
                ax1.set_title(f'{col} - 直方图')
                ax1.set_xlabel(col)
                ax1.set_ylabel('频次')

                # 箱线图
                df.boxplot(column=col, ax=ax2)
                ax2.set_title(f'{col} - 箱线图')

                plt.tight_layout()
                plots[f"distribution_{col}"] = self._fig_to_base64(fig)
                plt.close(fig)

            except Exception as e:
                logger.error(f"创建分布图失败 {col}: {e}")
                continue

        return plots

    def _create_correlation_plot(self, df: pd.DataFrame) -> Optional[str]:
        """创建相关性热力图"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return None

        try:
            plt.figure(figsize=(10, 8))
            correlation_matrix = df[numeric_cols].corr()
            sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                        square=True, fmt='.2f', cbar_kws={"shrink": .8})
            plt.title('数值列相关性热力图')
            plt.tight_layout()

            return self._fig_to_base64(plt.gcf())

        except Exception as e:
            logger.error(f"创建相关性图失败: {e}")
            return None

    def _create_categorical_plots(self, df: pd.DataFrame) -> Dict[str, str]:
        """创建分类数据图"""
        plots = {}
        categorical_cols = df.select_dtypes(include=['object']).columns

        for col in categorical_cols:
            try:
                value_counts = df[col].value_counts().head(10)  # 只显示前10个

                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
                fig.suptitle(f'{col} - 分类分布')

                # 柱状图
                value_counts.plot(kind='bar', ax=ax1, alpha=0.7)
                ax1.set_title(f'{col} - 柱状图')
                ax1.tick_params(axis='x', rotation=45)

                # 饼图（如果类别不多）
                if len(value_counts) <= 8:
                    value_counts.plot(kind='pie', ax=ax2, autopct='%1.1f%%')
                    ax2.set_title(f'{col} - 饼图')
                else:
                    ax2.text(0.5, 0.5, '类别过多\n不显示饼图',
                             ha='center', va='center', transform=ax2.transAxes)
                    ax2.set_title(f'{col} - 饼图')
                    ax2.axis('off')

                plt.tight_layout()
                plots[f"categorical_{col}"] = self._fig_to_base64(fig)
                plt.close(fig)

            except Exception as e:
                logger.error(f"创建分类图失败 {col}: {e}")
                continue

        return plots

    def _fig_to_base64(self, fig) -> str:
        """将matplotlib图形转换为base64字符串"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{img_str}"

    async def _generate_summary(self, df: pd.DataFrame, table_name: str,
                                basic_stats: Dict, llm_insights: Dict) -> Dict[str, Any]:
        """生成分析总结"""
        return {
            "table_name": table_name,
            "data_quality_score": self._calculate_data_quality_score(df),
            "key_metrics": self._extract_key_metrics(basic_stats),
            "recommendations": await self._generate_recommendations(df, llm_insights)
        }

    def _calculate_data_quality_score(self, df: pd.DataFrame) -> float:
        """计算数据质量分数"""
        total_score = 100

        # 缺失值扣分
        missing_rate = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
        total_score -= missing_rate * 50

        # 重复行扣分
        duplicate_rate = df.duplicated().mean()
        total_score -= duplicate_rate * 30

        return max(0, total_score)

    def _extract_key_metrics(self, basic_stats: Dict) -> List[str]:
        """提取关键指标"""
        metrics = []

        # 数据规模
        metrics.append(f"数据规模: {basic_stats['shape']['rows']}行 × {basic_stats['shape']['columns']}列")

        # 数值列关键指标
        for col, stats in basic_stats['numeric_columns'].items():
            metrics.append(f"{col}: 均值={stats['mean']:.2f}, 范围=[{stats['min']:.2f}, {stats['max']:.2f}]")

        return metrics

    async def _generate_recommendations(self, df: pd.DataFrame, llm_insights: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于数据质量的建议
        if df.isnull().any().any():
            recommendations.append("建议处理缺失值，可以考虑填充或删除")

        if df.duplicated().any():
            recommendations.append("建议删除重复数据行")

        # 基于LLM洞察的建议
        if 'text_insights' in llm_insights:
            # 这里可以添加基于LLM返回内容的建议提取逻辑
            recommendations.append("基于数据分析，建议进一步探索数据中的模式和关系")

        return recommendations