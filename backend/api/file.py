"""
文件相关蓝图 - 重构版本（只重构Excel转PDF功能）
"""
from flask import Blueprint, request, jsonify, send_from_directory, make_response
from backend.models.unified_db import DatabaseManager as OldDatabaseManager
from backend.utils.constants import UPLOAD_FOLDER, MAIN_ROOT, DATABASE, EXCEL_OUTPUT_ROOT
from pathlib import Path

# 新增导入
from backend.models.safe_unified_db import SafeDatabaseManager  # 使用安全的数据库管理器
from backend.service.file_mapping_service import file_mapping_service

from .file_handlers.excel_data_handler import ExcelDataHandler
excel_data_handler = ExcelDataHandler(MAIN_ROOT, EXCEL_OUTPUT_ROOT)

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



@file_bp.get('/file-by-id/<file_id>')
def get_file_by_id(file_id):
    try:
        print(f"🔍🔍 文件下载请求 file_id: {file_id}")

        # 直接使用 file_id（UUID格式）
        file_uuid = file_id.split('.')[0] if '.' in file_id else file_id
        print(f"🔍🔍 直接使用UUID: {file_uuid}")

        # 检查文件是否存在映射中
        file_info = file_mapping_service.get_file_info(file_uuid)
        if not file_info:
            print(f"❌ 文件映射服务中没有找到UUID: {file_uuid}")
            return jsonify({"error": "文件不存在"}), 404

        disk_name = file_info["disk_name"]
        PDF_DIR = Path(MAIN_ROOT) / UPLOAD_FOLDER

        # 🔥 调试：打印路径信息
        print(f"🔍 查找文件路径: {PDF_DIR}")
        print(f"🔍 文件名: {disk_name}")

        # 检查文件是否存在
        file_path = PDF_DIR / disk_name
        print(f"🔍 完整文件路径: {file_path}")

        if not file_path.exists():
            print(f"❌ 物理文件不存在: {file_path}")

            # 列出目录中的文件
            if PDF_DIR.exists():
                files_in_dir = list(PDF_DIR.glob("*.pdf"))
                print(f"📂 目录中的PDF文件: {[f.name for f in files_in_dir[:5]]}")
            else:
                print(f"❌ 目录不存在: {PDF_DIR}")

            return jsonify({"error": "物理文件不存在"}), 404

        print(f"✅ 准备返回文件: {disk_name}")
        return send_from_directory(str(PDF_DIR), disk_name)

    except Exception as e:
        print(f"❌❌ 文件下载失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "文件下载失败"}), 500




@file_bp.get('/excel-sheets/<file_id>')
def get_excel_sheets(file_id):
    """
    根据PDF文件ID获取对应的Excel sheet列表 - 修复路径问题
    """
    try:
        print(f"🔍🔍 获取Excel sheets请求 file_id: {file_id}")

        # 🔥🔥🔥 关键修复：清理file_id，移除.pdf扩展名
        clean_file_id = excel_data_handler.get_correct_pdf_id(file_id, db)

        # 2. 构建Excel文件目录路径
        excel_dir = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / clean_file_id  # 🔥 使用清理后的ID
        print(f"📁 Excel目录路径: {excel_dir}")

        if not excel_dir.exists():
            print(f"⚠️ Excel目录不存在: {excel_dir}")

            # 🔥🔥🔥 备选方案1：尝试使用原始file_id（不带.pdf）
            alt_excel_dir = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / file_id
            print(f"🔍🔍 尝试备选Excel目录1: {alt_excel_dir}")

            if alt_excel_dir.exists():
                excel_dir = alt_excel_dir
                print(f"✅ 使用备选目录1: {excel_dir}")
            else:
                # 🔥🔥🔥 备选方案2：尝试使用UUID部分
                if '_' in file_id:
                    uuid_part = file_id.split('_')[0]
                    alt_excel_dir2 = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / uuid_part
                    print(f"🔍🔍 尝试备选Excel目录2: {alt_excel_dir2}")

                    if alt_excel_dir2.exists():
                        excel_dir = alt_excel_dir2
                        print(f"✅ 使用备选目录2: {excel_dir}")
                    else:
                        return jsonify({"excel_files": []})
                else:
                    return jsonify({"excel_files": []})

        print(f"✅ Excel目录存在: {excel_dir}")

        # 3. 查找目录中的所有Excel文件
        excel_files = []
        supported_extensions = ['.xlsx', '.xls']

        for ext in supported_extensions:
            print(f"🔍🔍 查找扩展名: {ext}")
            for excel_file in excel_dir.glob(f"*{ext}"):
                print(f"🔍🔍 找到Excel文件: {excel_file}")
                if excel_file.is_file():
                    print(f"✅ 添加Excel文件: {excel_file.name}")
                    excel_files.append({
                        "file_name": excel_file.name,
                        "file_path": str(excel_file),
                        "file_size": excel_file.stat().st_size
                    })

        if not excel_files:
            print("⚠️ 目录中没有找到Excel文件")
            return jsonify({"excel_files": []})

        print(f"✅ 找到 {len(excel_files)} 个Excel文件")

        # 4. 读取每个Excel文件的sheet列表
        import pandas as pd
        result = []

        for excel_file in excel_files:
            try:
                print(f"🔍🔍 读取Excel文件: {excel_file['file_name']}")
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
                print(f"✅ 成功读取 {len(sheet_names)} 个sheet")

            except Exception as e:
                print(f"❌ 读取Excel文件失败 {excel_file['file_name']}: {e}")
                # 即使读取失败，也返回文件信息
                result.append({
                    "excel_file": excel_file["file_name"],
                    "sheets": [],
                    "total_sheets": 0,
                    "error": str(e)
                })
                continue

        print(f"✅ 返回结果: {len(result)} 个Excel文件信息")
        return jsonify({
            "excel_files": result,
            "pdf_id": clean_file_id,  # 🔥 返回清理后的ID
            "pdf_name": file_id,  # 保持原始file_id用于显示
            "total_excel_files": len(result)
        })

    except Exception as e:
        print(f"❌❌ 获取Excel sheets失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "获取表格列表失败"}), 500


@file_bp.get('/file/excel-data/<file_id>/<path:excel_file_name>/<sheet_name>')
def get_excel_data(file_id, excel_file_name, sheet_name):
    """
    读取Excel文件中特定sheet的数据
    """
    try:
        print(f"🔍🔍 获取Excel数据请求: file_id={file_id}, excel_file={excel_file_name}, sheet={sheet_name}")

        # 🔥🔥 关键修复：清理file_id，移除.pdf扩展名
        clean_file_id = excel_data_handler.get_correct_pdf_id(file_id, db)

        # 1. 构建Excel文件路径
        excel_dir = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / clean_file_id
        print(f"📁 Excel文件路径excel_dir: {excel_dir}")
        excel_path = excel_dir / excel_file_name

        print(f"📁 Excel文件路径: {excel_path}")

        if not excel_path.exists():
            print(f"❌ Excel文件不存在: {excel_path}")

            # 🔥🔥 尝试备选路径：如果清理后找不到，尝试使用原始file_id
            if clean_file_id != file_id:
                alt_excel_dir = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / file_id
                alt_excel_path = alt_excel_dir / excel_file_name
                print(f"🔍🔍 尝试备选路径: {alt_excel_path}")

                if alt_excel_path.exists():
                    excel_dir = alt_excel_dir
                    excel_path = alt_excel_path
                    print(f"✅ 使用备选路径: {excel_path}")
                else:
                    return jsonify({"error": "Excel文件不存在"}), 404
            else:
                return jsonify({"error": "Excel文件不存在"}), 404

        print(f"✅ Excel文件存在: {excel_path}")

        # 2. 读取Excel文件
        try:
            import pandas as pd
            print("🎯 直接读取Excel文件数据（跳过快照）")

            # 读取指定的sheet
            df = pd.read_excel(
                excel_path,
                sheet_name=sheet_name,
                header=None,  # 不自动识别表头
                dtype=str  # 全部读取为字符串
            )

            # 将NaN替换为空字符串
            df = df.fillna('')

            # 转换为二维列表
            data = df.values.tolist()

            print(f"✅ 成功读取sheet '{sheet_name}'，数据形状: {len(data)}行 x {len(data[0]) if data else 0}列")

            # 检查是否有元数据行
            metadata_row_index = -1
            for i, row in enumerate(data):
                if row and isinstance(row[0], str) and row[0].startswith('#METADATA_START#'):
                    metadata_row_index = i
                    print(f"🔍 找到元数据起始行: 第{i}行")
                    break

            # 如果有元数据，提取它
            metadata = {}
            if metadata_row_index >= 0:
                for i in range(metadata_row_index, min(metadata_row_index + 10, len(data))):
                    if i < len(data) and data[i]:
                        cell_value = str(data[i][0])
                        if cell_value.startswith('#METADATA_END#'):
                            break
                        elif ':' in cell_value and not cell_value.startswith('#'):
                            key, value = cell_value.split(':', 1)
                            metadata[key.strip()] = value.strip()
                            print(f"📄 提取元数据: {key} = {value}")

            # 如果找到元数据，在数据中移除元数据行
            if metadata_row_index >= 0:
                data = data[:metadata_row_index]
                print(f"✂️ 移除元数据行，保留 {len(data)} 行数据")

            return jsonify({
                "success": True,
                "data": data,
                "metadata": metadata,
                "rows": len(data),
                "cols": len(data[0]) if data else 0
            })

        except Exception as e:
            print(f"❌ 读取Excel文件失败: {e}")
            return jsonify({"error": f"读取Excel文件失败: {str(e)}"}), 500

    except Exception as e:
        print(f"❌❌ 获取Excel数据失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "获取Excel数据失败"}), 500




@file_bp.get('/excel-data/<file_id>/<path:excel_file_name>/<sheet_name>')
def get_excel_data_api(file_id, excel_file_name, sheet_name):
    """
    提供Excel数据API接口 - 修复路径问题
    """
    try:
        print(f"🎯🎯🎯 收到Excel数据API请求: file_id={file_id}, excel_file={excel_file_name}, sheet={sheet_name}")

        # 🔥🔥🔥 关键修复：清理file_id，移除.pdf扩展名
        clean_file_id = excel_data_handler.get_correct_pdf_id(file_id, db)

        # 1. 构建Excel文件路径
        excel_dir = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / clean_file_id
        excel_path = excel_dir / excel_file_name

        print(f"📁 Excel文件路径: {excel_path}")

        if not excel_path.exists():
            print(f"❌ Excel文件不存在: {excel_path}")

            # 🔥🔥🔥 备选方案1：尝试使用原始file_id
            if clean_file_id != file_id:
                alt_excel_dir = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / file_id
                alt_excel_path = alt_excel_dir / excel_file_name
                print(f"🔍🔍 尝试备选路径1: {alt_excel_path}")

                if alt_excel_path.exists():
                    excel_dir = alt_excel_dir
                    excel_path = alt_excel_path
                    clean_file_id = file_id
                    print(f"✅ 使用备选路径1: {excel_path}")
                else:
                    # 🔥🔥🔥 备选方案2：如果是数字ID，查询数据库获取UUID
                    if clean_file_id.isdigit():
                        print(f"🔍🔍 尝试备选方案2: 数字ID查询数据库 {clean_file_id}")
                        conn = db.connect()
                        if conn:
                            c = conn.cursor()
                            c.execute("SELECT filename FROM files WHERE id = ? AND deleted = 0", (clean_file_id,))
                            row = c.fetchone()
                            conn.close()

                            if row:
                                real_uuid = row["filename"].split('.')[0] if '.' in row["filename"] else row["filename"]
                                print(f"✅ 找到数据库对应UUID: {real_uuid}")

                                alt_excel_dir2 = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / real_uuid
                                alt_excel_path2 = alt_excel_dir2 / excel_file_name
                                print(f"🔍🔍 尝试数据库路径: {alt_excel_path2}")

                                if alt_excel_path2.exists():
                                    excel_dir = alt_excel_dir2
                                    excel_path = alt_excel_path2
                                    clean_file_id = real_uuid
                                    print(f"✅ 使用数据库路径: {excel_path}")
                                else:
                                    return jsonify({"success": False, "error": "Excel文件不存在"}), 404
                            else:
                                return jsonify({"success": False, "error": "Excel文件不存在"}), 404
                        else:
                            return jsonify({"success": False, "error": "Excel文件不存在"}), 404
                    else:
                        return jsonify({"success": False, "error": "Excel文件不存在"}), 404
            else:
                return jsonify({"success": False, "error": "Excel文件不存在"}), 404

        print(f"✅ Excel文件存在: {excel_path}")

        # 2. 读取Excel文件
        try:
            import pandas as pd
            print("🎯 直接读取Excel文件数据")

            # 读取指定的sheet
            df = pd.read_excel(
                excel_path,
                sheet_name=sheet_name,
                header=None,  # 不自动识别表头
                dtype=str  # 全部读取为字符串
            )

            # 将NaN替换为空字符串
            df = df.fillna('')

            # 🔥🔥🔥 转换为二维列表
            data = df.values.tolist()

            print(f"✅ 成功读取sheet '{sheet_name}'，数据形状: {len(data)}行 x {len(data[0]) if data else 0}列")

            # 🔥🔥🔥 提取元数据
            metadata = {}
            clean_data = []

            for row in data:
                if not row or not row[0]:
                    clean_data.append(row)
                    continue

                first_cell = str(row[0]).strip()

                # 查找包含冒号的行作为元数据
                if ":" in first_cell:
                    try:
                        key, value = first_cell.split(":", 1)
                        key = key.strip().lower()
                        value = value.strip()

                        # 只收集已知的元数据字段
                        valid_keys = ["bankname", "currency", "report_period", "unit", "table_name", "ocr_table_id"]
                        if key in valid_keys:
                            metadata[key] = value
                            print(f"✅ 找到元数据: {key} = {value}")
                        clean_data.append(row)
                    except:
                        clean_data.append(row)
                else:
                    clean_data.append(row)

            print(f"📋 提取的元数据: {metadata}")

            result = {
                "success": True,
                "data": clean_data,  # 返回清理后的数据
                "rows": len(clean_data),
                "cols": len(clean_data[0]) if clean_data else 0,
                "sheet_name": sheet_name,
                "excel_file": excel_file_name,
                "metadata": metadata,  # 🔥 返回提取的元数据
                "has_custom_metadata": bool(metadata),  # 🔥 标记是否有元数据
                "file_path": str(excel_path)
            }

            # 🔥🔥🔥 返回前端期望的格式
            return jsonify(result)

        except Exception as e:
            print(f"❌ 读取Excel文件失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": f"读取Excel文件失败: {str(e)}"}), 500

    except Exception as e:
        print(f"❌❌❌ 获取Excel数据API失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "获取Excel数据失败"}), 500


@file_bp.route('/excel/save-final', methods=['POST'])
def save_final_excel():
    """统一保存整个表格数据 - 保护其他Sheet"""
    data = request.json
    print("******************** 保存整个表格（保护其他Sheet） ******************")

    # 基础校验
    required_fields = ['pdf_id', 'excel_file', 'sheet_name', 'table_type', 'data']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少必要字段: {field}'}), 400

    try:
        pdf_id = data['pdf_id']
        excel_file = data['excel_file']
        sheet_name = data['sheet_name']
        table_type = data['table_type']
        table_data = data['data']

        print(f"💾 保存数据: PDF={pdf_id}, 文件={excel_file}, Sheet={sheet_name}, 类型={table_type}")
        print(f"📊 接收数据: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

        # 根据表类型选择保存方式
        if table_type == 'original':
            result = excel_data_handler.save_complete_table_data(pdf_id, excel_file, sheet_name, table_data, table_type)
        elif table_type == 'flattened':
            result = excel_data_handler.save_flattened_table_data(pdf_id, excel_file, sheet_name, table_data, table_type)
        else:
            return jsonify({'error': f'不支持的表类型: {table_type}'}), 400

        if not result['success']:
            return jsonify({'success': False, 'error': result['error']}), 500

        return jsonify({
            'success': True,
            'message': '表格数据保存成功',
            'saved_count': result.get('saved_rows', 0),
            'data_dimensions': result.get('data_dimensions', '未知'),
            'excel_updated': result.get('excel_updated', False),
            'sheets_protected': result.get('sheets_protected', False),
            'protected_sheets_count': result.get('protected_sheets_count', 0),
            'file_created': result.get('file_created', False)
        }), 200

    except Exception as e:
        print(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'保存失败: {str(e)}'}), 500












@file_bp.route('/excel/save-flattened', methods=['POST', 'OPTIONS'])
def save_flattened_data():
    """保存扁平化数据到独立的Excel文件（通过文件名前缀映射）"""
    if request.method == 'OPTIONS':
        # CORS预检请求处理
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    data = request.json
    print("******************** 保存扁平化数据到独立文件 ******************")

    # 基础校验
    required_fields = ['pdf_id', 'excel_file', 'sheet_name', 'table_type', 'flattened_data']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少必要字段: {field}'}), 400

    try:
        pdf_id = data['pdf_id']
        original_excel_file = data['excel_file']  # 原Excel文件名
        sheet_name = data['sheet_name']
        table_type = data['table_type']
        table_data = data['flattened_data']

        print(f"💾 保存扁平化数据: PDF={pdf_id}, 原文件={original_excel_file}, Sheet={sheet_name}")

        # 通过固定前缀生成扁平化Excel文件名
        flattened_excel_file = excel_data_handler.generate_flattened_filename(original_excel_file)
        print(f"📁 扁平化文件名: {flattened_excel_file}")
        print("&&&&&&&&&&&&扁平化文件名&&&&&&&&&&&&&")
        print(pdf_id,
            original_excel_file,
            flattened_excel_file,
            sheet_name,)

        # 保存到独立文件
        result = excel_data_handler.save_to_flattened_excel(
            pdf_id,
            original_excel_file,
            flattened_excel_file,
            sheet_name,
            table_data
        )

        if not result['success']:
            return jsonify({'success': False, 'error': result['error']}), 500

        return jsonify({
            'success': True,
            'message': '扁平化数据保存成功',
            'flattened_file': flattened_excel_file,
            'original_file': original_excel_file,
            'file_created': result.get('file_created', False),
            'sheet_created': result.get('sheet_created', False),
            'saved_rows': result.get('saved_rows', 0),
            'saved_columns': result.get('saved_columns', 0),
            'data_dimensions': result.get('data_dimensions', '未知')
        }), 200

    except Exception as e:
        print(f"❌ 扁平化数据保存失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'扁平化数据保存失败: {str(e)}'}), 500



@file_bp.route('/excel-data/<path:filename>')
def serve_excel_file(filename):
    """提供 Excel 文件下载"""
    # 修正：统一使用Path对象构建路径

    file_path = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT / filename
    if not file_path.exists():
        return "文件不存在", 404
    return send_from_directory(file_path.parent, file_path.name)


# 新增导入Excel扁平化处理器
from .file_handlers.excel_flatten_handler import ExcelFlattenHandler
# 初始化Excel扁平化处理器
excel_flatten_handler = ExcelFlattenHandler(CONVERTER_AVAILABLE, FinalDataConverter)

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
        # 获取请求数据
        data = request.get_json()

        if not data:
            print("❌ 请求数据为空")
            return jsonify({
                "success": False,
                "error": "请求数据为空"
            }), 400

        # 使用处理器处理
        result = excel_flatten_handler.excel_flatten_from_excel(data)

        if not result.get('success', True):
            return jsonify(result), 500

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



# 在Python中直接查看数据库内容
@file_bp.route('/debug-files')
def debug_files():
    """调试接口：查看数据库中的实际文件名"""
    conn = db.connect()
    c = conn.cursor()

    c.execute("""
        SELECT id, filename, raw_filename, file_type
        FROM files 
        WHERE deleted = 0 AND file_type = 'pdf'
        LIMIT 10
    """)

    rows = c.fetchall()
    conn.close()

    print("📋 数据库中的文件:")
    for row in rows:
        print(f"  ID: {row['id']}")
        print(f"  文件名: {row['filename']}")
        print(f"  原始名: {row['raw_filename']}")
        print(f"  类型: {row['file_type']}")
        print("  ---")

    return jsonify({
        "files": [dict(row) for row in rows]
    })



@file_bp.route('/debug-table-data')
def debug_table_data():
    """调试接口：查看表数据"""
    try:
        table_name = request.args.get('table', 'table_processing_records')
        limit = request.args.get('limit', 10, type=int)

        db_manager = SafeDatabaseManager()
        db_manager._connect()

        # 获取表数据
        db_manager.cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
        rows = db_manager.cursor.fetchall()

        # 获取表结构
        db_manager.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [dict(row) for row in db_manager.cursor.fetchall()]

        db_manager._close()

        return jsonify({
            "table": table_name,
            "columns": columns,
            "data": [dict(row) for row in rows],
            "count": len(rows)
        })

    except Exception as e:
        return jsonify({"error": str(e)})


@file_bp.route('/debug-search-query')
def debug_search_query():
    """调试搜索查询"""
    try:
        keyword = request.args.get('keyword', '建设银行')

        db_manager = SafeDatabaseManager()
        db_manager._connect()

        # 执行搜索查询
        query = """
            SELECT * FROM table_processing_records 
            WHERE bank_name LIKE ? OR pdf_folder LIKE ? 
            ORDER BY created_at DESC LIMIT 10
        """
        params = (f'%{keyword}%', f'%{keyword}%')

        print(f"🔍🔍 调试搜索查询:")
        print(f"SQL: {query}")
        print(f"参数: {params}")

        db_manager.cursor.execute(query, params)
        rows = db_manager.cursor.fetchall()

        db_manager._close()

        return jsonify({
            "query": query,
            "params": params,
            "results": [dict(row) for row in rows],
            "count": len(rows)
        })

    except Exception as e:
        return jsonify({"error": str(e)})



@file_bp.route('/debug-search-complete')
def debug_search_complete():
    """完整调试搜索流程"""
    try:
        keyword = request.args.get('keyword', '建设银行')

        print(f"🔍🔍 完整调试搜索流程: 关键词='{keyword}'")

        # 1. 直接执行SQL查询
        db_manager = SafeDatabaseManager()
        db_manager._connect()

        query = "SELECT * FROM table_processing_records WHERE bank_name LIKE ? LIMIT 5"
        params = (f'%{keyword}%',)

        db_manager.cursor.execute(query, params)
        rows = db_manager.cursor.fetchall()

        print(f"  📊 直接SQL查询结果: {len(rows)} 条")

        # 2. 转换为字典
        dict_results = []
        for i, row in enumerate(rows):
            row_dict = dict(row)
            dict_results.append(row_dict)
            print(f"    第{i + 1}条: {row_dict.get('bank_name', '无银行名')}")

        db_manager._close()

        # 3. 测试SafeDatabaseManager方法
        manager_results = db_manager.search_pdf_files(keyword, 5)
        print(f"  📊 SafeDatabaseManager结果: {len(manager_results)} 条")

        return jsonify({
            "direct_sql_count": len(rows),
            "direct_sql_results": dict_results,
            "manager_results_count": len(manager_results),
            "manager_results_sample": manager_results[:2] if manager_results else []
        })

    except Exception as e:
        return jsonify({"error": str(e)})



@file_bp.route('/search-pdf-compatible11')
def search_pdf_compatible11():
    """搜索PDF文件 - 实际搜索数据库版本"""
    print("🔥🔥🔥🔥🔥 search_pdf_compatible 函数被调用了！")

    try:
        keyword = request.args.get('keyword', '').strip()
        limit = request.args.get('limit', 100, type=int)

        print(f"🔍 搜索关键词: '{keyword}'")

        # 连接数据库
        db_manager = SafeDatabaseManager()

        # 使用 search_pdf_files 方法
        results = db_manager.search_pdf_files(keyword, limit)

        print(f"📊 数据库返回 {len(results)} 条结果")

        if not results:
            return jsonify({
                "files": [],
                "count": 0
            })

        # 转换为前端需要的格式
        files = []
        for row in results:
            # 确保 row 是字典
            if not isinstance(row, dict):
                row = dict(row)

            # 构建文件信息
            file_info = {
                "id": str(row.get("id", "")),
                "file_id": str(row.get("pdf_folder", "")),  # 重复id字段确保兼容
                "disk_name": row.get("pdf_folder", ""),
                "file_type": "pdf",
                "filename": row.get("bank_name", "未知银行"),
                "name": row.get("bank_name", "未知银行"),
                "matchType": "数据库匹配",
                "status": row.get("status", ""),
                "created_at": row.get("created_at", ""),
                "raw_filename": row.get("bank_name", "未知银行"),
            }

            files.append(file_info)

        print(f"✅ 转换完成，返回 {len(files)} 个文件")

        return jsonify({
            "files": files,
            "count": len(files)
        })

    except Exception as e:
        print(f"❌❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()

        # 出错时返回空数组
        return jsonify({
            "files": [],
            "count": 0
        })


@file_bp.route('/search-pdf-compatible')
def search_pdf_compatible():
    """搜索PDF文件 - 修复版本（搜索files表）"""
    print("🔥🔥🔥🔥🔥 search_pdf_compatible 函数被调用了！")

    try:
        keyword = request.args.get('keyword', '').strip()
        limit = request.args.get('limit', 100, type=int)

        print(f"🔍 搜索关键词: '{keyword}'")

        if not keyword:
            return jsonify({
                "files": [],
                "count": 0
            })

        # 🔥🔥 关键修复：直接连接数据库，搜索files表
        conn = db.connect()
        if not conn:
            return jsonify({"error": "数据库连接失败"}), 500

        c = conn.cursor()

        # 🔥🔥 修复SQL：搜索files表而不是table_processing_records
        query = """
            SELECT id, filename, raw_filename, file_type, created_at 
            FROM files 
            WHERE deleted = 0 
            AND file_type = 'pdf'
            AND (raw_filename LIKE ? OR filename LIKE ?)
            ORDER BY created_at DESC 
            LIMIT ?
        """

        search_pattern = f'%{keyword}%'
        params = (search_pattern, search_pattern, limit)

        print(f"🔍🔍 执行查询: {query}")
        print(f"🔍🔍 参数: {params}")

        c.execute(query, params)
        rows = c.fetchall()

        print(f"📊 数据库返回 {len(rows)} 条结果")

        # 转换为前端需要的格式
        files = []
        for row in rows:
            # 🔥🔥 修复字段映射：使用files表的字段
            file_info = {
                "id": row["id"],
                "file_id": row["filename"].split('.')[0] if '.' in row["filename"] else row["filename"],  # 使用UUID
                "disk_name": row["filename"],  # 磁盘文件名
                "file_type": row["file_type"],
                "filename": row["raw_filename"] or row["filename"],  # 显示中文名
                "name": row["raw_filename"] or row["filename"],  # 兼容字段
                "matchType": "文件名匹配",
                "status": "active",
                "created_at": row["created_at"],
                "raw_filename": row["raw_filename"]  # 原始文件名
            }
            files.append(file_info)
            print(f"✅ 找到文件: {file_info['filename']}")

        conn.close()

        print(f"✅ 转换完成，返回 {len(files)} 个文件")

        return jsonify({
            "files": files,
            "count": len(files)
        })

    except Exception as e:
        print(f"❌❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "files": [],
            "count": 0,
            "error": str(e)
        })


# 临时添加测试数据的接口
@file_bp.route('/add-test-pdf')
def add_test_pdf():
    """添加测试PDF记录"""
    try:
        conn = db.connect()
        c = conn.cursor()

        c.execute("""
            INSERT INTO files (filename, raw_filename, file_type, created_at) 
            VALUES (?, ?, ?, datetime('now'))
        """, ("test-uuid-1.pdf", "建设银行年度报告.pdf", "pdf"))

        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500







