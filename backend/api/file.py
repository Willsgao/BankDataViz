"""
文件相关蓝图
"""
from flask import Blueprint, request, jsonify, send_from_directory
from backend.models.database_manager import DatabaseManager
from backend.utils.constants import UPLOAD_FOLDER, MAIN_ROOT
from pathlib import Path

# 新增导入
from backend.service.file_mapping_service import file_mapping_service

file_bp = Blueprint('file', __name__)

db = DatabaseManager()



# 保持所有现有接口不变...
# ---------- 1. 列表（不含软删） ----------
@file_bp.get('/files')
def list_files():
    print("0000000000000000")
    conn = db.connect()
    if not conn:
        return jsonify({"error": "数据库连接失败"}), 500
    c = conn.cursor()
    c.execute(
        "SELECT id, filename, raw_filename, file_type, created_at "
        "FROM files WHERE deleted = 0 ORDER BY created_at DESC"
    )
    rows = c.fetchall()
    conn.close()

    return jsonify([
        {
            "id": r["id"],
            "filename": r["raw_filename"] or r["filename"],  # 优先中文
            "disk_name": r["filename"],  # UUID 实体名
            "file_type": r["file_type"],
            "created_at": r["created_at"],
        }
        for r in rows
    ])



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
        file_path = Path(f"{MAIN_ROOT}/{UPLOAD_FOLDER}") / real_name
        print(f"📁 文件路径: {file_path}")

        if not file_path.exists():
            print(f"❌ 物理文件不存在: {file_path}")
            return jsonify({"error": "物理文件不存在"}), 404

        # 返回文件
        print(f"📤 返回文件: {real_name}")
        return send_from_directory(UPLOAD_FOLDER, real_name)

    except Exception as e:
        print(f"❌ 文件查找错误: {e}")
        return jsonify({"error": "文件查找失败"}), 500
    finally:
        conn.close()


# ---------- 2.1 通过文件ID下载文件 ----------

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
        file_path = Path(UPLOAD_FOLDER) / row["filename"]
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


# ---------- 3. 软删除 ----------
@file_bp.delete('/file/<path:filename>')
def delete_file(filename):
    """
    仅把 deleted 置 1，不真删磁盘文件
    """
    conn = db.connect()
    if not conn:
        return jsonify({"error": "数据库连接失败"}), 500
    c = conn.cursor()

    # 先找真实磁盘名
    c.execute(
        "SELECT filename FROM files "
        "WHERE (raw_filename = ? OR filename = ?) AND deleted = 0",
        (filename, filename)
    )
    row = c.fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "文件不存在"}), 404

    real_name = row["filename"]
    c.execute("UPDATE files SET deleted = 1 WHERE filename = ?", (real_name,))
    conn.commit()
    conn.close()
    return jsonify({"message": "已隐藏"}), 200



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
        # 检查文件是否存在映射中
        file_info = file_mapping_service.get_file_info(file_id)
        if not file_info:
            return jsonify({"error": "文件不存在"}), 404

        disk_name = file_info["disk_name"]
        return send_from_directory(UPLOAD_FOLDER, disk_name)

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
        if not file_info:
            return jsonify({"error": "PDF文件不存在"}), 404

        # 2. 构建Excel文件目录路径
        excel_dir = Path(f"{MAIN_ROOT}/static/excel_data") / file_id
        print("**************excel_dir:", excel_dir)
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
                    print("excel_file.nameexcel_file.name")
                    print(excel_file.name)
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
        # 1. 构建Excel文件路径
        excel_dir = Path(f"{MAIN_ROOT}/static/excel_data") / file_id
        excel_path = excel_dir / excel_file_name

        print("get_file_by_id:", file_id)
        print("excel_path:", excel_path)

        if not excel_path.exists():
            return jsonify({"error": "Excel文件不存在"}), 404

        # 2. 读取指定sheet的数据
        import pandas as pd

        try:
            # 读取指定sheet
            df = pd.read_excel(excel_path, sheet_name=sheet_name)

            # 处理NaN值为空字符串
            df = df.fillna('')

            # 转换为前端需要的格式
            rows = []
            for _, row in df.iterrows():
                row_dict = {}
                for col in df.columns:
                    # 确保列名是字符串
                    col_name = str(col)
                    # 处理各种数据类型
                    cell_value = row[col]
                    if pd.isna(cell_value):
                        row_dict[col_name] = ""
                    else:
                        row_dict[col_name] = str(cell_value)
                rows.append(row_dict)

            return jsonify({
                "rows": rows,
                "total_rows": len(rows),
                "total_columns": len(df.columns) if len(rows) > 0 else 0,
                "sheet_name": sheet_name,
                "excel_file": excel_file_name,
                "pdf_id": file_id
            })

        except ValueError as e:
            if "Worksheet" in str(e) and "not found" in str(e):
                return jsonify({"error": f"Sheet '{sheet_name}' 不存在"}), 404
            else:
                raise e
        except Exception as e:
            print(f"读取Excel数据失败: {e}")
            return jsonify({"error": f"读取表格数据失败: {str(e)}"}), 500

    except Exception as e:
        print(f"处理Excel数据请求失败: {e}")
        return jsonify({"error": "处理请求失败"}), 500

