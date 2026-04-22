# -*- coding:utf-8 -*-

import os
from pathlib import Path

# ============================================================
# dotenv 加载：优先从环境变量读取凭证，.env 文件不参与 Git
# ============================================================
# 向后兼容：如果 .env 文件存在则加载，保持原有硬编码值作为 fallback
try:
    from dotenv import load_dotenv
    # 尝试加载项目根目录的 .env 文件
    _env_path = Path(__file__).parent.parent.parent / '.env'
    if _env_path.exists():
        load_dotenv(_env_path)
        print(f"[Constants] 已加载 .env 文件: {_env_path}")
    else:
        print("[Constants] 未找到 .env 文件，将使用代码中的默认值（仅用于本地开发）")
except ImportError:
    # 未安装 python-dotenv 时跳过，但所有凭证读取逻辑仍走 os.environ
    pass

# 方法2：使用 pathlib
current_file = Path(__file__).resolve()  # 获取当前文件的绝对路径
MAIN_ROOT = current_file.parent.parent.parent  # 向上回退3层

# 🔥 新增：正确计算项目根目录
def get_project_root():
    """获取项目根目录"""
    try:
        # 向上3级：constants.py → utils → backend → 项目根目录
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent

        # 验证是否为项目根目录
        if (project_root / "project-config.json").exists() or (project_root / "backend").exists():
            print(f"[Constants] 计算的项目根目录: {project_root}")
            return project_root
        else:
            # 如果不在预期位置，向上查找
            for parent in current_file.parents:
                if (parent / "project-config.json").exists() or (parent / "backend").exists():
                    print(f"[Constants] 查找到的项目根目录: {parent}")
                    return parent

            print(f"[Constants] 未找到项目根目录，使用当前目录: {project_root}")
            return project_root
    except Exception as e:
        print(f"[Constants] 计算项目根目录失败: {e}")
        return Path.cwd()


# 新增常量：正确的项目根目录
PROJECT_ROOT = get_project_root()
PROJECT_ROOT_STR = str(PROJECT_ROOT)


# 百度表格识别
# 百度OCR配置（从环境变量读取，.env 中配置 BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY）
# 重要：fallback 为空字符串，若未配置 .env 则调用会失败（安全优先）
BAIDU_OCR_CONFIG = {
    "API_KEY": os.environ.get("BAIDU_OCR_API_KEY", ""),
    "SECRET_KEY": os.environ.get("BAIDU_OCR_SECRET_KEY", ""),
}
# 其他应用配置
BAIDU_APP_CONFIG = {
    "TIMEOUT": 30,
    "MAX_RETRIES": 3
}


# 图片切割的URL
# REMOTE_LAYOUT_URL = "http://i-2.gpushare.com:37987/layout"
REMOTE_LAYOUT_URL = "http://i-2.gpushare.com:30417/layout"


# 静态文件路径配置
SAVE_PATH = r'data/backend'
UPLOAD_FOLDER = r'data/backend/static/uploads'
UPLOAD_EXCEL_DIR = r'data/backend/static/uploads/excel'  # Excel上传目录
UPLOAD_PDF_DIR = r'data/backend/static/uploads/pdf'      # PDF上传目录
PROCESSED_EXCEL_DIR = r'data/backend/static/processed/excel'  # 成品Excel目录
PROCESSED_REPORTS_DIR = r'data/backend/static/processed/reports'  # 成品报告目录
PNG_OUTPUT_ROOT = r'data/backend/static/pdf2pngs'
EXCEL_OUTPUT_ROOT = r'data/backend/static/excel_data'
JOINED_TABLES_ROOT = r'data/backend/static/joined_tables'
DATABASE = r'data/database.db'
OBJ_CACHE = "data/backend/obj_cache"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

# ⭐⭐⭐ 新增：完整的静态文件路径常量 ⭐⭐⭐
# 使用Path对象确保跨平台兼容性
STATIC_DIR = Path(MAIN_ROOT) / "data" / "backend" / "static"
print("STATIC_DIRSTATIC_DIR:", STATIC_DIR, MAIN_ROOT)
EXCEL_DATA_DIR = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT
UPLOAD_DIR = Path(MAIN_ROOT) / UPLOAD_FOLDER
UPLOAD_EXCEL_DIR = Path(MAIN_ROOT) / UPLOAD_EXCEL_DIR  # Excel上传目录
UPLOAD_PDF_DIR = Path(MAIN_ROOT) / UPLOAD_PDF_DIR      # PDF上传目录
PROCESSED_EXCEL_DIR = Path(MAIN_ROOT) / PROCESSED_EXCEL_DIR  # 成品Excel目录
PROCESSED_REPORTS_DIR = Path(MAIN_ROOT) / PROCESSED_REPORTS_DIR  # 成品报告目录
PNG_OUTPUT_DIR = Path(MAIN_ROOT) / PNG_OUTPUT_ROOT
JOINED_TABLES_DIR = Path(MAIN_ROOT) / JOINED_TABLES_ROOT
DATABASE_PATH = Path(MAIN_ROOT) / DATABASE
OBJ_CACHE_PATH = Path(MAIN_ROOT) / OBJ_CACHE

# ⭐⭐⭐ 新增：API路由路径常量 ⭐⭐⭐
API_EXCEL_DATA_PREFIX = "/api/excel-data"
API_STATIC_PREFIX = "/api/static"
STATIC_CONVERTED_PREFIX = "/static/joined_tables"

# ⭐⭐⭐ 新增：文件夹路径常量 ⭐⭐⭐
FILTERED_TABLES_DIR = STATIC_DIR / "filtered_tables"  # 裁剪表格目录
print("FILTERED_TABLES_DIR::::", FILTERED_TABLES_DIR)
# 在 constants.py 中添加
EXCEL_DATA_URL_PREFIX = "/api/excel-data"
EXCEL_DATA_RELATIVE_PATH = "static/excel_data"


# 在 ALLOWED_EXTENSIONS 后面添加
NON_FINANCIAL_PROMPT = """
【角色】通用表格数据提取专家

# 核心任务
准确识别和提取各种类型的非金融表格数据，包括但不限于：产品清单、人员名单、统计报表、信息表格等

# 处理规则
1. 直接提取所有可见的表格数据
2. 保持原始表格的行列结构
3. 基础数据清洗和格式统一

# 数据提取要求
- 提取所有表头信息作为列标题
- 提取所有数据行，保持原有顺序
- 空白单元格标记为 "-"
- 数值处理：删除千位符，括号转负号
- 文本内容：原样保留，不做金融术语转换

# 输出格式
<non_financial_data>
```csv
序号|表头1|表头2|表头3|表头4
1|数据A1|数据A2|数据A3|数据A4
2|数据B1|数据B2|数据B3|数据B4
3|数据C1|数据C2|数据C3|数据C4
</non_financial_data>
"""

# 在 PROMPT_NAMES 后面添加表格类型配置
TABLE_TYPES = {
    "financial": "financial",  # 金融表格
    "non_financial": "non_financial"  # 普通表格
}


# 火山引擎 ARK API Key（从环境变量读取，.env 中配置 LLM_API_KEY）
# 重要：fallback 为空字符串，若未配置 .env 则调用会失败（安全优先）
ARK_API_KEY = os.environ.get("LLM_API_KEY", "")


# ============================================================
# 银行数据仓库 Feature Flag
# ============================================================
# 设置为 True 时，Table Worker 处理完 PDF 后会自动将数据写入银行数据仓库
# 设置为 False 时，不写入数据仓库
# 也可以通过环境变量 ENABLE_BANK_WAREHOUSE=true 覆盖此设置

ENABLE_BANK_WAREHOUSE = True
# ENABLE_BANK_WAREHOUSE = os.environ.get('ENABLE_BANK_WAREHOUSE',
#     'true').lower() == 'true'



