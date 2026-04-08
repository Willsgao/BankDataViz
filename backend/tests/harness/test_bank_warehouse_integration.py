# -*- coding: utf-8 -*-
"""
银行数据仓库 - Harness 集成测试

测试覆盖：
1. 种子数据写入
2. 银行 CRUD
3. 报告 CRUD
4. 表格数据读写
5. 趋势分析
6. 多银行对比
7. 指标排名
8. 数据统计
9. API 层测试（通过 BankDataService）
10. 边界条件测试

运行方式：
    python backend/tests/harness/test_bank_warehouse_integration.py
"""

import sys
import os
import json
import unittest
import tempfile

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.database.bank_warehouse.bank_warehouse import BankWarehouseManager
from backend.database.bank_warehouse.bank_schema import BankType, ReportType
from backend.services.bank_data_service import BankDataService


class HarnessTestBase(unittest.TestCase):
    """测试基类 - 使用临时数据库"""

    @classmethod
    def setUpClass(cls):
        """创建临时数据库"""
        cls.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.temp_db.close()
        cls.db_path = cls.temp_db.name
        cls.warehouse = BankWarehouseManager(db_path=cls.db_path)
        cls.warehouse.init_database()
        print(f"\n[SETUP] Test database: {cls.db_path}")

    @classmethod
    def tearDownClass(cls):
        """清理临时数据库"""
        try:
            os.unlink(cls.db_path)
            print(f"\n[TEARDOWN] Cleaned up: {cls.db_path}")
        except Exception:
            pass


class TestSeedData(HarnessTestBase):
    """测试种子数据写入"""

    def test_01_seed_database(self):
        """测试写入12家银行的种子数据"""
        print("\n" + "="*60)
        print("[TEST] Seed Data: 写入演示银行数据")
        print("="*60)

        from backend.database.bank_warehouse.seed_data import seed_database
        result = seed_database.__wrapped__(self.warehouse) if hasattr(seed_database, '__wrapped__') else None

        # 改用直接调用的方式测试
        from backend.database.bank_warehouse import seed_data as sd

        # 直接调用内部逻辑
        for bank_data in sd.BANKS_DATA[:3]:  # 只写3家做测试
            bank_id = self.warehouse.save_bank(bank_data)
            self.assertIsNotNone(bank_id, f"保存银行失败: {bank_data['bank_name']}")
            print(f"  [OK] Saved bank: {bank_data['bank_name']} (ID={bank_id})")

        # 写指标数据
        banks = self.warehouse.get_all_banks()
        for bank in banks[:1]:
            bank_code = bank['bank_code']
            fin_data = sd.FINANCIAL_DATA.get(bank_code, {})
            if not fin_data:
                continue

            report_id = self.warehouse.save_report({
                "bank_id": bank['id'],
                "report_type": ReportType.ANNUAL,
                "period": "2020-2024",
                "fiscal_year": 2024,
                "status": "completed",
            })
            self.assertIsNotNone(report_id)

            for table_name in ["利润表", "资产负债表"]:
                rows = []
                for indicator_name, year_values in fin_data.items():
                    if sd.TABLE_CATEGORY_MAP.get(indicator_name) != table_name:
                        continue
                    row = {"indicator_name": indicator_name, "unit": "亿元"}
                    for year in [2020, 2021, 2022, 2023, 2024]:
                        val = year_values.get(year)
                        if val is not None:
                            row[f"value_{year}"] = val
                    rows.append(row)

                if rows:
                    count = self.warehouse.save_batch_table_data(report_id, table_name, rows)
                    self.assertGreater(count, 0, f"应写入 {table_name} 数据")
                    print(f"  [OK] Table '{table_name}': {count} rows saved")

        stats = self.warehouse.get_statistics()
        self.assertGreater(stats['banks'], 0, "应有银行数据")
        print(f"\n[PASS] Seed test: banks={stats['banks']}, reports={stats['reports']}")


class TestBankCRUD(HarnessTestBase):
    """测试银行增删查改"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 写入测试数据
        cls.bank_id = cls.warehouse.save_bank({
            'bank_code': 'TEST_ICBC',
            'bank_name': '测试工商银行',
            'bank_type': BankType.STATE_OWNED,
            'listed_status': 'listed',
        })

    def test_01_save_bank(self):
        """测试保存银行"""
        print("\n[TEST] save_bank")
        self.assertIsNotNone(self.bank_id)
        self.assertGreater(self.bank_id, 0)
        print(f"  [OK] bank_id = {self.bank_id}")

    def test_02_get_bank(self):
        """测试获取银行"""
        print("\n[TEST] get_bank")
        bank = self.warehouse.get_bank(self.bank_id)
        self.assertIsNotNone(bank)
        self.assertEqual(bank['bank_name'], '测试工商银行')
        self.assertEqual(bank['bank_code'], 'TEST_ICBC')
        print(f"  [OK] bank = {bank['bank_name']}")

    def test_03_search_banks(self):
        """测试搜索银行"""
        print("\n[TEST] search_banks")
        results = self.warehouse.search_banks('测试工商')
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['bank_name'], '测试工商银行')
        print(f"  [OK] Found {len(results)} result(s)")

    def test_04_get_all_banks(self):
        """测试获取全部银行"""
        print("\n[TEST] get_all_banks")
        banks = self.warehouse.get_all_banks()
        self.assertGreater(len(banks), 0)
        print(f"  [OK] Total banks: {len(banks)}")

    def test_05_update_bank(self):
        """测试更新银行（upsert）"""
        print("\n[TEST] update_bank (upsert)")
        new_id = self.warehouse.save_bank({
            'bank_code': 'TEST_ICBC',
            'bank_name': '测试工商银行（更新）',
            'bank_type': BankType.STATE_OWNED,
        })
        bank = self.warehouse.get_bank(new_id or self.bank_id)
        self.assertIsNotNone(bank)
        print(f"  [OK] Bank updated, name={bank['bank_name']}")


class TestReportCRUD(HarnessTestBase):
    """测试报告增删查改"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_id = cls.warehouse.save_bank({
            'bank_code': 'RPT_TEST',
            'bank_name': '报告测试银行',
            'bank_type': BankType.JOINT_STOCK,
            'listed_status': 'listed',
        })

    def test_01_save_report(self):
        """测试保存报告"""
        print("\n[TEST] save_report")
        report_id = self.warehouse.save_report({
            'bank_id': self.bank_id,
            'report_type': ReportType.ANNUAL,
            'period': '2024A',
            'fiscal_year': 2024,
            'status': 'completed',
        })
        self.assertIsNotNone(report_id)
        self.assertGreater(report_id, 0)
        self.__class__.report_id = report_id
        print(f"  [OK] report_id = {report_id}")

    def test_02_get_report(self):
        """测试获取报告"""
        print("\n[TEST] get_report")
        if not hasattr(self.__class__, 'report_id'):
            self.skipTest("No report_id from previous test")
        report = self.warehouse.get_report(self.__class__.report_id)
        self.assertIsNotNone(report)
        self.assertEqual(report['fiscal_year'], 2024)
        print(f"  [OK] report period={report['period']}")

    def test_03_get_reports_by_bank(self):
        """测试按银行获取报告"""
        print("\n[TEST] get_reports_by_bank")
        reports = self.warehouse.get_reports_by_bank(self.bank_id)
        self.assertGreater(len(reports), 0)
        print(f"  [OK] Found {len(reports)} report(s)")


class TestTableData(HarnessTestBase):
    """测试表格数据读写"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_id = cls.warehouse.save_bank({
            'bank_code': 'DATA_TEST',
            'bank_name': '数据测试银行',
            'bank_type': BankType.CITY_COMMERCIAL,
            'listed_status': 'listed',
        })
        cls.report_id = cls.warehouse.save_report({
            'bank_id': cls.bank_id,
            'report_type': ReportType.ANNUAL,
            'period': '2020-2024',
            'fiscal_year': 2024,
            'status': 'completed',
        })

    def test_01_save_batch_table_data(self):
        """测试批量写入表格数据"""
        print("\n[TEST] save_batch_table_data")
        rows = [
            {'indicator_name': '营业收入', 'unit': '亿元',
             'value_2020': 100, 'value_2021': 120, 'value_2022': 140, 'value_2023': 160, 'value_2024': 180},
            {'indicator_name': '净利润', 'unit': '亿元',
             'value_2020': 30,  'value_2021': 36,  'value_2022': 42,  'value_2023': 48,  'value_2024': 55},
            {'indicator_name': '净息差(%)', 'unit': '%',
             'value_2020': 2.5, 'value_2021': 2.4, 'value_2022': 2.3, 'value_2023': 2.1, 'value_2024': 2.0},
        ]
        count = self.warehouse.save_batch_table_data(self.report_id, '利润表', rows)
        self.assertEqual(count, 3)
        print(f"  [OK] Saved {count} rows")

    def test_02_get_table_data_by_report(self):
        """测试按报告获取数据"""
        print("\n[TEST] get_table_data_by_report")
        data = self.warehouse.get_table_data_by_report(self.report_id, '利润表')
        self.assertGreater(len(data), 0)
        # 验证 value_dict 结构
        first = data[0]
        self.assertIn('value_dict', first)
        self.assertIsInstance(first['value_dict'], dict)
        print(f"  [OK] Got {len(data)} rows, first indicator={first['indicator_name']}")
        print(f"  [OK] value_dict keys: {list(first['value_dict'].keys())}")

    def test_03_value_json_integrity(self):
        """测试 value_json 数据完整性"""
        print("\n[TEST] value_json integrity")
        data = self.warehouse.get_table_data_by_report(self.report_id, '利润表')
        revenue_row = next((d for d in data if d['indicator_name'] == '营业收入'), None)
        self.assertIsNotNone(revenue_row)
        vd = revenue_row['value_dict']
        self.assertAlmostEqual(vd.get('2020'), 100.0)
        self.assertAlmostEqual(vd.get('2024'), 180.0)
        print(f"  [OK] 营业收入 2020={vd.get('2020')}, 2024={vd.get('2024')}")


class TestAnalysisService(HarnessTestBase):
    """测试分析服务"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 写入两家银行的多年数据
        for i, bank_data in enumerate([
            {'bank_code': 'ANAL_A', 'bank_name': '分析银行A', 'bank_type': BankType.STATE_OWNED, 'listed_status': 'listed'},
            {'bank_code': 'ANAL_B', 'bank_name': '分析银行B', 'bank_type': BankType.JOINT_STOCK, 'listed_status': 'listed'},
        ]):
            bank_id = cls.warehouse.save_bank(bank_data)
            report_id = cls.warehouse.save_report({
                'bank_id': bank_id,
                'report_type': ReportType.ANNUAL,
                'period': '2020-2024',
                'fiscal_year': 2024,
                'status': 'completed',
            })
            base = (i + 1) * 100
            cls.warehouse.save_batch_table_data(report_id, '利润表', [{
                'indicator_name': '净利润', 'unit': '亿元',
                'value_2020': base, 'value_2021': base+10, 'value_2022': base+20,
                'value_2023': base+30, 'value_2024': base+40,
            }])
            if i == 0:
                cls.bank_a_id = bank_id
            else:
                cls.bank_b_id = bank_id

    def test_01_indicator_trend(self):
        """测试指标趋势查询"""
        print("\n[TEST] get_indicator_trend")
        result = self.warehouse.get_indicator_trend(
            bank_id=self.bank_a_id,
            indicator_name='净利润',
            years=[2020, 2021, 2022, 2023, 2024]
        )
        self.assertIsNotNone(result)
        self.assertIn('data', result)
        self.assertIn('bank_id', result)
        self.assertIn('indicator_name', result)
        # data 应该是一个 dict，key 为年份
        self.assertIsInstance(result['data'], dict)
        print(f"  [OK] Trend result: bank_id={result['bank_id']}, data_years={list(result['data'].keys())}")

    def test_02_statistics(self):
        """测试统计信息"""
        print("\n[TEST] get_statistics")
        stats = self.warehouse.get_statistics()
        self.assertIn('banks', stats)
        self.assertIn('reports', stats)
        self.assertIn('table_data', stats)
        self.assertGreater(stats['banks'], 0)
        print(f"  [OK] Stats: {stats}")


class TestBankDataService(HarnessTestBase):
    """测试 BankDataService 服务层"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # BankDataService 使用默认数据库，这里我们仅测试接口签名和逻辑
        cls.service = BankDataService(db_path=cls.db_path)
        # 写入测试数据
        cls.bank_id = cls.warehouse.save_bank({
            'bank_code': 'SVC_TEST',
            'bank_name': '服务层测试银行',
            'bank_type': BankType.STATE_OWNED,
            'listed_status': 'listed',
        })
        cls.report_id = cls.warehouse.save_report({
            'bank_id': cls.bank_id,
            'report_type': ReportType.ANNUAL,
            'period': '2020-2024',
            'fiscal_year': 2024,
            'status': 'completed',
        })
        cls.warehouse.save_batch_table_data(cls.report_id, '利润表', [{
            'indicator_name': '净利润', 'unit': '亿元',
            'value_2020': 50, 'value_2021': 60, 'value_2022': 70, 'value_2023': 80, 'value_2024': 90,
        }])

    def test_01_get_all_banks(self):
        """测试服务层获取银行列表"""
        print("\n[TEST] BankDataService.get_all_banks")
        banks = self.service.get_all_banks(listed_only=False)
        self.assertIsInstance(banks, list)
        print(f"  [OK] Got {len(banks)} banks")

    def test_02_get_bank_detail(self):
        """测试服务层获取银行详情"""
        print("\n[TEST] BankDataService.get_bank_detail")
        bank = self.service.get_bank_detail(self.bank_id)
        self.assertIsNotNone(bank)
        self.assertIn('report_count', bank)
        print(f"  [OK] {bank['bank_name']}, report_count={bank['report_count']}")

    def test_03_get_bank_statistics(self):
        """测试服务层统计"""
        print("\n[TEST] BankDataService.get_bank_statistics")
        stats = self.service.get_bank_statistics()
        self.assertIn('total_banks', stats)
        self.assertIn('total_reports', stats)
        print(f"  [OK] Stats: {stats}")

    def test_04_get_report_tables(self):
        """测试获取报告表格列表"""
        print("\n[TEST] BankDataService.get_report_tables")
        tables = self.service.get_report_tables(self.report_id)
        self.assertIsInstance(tables, list)
        self.assertIn('利润表', tables)
        print(f"  [OK] Tables: {tables}")

    def test_05_get_table_indicators(self):
        """测试获取表格指标"""
        print("\n[TEST] BankDataService.get_table_indicators")
        indicators = self.service.get_table_indicators(self.report_id, '利润表')
        self.assertGreater(len(indicators), 0)
        print(f"  [OK] Got {len(indicators)} indicators")

    def test_06_get_indicator_trend(self):
        """测试指标趋势"""
        print("\n[TEST] BankDataService.get_indicator_trend")
        trend = self.service.get_indicator_trend(self.bank_id, '净利润')
        self.assertIn('years', trend)
        self.assertIn('values', trend)
        print(f"  [OK] Trend years={trend['years']}")

    def test_07_export_bank_full_data(self):
        """测试导出银行全量数据"""
        print("\n[TEST] BankDataService.export_bank_full_data")
        data = self.service.export_bank_full_data(self.bank_id)
        self.assertIn('bank', data)
        self.assertIn('reports', data)
        print(f"  [OK] Exported, reports count={len(data['reports'])}")


class TestEdgeCases(HarnessTestBase):
    """边界条件测试"""

    def test_01_get_nonexistent_bank(self):
        """测试获取不存在的银行"""
        print("\n[TEST] get_nonexistent_bank")
        result = self.warehouse.get_bank(99999)
        self.assertIsNone(result)
        print("  [OK] Returns None for non-existent bank")

    def test_02_search_empty_keyword(self):
        """测试空关键词搜索"""
        print("\n[TEST] search_empty_keyword")
        results = self.warehouse.search_banks('')
        self.assertIsInstance(results, list)
        print(f"  [OK] Empty search returns list (len={len(results)})")

    def test_03_save_duplicate_bank_code(self):
        """测试重复 bank_code（应 upsert）"""
        print("\n[TEST] duplicate_bank_code upsert")
        id1 = self.warehouse.save_bank({'bank_code': 'DUP_TEST', 'bank_name': '重复银行V1', 'bank_type': BankType.PRIVATE})
        id2 = self.warehouse.save_bank({'bank_code': 'DUP_TEST', 'bank_name': '重复银行V2', 'bank_type': BankType.PRIVATE})
        bank = self.warehouse.get_bank(id2 or id1)
        self.assertIsNotNone(bank)
        print(f"  [OK] Upsert OK, final name={bank['bank_name']}")

    def test_04_empty_table_data(self):
        """测试写入空数据"""
        print("\n[TEST] empty_table_data")
        bank_id = self.warehouse.save_bank({'bank_code': 'EMPTY_TEST', 'bank_name': '空数据银行', 'bank_type': BankType.RURAL_COMMERCIAL})
        report_id = self.warehouse.save_report({'bank_id': bank_id, 'report_type': 'annual', 'period': '2024A', 'fiscal_year': 2024})
        count = self.warehouse.save_batch_table_data(report_id, '空表', [])
        self.assertEqual(count, 0)
        print("  [OK] Empty rows returns 0")

    def test_05_get_trend_no_data(self):
        """测试无数据时趋势接口"""
        print("\n[TEST] trend_no_data")
        result = self.warehouse.get_indicator_trend(99999, '不存在的指标', [2020, 2021])
        self.assertIsNotNone(result)
        # 底层方法返回 {bank_id, indicator_name, data}
        self.assertIn('data', result)
        self.assertIsInstance(result['data'], dict)
        print(f"  [OK] Returns structure even with no data: {result}")


def run_all_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestSeedData,
        TestBankCRUD,
        TestReportCRUD,
        TestTableData,
        TestAnalysisService,
        TestBankDataService,
        TestEdgeCases,
    ]

    for cls in test_classes:
        tests = loader.loadTestsFromTestCase(cls)
        suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"[SUMMARY] Tests run: {result.testsRun}")
    print(f"[SUMMARY] Failures: {len(result.failures)}")
    print(f"[SUMMARY] Errors:   {len(result.errors)}")
    if result.wasSuccessful():
        print("[SUMMARY] ALL TESTS PASSED!")
    else:
        print("[SUMMARY] SOME TESTS FAILED!")
    print("="*60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
