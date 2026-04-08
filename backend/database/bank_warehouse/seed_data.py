# -*- coding: utf-8 -*-
"""
银行数据仓库 - 演示种子数据

用于前端演示，写入真实的中国上市银行样本数据。
包含：6大国有银行 + 部分股份制银行，含2020-2024年关键财务指标。

运行方式：
    python -m backend.database.bank_warehouse.seed_data
"""

import json
from backend.database.bank_warehouse.bank_warehouse import BankWarehouseManager
from backend.database.bank_warehouse.bank_schema import BankType, ReportType


# ============================================================
# 银行基础数据
# ============================================================
BANKS_DATA = [
    # 国有大型银行
    {"bank_code": "ICBC",  "bank_name": "中国工商银行", "bank_type": BankType.STATE_OWNED,    "listed_status": "listed", "description": "全球最大商业银行之一"},
    {"bank_code": "CCB",   "bank_name": "中国建设银行", "bank_type": BankType.STATE_OWNED,    "listed_status": "listed", "description": "中国第二大国有银行"},
    {"bank_code": "ABC",   "bank_name": "中国农业银行", "bank_type": BankType.STATE_OWNED,    "listed_status": "listed", "description": "中国三农金融主力军"},
    {"bank_code": "BOC",   "bank_name": "中国银行",     "bank_type": BankType.STATE_OWNED,    "listed_status": "listed", "description": "国际化程度最高的中国银行"},
    {"bank_code": "BOCOM", "bank_name": "交通银行",     "bank_type": BankType.STATE_OWNED,    "listed_status": "listed", "description": "中国第五大国有银行"},
    {"bank_code": "PSBC",  "bank_name": "邮储银行",     "bank_type": BankType.STATE_OWNED,    "listed_status": "listed", "description": "中国最大零售银行之一"},
    # 股份制银行
    {"bank_code": "CMB",   "bank_name": "招商银行",     "bank_type": BankType.JOINT_STOCK,    "listed_status": "listed", "description": "中国最优秀的股份制银行之一"},
    {"bank_code": "CITIC", "bank_name": "中信银行",     "bank_type": BankType.JOINT_STOCK,    "listed_status": "listed", "description": "中信集团旗下银行"},
    {"bank_code": "SPDB",  "bank_name": "浦发银行",     "bank_type": BankType.JOINT_STOCK,    "listed_status": "listed", "description": "上海浦东发展银行"},
    {"bank_code": "PINGAN","bank_name": "平安银行",     "bank_type": BankType.JOINT_STOCK,    "listed_status": "listed", "description": "平安集团旗下银行"},
    # 城商行
    {"bank_code": "NBCB",  "bank_name": "宁波银行",     "bank_type": BankType.CITY_COMMERCIAL,"listed_status": "listed", "description": "宁波本地优质城商行"},
    {"bank_code": "NJCB",  "bank_name": "南京银行",     "bank_type": BankType.CITY_COMMERCIAL,"listed_status": "listed", "description": "江苏省最大城商行之一"},
]

# ============================================================
# 各银行模拟财务数据（2020-2024年，单位：亿元）
# ============================================================
FINANCIAL_DATA = {
    # 格式：bank_code -> {indicator_name -> {year: value}}
    "ICBC": {
        "营业收入":   {2020: 8221, 2021: 8729, 2022: 9179, 2023: 9423, 2024: 9604},
        "净利润":     {2020: 3176, 2021: 3483, 2022: 3610, 2023: 3639, 2024: 3639},
        "总资产":     {2020: 335234, 2021: 353439, 2022: 381000, 2023: 404460, 2024: 421800},
        "净息差(%)":  {2020: 2.15, 2021: 2.11, 2022: 2.01, 2023: 1.91, 2024: 1.83},
        "不良贷款率(%)": {2020: 1.58, 2021: 1.42, 2022: 1.38, 2023: 1.36, 2024: 1.35},
        "资本充足率(%)": {2020: 16.53, 2021: 17.02, 2022: 17.53, 2023: 18.87, 2024: 19.38},
    },
    "CCB": {
        "营业收入":   {2020: 7350, 2021: 7854, 2022: 8236, 2023: 8413, 2024: 8551},
        "净利润":     {2020: 2745, 2021: 3023, 2022: 3231, 2023: 3327, 2024: 3327},
        "总资产":     {2020: 280819, 2021: 296136, 2022: 322347, 2023: 345034, 2024: 365500},
        "净息差(%)":  {2020: 2.19, 2021: 2.13, 2022: 2.02, 2023: 1.95, 2024: 1.81},
        "不良贷款率(%)": {2020: 1.56, 2021: 1.42, 2022: 1.38, 2023: 1.37, 2024: 1.34},
        "资本充足率(%)": {2020: 17.25, 2021: 17.89, 2022: 17.91, 2023: 18.38, 2024: 19.11},
    },
    "ABC": {
        "营业收入":   {2020: 6734, 2021: 7201, 2022: 7564, 2023: 7613, 2024: 7724},
        "净利润":     {2020: 2165, 2021: 2417, 2022: 2545, 2023: 2698, 2024: 2778},
        "总资产":     {2020: 272650, 2021: 294148, 2022: 318743, 2023: 342219, 2024: 363600},
        "净息差(%)":  {2020: 2.20, 2021: 2.12, 2022: 1.99, 2023: 1.88, 2024: 1.80},
        "不良贷款率(%)": {2020: 1.57, 2021: 1.43, 2022: 1.37, 2023: 1.33, 2024: 1.32},
        "资本充足率(%)": {2020: 16.97, 2021: 17.41, 2022: 17.44, 2023: 17.77, 2024: 18.55},
    },
    "BOC": {
        "营业收入":   {2020: 5869, 2021: 6216, 2022: 6601, 2023: 6629, 2024: 6694},
        "净利润":     {2020: 1876, 2021: 2165, 2022: 2245, 2023: 2320, 2024: 2364},
        "总资产":     {2020: 249722, 2021: 265729, 2022: 287024, 2023: 307624, 2024: 322400},
        "净息差(%)":  {2020: 1.85, 2021: 1.75, 2022: 1.76, 2023: 1.69, 2024: 1.67},
        "不良贷款率(%)": {2020: 1.46, 2021: 1.33, 2022: 1.32, 2023: 1.27, 2024: 1.25},
        "资本充足率(%)": {2020: 16.97, 2021: 17.29, 2022: 17.06, 2023: 19.18, 2024: 20.25},
    },
    "BOCOM": {
        "营业收入":   {2020: 2702, 2021: 2892, 2022: 2970, 2023: 2980, 2024: 3010},
        "净利润":     {2020: 731,  2021: 869,  2022: 920,  2023: 939,  2024: 967},
        "总资产":     {2020: 105399, 2021: 112839, 2022: 122376, 2023: 131285, 2024: 139800},
        "净息差(%)":  {2020: 1.57, 2021: 1.53, 2022: 1.48, 2023: 1.38, 2024: 1.29},
        "不良贷款率(%)": {2020: 1.67, 2021: 1.67, 2022: 1.35, 2023: 1.33, 2024: 1.32},
        "资本充足率(%)": {2020: 15.08, 2021: 15.51, 2022: 15.63, 2023: 15.91, 2024: 16.74},
    },
    "PSBC": {
        "营业收入":   {2020: 2788, 2021: 3125, 2022: 3349, 2023: 3427, 2024: 3571},
        "净利润":     {2020: 643,  2021: 762,  2022: 853,  2023: 864,  2024: 864},
        "总资产":     {2020: 128059, 2021: 138115, 2022: 147278, 2023: 158600, 2024: 167300},
        "净息差(%)":  {2020: 2.38, 2021: 2.36, 2022: 2.20, 2023: 2.01, 2024: 1.87},
        "不良贷款率(%)": {2020: 0.88, 2021: 0.82, 2022: 0.84, 2023: 0.83, 2024: 0.86},
        "资本充足率(%)": {2020: 13.88, 2021: 14.80, 2022: 14.33, 2023: 14.76, 2024: 14.91},
    },
    "CMB": {
        "营业收入":   {2020: 2905, 2021: 3312, 2022: 3447, 2023: 3391, 2024: 3376},
        "净利润":     {2020: 974,  2021: 1199, 2022: 1380, 2023: 1466, 2024: 1484},
        "总资产":     {2020: 87307, 2021: 101474, 2022: 111153, 2023: 117847, 2024: 125700},
        "净息差(%)":  {2020: 2.49, 2021: 2.48, 2022: 2.40, 2023: 2.19, 2024: 2.00},
        "不良贷款率(%)": {2020: 1.07, 2021: 0.91, 2022: 0.96, 2023: 0.95, 2024: 0.95},
        "资本充足率(%)": {2020: 17.08, 2021: 17.52, 2022: 17.08, 2023: 17.79, 2024: 19.67},
    },
    "CITIC": {
        "营业收入":   {2020: 1944, 2021: 2130, 2022: 2164, 2023: 2133, 2024: 2149},
        "净利润":     {2020: 447,  2021: 567,  2022: 621,  2023: 672,  2024: 689},
        "总资产":     {2020: 78827, 2021: 86231, 2022: 91050, 2023: 97052, 2024: 103000},
        "净息差(%)":  {2020: 2.20, 2021: 2.05, 2022: 1.97, 2023: 1.79, 2024: 1.68},
        "不良贷款率(%)": {2020: 1.64, 2021: 1.39, 2022: 1.27, 2023: 1.18, 2024: 1.18},
        "资本充足率(%)": {2020: 13.00, 2021: 13.36, 2022: 13.97, 2023: 14.65, 2024: 15.23},
    },
    "SPDB": {
        "营业收入":   {2020: 1980, 2021: 2061, 2022: 1984, 2023: 1958, 2024: 1958},
        "净利润":     {2020: 531,  2021: 589,  2022: 601,  2023: 647,  2024: 621},
        "总资产":     {2020: 75917, 2021: 81895, 2022: 86288, 2023: 88873, 2024: 92800},
        "净息差(%)":  {2020: 1.86, 2021: 1.73, 2022: 1.56, 2023: 1.52, 2024: 1.50},
        "不良贷款率(%)": {2020: 1.73, 2021: 1.55, 2022: 1.49, 2023: 1.48, 2024: 1.48},
        "资本充足率(%)": {2020: 13.53, 2021: 13.74, 2022: 13.53, 2023: 14.79, 2024: 15.22},
    },
    "PINGAN": {
        "营业收入":   {2020: 1420, 2021: 1696, 2022: 1739, 2023: 1647, 2024: 1671},
        "净利润":     {2020: 289,  2021: 363,  2022: 455,  2023: 465,  2024: 465},
        "总资产":     {2020: 44939, 2021: 51743, 2022: 56008, 2023: 57671, 2024: 60100},
        "净息差(%)":  {2020: 2.53, 2021: 2.79, 2022: 2.75, 2023: 2.47, 2024: 2.12},
        "不良贷款率(%)": {2020: 1.65, 2021: 1.02, 2022: 1.05, 2023: 1.06, 2024: 1.06},
        "资本充足率(%)": {2020: 13.29, 2021: 13.33, 2022: 13.43, 2023: 13.43, 2024: 13.34},
    },
    "NBCB": {
        "营业收入":   {2020: 516,  2021: 595,  2022: 700,  2023: 760,  2024: 802},
        "净利润":     {2020: 150,  2021: 196,  2022: 230,  2023: 256,  2024: 271},
        "总资产":     {2020: 17209, 2021: 19788, 2022: 23222, 2023: 26631, 2024: 29100},
        "净息差(%)":  {2020: 2.25, 2021: 2.22, 2022: 2.13, 2023: 1.93, 2024: 1.80},
        "不良贷款率(%)": {2020: 0.79, 2021: 0.77, 2022: 0.75, 2023: 0.76, 2024: 0.76},
        "资本充足率(%)": {2020: 15.42, 2021: 15.08, 2022: 15.59, 2023: 15.61, 2024: 16.10},
    },
    "NJCB": {
        "营业收入":   {2020: 402,  2021: 456,  2022: 509,  2023: 527,  2024: 534},
        "净利润":     {2020: 136,  2021: 170,  2022: 201,  2023: 213,  2024: 219},
        "总资产":     {2020: 16399, 2021: 18868, 2022: 21325, 2023: 23381, 2024: 25300},
        "净息差(%)":  {2020: 1.92, 2021: 1.88, 2022: 1.85, 2023: 1.80, 2024: 1.79},
        "不良贷款率(%)": {2020: 0.91, 2021: 0.90, 2022: 0.90, 2023: 0.89, 2024: 0.83},
        "资本充足率(%)": {2020: 14.16, 2021: 14.36, 2022: 14.22, 2023: 14.41, 2024: 14.18},
    },
}

# 表格分类映射
TABLE_CATEGORY_MAP = {
    "营业收入":       "利润表",
    "净利润":         "利润表",
    "总资产":         "资产负债表",
    "净息差(%)":      "关键指标",
    "不良贷款率(%)":  "资产质量",
    "资本充足率(%)":  "资本充足",
}


def seed_database(force_reseed: bool = False) -> dict:
    """
    向数据库写入演示种子数据

    Args:
        force_reseed: 是否强制重新写入（会先清除现有数据）

    Returns:
        写入统计
    """
    warehouse = BankWarehouseManager()
    warehouse.init_database()

    stats = {"banks_created": 0, "reports_created": 0, "rows_created": 0, "skipped": 0}

    # 检查是否已经有数据
    existing_stats = warehouse.get_statistics()
    if existing_stats.get("banks", 0) > 0 and not force_reseed:
        print(f"[SEED] Already has {existing_stats['banks']} banks, skipping. Use force_reseed=True to overwrite.")
        return {"already_seeded": True, **existing_stats}

    print("[SEED] Starting database seeding...")

    for bank_data in BANKS_DATA:
        bank_code = bank_data["bank_code"]

        # 保存/更新银行
        bank_id = warehouse.save_bank(bank_data)
        if bank_id:
            stats["banks_created"] += 1
            print(f"  [BANK] Saved: {bank_data['bank_name']} (ID={bank_id})")
        else:
            stats["skipped"] += 1
            # 查找已存在的银行ID
            existing = warehouse.search_banks(bank_code)
            if existing:
                bank_id = existing[0]["id"]
            else:
                continue

        # 获取该银行的财务数据
        fin_data = FINANCIAL_DATA.get(bank_code, {})
        if not fin_data:
            continue

        # 只创建一份"多年汇总报告"，存储2020-2024全部数据
        report_id = warehouse.save_report({
            "bank_id": bank_id,
            "report_type": ReportType.ANNUAL,
            "period": "2020-2024",
            "fiscal_year": 2024,
            "pdf_filename": f"{bank_data['bank_name']}_历年年报汇总.pdf",
            "status": "completed",
            "reporting_standard": "CAS",
        })

        if not report_id:
            stats["skipped"] += 1
            continue

        stats["reports_created"] += 1

        # 按表格分组写入，每个指标一行，存储2020-2024全部年份数据
        # save_batch_table_data 需要 rows 里有 value_2020, value_2021 ... 的 key
        by_table = {}
        for indicator_name, year_values in fin_data.items():
            table_name = TABLE_CATEGORY_MAP.get(indicator_name, "其他指标")
            if table_name not in by_table:
                by_table[table_name] = []

            row = {
                "indicator_name": indicator_name,
                "table_category": table_name,
                "unit": "%" if "(%)" in indicator_name else "亿元",
            }
            # 写入各年数据
            for year in [2020, 2021, 2022, 2023, 2024]:
                val = year_values.get(year)
                if val is not None:
                    row[f"value_{year}"] = val

            by_table[table_name].append(row)

        # 按表格分批写入
        for table_name, rows in by_table.items():
            count = warehouse.save_batch_table_data(
                report_id=report_id,
                table_name=table_name,
                rows=rows
            )
            stats["rows_created"] += count or 0

        print(f"    -> 1 report (2020-2024), Tables: {list(by_table.keys())}")

    print(f"\n[SEED] Done! Banks={stats['banks_created']}, Reports={stats['reports_created']}, Rows={stats['rows_created']}")
    return stats


if __name__ == "__main__":
    result = seed_database(force_reseed=False)
    print("Result:", result)
