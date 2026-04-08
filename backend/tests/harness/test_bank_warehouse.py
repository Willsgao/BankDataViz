# -*- coding: utf-8 -*-
"""
[E][E][E][E][E][E] Harness [E][E][E][E]

[E][E][E][E][E]
1. [E][E][E][E][E][E][E][E]
2. [E][E]CRUD[E][E]
3. [E][E]CRUD[E][E]
4. [E][E][E][E]CRUD[E][E]
5. [E][E][E][E][E][E]
6. [E][E][E][E][E][E]
7. [E][E][E][E][E][E]

[E][E][E]
    python -m pytest backend/tests/harness/test_bank_warehouse.py -v
    [E]
    python backend/tests/harness/test_bank_warehouse.py
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

# [E][E][E][E][E][E][E][E][E][E]
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.bank_warehouse.bank_warehouse import BankWarehouseManager
from backend.database.bank_warehouse.bank_schema import (
    TableNames,
    BankType,
    ReportType,
    ReportStatus,
    ProcessingStatus,
    ChangeType,
    MemberLevel,
)


class TestBankWarehouseInit(unittest.TestCase):
    """[E][E][E][E][E][E][E][E]"""

    @classmethod
    def setUpClass(cls):
        """[E][E][E][E][E][E][E]"""
        cls.temp_db = tempfile.NamedTemporaryFile(
            suffix='.db', delete=False
        )
        cls.temp_db.close()
        cls.db_path = cls.temp_db.name
        cls.warehouse = BankWarehouseManager(db_path=cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """[E][E][E][E][E][E][E]"""
        try:
            os.unlink(cls.db_path)
        except:
            pass

    def test_01_init_database(self):
        """[E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        result = self.warehouse.init_database()
        self.assertTrue(result, "[E][E][E][E][E][E][E][E][E][E]")

        # [E][E][E][E][E][E][E]
        self.assertTrue(
            self.warehouse.check_tables_exist(),
            "[E][E][E][E][E][E][E][E]"
        )

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")

    def test_02_database_info(self):
        """[E][E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E][E]")
        print("=" * 60)

        info = self.warehouse.get_database_info()

        print(f"   [E][E][E][E][E]: {info['database_path']}")
        print(f"   [E][E][E][E][E]: {info['database_size_mb']} MB")
        print(f"   [E][E][E]: {info['table_count']}")
        print(f"   [E][E][E]: {info['tables']}")

        self.assertGreater(info['table_count'], 0, "[E][E][E][E][E][E]")
        self.assertIn('banks', info['tables'], "[E][E][E]banks[E]")
        self.assertIn('reports', info['tables'], "[E][E][E]reports[E]")
        self.assertIn('table_data', info['tables'], "[E][E][E]table_data[E]")

        print("[OK] [E][E][E][E][E][E][E][E][E][E][E]")


class TestBankCRUD(unittest.TestCase):
    """[E][E][E][E]CRUD[E][E]"""

    @classmethod
    def setUpClass(cls):
        """[E][E][E][E][E][E][E]"""
        cls.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.temp_db.close()
        cls.db_path = cls.temp_db.name
        cls.warehouse = BankWarehouseManager(db_path=cls.db_path)
        cls.warehouse.init_database()

    @classmethod
    def tearDownClass(cls):
        """[E][E][E][E][E][E][E]"""
        try:
            os.unlink(cls.db_path)
        except:
            pass

    def test_01_save_bank(self):
        """[E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E]")
        print("=" * 60)

        bank_info = {
            'bank_code': 'ICBC',
            'bank_name': '[E][E][E][E][E][E]',
            'bank_type': BankType.STATE_OWNED,
            'listed_status': 'listed',
            'description': '[E][E][E][E][E][E][E][E][E]'
        }

        bank_id = self.warehouse.save_bank(bank_info)
        print(f"   [E][E][E][E]ID: {bank_id}")

        self.assertGreater(bank_id, 0, "[E][E]ID[E][E][E][E]0")

        # [E][E][E][E][E][E][E]
        bank_info2 = {
            'bank_code': 'CMBC',
            'bank_name': '[E][E][E][E]',
            'bank_type': BankType.JOINT_STOCK,
            'listed_status': 'listed'
        }
        bank_id2 = self.warehouse.save_bank(bank_info2)
        self.assertGreater(bank_id2, 0)

        # [E][E][E][E][E][E][E]bank_code[E]
        bank_info_update = {
            'bank_code': 'ICBC',
            'bank_name': '[E][E][E][E][E][E][E][E][E][E][E][E]',
            'description': '[E][E][E][E][E][E]'
        }
        bank_id_update = self.warehouse.save_bank(bank_info_update)
        self.assertEqual(bank_id, bank_id_update, "[E][E][E][E][E][E][E][E]ID")

        print("[OK] [E][E][E][E][E][E][E][E]")

    def test_02_get_bank(self):
        """[E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E]")
        print("=" * 60)

        # [E][E][E][E][E][E][E]
        bank_info = {
            'bank_code': 'CCB',
            'bank_name': '[E][E][E][E][E][E]',
            'bank_type': BankType.STATE_OWNED
        }
        bank_id = self.warehouse.save_bank(bank_info)

        # [E][E]ID[E][E]
        bank = self.warehouse.get_bank(bank_id)
        print(f"   [E][E][E][E]: {bank['bank_name']}")
        print(f"   [E][E][E][E]: {bank['bank_type']}")

        self.assertIsNotNone(bank, "[E][E][E][E][E][E][E][E]")
        self.assertEqual(bank['bank_code'], 'CCB')
        self.assertEqual(bank['bank_name'], '[E][E][E][E][E][E]')

        # [E][E]bank_code[E][E]
        bank2 = self.warehouse.get_bank_by_code('CCB')
        self.assertIsNotNone(bank2, "[E][E][E][E][E]bank_code[E][E]")
        self.assertEqual(bank2['id'], bank_id)

        print("[OK] [E][E][E][E][E][E][E][E]")

    def test_03_get_all_banks(self):
        """[E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        # [E][E][E][E][E][E]
        banks_to_save = [
            {'bank_code': 'ABC', 'bank_name': '[E][E][E][E][E][E]', 'bank_type': BankType.STATE_OWNED},
            {'bank_code': 'BOC', 'bank_name': '[E][E][E][E]', 'bank_type': BankType.STATE_OWNED},
            {'bank_code': 'COMM', 'bank_name': '[E][E][E][E]', 'bank_type': BankType.STATE_OWNED},
        ]
        for bank in banks_to_save:
            self.warehouse.save_bank(bank)

        # [E][E][E][E][E][E]
        all_banks = self.warehouse.get_all_banks()
        print(f"   [E][E][E][E]: {len(all_banks)}")

        self.assertGreater(len(all_banks), 3, "[E][E][E][E][E]3[E][E][E]")

        # [E][E][E][E][E]
        state_banks = self.warehouse.get_all_banks(bank_type=BankType.STATE_OWNED)
        print(f"   [E][E][E][E][E]: {len(state_banks)}")

        for bank in state_banks:
            self.assertEqual(bank['bank_type'], BankType.STATE_OWNED)

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")

    def test_04_search_banks(self):
        """[E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E]")
        print("=" * 60)

        # [E][E]XYZ[E][E]
        unique_keyword = 'XYZ_NOT_EXIST_12345'
        self.warehouse.save_bank({
            'bank_code': 'XYZ',
            'bank_name': f'XYZ[E][E][E]',
            'bank_type': BankType.STATE_OWNED
        })

        # [E][E][E][E][E]
        results = self.warehouse.search_banks('XYZ')
        print(f"   [E][E]'XYZ'[E][E]: {len(results)} [E]")
        self.assertGreater(len(results), 0, "[E][E][E][E][E][E][E][E]")

        # [E][E][E][E][E][E]unique_keyword[E]
        results2 = self.warehouse.search_banks(unique_keyword)
        print(f"   [E][E]'{unique_keyword}'[E][E]: {len(results2)} [E]")
        self.assertEqual(len(results2), 0, "[E][E][E][E][E][E]")

        print("[OK] [E][E][E][E][E][E][E][E]")


class TestReportCRUD(unittest.TestCase):
    """[E][E][E][E]CRUD[E][E]"""

    @classmethod
    def setUpClass(cls):
        """[E][E][E][E][E][E][E]"""
        cls.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.temp_db.close()
        cls.db_path = cls.temp_db.name
        cls.warehouse = BankWarehouseManager(db_path=cls.db_path)
        cls.warehouse.init_database()

        # [E][E][E][E][E][E]
        cls.bank_id = cls.warehouse.save_bank({
            'bank_code': 'TEST',
            'bank_name': '[E][E][E][E]',
            'bank_type': BankType.JOINT_STOCK
        })

    @classmethod
    def tearDownClass(cls):
        """[E][E][E][E][E][E][E]"""
        try:
            os.unlink(cls.db_path)
        except:
            pass

    def test_01_save_report(self):
        """[E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E]")
        print("=" * 60)

        report_info = {
            'bank_id': self.bank_id,
            'report_type': ReportType.ANNUAL,
            'period': '2024A',
            'report_date': '2024-03-29',
            'fiscal_year': 2024,
            'pdf_path': '/path/to/report.pdf',
            'status': ReportStatus.COMPLETED
        }

        report_id = self.warehouse.save_report(report_info)
        print(f"   [E][E][E][E]ID: {report_id}")

        self.assertGreater(report_id, 0, "[E][E]ID[E][E][E][E]0")

        # [E][E][E][E][E][E][E][E][E][E]
        report_info2 = {
            'bank_id': self.bank_id,
            'report_type': ReportType.ANNUAL,
            'period': '2024A',
            'pdf_path': '/path/to/new_report.pdf',
            'status': ReportStatus.COMPLETED
        }
        report_id2 = self.warehouse.save_report(report_info2)
        self.assertEqual(report_id, report_id2, "[E][E][E][E][E][E][E]ID")

        print("[OK] [E][E][E][E][E][E][E][E]")

    def test_02_get_reports_by_bank(self):
        """[E][E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        # [E][E][E][E][E][E]
        for year in [2022, 2023, 2024]:
            self.warehouse.save_report({
                'bank_id': self.bank_id,
                'report_type': ReportType.ANNUAL,
                'period': f'{year}A',
                'fiscal_year': year,
                'report_date': f'{year + 1}-03-29'
            })

        # [E][E][E][E][E][E]
        reports = self.warehouse.get_reports_by_bank(self.bank_id)
        print(f"   [E][E][E][E]: {len(reports)}")

        self.assertGreater(len(reports), 0, "[E][E][E][E][E]")

        # [E][E][E][E][E]
        reports_2024 = self.warehouse.get_reports_by_bank(
            self.bank_id, fiscal_year=2024
        )
        self.assertEqual(len(reports_2024), 1, "2024[E][E][E][E]1[E][E][E]")

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")


class TestTableDataCRUD(unittest.TestCase):
    """[E][E][E][E][E][E]CRUD[E][E]"""

    @classmethod
    def setUpClass(cls):
        """[E][E][E][E][E][E][E]"""
        cls.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.temp_db.close()
        cls.db_path = cls.temp_db.name
        cls.warehouse = BankWarehouseManager(db_path=cls.db_path)
        cls.warehouse.init_database()

        # [E][E][E][E][E][E][E][E][E]
        cls.bank_id = cls.warehouse.save_bank({
            'bank_code': 'TEST2',
            'bank_name': '[E][E][E][E]2',
            'bank_type': BankType.CITY_COMMERCIAL
        })
        cls.report_id = cls.warehouse.save_report({
            'bank_id': cls.bank_id,
            'report_type': ReportType.ANNUAL,
            'period': '2024A',
            'fiscal_year': 2024
        })

    @classmethod
    def tearDownClass(cls):
        """[E][E][E][E][E][E][E]"""
        try:
            os.unlink(cls.db_path)
        except:
            pass

    def test_01_save_table_data(self):
        """[E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        data_info = {
            'report_id': self.report_id,
            'table_name': '[E][E][E]',
            'table_category': 'income',
            'page_number': 10,
            'row_index': 0,
            'indicator_name': '[E][E][E][E]',
            'value_json': '{"2022": 3000.5, "2023": 3200.8, "2024": 3500.2}',
            'unit': '[E][E]'
        }

        data_id = self.warehouse.save_table_data(data_info)
        print(f"   [E][E][E][E]ID: {data_id}")

        self.assertGreater(data_id, 0, "[E][E]ID[E][E][E][E]0")

        # [E][E][E][E][E][E][E]
        data_info2 = {
            'report_id': self.report_id,
            'table_name': '[E][E][E]',
            'page_number': 10,
            'row_index': 1,
            'indicator_name': '[E][E][E]',
            'value_json': '{"2022": 900.1, "2023": 1000.5, "2024": 1100.8}'
        }
        data_id2 = self.warehouse.save_table_data(data_info2)
        self.assertGreater(data_id2, 0)

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")

    def test_02_save_batch_table_data(self):
        """[E][E][E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E][E][E]")
        print("=" * 60)

        rows = [
            {
                'indicator_name': '[E][E][E][E]',
                'page_number': 5,
                'value_2022': 15000.0,
                'value_2023': 16000.0,
                'value_2024': 17000.0,
                'unit': '[E][E]'
            },
            {
                'indicator_name': '[E][E][E][E]',
                'page_number': 5,
                'value_2022': 13500.0,
                'value_2023': 14400.0,
                'value_2024': 15300.0,
                'unit': '[E][E]'
            },
            {
                'indicator_name': '[E][E][E][E][E]',
                'page_number': 5,
                'value_2022': 1500.0,
                'value_2023': 1600.0,
                'value_2024': 1700.0,
                'unit': '[E][E]'
            }
        ]

        count = self.warehouse.save_batch_table_data(
            report_id=self.report_id,
            table_name='[E][E][E][E][E]',
            rows=rows,
            source_info={'pdf_path': '/path/to/report.pdf'}
        )

        print(f"   [E][E][E][E]: {count} [E]")

        self.assertEqual(count, 3, "[E][E][E][E]3[E][E][E]")

        print("[OK] [E][E][E][E][E][E][E][E][E][E][E][E]")

    def test_03_get_table_data(self):
        """[E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        data_list = self.warehouse.get_table_data_by_report(
            self.report_id, table_name='[E][E][E]'
        )

        print(f"   [E][E][E][E][E]: {len(data_list)} [E]")

        self.assertGreater(len(data_list), 0, "[E][E][E][E][E]")

        # [E][E]value_dict
        for data in data_list:
            if data.get('value_json'):
                self.assertIn('value_dict', data)
                print(f"   {data['indicator_name']}: {data['value_dict']}")

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")


class TestDataSource(unittest.TestCase):
    """[E][E][E][E][E][E]"""

    @classmethod
    def setUpClass(cls):
        """[E][E][E][E][E][E][E]"""
        cls.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.temp_db.close()
        cls.db_path = cls.temp_db.name
        cls.warehouse = BankWarehouseManager(db_path=cls.db_path)
        cls.warehouse.init_database()

        # [E][E][E][E][E][E]
        cls.bank_id = cls.warehouse.save_bank({
            'bank_code': 'SRC',
            'bank_name': '[E][E][E][E][E][E]'
        })
        cls.report_id = cls.warehouse.save_report({
            'bank_id': cls.bank_id,
            'report_type': ReportType.ANNUAL,
            'period': '2024A'
        })
        cls.data_id = cls.warehouse.save_table_data({
            'report_id': cls.report_id,
            'table_name': '[E][E][E]',
            'indicator_name': '[E][E][E][E]',
            'page_number': 1
        })

    @classmethod
    def tearDownClass(cls):
        """[E][E][E][E][E][E][E]"""
        try:
            os.unlink(cls.db_path)
        except:
            pass

    def test_01_save_data_source(self):
        """[E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        source_info = {
            'table_data_id': self.data_id,
            'pdf_path': '/path/to/test_report.pdf',
            'page_number': 5,
            'pdf_hash': 'abc123hash',
            'image_path': '/path/to/page_5.png',
            'confidence_score': 0.95
        }

        source_id = self.warehouse.save_data_source(source_info)
        print(f"   [E][E]ID: {source_id}")

        self.assertGreater(source_id, 0, "[E][E]ID[E][E][E][E]0")

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")

    def test_02_get_data_sources(self):
        """[E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        sources = self.warehouse.get_data_sources(self.data_id)
        print(f"   [E][E][E][E][E]: {len(sources)}")

        self.assertGreater(len(sources), 0, "[E][E][E][E][E][E][E]")
        self.assertEqual(sources[0]['pdf_path'], '/path/to/test_report.pdf')

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")


class TestDataVersion(unittest.TestCase):
    """[E][E][E][E][E][E]"""

    @classmethod
    def setUpClass(cls):
        """[E][E][E][E][E][E][E]"""
        cls.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.temp_db.close()
        cls.db_path = cls.temp_db.name
        cls.warehouse = BankWarehouseManager(db_path=cls.db_path)
        cls.warehouse.init_database()

        # [E][E][E][E][E][E]
        cls.bank_id = cls.warehouse.save_bank({
            'bank_code': 'VER',
            'bank_name': '[E][E][E][E][E][E]'
        })
        cls.report_id = cls.warehouse.save_report({
            'bank_id': cls.bank_id,
            'report_type': ReportType.ANNUAL,
            'period': '2024A'
        })
        cls.data_id = cls.warehouse.save_table_data({
            'report_id': cls.report_id,
            'table_name': '[E][E][E]',
            'indicator_name': '[E][E][E][E]',
            'value_json': '{"2024": 1000}'
        })

    @classmethod
    def tearDownClass(cls):
        """[E][E][E][E][E][E][E]"""
        try:
            os.unlink(cls.db_path)
        except:
            pass

    def test_01_save_data_version(self):
        """[E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        # [E][E][E][E]
        version1 = self.warehouse.save_data_version(
            table_data_id=self.data_id,
            change_type=ChangeType.INITIAL,
            old_value=None,
            new_value={'2024': 1000},
            changed_by='system'
        )
        print(f"   [E][E]1: {version1}")
        self.assertEqual(version1, 1, "[E][E][E][E][E][E][E]1")

        # [E][E][E][E]
        version2 = self.warehouse.save_data_version(
            table_data_id=self.data_id,
            change_type=ChangeType.MANUAL_EDIT,
            old_value={'2024': 1000},
            new_value={'2024': 1050},
            changed_by='admin',
            change_reason='[E][E][E][E]'
        )
        print(f"   [E][E]2: {version2}")
        self.assertEqual(version2, 2, "[E][E][E][E][E][E][E][E]2")

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")

    def test_02_get_data_versions(self):
        """[E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        versions = self.warehouse.get_data_versions(self.data_id)
        print(f"   [E][E][E][E][E]: {len(versions)}")

        self.assertEqual(len(versions), 2, "[E][E][E]2[E][E][E][E][E]")

        # [E][E][E][E][E][E]
        self.assertEqual(versions[0]['version'], 2, "[E][E][E][E][E][E][E]2")
        self.assertEqual(versions[1]['version'], 1, "[E][E][E][E][E][E]1")

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")


class TestStatistics(unittest.TestCase):
    """[E][E][E][E][E][E]"""

    @classmethod
    def setUpClass(cls):
        """[E][E][E][E][E][E][E]"""
        cls.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.temp_db.close()
        cls.db_path = cls.temp_db.name
        cls.warehouse = BankWarehouseManager(db_path=cls.db_path)
        cls.warehouse.init_database()

        # [E][E][E][E][E][E]
        for i, btype in enumerate([BankType.STATE_OWNED, BankType.JOINT_STOCK, BankType.CITY_COMMERCIAL]):
            bank_id = cls.warehouse.save_bank({
                'bank_code': f'STAT{i}',
                'bank_name': f'[E][E][E][E][E][E]{i}',
                'bank_type': btype
            })
            for year in [2022, 2023, 2024]:
                cls.warehouse.save_report({
                    'bank_id': bank_id,
                    'report_type': ReportType.ANNUAL,
                    'period': f'{year}A',
                    'fiscal_year': year
                })

    @classmethod
    def tearDownClass(cls):
        """[E][E][E][E][E][E][E]"""
        try:
            os.unlink(cls.db_path)
        except:
            pass

    def test_01_get_statistics(self):
        """[E][E][E][E][E][E][E][E]"""
        print("\n" + "=" * 60)
        print("[TEST] [E][E]: [E][E][E][E][E][E]")
        print("=" * 60)

        stats = self.warehouse.get_statistics()

        print(f"   [E][E][E][E]: {stats.get('banks', 0)}")
        print(f"   [E][E][E][E]: {stats.get('reports', 0)}")

        # [E][E][E][E][E][E]
        print("   [E][E][E][E][E][E]:")
        for item in stats.get('bank_type_distribution', []):
            print(f"      - {item['type']}: {item['count']}")

        # [E][E][E][E]
        print("   [E][E][E][E][E][E]:")
        for item in stats.get('report_year_distribution', []):
            print(f"      - {item['year']}[E]: {item['count']}[E]")

        self.assertGreater(stats.get('banks', 0), 0, "[E][E][E][E][E][E][E]")
        self.assertGreater(stats.get('reports', 0), 0, "[E][E][E][E][E][E][E]")

        print("[OK] [E][E][E][E][E][E][E][E][E][E]")


# ============================================================
# [E][E][E][E]
# ============================================================

def run_tests():
    """[E][E][E][E][E][E]"""
    print("\n" + "=" * 80)
    print("[TEST] [E][E][E][E][E][E] Harness [E][E][E][E]")
    print("=" * 80)

    # [E][E][E][E][E][E]
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # [E][E][E][E][E]
    suite.addTests(loader.loadTestsFromTestCase(TestBankWarehouseInit))
    suite.addTests(loader.loadTestsFromTestCase(TestBankCRUD))
    suite.addTests(loader.loadTestsFromTestCase(TestReportCRUD))
    suite.addTests(loader.loadTestsFromTestCase(TestTableDataCRUD))
    suite.addTests(loader.loadTestsFromTestCase(TestDataSource))
    suite.addTests(loader.loadTestsFromTestCase(TestDataVersion))
    suite.addTests(loader.loadTestsFromTestCase(TestStatistics))

    # [E][E][E][E]
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # [E][E][E][E][E][E]
    print("\n" + "=" * 80)
    print("[TEST] [E][E][E][E][E][E]")
    print("=" * 80)
    print(f"   [E][E][E][E]: {result.testsRun}")
    print(f"   [E][E]: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   [E][E]: {len(result.failures)}")
    print(f"   [E][E]: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n[TEST] [E][E][E][E][E][E][E]")
    else:
        print("\n[X] [E][E][E][E][E][E][E][E][E][E]")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
