# -*- coding: utf-8 -*-
"""
银行数据仓库表结构定义 - 国内版 + 预留国际扩展字段

设计理念：
1. 国内优先：满足当前2000+银行数据管理需求
2. 预留扩展：为未来国际银行数据预留字段
3. 数据溯源：每条数据可追溯到原始PDF
4. 版本管理：支持数据历史变更追踪

作者：DocuVista Team
版本：1.0.0
"""

# ============================================================
# 银行基础信息表 (banks)
# ============================================================
CREATE_BANKS_TABLE = """
CREATE TABLE IF NOT EXISTS banks (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 国内银行标识
    bank_code VARCHAR(20) UNIQUE,
    bank_name VARCHAR(200) NOT NULL,

    -- 银行类型
    bank_type VARCHAR(50),

    -- 上市状态
    listed_status VARCHAR(20) DEFAULT 'listed',

    -- 描述信息
    description TEXT,

    -- 预留国际扩展字段
    swift_code VARCHAR(11),
    isin VARCHAR(12),
    country_code VARCHAR(10),
    country_name VARCHAR(100),
    base_currency VARCHAR(3) DEFAULT 'CNY',

    -- 状态
    status VARCHAR(20) DEFAULT 'active',

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

# ============================================================
# 报告记录表 (reports)
# ============================================================
CREATE_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS reports (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 关联银行
    bank_id INTEGER NOT NULL,

    -- 报告基本信息
    report_type VARCHAR(30) NOT NULL,
    period VARCHAR(20) NOT NULL,

    -- 报告日期
    report_date DATE,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,

    -- 报告准则
    reporting_standard VARCHAR(20) DEFAULT 'CAS',

    -- 原始文件信息
    pdf_filename VARCHAR(500),
    pdf_path VARCHAR(1000),
    pdf_hash VARCHAR(64),

    -- 处理状态
    status VARCHAR(20) DEFAULT 'pending',

    -- Excel输出
    excel_output_path VARCHAR(1000),

    -- 溯源信息
    source_pdf_folder VARCHAR(500),
    source_pages TEXT,

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (bank_id) REFERENCES banks(id) ON DELETE CASCADE
)
"""

# ============================================================
# 原始表格数据表 (table_data) - 核心数据表
# ============================================================
CREATE_TABLE_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS table_data (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 关联报告
    report_id INTEGER NOT NULL,

    -- 表格信息
    table_name VARCHAR(200) NOT NULL,
    table_category VARCHAR(50),

    -- 位置信息
    page_number INTEGER,
    row_index INTEGER,

    -- 指标数据
    indicator_name VARCHAR(500) NOT NULL,
    indicator_code VARCHAR(50),

    -- 年份数据（使用JSON存储更灵活）
    value_json TEXT,
    unit VARCHAR(20) DEFAULT '万元',

    -- 数据状态
    is_adjusted BOOLEAN DEFAULT 0,
    adjusted_value DECIMAL(20,4),
    adjustment_reason TEXT,

    -- 备注
    notes TEXT,

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
)
"""

# ============================================================
# 数据溯源表 (data_sources)
# ============================================================
CREATE_DATA_SOURCES_TABLE = """
CREATE TABLE IF NOT EXISTS data_sources (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 关联表格数据
    table_data_id INTEGER NOT NULL,

    -- PDF溯源
    pdf_path VARCHAR(1000) NOT NULL,
    page_number INTEGER NOT NULL,
    pdf_hash VARCHAR(64),

    -- 图片溯源
    image_path VARCHAR(1000),
    image_hash VARCHAR(64),

    -- 缓存路径
    ocr_cache_path VARCHAR(1000),
    llm_cache_path VARCHAR(1000),

    -- LLM分析结果
    llm_response TEXT,
    confidence_score DECIMAL(5,4),

    -- 状态
    status VARCHAR(20) DEFAULT 'active',

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (table_data_id) REFERENCES table_data(id) ON DELETE CASCADE
)
"""

# ============================================================
# 数据版本历史表 (data_versions)
# ============================================================
CREATE_DATA_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS data_versions (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 关联表格数据
    table_data_id INTEGER NOT NULL,

    -- 版本信息
    version INTEGER NOT NULL,
    change_type VARCHAR(20) NOT NULL,

    -- 变更内容
    old_value TEXT,
    new_value TEXT,
    old_value_json TEXT,
    new_value_json TEXT,

    -- 变更信息
    changed_by VARCHAR(100),
    change_reason TEXT,
    change_notes TEXT,

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (table_data_id) REFERENCES table_data(id) ON DELETE CASCADE
)
"""

# ============================================================
# 处理任务记录表 (processing_jobs)
# ============================================================
CREATE_PROCESSING_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS processing_jobs (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 任务标识
    job_id VARCHAR(100) UNIQUE NOT NULL,
    report_id INTEGER,

    -- 任务信息
    bank_id INTEGER,
    bank_name VARCHAR(200),
    pdf_folder VARCHAR(500),

    -- 任务状态
    status VARCHAR(20) DEFAULT 'pending',
    stage VARCHAR(50),
    progress INTEGER DEFAULT 0,

    -- 统计
    total_images INTEGER DEFAULT 0,
    processed_images INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,

    -- 结果
    excel_files TEXT,
    error_message TEXT,
    raw_result TEXT,

    -- 时间
    start_time DATETIME,
    end_time DATETIME,

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL,
    FOREIGN KEY (bank_id) REFERENCES banks(id) ON DELETE SET NULL
)
"""

# ============================================================
# 会员表 (members) - 二期预留
# ============================================================
CREATE_MEMBERS_TABLE = """
CREATE TABLE IF NOT EXISTS members (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 用户信息
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(200),
    phone VARCHAR(20),

    -- 会员信息
    member_level VARCHAR(20) DEFAULT 'free',
    allowed_banks TEXT,
    allowed_countries TEXT,

    -- 状态
    status VARCHAR(20) DEFAULT 'active',

    -- 使用限制
    max_banks INTEGER DEFAULT 10,
    max_queries_per_day INTEGER DEFAULT 100,

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME
)
"""


# ============================================================
# 所有表的创建语句列表
# ============================================================
ALL_TABLES = [
    ("banks", CREATE_BANKS_TABLE),
    ("reports", CREATE_REPORTS_TABLE),
    ("table_data", CREATE_TABLE_DATA_TABLE),
    ("data_sources", CREATE_DATA_SOURCES_TABLE),
    ("data_versions", CREATE_DATA_VERSIONS_TABLE),
    ("processing_jobs", CREATE_PROCESSING_JOBS_TABLE),
    ("members", CREATE_MEMBERS_TABLE),
]


# ============================================================
# 表结构常量
# ============================================================
class TableNames:
    """表名常量"""
    BANKS = "banks"
    REPORTS = "reports"
    TABLE_DATA = "table_data"
    DATA_SOURCES = "data_sources"
    DATA_VERSIONS = "data_versions"
    PROCESSING_JOBS = "processing_jobs"
    MEMBERS = "members"


class BankType:
    """银行类型枚举"""
    STATE_OWNED = "国有大型银行"
    JOINT_STOCK = "股份制银行"
    CITY_COMMERCIAL = "城市商业银行"
    RURAL_COMMERCIAL = "农村商业银行"
    PRIVATE = "民营银行"
    FOREIGN = "外资银行"


class ReportType:
    """报告类型枚举"""
    ANNUAL = "annual"
    QUARTER = "quarter"
    HALF = "half"
    MONTHLY = "monthly"


class ReportStatus:
    """报告状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStatus:
    """处理状态枚举"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChangeType:
    """变更类型枚举"""
    INITIAL = "initial"
    MANUAL_EDIT = "manual_edit"
    AUTO_CORRECT = "auto_correct"
    DATA_IMPORT = "data_import"


class MemberLevel:
    """会员等级枚举"""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
