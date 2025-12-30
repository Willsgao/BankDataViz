"""
文件相关蓝图 - 重构版本（只重构Excel转PDF功能）
"""
from flask import Blueprint, request, jsonify, send_from_directory
from backend.models.unified_db import DatabaseManager as OldDatabaseManager
from backend.utils.constants import UPLOAD_FOLDER, MAIN_ROOT, DATABASE, EXCEL_OUTPUT_ROOT
from pathlib import Path
import datetime

# 新增导入
from backend.service.file_mapping_service import file_mapping_service

import pandas as pd

file_bp = Blueprint('file', __name__)

db = OldDatabaseManager(DATABASE)


# 尝试导入转换器，提供多种导入路径
CONVERTER_AVAILABLE = False
FinalDataConverter = None

try:
    # 尝试从 backend.src.services.table_processor 导入
    from backend.src.services.table_processor.long_format_converter import FinalDataConverter as FC
    FinalDataConverter = FC
    CONVERTER_AVAILABLE = True
    print("✅ long_format_converter 从标准路径导入成功")
except ImportError as e:
    print(f"⚠️ 标准路径导入失败: {e}")
    try:
        # 尝试从当前目录导入
        from long_format_converter import FinalDataConverter as FC
        FinalDataConverter = FC
        CONVERTER_AVAILABLE = True
        print("✅ long_format_converter 从当前目录导入成功")
    except ImportError as e2:
        print(f"❌ 所有导入尝试都失败: {e2}")
        CONVERTER_AVAILABLE = False



# ========== 导入重构后的Excel转PDF功能模块 ==========
from .file_handlers.validators import (
    validate_excel_file,
    validate_conversion_params,
    ValidationError
)
from .file_handlers.processors import (
    save_uploaded_file,
    convert_excel_to_pdf,
    save_and_return_result
)


# ========== 原有的所有接口保持不变 ==========
# 只添加新的Excel转PDF接口，其他所有接口保持原样
@file_bp.get('/files')
def list_files():
    print("🔍 文件列表API被调用")
    print(f"📁 FILES - 数据库路径: {DATABASE}")

    conn = db.connect()
    if not conn:
        print("❌ 数据库连接失败")
        return jsonify({"error": "数据库连接失败"}), 500

    c = conn.cursor()

    # 先查询所有文件（包括已删除的）
    c.execute("SELECT COUNT(*) as total FROM files")
    total_count = c.fetchone()[0]
    print(f"📊 数据库中总文件数（包括已删除）: {total_count}")

    c.execute("SELECT COUNT(*) as active FROM files WHERE deleted = 0")
    active_count = c.fetchone()[0]
    print(f"📊 未删除的文件数: {active_count}")

    # 执行原始查询
    c.execute(
        "SELECT id, filename, raw_filename, file_type, created_at, deleted "
        "FROM files WHERE deleted = 0 ORDER BY created_at DESC"
    )
    rows = c.fetchall()

    print(f"📋 查询结果行数: {len(rows)}")

    # 打印所有查询到的行（包括已删除的）
    c.execute("SELECT id, filename, raw_filename, deleted FROM files")
    all_rows = c.fetchall()
    print(f"📋 数据库中所有文件记录: {all_rows}")

    files_list = []
    upload_dir = Path(MAIN_ROOT) / UPLOAD_FOLDER
    missing_files = []  # 记录不存在的文件ID

    for row in rows:
        file_id = row[0]
        disk_name = row[1]  # UUID文件名
        raw_name = row[2]  # 原始中文名
        file_type = row[3]

        # 检查物理文件是否存在
        file_path = upload_dir / disk_name
        file_exists = file_path.exists()

        if file_exists:
            file_info = {
                "id": file_id,
                "filename": raw_name or disk_name,
                "disk_name": disk_name,
                "file_type": file_type,
                "created_at": row[4],
                "file_id": disk_name.split('.')[0] if '.' in disk_name else disk_name
            }
            files_list.append(file_info)
            print(f"✅ 包含文件: {raw_name} (磁盘名: {disk_name})")
        else:
            print(f"❌ 文件不存在，跳过: {raw_name} (磁盘名: {disk_name})")
            missing_files.append(file_id)

    # 自动删除数据库中不存在的文件记录（可选）
    if missing_files:
        print(f"🗑️ 自动删除 {len(missing_files)} 个不存在的文件记录")
        placeholders = ','.join('?' * len(missing_files))
        c.execute(f"DELETE FROM files WHERE id IN ({placeholders})", missing_files)
        conn.commit()

    conn.close()

    print(f"✅ 返回给前端的有效文件数: {len(files_list)}")
    return jsonify(files_list)



# ---------- 2. 下载/预览（不返回已软删） ----------
@file_bp.get('/file/<path:filename>')
def get_file(filename):
    """
    filename 可能是中文原始名，也可能是磁盘 UUID 名；
    一律先查库映射到真实磁盘名，且只返回未删除的。
    """
    print(f"🔍 查找文件: {filename}")

    conn = db.connect()
    if not conn:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        c = conn.cursor()
        # 查询文件信息（包括ID和磁盘文件名）
        c.execute(
            "SELECT id, filename, raw_filename FROM files "
            "WHERE (raw_filename = ? OR filename = ?) AND deleted = 0",
            (filename, filename)
        )
        row = c.fetchone()

        if row is None:
            print(f"❌ 文件不存在或已隐藏: {filename}")
            return jsonify({"error": "文件不存在或已隐藏"}), 404

        file_id = row["id"]
        real_name = row["filename"]  # 磁盘 UUID 文件名
        raw_name = row["raw_filename"]  # 原始中文名

        print(f"✅ 找到文件: ID={file_id}, 磁盘名={real_name}, 原始名={raw_name}")

        # 构建文件路径
        upload_dir = Path(MAIN_ROOT) / UPLOAD_FOLDER
        file_path = upload_dir / real_name
        print(f"📁 文件路径: {file_path}")
        print(f"📁 上传目录: {upload_dir}")

        if not file_path.exists():
            print(f"❌ 物理文件不存在: {file_path}")
            return jsonify({"error": "物理文件不存在"}), 404

        # 返回文件 - 使用正确的目录路径
        print(f"📤 返回文件: {real_name}")
        return send_from_directory(str(upload_dir), real_name)

    except Exception as e:
        print(f"❌ 文件查找错误: {e}")
        return jsonify({"error": "文件查找失败"}), 500
    finally:
        conn.close()




# ---------- 2.2 获取文件信息 ----------
@file_bp.get('/file-info/<path:filename>')
def get_file_info(filename):
    """获取文件详细信息"""
    print(f"🔍 获取文件信息: {filename}")

    conn = db.connect()
    if not conn:
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, filename, raw_filename, file_type, created_at FROM files "
            "WHERE (raw_filename = ? OR filename = ?) AND deleted = 0",
            (filename, filename)
        )
        row = c.fetchone()

        if row is None:
            return jsonify({"error": "文件不存在或已隐藏"}), 404

        # 构建文件路径信息
        upload_dir = Path(MAIN_ROOT) / UPLOAD_FOLDER
        file_path = upload_dir / row["filename"]
        file_exists = file_path.exists()

        return jsonify({
            "id": row["id"],
            "disk_name": row["filename"],
            "original_name": row["raw_filename"],
            "file_type": row["file_type"],
            "created_at": row["created_at"],
            "file_exists": file_exists,
            "file_path": str(file_path)
        })

    except Exception as e:
        print(f"❌ 获取文件信息错误: {e}")
        return jsonify({"error": "获取文件信息失败"}), 500
    finally:
        conn.close()




# ---------- 3. 软删除（增强版：物理文件不存在时直接删除） ----------
@file_bp.delete('/file/<path:filename>')
def delete_file(filename):
    """
    删除文件逻辑：
    1. 如果物理文件不存在，直接删除数据库记录
    2. 如果物理文件存在，只进行软删除 (deleted = 1)
    """
    conn = db.connect()
    if not conn:
        return jsonify({"error": "数据库连接失败"}), 500

    c = conn.cursor()

    try:
        # 先找真实磁盘名和文件信息
        c.execute(
            "SELECT id, filename, raw_filename FROM files "
            "WHERE (raw_filename = ? OR filename = ?) AND deleted = 0",
            (filename, filename)
        )
        row = c.fetchone()
        if row is None:
            conn.close()
            return jsonify({"error": "文件不存在"}), 404

        file_id = row["id"]
        real_name = row["filename"]
        raw_name = row["raw_filename"]

        print(f"🔍 删除文件: ID={file_id}, 磁盘名={real_name}, 原始名={raw_name}")

        # 检查物理文件是否存在
        upload_dir = Path(MAIN_ROOT) / UPLOAD_FOLDER
        file_path = upload_dir / real_name

        if not file_path.exists():
            print(f"📁 物理文件不存在，直接删除数据库记录: {file_path}")
            # 物理文件不存在，直接删除数据库记录
            c.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
            conn.close()
            return jsonify({"message": "文件已彻底删除（物理文件不存在）"}), 200
        else:
            print(f"📁 物理文件存在，进行软删除: {file_path}")
            # 物理文件存在，进行软删除
            c.execute("UPDATE files SET deleted = 1 WHERE filename = ?", (real_name,))
            conn.commit()
            conn.close()
            return jsonify({"message": "已隐藏（软删除）"}), 200

    except Exception as e:
        print(f"❌ 删除文件时出错: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({"error": "删除文件失败"}), 500




# ---------- 4. 搜索PDF文件（新增接口） ----------
@file_bp.get('/search-pdf')
def search_pdf():
    """
    搜索PDF文件名称 - 基于文件映射服务
    参数: keyword - 搜索关键词
    返回: 匹配的PDF文件列表（显示原始中文名）
    """
    keyword = request.args.get('keyword', '').strip()
    print(f"搜索关键词: '{keyword}'")

    if not keyword:
        return jsonify({"files": []})

    try:
        # 使用文件映射服务搜索PDF文件
        search_results = file_mapping_service.search_files(keyword, 'pdf')

        return jsonify({"files": search_results})

    except Exception as e:
        print(f"搜索PDF失败: {e}")
        return jsonify({"error": "搜索失败"}), 500




# 添加文件下载接口（通过文件ID）
@file_bp.get('/file-by-id/<file_id>')
def get_file_by_id(file_id):
    """通过文件ID下载文件"""
    try:

        # 如果file_id包含扩展名，提取纯UUID部分
        if '.' in file_id:
            file_uuid = file_id.split('.')[0]
        else:
            file_uuid = file_id

        # 检查文件是否存在映射中
        file_info = file_mapping_service.get_file_info(file_uuid)
        if not file_info:
            return jsonify({"error": "文件不存在"}), 404

        disk_name = file_info["disk_name"]
        PDF_DIR = Path(MAIN_ROOT) / UPLOAD_FOLDER
        return send_from_directory(PDF_DIR, disk_name)

    except Exception as e:
        print(f"文件下载失败: {e}")
        return jsonify({"error": "文件下载失败"}), 500



# ---------- 5. 获取PDF对应的Excel sheet列表 ----------
@file_bp.get('/excel-sheets/<file_id>')
def get_excel_sheets(file_id):
    """
    根据PDF文件ID获取对应的Excel sheet列表
    Excel文件存储在 backend/static/excel_data/<file_id>/ 目录中
    """
    try:
        # 1. 验证PDF文件是否存在
        file_info = file_mapping_service.get_file_info(file_id)
        print("file_info:", file_info)
        if not file_info:
            return jsonify({"error": "PDF文件不存在"}), 404

        # 2. 构建Excel文件目录路径 - 修正：统一使用Path对象
        excel_dir = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / file_id

        if not excel_dir.exists():
            return jsonify({"excel_files": []})

        # 3. 查找目录中的所有Excel文件
        excel_files = []
        supported_extensions = ['.xlsx', '.xls']

        for ext in supported_extensions:
            print("ext:::", ext)
            for excel_file in excel_dir.glob(f"*{ext}"):
                print("excel_file:", excel_file)
                if excel_file.is_file():
                    print("excel_file.name:", excel_file.name)
                    excel_files.append({
                        "file_name": excel_file.name,
                        "file_path": str(excel_file),
                        "file_size": excel_file.stat().st_size
                    })

        if not excel_files:
            return jsonify({"excel_files": []})

        # 4. 读取每个Excel文件的sheet列表
        import pandas as pd
        result = []

        for excel_file in excel_files:
            try:
                # 读取Excel文件的所有sheet
                excel_file_obj = pd.ExcelFile(excel_file["file_path"])
                sheet_names = excel_file_obj.sheet_names

                file_sheets = []
                for sheet_name in sheet_names:
                    file_sheets.append({
                        "name": sheet_name,
                        "excel_file": excel_file["file_name"]
                    })

                result.append({
                    "excel_file": excel_file["file_name"],
                    "sheets": file_sheets,
                    "total_sheets": len(sheet_names)
                })

            except Exception as e:
                print(f"读取Excel文件失败 {excel_file['file_name']}: {e}")
                # 即使读取失败，也返回文件信息
                result.append({
                    "excel_file": excel_file["file_name"],
                    "sheets": [],
                    "total_sheets": 0,
                    "error": str(e)
                })
                continue


        print("&&&&&&&&&&&file_info&&&&&&&&&&&")
        print(file_info)

        return jsonify({
            "excel_files": result,
            "pdf_id": file_id,
            "pdf_name": file_info["original_name"],
            "total_excel_files": len(result)
        })

    except Exception as e:
        print(f"获取Excel sheet列表失败: {e}")
        return jsonify({"error": "获取表格列表失败"}), 500




# ---------- 6. 获取Excel表格数据 ----------
@file_bp.get('/excel-data/<file_id>/<path:excel_file_name>/<sheet_name>')
def get_excel_data(file_id, excel_file_name, sheet_name):
    """
    根据文件ID、Excel文件名和sheet名称获取Excel数据
    """
    try:

        # ---------- 0. 优先读最新 JSON 快照（风格同原代码） ----------
        import json

        snap_dir = Path(MAIN_ROOT) / r'data/backend/static/modify_data' / file_id
        snap_dir.mkdir(parents=True, exist_ok=True)  # 保证目录存在
        pattern = f"{file_id}_{sheet_name}_*.json"
        snap_list = sorted(snap_dir.glob(pattern), reverse=True)
        if snap_list:
            latest_snap = snap_list[0]
            try:
                with open(latest_snap, 'r', encoding='utf-8') as f:
                    snap_data = json.load(f)
                # 直接返回快照数据，格式与原来一致
                return jsonify({
                    "rows": snap_data["data"],
                    "total_rows": len(snap_data["data"]),
                    "total_columns": len(snap_data["data"][0]) if snap_data["data"] else 0,
                    "sheet_name": sheet_name,
                    "excel_file": excel_file_name,
                    "pdf_id": file_id,
                    "has_dual_headers": True,
                    "source": "snapshot"
                }), 200
            except Exception as e:
                print(f"[WARN] 快照读取失败 {latest_snap} -> 回退Excel: {e}")


        # 1. 构建Excel文件路径
        excel_dir = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / file_id
        excel_path = excel_dir / excel_file_name

        print("获取Excel数据 - 文件ID:", file_id)
        print("Excel文件路径:", excel_path)

        if not excel_path.exists():
            return jsonify({"error": "Excel文件不存在"}), 404

        # 2. 读取指定sheet，不把任何行当作表头
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
        df = df.fillna('')

        print("Excel原始数据形状:", df.shape)
        print("列数:", df.shape[1], "行数:", df.shape[0])


        # 获取表头
        horizontal_headers = []
        vertical_headers = []
        data_rows = []

        # 提取横向表头（第一行，从第二列开始）
        if df.shape[0] > 0:
            # 第一列第一行可能是左上角单元格
            top_left_cell = str(df.iloc[0, 0]) if df.iloc[0, 0] != '' else ""

            # 横向表头（第一行，从第二列开始）
            for col in range(1, df.shape[1]):
                header = str(df.iloc[0, col]) if df.iloc[0, col] != '' else f""
                horizontal_headers.append(header)

        # 提取纵向表头（第一列，从第二行开始）
        if df.shape[1] > 0:
            for row in range(1, df.shape[0]):
                header = str(df.iloc[row, 0]) if df.iloc[row, 0] != '' else f""
                vertical_headers.append(header)

        # 提取数据（从第二行第二列开始）
        for row in range(1, df.shape[0]):
            data_row = []
            for col in range(1, df.shape[1]):
                value = df.iloc[row, col]
                # 尝试保持数值类型
                try:
                    if isinstance(value, (int, float)):
                        data_row.append(value)
                    elif str(value).replace(',', '').replace('.', '').isdigit():
                        clean_value = str(value).replace(',', '')
                        if '.' in str(value):
                            data_row.append(float(clean_value))
                        else:
                            data_row.append(int(clean_value))
                    else:
                        data_row.append(str(value) if value != '' else "")
                except:
                    data_row.append(str(value) if value != '' else "")
            data_rows.append(data_row)

        print("数据结构分析:")
        print(f"- 左上角单元格: {top_left_cell}")
        print(f"- 横向表头数: {len(horizontal_headers)}")
        print(f"- 纵向表头数: {len(vertical_headers)}")
        print(f"- 数据行数: {len(data_rows)}")
        print(f"- 数据列数: {len(data_rows[0]) if data_rows else 0}")
        print(f"- 横向表头样本: {horizontal_headers[:3]}")
        print(f"- 纵向表头样本: {vertical_headers[:3]}")
        print(f"- 数据样本: {data_rows[0][:3] if data_rows else '无'}")

        # 4. 构建前端友好的数据结构
        frontend_data = []

        # 添加元数据行
        metadata_row = {
            "__metadata": {
                "has_dual_headers": True,
                "top_left_cell": top_left_cell,
                "horizontal_headers": horizontal_headers,
                "vertical_headers": vertical_headers
            }
        }
        frontend_data.append(metadata_row)

        # 添加表头数据行（第一行：左上角 + 横向表头）
        header_row = {
            "__is_first_row": True,
            "__top_left_cell": top_left_cell
        }
        for i, header in enumerate(horizontal_headers, 1):
            header_row[f"H_{i}"] = header

        frontend_data.append(header_row)

        # 添加数据行（纵向表头 + 数据）
        for i in range(len(data_rows)):
            row_data = data_rows[i]
            vertical_header = vertical_headers[i] if i < len(vertical_headers) else f""

            row_obj = {
                "__is_data_row": True,
                "__vertical_header": vertical_header
            }

            for j, value in enumerate(row_data, 1):
                row_obj[f"H_{j}"] = value

            frontend_data.append(row_obj)

        # 5. 返回给前端
        return jsonify({
            "rows": frontend_data,
            "total_rows": len(frontend_data),
            "total_columns": len(horizontal_headers),
            "sheet_name": sheet_name,
            "excel_file": excel_file_name,
            "pdf_id": file_id,
            "has_dual_headers": True
        })

    except Exception as e:
        print(f"处理Excel数据请求失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500



@file_bp.route('/excel-data/<path:filename>')
def serve_excel_file(filename):
    """提供 Excel 文件下载"""
    # 修正：统一使用Path对象构建路径
    file_path = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / filename
    if not file_path.exists():
        return "文件不存在", 404
    return send_from_directory(file_path.parent, file_path.name)




# ---------- 7. Excel数据扁平化处理（支持Excel标准格式） ----------
@file_bp.route('/excel-flatten', methods=['POST', 'OPTIONS'])
def excel_flatten_from_excel():
    """
    处理从Excel直接提取的标准格式数据
    使用long_format_converter.py的逻辑进行扁平化转换
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    try:
        # 检查转换器是否可用
        if not CONVERTER_AVAILABLE:
            print("❌ 转换器不可用")
            return jsonify({
                "success": False,
                "error": "数据转换器模块不可用"
            }), 500

        # 获取请求数据
        data = request.get_json()

        if not data:
            print("❌ 请求数据为空")
            return jsonify({
                "success": False,
                "error": "请求数据为空"
            }), 400

        table_data = data.get('table_data', [])
        source_info = data.get('source_info', {})

        if not table_data or len(table_data) < 2:
            print("❌ 表格数据至少需要表头行和一个数据行")
            return jsonify({
                "success": False,
                "error": "表格数据至少需要表头行和一个数据行"
            }), 400

        print(f"📊 开始处理Excel表格数据:")
        print(f"  - 原始表格尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

        # 关键：检查第一行是否是表头，如果不是，需要添加表头行
        print(f"📊 检查表格结构...")
        print(f"  - 第一行数据: {table_data[0] if len(table_data) > 0 else '无'}")

        # 判断是否需要添加表头行
        # 规则：如果第一行看起来不像表头（都是数字或空），则添加默认表头
        needs_header_row = False

        if len(table_data) > 0 and len(table_data[0]) > 0:
            first_row = table_data[0]
            # 检查第一行是否包含表头特征（文本而非纯数字）
            has_text_header = False
            for cell in first_row:
                if isinstance(cell, str) and cell.strip() and not cell.replace('.', '').replace(',', '').replace('-',
                                                                                                                 '').isdigit():
                    has_text_header = True
                    break

            if not has_text_header:
                print(f"⚠️ 第一行看起来不是表头，需要添加表头行")
                needs_header_row = True

        # 如果需要添加表头行
        processed_table_data = []
        if needs_header_row:
            print(f"🔄 添加表头行到表格数据中...")

            # 创建表头行
            # 第一列是空或行表头标记
            num_columns = len(table_data[0]) if table_data else 0
            header_row = [""]  # 左上角单元格为空

            # 添加列标题
            for i in range(1, num_columns):
                header_row.append(f"列{i}")

            processed_table_data = [header_row] + table_data
        else:
            processed_table_data = table_data

        print(
            f"📊 处理后的表格尺寸: {len(processed_table_data)}行 × {len(processed_table_data[0]) if processed_table_data else 0}列")
        print(f"📊 第一行（表头）: {processed_table_data[0] if len(processed_table_data) > 0 else '无'}")
        print(f"📊 第二行（数据）: {processed_table_data[1] if len(processed_table_data) > 1 else '无'}")

        # 创建转换器实例
        converter = FinalDataConverter()

        # 准备表格元数据
        table_metadata = {
            'name': source_info.get('table_name', 'Excel表格'),
            'default_unit': source_info.get('default_unit', ''),
            'default_currency': source_info.get('default_currency', '人民币'),
            'default_report_period': source_info.get('default_report_period', ''),
            'headers': {
                'rows': [],  # 行表头
                'cols': []  # 列表头
            }
        }

        print(f"📊 提取原始标记信息...")

        print(f"\n📊 ============ 正确读取标记信息 ============")

        # 1. 找行标记列（在第一行中找）
        row_mark_col_index = -1
        if len(processed_table_data) > 0:
            first_row = processed_table_data[0]
            for j in range(len(first_row)):
                header = str(first_row[j]).strip() if first_row[j] else ""
                if header == "行标记":
                    row_mark_col_index = j
                    print(f"✅ '行标记'列位置: 第{j}列（索引{j}）")
                    print(f"   这一列存储每行的行标记值")
                    break

        # 2. 找列标记行（在第一列中找）
        col_mark_row_index = -1
        for i in range(len(processed_table_data)):
            if len(processed_table_data[i]) > 0:
                cell_value = str(processed_table_data[i][0]).strip() if processed_table_data[i][0] else ""
                if cell_value == "列标记":
                    col_mark_row_index = i
                    print(f"✅ '列标记'行位置: 第{i}行（索引{i}）")
                    print(f"   这一行存储每列的列标记值")
                    break

        # 3. 读取行标记（从行标记列读取）
        print(f"\n🔍 读取行标记（从'行标记'列读取）...")
        row_marks = []
        if row_mark_col_index >= 0:
            print(f"  读取'行标记'列（第{row_mark_col_index}列）的数据作为行标记:")

            # 从第二行开始读取（跳过表头行）
            for i in range(1, len(processed_table_data)):
                if row_mark_col_index < len(processed_table_data[i]):
                    mark_value = processed_table_data[i][row_mark_col_index]
                    print(f"    行{i}（索引{i}）: 值='{mark_value}', 类型={type(mark_value)}")
                    try:
                        if mark_value is None or mark_value == "":
                            row_mark = 1
                        else:
                            # 尝试转换为整数
                            if isinstance(mark_value, (int, float)):
                                row_mark = int(mark_value)
                            else:
                                row_mark = int(float(mark_value)) if '.' in str(mark_value) else int(mark_value)
                        print(f"      → 行标记值: {row_mark}")
                    except Exception as e:
                        print(f"      ❌ 转换失败: {e}, 使用默认值1")
                        row_mark = 1
                    row_marks.append(row_mark)
                else:
                    print(f"    行{i}: 无数据，使用默认值1")
                    row_marks.append(1)

            print(f"  ✅ 读取完成: {len(row_marks)}个行标记值")
            print(f"    行标记: {row_marks}")
        else:
            print(f"  ❌ 未找到'行标记'列")

        # 4. 读取列标记（从列标记行读取）
        print(f"\n🔍 读取列标记（从'列标记'行读取）...")
        col_marks = []
        if col_mark_row_index >= 0:
            print(f"  读取'列标记'行（第{col_mark_row_index}行）的数据作为列标记:")

            col_mark_row = processed_table_data[col_mark_row_index]
            print(f"  列标记行数据: {col_mark_row}")

            # 从第二列开始读取（跳过第一列的"列标记"文本）
            for j in range(1, len(col_mark_row)):
                mark_value = col_mark_row[j]
                print(f"    列{j}（索引{j}）: 值='{mark_value}', 类型={type(mark_value)}")
                try:
                    if mark_value is None or mark_value == "":
                        col_mark = 1
                    else:
                        # 尝试转换为整数
                        if isinstance(mark_value, (int, float)):
                            col_mark = int(mark_value)
                        else:
                            col_mark = int(float(mark_value)) if '.' in str(mark_value) else int(mark_value)
                    print(f"      → 列标记值: {col_mark}")
                except Exception as e:
                    print(f"      ❌ 转换失败: {e}, 使用默认值1")
                    col_mark = 1
                col_marks.append(col_mark)

            print(f"  ✅ 读取完成: {len(col_marks)}个列标记值")
            print(f"    列标记: {col_marks}")
        else:
            print(f"  ❌ 未找到'列标记'行")

        print(f"\n📊 ============ 标记信息验证 ============")
        print(
            f"表格尺寸: {len(processed_table_data)}行 × {len(processed_table_data[0]) if processed_table_data else 0}列")
        print(f"行标记列位置: {row_mark_col_index}")
        print(f"列标记行位置: {col_mark_row_index}")
        print(f"行标记数量: {len(row_marks)} (应有数据行: {len(processed_table_data) - 1})")
        print(
            f"列标记数量: {len(col_marks)} (应有数据列: {len(processed_table_data[0]) - 1 if processed_table_data else 0})")

        # 验证
        expected_row_marks = len(processed_table_data) - 1  # 减去表头行
        expected_col_marks = len(processed_table_data[0]) - 1 if processed_table_data else 0  # 减去行表头列

        if len(row_marks) != expected_row_marks:
            print(f"⚠️ 行标记数量不匹配: 预期{expected_row_marks}，实际{len(row_marks)}")
        if len(col_marks) != expected_col_marks:
            print(f"⚠️ 列标记数量不匹配: 预期{expected_col_marks}，实际{len(col_marks)}")

        marks_info = {
            'row_marks': row_marks,
            'col_marks': col_marks,
            'row_mark_col_index': row_mark_col_index,
            'col_mark_row_index': col_mark_row_index
        }


        # 执行转换
        print(f"🔄 开始转换表格数据...")

        long_format_data = converter.convert_table_to_long_format(
            table_data=table_data,
            table_metadata=table_metadata,
            marks_info=marks_info,
            bank_name=source_info.get('bank_name', '中国建设银行'),
            page_num=source_info.get('page_num', 1),
            entity=source_info.get('entity', '本集团')
        )

        print(f"✅ 转换完成: {len(long_format_data)} 条标准格式记录")

        # ============ 关键：将长格式数据转换为前端需要的双表头格式 ============
        print(f"🔄 将长格式数据转换为前端双表头格式...")

        if not long_format_data or len(long_format_data) == 0:
            print("⚠️ 长格式数据为空，返回空结构")
            frontend_rows = []
        else:
            # 1. 提取所有字段名作为表头
            field_names = list(long_format_data[0].keys())
            print(f"📊 字段名（表头）: {field_names}")

            # 2. 构建前端需要的rows数组
            frontend_rows = []

            # 2.1 添加元数据行
            metadata_row = {
                "__metadata": {
                    "has_dual_headers": True,
                    "top_left_cell": "",
                    "horizontal_headers": field_names,  # 所有字段名作为横向表头
                    "vertical_headers": []  # 纵向表头为空，因为每条记录是一行
                }
            }
            frontend_rows.append(metadata_row)

            # 2.2 添加表头行（第一行数据是字段名本身）
            header_row = {
                "__is_first_row": True,
                "__top_left_cell": "字段名"
            }
            for i, field_name in enumerate(field_names, 1):
                header_row[f"H_{i}"] = field_name

            frontend_rows.append(header_row)

            # 2.3 添加数据行
            for record_idx, record in enumerate(long_format_data):
                data_row = {
                    "__is_data_row": True,
                    "__vertical_header": f"记录{record_idx + 1}"  # 行表头
                }

                # 将每个字段的值放入对应的列
                for i, field_name in enumerate(field_names, 1):
                    value = record.get(field_name, "")
                    # 特殊处理：如果是行标记，保持数值类型
                    if field_name == '行标记' and isinstance(value, (int, float)):
                        data_row[f"H_{i}"] = value
                    else:
                        data_row[f"H_{i}"] = str(value) if value is not None else ""

                frontend_rows.append(data_row)

            print(f"✅ 转换完成: {len(frontend_rows)} 行前端格式数据")
            print(f"📊 数据结构: 元数据行1 + 表头行1 + {len(long_format_data)} 数据行")

        # ============ 返回与get_excel_data相同的格式 ============
        return jsonify({
            "rows": frontend_rows,
            "total_rows": len(frontend_rows),
            "total_columns": len(field_names) if long_format_data else 0,
            "sheet_name": source_info.get('table_name', '扁平化数据'),
            "excel_file": source_info.get('excel_file', ''),
            "pdf_id": source_info.get('pdf_id', ''),
            "has_dual_headers": True,
            "success": True,
            "source_info": source_info,
            "timestamp": datetime.datetime.now().isoformat(),
            "stats": {
                "original_rows": len(table_data),
                "converted_records": len(long_format_data),
                "has_data": len(long_format_data) > 0
            }
        })

        print("------------------------------")
        print(result)

        # 返回数据
        return jsonify(result)

    except Exception as e:
        print(f"❌ Excel数据处理失败: {str(e)}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": f"处理失败: {str(e)}"
        }), 500




# 后端API示例（Python Flask）
@file_bp.route('/excel/save-final', methods=['POST'])
def save_final_excel():
    """最终保存：把前端最新数据写成 JSON 快照"""
    data = request.json
    print("******************** data ******************")
    from pprint import pprint
    pprint(data)

    # 1. 基础校验
    required_fields = ['pdf_id', 'excel_file', 'sheet_name', 'data']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少必要字段: {field}'}), 400

    # 2. 拼路径：统一用 MAIN_ROOT 风格
    from pathlib import Path
    import time
    import os

    file_id   = data['pdf_id']
    sheet_name = data['sheet_name']

    snap_dir  = Path(MAIN_ROOT) / r'data/backend/static/modify_data' / file_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    ts = int(time.time())
    file_name = f"{file_id}_{sheet_name}_{ts}.json"
    file_path = snap_dir / file_name

    # 3. 落盘
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return jsonify({'success': False, 'error': f'写入失败: {e}'}), 500

    # 4. 返回成功
    return jsonify({
        'success': True,
        'message': '已保存最新数据',
        'saved_file': str(file_name),
        'saved_path': str(file_path.relative_to(Path(MAIN_ROOT)))   # 相对路径，调试用
    }), 200


# ========== 新增的Excel转PDF接口 ==========
@file_bp.route('/convert/excel-to-pdf', methods=['POST'])
def convert_excel_to_pdf_api():
    """Excel转PDF接口 - 新增功能"""
    try:
        # 1. 获取文件和参数
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400

        file = request.files['file']
        pages = request.form.get('pages', 'all')
        orientation = request.form.get('orientation', 'portrait')
        dpi = int(request.form.get('dpi', 200))

        # 2. 验证文件
        validate_excel_file(file)

        # 3. 验证参数
        orientation, page_range = validate_conversion_params(orientation, pages)

        # 4. 保存上传的文件
        temp_filepath = save_uploaded_file(file)

        # 5. 执行转换
        output_filepath = convert_excel_to_pdf(
            temp_filepath,
            page_range=page_range,
            orientation=orientation,
            dpi=dpi
        )

        # 6. 返回结果
        return save_and_return_result(output_filepath)

    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'转换失败: {str(e)}'}), 500


# 在 file.py 中添加一个通用的OPTIONS处理
@file_bp.route('/save-excel-modifications', methods=['OPTIONS'])
def handle_save_options():
    """处理CORS预检请求"""
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:8080')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@file_bp.route('/save-excel-modifications', methods=['POST'])
def save_excel_modifications():
    """保存Excel修改"""
    # 添加CORS头
    response = jsonify({'success': True, 'message': '保存成功'})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:8080')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

