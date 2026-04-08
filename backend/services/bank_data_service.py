# -*- coding: utf-8 -*-
"""
银行数据服务层 - 业务逻辑封装

功能：
1. 银行信息查询服务
2. 报告数据查询服务
3. 指标趋势分析
4. 多银行对比分析
5. 数据导出服务

作者：DocuVista Team
版本：1.0.0
"""

import json
from typing import List, Dict, Any, Optional
from backend.database.bank_warehouse.bank_warehouse import BankWarehouseManager
from backend.database.bank_warehouse.bank_schema import (
    TableNames,
    BankType,
    ReportType,
)


class BankDataService:
    """
    银行数据服务类

    提供业务层的数据查询和分析功能。
    封装底层数据库操作，提供更友好的业务接口。

    用法：
        service = BankDataService()
        banks = service.get_all_banks()
        trends = service.get_indicator_trend(bank_id=1, indicator='净利润')
    """

    def __init__(self, db_path: str = None):
        """初始化服务

        Args:
            db_path: 可选，数据库路径，默认使用配置文件路径
        """
        self.warehouse = BankWarehouseManager(db_path=db_path)

        # 确保数据库表存在
        if not self.warehouse.check_tables_exist():
            self.warehouse.init_database()

    # ============================================================
    # 银行信息服务
    # ============================================================

    def get_all_banks(
        self,
        bank_type: str = None,
        listed_only: bool = True,
        status: str = 'active'
    ) -> List[Dict[str, Any]]:
        """
        获取所有银行列表

        Args:
            bank_type: 银行类型筛选
            listed_only: 仅返回已上市银行
            status: 状态筛选

        Returns:
            银行列表
        """
        banks = self.warehouse.get_all_banks(
            bank_type=bank_type,
            status=status
        )

        # 过滤已上市
        if listed_only:
            banks = [b for b in banks if b.get('listed_status') == 'listed']

        return banks

    def search_banks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索银行

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的银行列表
        """
        return self.warehouse.search_banks(keyword)

    def get_bank_detail(self, bank_id: int) -> Optional[Dict[str, Any]]:
        """
        获取银行详细信息

        Args:
            bank_id: 银行ID

        Returns:
            银行详情或None
        """
        bank = self.warehouse.get_bank(bank_id)
        if not bank:
            return None

        # 获取该银行的报告数量
        reports = self.warehouse.get_reports_by_bank(bank_id)
        bank['report_count'] = len(reports)

        # 获取最新报告年份
        if reports:
            years = [r.get('fiscal_year') for r in reports if r.get('fiscal_year')]
            bank['latest_year'] = max(years) if years else None

        return bank

    def get_bank_statistics(self) -> Dict[str, Any]:
        """
        获取银行统计信息

        Returns:
            统计信息字典
        """
        stats = self.warehouse.get_statistics()

        return {
            'total_banks': stats.get('banks', 0),
            'total_reports': stats.get('reports', 0),
            'total_table_data': stats.get('table_data', 0),
            'bank_type_distribution': stats.get('bank_type_distribution', []),
            'report_year_distribution': stats.get('report_year_distribution', [])
        }

    # ============================================================
    # 报告查询服务
    # ============================================================

    def get_bank_reports(
        self,
        bank_id: int,
        report_type: str = None,
        year: int = None
    ) -> List[Dict[str, Any]]:
        """
        获取银行的报告列表

        Args:
            bank_id: 银行ID
            report_type: 报告类型筛选
            year: 财年筛选

        Returns:
            报告列表
        """
        return self.warehouse.get_reports_by_bank(
            bank_id=bank_id,
            report_type=report_type,
            fiscal_year=year
        )

    def get_report_detail(self, report_id: int) -> Optional[Dict[str, Any]]:
        """
        获取报告详细信息

        Args:
            report_id: 报告ID

        Returns:
            报告详情
        """
        report = self.warehouse.get_report(report_id)
        if not report:
            return None

        # 获取关联银行信息
        if report.get('bank_id'):
            bank = self.warehouse.get_bank(report['bank_id'])
            if bank:
                report['bank_name'] = bank.get('bank_name')
                report['bank_code'] = bank.get('bank_code')

        # 获取表格数据统计
        table_data = self.warehouse.get_table_data_by_report(report_id)
        report['table_count'] = len(set(d.get('table_name') for d in table_data))
        report['indicator_count'] = len(table_data)

        return report

    def get_report_tables(self, report_id: int) -> List[str]:
        """
        获取报告包含的表格列表

        Args:
            report_id: 报告ID

        Returns:
            表格名称列表
        """
        table_data = self.warehouse.get_table_data_by_report(report_id)
        table_names = set(d.get('table_name') for d in table_data if d.get('table_name'))
        return sorted(list(table_names))

    # ============================================================
    # 表格数据查询服务
    # ============================================================

    def get_table_indicators(
        self,
        report_id: int,
        table_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        获取表格指标数据

        Args:
            report_id: 报告ID
            table_name: 表格名称

        Returns:
            指标数据列表
        """
        return self.warehouse.get_table_data_by_report(
            report_id=report_id,
            table_name=table_name
        )

    def get_indicator_value(
        self,
        report_id: int,
        indicator_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定指标的值

        Args:
            report_id: 报告ID
            indicator_name: 指标名称

        Returns:
            指标数据
        """
        table_data = self.warehouse.get_table_data_by_report(report_id)

        for data in table_data:
            if data.get('indicator_name') == indicator_name:
                return data

        return None

    # ============================================================
    # 趋势分析服务
    # ============================================================

    def get_indicator_trend(
        self,
        bank_id: int,
        indicator_name: str,
        years: List[int] = None
    ) -> Dict[str, Any]:
        """
        获取某银行某指标的历史趋势

        Args:
            bank_id: 银行ID
            indicator_name: 指标名称
            years: 要查询的年份列表

        Returns:
            趋势数据，格式：{bank_id, indicator_name, years: [...], values: [...], data: {...}}
        """
        if years is None:
            years = [2020, 2021, 2022, 2023, 2024]

        raw = self.warehouse.get_indicator_trend(
            bank_id=bank_id,
            indicator_name=indicator_name,
            years=years
        )

        # 将 {year: value} data 转换为 years/values 列表，方便前端绘图
        data_dict = raw.get('data', {})
        sorted_years = sorted(years)
        values = [data_dict.get(y) for y in sorted_years]

        return {
            'bank_id': raw.get('bank_id'),
            'indicator_name': raw.get('indicator_name'),
            'years': sorted_years,
            'values': values,
            'data': data_dict,
        }

    def get_multiple_banks_indicator(
        self,
        bank_ids: List[int],
        indicator_name: str,
        year: int = None
    ) -> List[Dict[str, Any]]:
        """
        获取多个银行的同一指标对比

        Args:
            bank_ids: 银行ID列表
            indicator_name: 指标名称
            year: 年份（不指定则取最新）

        Returns:
            多个银行的指标数据
        """
        results = []

        for bank_id in bank_ids:
            bank = self.warehouse.get_bank(bank_id)
            if not bank:
                continue

            reports = self.warehouse.get_reports_by_bank(bank_id, report_type='annual')
            if not reports:
                continue

            # 找到指定年份的报告
            target_report = None
            if year:
                for r in reports:
                    if r.get('fiscal_year') == year:
                        target_report = r
                        break
            else:
                # 取最新年份
                reports_sorted = sorted(reports, key=lambda x: x.get('fiscal_year', 0), reverse=True)
                target_report = reports_sorted[0] if reports_sorted else None

            if not target_report:
                continue

            # 获取指标数据
            indicator = self.get_indicator_value(target_report['id'], indicator_name)
            if indicator:
                results.append({
                    'bank_id': bank_id,
                    'bank_name': bank.get('bank_name'),
                    'bank_code': bank.get('bank_code'),
                    'year': target_report.get('fiscal_year'),
                    'value': indicator.get('value_dict', {}),
                    'unit': indicator.get('unit', '万元')
                })

        return results

    def get_indicator_ranking(
        self,
        indicator_name: str,
        year: int = None,
        bank_type: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取某指标的企业排名

        Args:
            indicator_name: 指标名称
            year: 年份
            bank_type: 银行类型筛选
            limit: 返回数量

        Returns:
            排名列表
        """
        # 获取所有银行
        banks = self.warehouse.get_all_banks(bank_type=bank_type)

        rankings = []

        for bank in banks:
            # 获取最新报告
            reports = self.warehouse.get_reports_by_bank(
                bank['id'],
                report_type='annual'
            )

            if not reports:
                continue

            # 找到指定年份的报告
            target_report = None
            if year:
                for r in reports:
                    if r.get('fiscal_year') == year:
                        target_report = r
                        break
            else:
                reports_sorted = sorted(reports, key=lambda x: x.get('fiscal_year', 0), reverse=True)
                target_report = reports_sorted[0] if reports_sorted else None

            if not target_report:
                continue

            # 获取指标值
            indicator = self.get_indicator_value(target_report['id'], indicator_name)
            if indicator and indicator.get('value_dict'):
                value_dict = indicator['value_dict']
                # 取最新年份的值
                target_year = str(year) if year else str(target_report.get('fiscal_year'))
                value = value_dict.get(target_year)

                if value is not None:
                    rankings.append({
                        'bank_id': bank['id'],
                        'bank_name': bank['bank_name'],
                        'bank_code': bank.get('bank_code'),
                        'bank_type': bank.get('bank_type'),
                        'year': target_report.get('fiscal_year'),
                        'value': value,
                        'unit': indicator.get('unit', '万元')
                    })

        # 按值排序
        rankings.sort(key=lambda x: x.get('value') or 0, reverse=True)

        # 添加排名
        for i, item in enumerate(rankings[:limit]):
            item['rank'] = i + 1

        return rankings[:limit]

    # ============================================================
    # 数据导出服务
    # ============================================================

    def export_bank_full_data(
        self,
        bank_id: int,
        format: str = 'json'
    ) -> Dict[str, Any]:
        """
        导出银行完整数据

        Args:
            bank_id: 银行ID
            format: 导出格式（json/excel）

        Returns:
            导出数据
        """
        bank = self.warehouse.get_bank(bank_id)
        if not bank:
            return {}

        reports = self.warehouse.get_reports_by_bank(bank_id)

        result = {
            'bank': bank,
            'reports': []
        }

        for report in reports:
            report_data = self.warehouse.get_table_data_by_report(report['id'])
            result['reports'].append({
                'report_id': report['id'],
                'period': report.get('period'),
                'fiscal_year': report.get('fiscal_year'),
                'report_date': report.get('report_date'),
                'data': report_data
            })

        return result

    def export_indicator_comparison(
        self,
        bank_ids: List[int],
        indicator_names: List[str],
        year: int = None
    ) -> Dict[str, Any]:
        """
        导出多银行多指标对比数据

        Args:
            bank_ids: 银行ID列表
            indicator_names: 指标名称列表
            year: 年份

        Returns:
            对比数据
        """
        result = {
            'banks': [],
            'indicators': indicator_names,
            'year': year
        }

        for bank_id in bank_ids:
            bank = self.warehouse.get_bank(bank_id)
            if not bank:
                continue

            bank_data = {
                'bank_id': bank_id,
                'bank_name': bank.get('bank_name'),
                'bank_code': bank.get('bank_code'),
                'indicators': {}
            }

            for indicator_name in indicator_names:
                values = self.get_multiple_banks_indicator(
                    bank_ids=[bank_id],
                    indicator_name=indicator_name,
                    year=year
                )
                if values:
                    bank_data['indicators'][indicator_name] = values[0].get('value', {})

            result['banks'].append(bank_data)

        return result

    # ============================================================
    # 数据溯源服务
    # ============================================================

    def get_data_sources(self, table_data_id: int) -> List[Dict[str, Any]]:
        """
        获取数据的溯源信息

        Args:
            table_data_id: 表格数据ID

        Returns:
            溯源信息列表
        """
        return self.warehouse.get_data_sources(table_data_id)

    def get_data_versions(self, table_data_id: int) -> List[Dict[str, Any]]:
        """
        获取数据版本历史

        Args:
            table_data_id: 表格数据ID

        Returns:
            版本历史列表
        """
        return self.warehouse.get_data_versions(table_data_id)


# 全局服务实例
bank_data_service = BankDataService()
