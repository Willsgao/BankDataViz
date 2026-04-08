# -*- coding: utf-8 -*-
"""
[E][E][E][E][E][E][E][E][E] - [E][E][E][E][E][E][E][E]

[E][E][E]
1. [E][E][E][E][E][E][E][E][E]
2. [E][E][E][E]CRUD
3. [E][E][E][E]CRUD
4. [E][E][E][E]CRUD
5. [E][E][E][E][E][E]
6. [E][E][E][E][E][E]

[E][E][E]DocuVista Team
[E][E][E]1.0.0
"""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

# [E][E][E][E][E][E][E]
from .bank_schema import (
    TableNames,
    BankType,
    ReportType,
    ReportStatus,
    ProcessingStatus,
    ChangeType,
    MemberLevel,
    ALL_TABLES,
)


class BankWarehouseManager:
    """
    [E][E][E][E][E][E][E][E][E]

    [E][E][E][E][E]
        # [E][E][E]
        warehouse = BankWarehouseManager()

        # [E][E][E][E][E][E][E]
        warehouse.init_database()

        # [E][E][E][E]
        bank_id = warehouse.save_bank({
            'bank_code': 'ICBC',
            'bank_name': '[E][E][E][E][E][E]',
            'bank_type': '[E][E][E][E][E][E]'
        })

        # [E][E][E][E]
        report_id = warehouse.save_report({
            'bank_id': bank_id,
            'report_type': 'annual',
            'period': '2024A',
            'report_date': '2024-03-29'
        })

        # [E][E][E][E][E][E]
        warehouse.save_table_data({
            'report_id': report_id,
            'table_name': '[E][E][E]',
            'indicator_name': '[E][E][E]',
            'value_json': '{"2020": 3159.06, "2021": 3483.38, "2022": 3604.83}'
        })
    """

    def __init__(self, db_path: str = None):
        """
        [E][E][E][E][E][E][E][E][E][E][E][E]

        Args:
            db_path: [E][E][E][E][E][E][E][E][E][E][E][E][E][E][E][E][E]
        """
        # [E][E][E][E][E][E][E]
        if db_path is None:
            from backend.configs.config import config
            self.db_path = config.DATABASE_PATH
        else:
            self.db_path = db_path

        # [E][E][E][E][E][E][E][E][E]
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        print(f"[BankWarehouseManager] [E][E][E][E][E]: {self.db_path}")
        print(f"[BankWarehouseManager] [E][E][E][E][E]: {os.path.exists(self.db_path)}")

    # ============================================================
    # [E][E][E][E][E][E][E]
    # ============================================================

    @contextmanager
    def get_connection(self):
        """
        [E][E][E][E][E][E][E][E][E][E][E][E][E][E]

        [E][E][E]
            with warehouse.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM banks")
                ...
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def connect(self) -> sqlite3.Connection:
        """[E][E][E][E][E][E][E]"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ============================================================
    # [E][E][E][E][E][E]
    # ============================================================

    def init_database(self) -> bool:
        """
        [E][E][E][E][E][E][E][E][E]

        Returns:
            bool: [E][E][E][E]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                print("=" * 60)
                print("[BUILD]  [E][E][E][E][E][E][E][E][E][E][E][E]...")
                print("=" * 60)

                for table_name, create_sql in ALL_TABLES:
                    print(f"[TABLE] [E][E][E]: {table_name}")
                    cursor.executescript(create_sql)

                conn.commit()

                print("=" * 60)
                print("[OK] [E][E][E][E][E][E][E][E][E][E][E][E][E][E]!")
                print("=" * 60)

                # [E][E][E][E][E]
                self._print_table_info()

                return True

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _print_table_info(self):
        """[E][E][E][E][E][E][E][E]"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = cursor.fetchall()

            print("\n[STATS] [E][E][E][E][E][E]:")
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"   - {table_name}: {count} [E][E][E]")

    def check_tables_exist(self) -> bool:
        """
        [E][E][E][E][E][E][E][E][E][E][E][E][E]

        Returns:
            bool: [E][E][E][E][E][E][E]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                existing_tables = {row[0] for row in cursor.fetchall()}

                required_tables = {name for name, _ in ALL_TABLES}
                missing_tables = required_tables - existing_tables

                if missing_tables:
                    print(f"[WARN] [E][E][E]: {missing_tables}")
                    return False

                return True

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E]: {e}")
            return False

    # ============================================================
    # [E][E][E][E]CRUD
    # ============================================================

    def save_bank(self, bank_info: Dict[str, Any]) -> int:
        """
        [E][E][E][E][E][E]

        Args:
            bank_info: [E][E][E][E][E][E][E][E][E][E]
                - bank_code: [E][E][E][E]
                - bank_name: [E][E][E][E]
                - bank_type: [E][E][E][E]
                - listed_status: [E][E][E][E]
                - description: [E][E]
                - ([E][E]) swift_code, isin, country_code [E][E][E][E][E]

        Returns:
            int: [E][E]ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # [E][E][E][E][E][E][E]
                bank_code = bank_info.get('bank_code')
                if bank_code:
                    cursor.execute(
                        "SELECT id FROM banks WHERE bank_code = ?",
                        (bank_code,)
                    )
                    existing = cursor.fetchone()

                    if existing:
                        # [E][E]
                        bank_id = existing[0]
                        self._update_bank(cursor, bank_id, bank_info)
                        print(f"[OK] [E][E][E][E]: {bank_info.get('bank_name')} (ID: {bank_id})")
                    else:
                        # [E][E]
                        bank_id = self._insert_bank(cursor, bank_info)
                        print(f"[OK] [E][E][E][E]: {bank_info.get('bank_name')} (ID: {bank_id})")
                else:
                    # [E]bank_code[E][E][E][E][E][E][E][E]
                    bank_name = bank_info.get('bank_name')
                    cursor.execute(
                        "SELECT id FROM banks WHERE bank_name = ?",
                        (bank_name,)
                    )
                    existing = cursor.fetchone()

                    if existing:
                        bank_id = existing[0]
                        self._update_bank(cursor, bank_id, bank_info)
                    else:
                        bank_id = self._insert_bank(cursor, bank_info)
                        print(f"[OK] [E][E][E][E]: {bank_name} (ID: {bank_id})")

                conn.commit()
                return bank_id

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E]: {e}")
            import traceback
            traceback.print_exc()
            return -1

    def _insert_bank(self, cursor, bank_info: Dict[str, Any]) -> int:
        """[E][E][E][E][E][E]"""
        cursor.execute("""
            INSERT INTO banks (
                bank_code, bank_name, bank_type, listed_status,
                description, swift_code, isin, country_code,
                country_name, base_currency, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bank_info.get('bank_code'),
            bank_info.get('bank_name'),
            bank_info.get('bank_type'),
            bank_info.get('listed_status', 'listed'),
            bank_info.get('description'),
            bank_info.get('swift_code'),
            bank_info.get('isin'),
            bank_info.get('country_code'),
            bank_info.get('country_name'),
            bank_info.get('base_currency', 'CNY'),
            bank_info.get('status', 'active')
        ))
        return cursor.lastrowid

    def _update_bank(self, cursor, bank_id: int, bank_info: Dict[str, Any]):
        """[E][E][E][E][E][E]"""
        cursor.execute("""
            UPDATE banks SET
                bank_name = COALESCE(?, bank_name),
                bank_type = COALESCE(?, bank_type),
                listed_status = COALESCE(?, listed_status),
                description = COALESCE(?, description),
                swift_code = COALESCE(?, swift_code),
                isin = COALESCE(?, isin),
                country_code = COALESCE(?, country_code),
                country_name = COALESCE(?, country_name),
                base_currency = COALESCE(?, base_currency),
                status = COALESCE(?, status),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            bank_info.get('bank_name'),
            bank_info.get('bank_type'),
            bank_info.get('listed_status'),
            bank_info.get('description'),
            bank_info.get('swift_code'),
            bank_info.get('isin'),
            bank_info.get('country_code'),
            bank_info.get('country_name'),
            bank_info.get('base_currency'),
            bank_info.get('status'),
            bank_id
        ))

    def get_bank(self, bank_id: int) -> Optional[Dict[str, Any]]:
        """[E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM banks WHERE id = ?", (bank_id,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E]: {e}")
            return None

    def get_bank_by_code(self, bank_code: str) -> Optional[Dict[str, Any]]:
        """[E][E][E][E][E][E][E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM banks WHERE bank_code = ?",
                    (bank_code,)
                )
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E]: {e}")
            return None

    def get_all_banks(
        self,
        bank_type: str = None,
        listed_status: str = None,
        status: str = 'active',
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """[E][E][E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                sql = "SELECT * FROM banks WHERE 1=1"
                params = []

                if bank_type:
                    sql += " AND bank_type = ?"
                    params.append(bank_type)

                if listed_status:
                    sql += " AND listed_status = ?"
                    params.append(listed_status)

                if status:
                    sql += " AND status = ?"
                    params.append(status)

                sql += " ORDER BY bank_name LIMIT ?"
                params.append(limit)

                cursor.execute(sql, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            return []

    def search_banks(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """[E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM banks
                    WHERE bank_name LIKE ? OR bank_code LIKE ?
                    ORDER BY bank_name
                    LIMIT ?
                """, (f'%{keyword}%', f'%{keyword}%', limit))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E]: {e}")
            return []

    # ============================================================
    # [E][E][E][E]CRUD
    # ============================================================

    def save_report(self, report_info: Dict[str, Any]) -> int:
        """
        [E][E][E][E][E][E]

        Args:
            report_info: [E][E][E][E][E][E]

        Returns:
            int: [E][E]ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # [E][E][E][E][E][E][E]
                cursor.execute("""
                    SELECT id FROM reports
                    WHERE bank_id = ? AND report_type = ? AND period = ?
                """, (
                    report_info.get('bank_id'),
                    report_info.get('report_type'),
                    report_info.get('period')
                ))
                existing = cursor.fetchone()

                if existing:
                    # [E][E]
                    report_id = existing[0]
                    self._update_report(cursor, report_id, report_info)
                    print(f"[OK] [E][E][E][E] ID: {report_id}")
                else:
                    # [E][E]
                    report_id = self._insert_report(cursor, report_info)
                    print(f"[OK] [E][E][E][E] ID: {report_id}")

                conn.commit()
                return report_id

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E]: {e}")
            import traceback
            traceback.print_exc()
            return -1

    def _insert_report(self, cursor, report_info: Dict[str, Any]) -> int:
        """[E][E][E][E][E][E]"""
        cursor.execute("""
            INSERT INTO reports (
                bank_id, report_type, period, report_date,
                fiscal_year, fiscal_quarter, reporting_standard,
                pdf_filename, pdf_path, pdf_hash, status,
                excel_output_path, source_pdf_folder, source_pages
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_info.get('bank_id'),
            report_info.get('report_type'),
            report_info.get('period'),
            report_info.get('report_date'),
            report_info.get('fiscal_year'),
            report_info.get('fiscal_quarter'),
            report_info.get('reporting_standard', 'CAS'),
            report_info.get('pdf_filename'),
            report_info.get('pdf_path'),
            report_info.get('pdf_hash'),
            report_info.get('status', 'pending'),
            report_info.get('excel_output_path'),
            report_info.get('source_pdf_folder'),
            json.dumps(report_info.get('source_pages', [])) if report_info.get('source_pages') else None
        ))
        return cursor.lastrowid

    def _update_report(self, cursor, report_id: int, report_info: Dict[str, Any]):
        """[E][E][E][E][E][E]"""
        cursor.execute("""
            UPDATE reports SET
                pdf_filename = COALESCE(?, pdf_filename),
                pdf_path = COALESCE(?, pdf_path),
                pdf_hash = COALESCE(?, pdf_hash),
                status = COALESCE(?, status),
                excel_output_path = COALESCE(?, excel_output_path),
                source_pdf_folder = COALESCE(?, source_pdf_folder),
                source_pages = COALESCE(?, source_pages),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            report_info.get('pdf_filename'),
            report_info.get('pdf_path'),
            report_info.get('pdf_hash'),
            report_info.get('status'),
            report_info.get('excel_output_path'),
            report_info.get('source_pdf_folder'),
            json.dumps(report_info.get('source_pages')) if report_info.get('source_pages') else None,
            report_id
        ))

    def get_reports_by_bank(
        self,
        bank_id: int,
        report_type: str = None,
        fiscal_year: int = None
    ) -> List[Dict[str, Any]]:
        """[E][E][E][E][E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                sql = "SELECT * FROM reports WHERE bank_id = ?"
                params = [bank_id]

                if report_type:
                    sql += " AND report_type = ?"
                    params.append(report_type)

                if fiscal_year:
                    sql += " AND fiscal_year = ?"
                    params.append(fiscal_year)

                sql += " ORDER BY fiscal_year DESC, report_date DESC"

                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            return []

    def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        """[E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
                row = cursor.fetchone()

                if row:
                    result = dict(row)
                    # [E][E]source_pages JSON
                    if result.get('source_pages'):
                        try:
                            result['source_pages'] = json.loads(result['source_pages'])
                        except:
                            pass
                    return result
                return None

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E]: {e}")
            return None

    # ============================================================
    # [E][E][E][E]CRUD
    # ============================================================

    def save_table_data(self, data_info: Dict[str, Any]) -> int:
        """
        [E][E][E][E][E][E]

        Args:
            data_info: [E][E][E][E][E][E]

        Returns:
            int: [E][E]ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # [E][E][E][E][E][E][E]
                cursor.execute("""
                    SELECT id FROM table_data
                    WHERE report_id = ? AND table_name = ?
                    AND indicator_name = ? AND page_number = ?
                """, (
                    data_info.get('report_id'),
                    data_info.get('table_name'),
                    data_info.get('indicator_name'),
                    data_info.get('page_number')
                ))
                existing = cursor.fetchone()

                if existing:
                    data_id = existing[0]
                    self._update_table_data(cursor, data_id, data_info)
                else:
                    data_id = self._insert_table_data(cursor, data_info)

                conn.commit()
                return data_id

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            import traceback
            traceback.print_exc()
            return -1

    def save_batch_table_data(
        self,
        report_id: int,
        table_name: str,
        rows: List[Dict[str, Any]],
        source_info: Dict[str, Any] = None
    ) -> int:
        """
        [E][E][E][E][E][E][E][E]

        Args:
            report_id: [E][E]ID
            table_name: [E][E][E][E]
            rows: [E][E][E][E][E]
            source_info: [E][E][E][E]

        Returns:
            int: [E][E][E][E][E][E][E]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                count = 0

                for row_index, row in enumerate(rows):
                    # [E][E][E][E][E][E]
                    value_json = {}
                    for year in range(2020, 2026):
                        key = f'value_{year}'
                        if key in row and row[key] is not None:
                            try:
                                value_json[str(year)] = float(row[key])
                            except (ValueError, TypeError):
                                pass

                    data_info = {
                        'report_id': report_id,
                        'table_name': table_name,
                        'table_category': row.get('table_category'),
                        'page_number': row.get('page_number'),
                        'row_index': row_index,
                        'indicator_name': row.get('indicator_name', row.get('[E][E][E][E]', '')),
                        'indicator_code': row.get('indicator_code'),
                        'value_json': json.dumps(value_json) if value_json else None,
                        'unit': row.get('unit', '[E][E]'),
                        'notes': row.get('notes')
                    }

                    cursor.execute("""
                        SELECT id FROM table_data
                        WHERE report_id = ? AND table_name = ?
                        AND indicator_name = ? AND page_number = ?
                    """, (
                        report_id,
                        table_name,
                        data_info['indicator_name'],
                        data_info['page_number']
                    ))
                    existing = cursor.fetchone()

                    if existing:
                        self._update_table_data(cursor, existing[0], data_info)
                    else:
                        self._insert_table_data(cursor, data_info)

                    count += 1

                    # [E][E][E][E][E][E]
                    if source_info and existing is None:
                        pass  # [E][E][E][E][E][E][E]

                conn.commit()
                print(f"[OK] [E][E][E][E] {count} [E][E][E]")
                return count

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E]: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def _insert_table_data(self, cursor, data_info: Dict[str, Any]) -> int:
        """[E][E][E][E][E][E]"""
        cursor.execute("""
            INSERT INTO table_data (
                report_id, table_name, table_category,
                page_number, row_index, indicator_name,
                indicator_code, value_json, unit,
                is_adjusted, adjusted_value, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data_info.get('report_id'),
            data_info.get('table_name'),
            data_info.get('table_category'),
            data_info.get('page_number'),
            data_info.get('row_index'),
            data_info.get('indicator_name'),
            data_info.get('indicator_code'),
            data_info.get('value_json'),
            data_info.get('unit', '[E][E]'),
            data_info.get('is_adjusted', 0),
            data_info.get('adjusted_value'),
            data_info.get('notes')
        ))
        return cursor.lastrowid

    def _update_table_data(self, cursor, data_id: int, data_info: Dict[str, Any]):
        """[E][E][E][E][E][E]"""
        cursor.execute("""
            UPDATE table_data SET
                value_json = COALESCE(?, value_json),
                unit = COALESCE(?, unit),
                is_adjusted = COALESCE(?, is_adjusted),
                adjusted_value = COALESCE(?, adjusted_value),
                notes = COALESCE(?, notes),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            data_info.get('value_json'),
            data_info.get('unit'),
            data_info.get('is_adjusted'),
            data_info.get('adjusted_value'),
            data_info.get('notes'),
            data_id
        ))

    def get_table_data_by_report(
        self,
        report_id: int,
        table_name: str = None
    ) -> List[Dict[str, Any]]:
        """[E][E][E][E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                sql = "SELECT * FROM table_data WHERE report_id = ?"
                params = [report_id]

                if table_name:
                    sql += " AND table_name = ?"
                    params.append(table_name)

                sql += " ORDER BY table_name, row_index"

                cursor.execute(sql, params)
                rows = cursor.fetchall()

                result = []
                for row in rows:
                    item = dict(row)
                    # [E][E]value_json
                    if item.get('value_json'):
                        try:
                            item['value_dict'] = json.loads(item['value_json'])
                        except:
                            item['value_dict'] = {}
                    result.append(item)

                return result

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            return []

    def get_indicator_trend(
        self,
        bank_id: int,
        indicator_name: str,
        years: List[int] = None
    ) -> Dict[str, Any]:
        """[E][E][E][E][E][E][E][E][E][E][E][E][E]"""
        try:
            if years is None:
                years = [2020, 2021, 2022, 2023, 2024]

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # [E][E][E][E][E][E][E][E][E][E][E]
                cursor.execute("""
                    SELECT id, fiscal_year, period
                    FROM reports
                    WHERE bank_id = ? AND report_type = 'annual'
                    ORDER BY fiscal_year DESC
                """, (bank_id,))

                reports = cursor.fetchall()

                result = {
                    'bank_id': bank_id,
                    'indicator_name': indicator_name,
                    'data': {}
                }

                for report in reports:
                    report_id, fiscal_year, period = report['id'], report['fiscal_year'], report['period']

                    cursor.execute("""
                        SELECT value_json FROM table_data
                        WHERE report_id = ? AND indicator_name = ?
                    """, (report_id, indicator_name))

                    row = cursor.fetchone()
                    if row and row['value_json']:
                        try:
                            value_dict = json.loads(row['value_json'])
                            result['data'][fiscal_year] = value_dict.get(str(fiscal_year))
                        except:
                            pass

                return result

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            return {}

    # ============================================================
    # [E][E][E][E]
    # ============================================================

    def save_data_source(self, source_info: Dict[str, Any]) -> int:
        """[E][E][E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO data_sources (
                        table_data_id, pdf_path, page_number, pdf_hash,
                        image_path, image_hash, ocr_cache_path,
                        llm_cache_path, llm_response, confidence_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_info.get('table_data_id'),
                    source_info.get('pdf_path'),
                    source_info.get('page_number'),
                    source_info.get('pdf_hash'),
                    source_info.get('image_path'),
                    source_info.get('image_hash'),
                    source_info.get('ocr_cache_path'),
                    source_info.get('llm_cache_path'),
                    source_info.get('llm_response'),
                    source_info.get('confidence_score')
                ))

                conn.commit()
                return cursor.lastrowid

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            return -1

    def get_data_sources(self, table_data_id: int) -> List[Dict[str, Any]]:
        """[E][E][E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM data_sources
                    WHERE table_data_id = ?
                    ORDER BY created_at DESC
                """, (table_data_id,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            return []

    # ============================================================
    # [E][E][E][E]
    # ============================================================

    def save_data_version(
        self,
        table_data_id: int,
        change_type: str,
        old_value: Any,
        new_value: Any,
        changed_by: str = None,
        change_reason: str = None
    ) -> int:
        """[E][E][E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # [E][E][E][E][E][E][E]
                cursor.execute("""
                    SELECT MAX(version) FROM data_versions
                    WHERE table_data_id = ?
                """, (table_data_id,))
                max_version = cursor.fetchone()[0] or 0
                new_version = max_version + 1

                # [E][E][E][E][E][E][E]JSON[E]
                old_value_json = json.dumps(old_value) if isinstance(old_value, (dict, list)) else str(old_value) if old_value else None
                new_value_json = json.dumps(new_value) if isinstance(new_value, (dict, list)) else str(new_value) if new_value else None

                cursor.execute("""
                    INSERT INTO data_versions (
                        table_data_id, version, change_type,
                        old_value, new_value, old_value_json, new_value_json,
                        changed_by, change_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    table_data_id,
                    new_version,
                    change_type,
                    old_value_json,
                    new_value_json,
                    old_value_json,
                    new_value_json,
                    changed_by,
                    change_reason
                ))

                conn.commit()
                return new_version

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            return -1

    def get_data_versions(self, table_data_id: int) -> List[Dict[str, Any]]:
        """[E][E][E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM data_versions
                    WHERE table_data_id = ?
                    ORDER BY version DESC
                """, (table_data_id,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            return []

    # ============================================================
    # [E][E][E][E]
    # ============================================================

    def get_statistics(self) -> Dict[str, Any]:
        """[E][E][E][E][E][E][E][E][E]"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                stats = {}

                # [E][E][E][E][E][E][E]
                for table_name, _ in ALL_TABLES:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    stats[table_name] = cursor.fetchone()[0]

                # [E][E][E][E][E][E]
                cursor.execute("""
                    SELECT bank_type, COUNT(*) as count
                    FROM banks
                    WHERE bank_type IS NOT NULL
                    GROUP BY bank_type
                """)
                stats['bank_type_distribution'] = [
                    {'type': row[0], 'count': row[1]}
                    for row in cursor.fetchall()
                ]

                # [E][E][E][E][E][E]
                cursor.execute("""
                    SELECT fiscal_year, COUNT(*) as count
                    FROM reports
                    WHERE fiscal_year IS NOT NULL
                    GROUP BY fiscal_year
                    ORDER BY fiscal_year DESC
                    LIMIT 10
                """)
                stats['report_year_distribution'] = [
                    {'year': row[0], 'count': row[1]}
                    for row in cursor.fetchall()
                ]

                return stats

        except Exception as e:
            print(f"[ERR] [E][E][E][E][E][E][E][E]: {e}")
            return {}

    def get_database_info(self) -> Dict[str, Any]:
        """[E][E][E][E][E][E][E][E][E]"""
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]

        return {
            'database_path': self.db_path,
            'database_size_mb': round(db_size / 1024 / 1024, 2),
            'table_count': len(tables),
            'tables': tables
        }
