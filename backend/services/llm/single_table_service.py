
import os
import time
import asyncio
import pandas as pd

from pathlib import Path
from flask import jsonify, request

from backend.schemas.table_schemas import ExcelSaveConfig
from backend.services.llm.task_management_service import logger

from backend.services.llm.utils import (
    validate_required_params,
    convert_to_excel_url)

from backend.services.llm.core_service import  (
    get_non_financial_table_service,
    get_table_processor)

from backend.utils.constants import EXCEL_DATA_DIR


async def _process_single_image(data):
    """处理单张图片的异步函数 - 添加Excel存在性检查"""
    try:
        # 验证必要参数
        is_valid, error_msg = validate_required_params(
            data, ['image_path', 'output_path']
        )

        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }

        image_path = data.get('image_path')
        output_path = data.get('output_path')
        sheet_name = data.get('sheet_name', '识别结果')
        bank_name = data.get('bank_name', '未知银行')
        file_name = data.get('file_name', Path(image_path).stem)

        print("************image_path****output_path****************")
        print(image_path)
        print(output_path)

        # 检查图片文件是否存在
        if not Path(image_path).exists():
            return {
                "success": False,
                "error": f"图片文件不存在: {image_path}"
            }

        # ⭐⭐⭐ 如果Excel不存在，继续原有的LLM识别流程 ⭐⭐⭐
        processor = get_table_processor()

        if not processor.llm_client:
            return {
                "success": False,
                "error": "请先配置LLM客户端"
            }

        # ⭐⭐⭐ 修复：使用常量中的路径 ⭐⭐⭐
        # 使用已有的标识创建Excel存储文件夹
        folder_name = Path(image_path).stem.split('_')[0]
        excel_dir = EXCEL_DATA_DIR / folder_name
        excel_dir.mkdir(parents=True, exist_ok=True)

        # 重新构建输出路径
        excel_filename = Path(output_path).name
        new_output_path = excel_dir / excel_filename
        final_output_path = str(new_output_path)

        print(f"✅ 正确的Excel文件路径: {final_output_path}")

        # ⭐⭐⭐ 再次检查最终路径的缓存（确保路径一致性）⭐⭐⭐
        final_cache_result = _check_excel_cache_with_validation(
            image_path,
            final_output_path,
            sheet_name,
            "financial"
        )
        if final_cache_result:
            print("✅ 从最终路径缓存返回金融表格数据")
            return final_cache_result

        # 配置Excel保存参数
        excel_config = ExcelSaveConfig(
            anchor_cell=data.get('anchor_cell', 'R2'),
            width_px=data.get('width_px', 768),
            mode=data.get('mode', 'overwrite')
        )

        # 处理图片
        result = await processor.process_table_pipeline(
            image_path=image_path,
            out_file=final_output_path,
            sheet_name=sheet_name,
            bank_name=bank_name,
            file_name=file_name,
            excel_config=excel_config
        )

        print(f"单张图片result: {result}")

        # ⭐⭐⭐ 修改：使用真实的表格名 ⭐⭐⭐
        table_name = result.table_name
        if not table_name or table_name.startswith('表格_'):
            # 如果没有获取到真实表格名，使用图片文件名
            table_name = Path(image_path).stem

        # ⭐⭐⭐ 关键修复：确保生成有效的Excel文件 ⭐⭐⭐
        excel_exists = Path(final_output_path).exists()

        # 如果Excel文件不存在，但处理成功，创建一个基础Excel文件
        if not excel_exists and (result.status == "success" or result.status == "non_financial"):
            try:
                import pandas as pd
                from backend.services.excel_storage_service import ExcelStorageService

                excel_service = ExcelStorageService()
                # 创建基础Excel文件
                excel_service.create_new_excel(final_output_path)

                # 添加基础信息工作表
                basic_data = {
                    '信息类型': ['处理状态', '表格类型', '复杂度', '评估原因', '图片路径'],
                    '值': [
                        result.status,
                        '非金融表格' if result.status == 'non_financial' else '金融表格',
                        result.complexity,
                        result.assessment_reason,
                        image_path
                    ]
                }
                basic_df = pd.DataFrame(basic_data)

                excel_service.save_dataframe(
                    df=basic_df,
                    excel_path=final_output_path,
                    sheet_name=sheet_name,
                    map_name=table_name,  # ⭐⭐⭐ 使用真实表格名 ⭐⭐⭐
                    image_data=image_path if Path(image_path).exists() else None
                )

                excel_exists = True
                print("✅ 已创建基础Excel文件")

            except Exception as create_error:
                print(f"❌ 创建基础Excel文件失败: {create_error}")

        # ⭐⭐⭐ 统一返回格式 ⭐⭐⭐
        if (result.status == "success" or result.status == "non_financial") and excel_exists:
            # 构建前端可访问的URL
            excel_url = convert_to_excel_url(final_output_path)

            # 判断是否为非金融表格
            is_non_financial = result.status == "non_financial"

            # 读取Excel数据构建recognizedData
            headers = []
            data_list = []
            try:
                import pandas as pd
                df = pd.read_excel(final_output_path, sheet_name=sheet_name)
                if not df.empty:
                    headers = list(df.columns)
                    for _, row in df.iterrows():
                        row_data = {}
                        for header in headers:
                            cell_value = row[header]
                            row_data[header] = str(cell_value) if pd.notna(cell_value) else ""
                        data_list.append(row_data)
            except Exception as e:
                print(f"❌ 读取Excel数据失败: {e}")

            # 构建与批量处理一致的返回格式
            return {
                "success": True,
                "data": {
                    # 基础信息（与批量处理统一）
                    "total": 1,
                    "success": 1,
                    "failed": 0,
                    "non_financial": 1 if is_non_financial else 0,
                    "results": [
                        {
                            "image_path": image_path,
                            "status": result.status,
                            "status_text": "成功" if result.status == "success" else "非金融表格",
                            "complexity": result.complexity,
                            "table_name": table_name,  # ⭐⭐⭐ 使用真实表格名 ⭐⭐⭐
                            "sheet_name": sheet_name,
                            "error_message": result.error_message,
                            "assessment_reason": result.assessment_reason,
                            "success": True,
                            "is_non_financial": is_non_financial,
                            "output_file": final_output_path,
                            "excel_url": excel_url
                        }
                    ],
                    "output_file": final_output_path,
                    "excel_url": excel_url,
                    "table_type": "financial" if not is_non_financial else "non_financial",
                    "processing_completed": True,
                    "message": "单张图片处理完成",
                    "excel_saved": True,
                    "from_cache": False  # 明确标记不是从缓存加载
                },
                # ⭐⭐⭐ 关键修复：添加 recognizedData 字段 ⭐⭐⭐
                "recognizedData": {
                    "headers": headers,
                    "data": data_list,
                    "tableName": table_name,
                    "excelPath": final_output_path,
                    "fromCache": False
                },
                "task_id": f"single_{int(time.time())}",
                "processing_completed": True,
                "from_cache": False
            }
        else:
            return {
                "success": False,
                "error": result.error_message or "表格处理失败",
                "errorCode": "PROCESS_FAILED"
            }

    except Exception as e:
        print(f"❌ _process_single_image 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "errorCode": "SYSTEM_ERROR"
        }


async def _process_non_financial_table(data):
    """处理普通表格的异步函数 - 添加Excel存在性检查"""
    try:
        # 验证必要参数
        is_valid, error_msg = validate_required_params(
            data, ['image_path', 'output_path']
        )

        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }

        image_path = data.get('image_path')
        output_path = data.get('output_path')
        sheet_name = data.get('sheet_name', '普通表格识别结果')
        bank_name = data.get('bank_name', '未知机构')
        file_name = data.get('file_name', Path(image_path).stem)


        # 检查图片文件是否存在
        if not Path(image_path).exists():
            return {
                "success": False,
                "error": f"图片文件不存在: {image_path}"
            }

        # ⭐⭐⭐ 关键修复：使用常量中的路径 ⭐⭐⭐
        # 使用已有的标识创建Excel存储文件夹
        folder_name = Path(image_path).stem.split('_')[0]
        excel_dir = EXCEL_DATA_DIR / folder_name
        excel_dir.mkdir(parents=True, exist_ok=True)

        # 重新构建输出路径（确保路径一致性）
        excel_filename = Path(output_path).name
        new_output_path = excel_dir / excel_filename
        final_output_path = str(new_output_path)

        print(f"✅ 正确的普通表格Excel文件路径: {final_output_path}")


        # ⭐⭐⭐ 如果Excel不存在，继续原有的LLM识别流程 ⭐⭐⭐
        service = get_non_financial_table_service()

        if not service.llm_client:
            return {
                "success": False,
                "error": "请先配置LLM客户端"
            }

        # 配置Excel保存参数
        excel_config = ExcelSaveConfig(
            anchor_cell=data.get('anchor_cell', 'R2'),
            width_px=data.get('width_px', 768),
            mode=data.get('mode', 'overwrite')
        )

        # 处理普通表格
        result = await service.process_table_pipeline(
            image_path=image_path,
            out_file=final_output_path,
            sheet_name=sheet_name,
            bank_name=bank_name,
            file_name=file_name,
            excel_config=excel_config
        )

        print(f"普通表格处理结果 - 状态: {result.status}, 错误信息: {result.error_message}")

        # ⭐⭐⭐ 修改：使用真实的表格名 ⭐⭐⭐
        table_name = result.table_name
        if not table_name or table_name.startswith('表格_'):
            # 如果没有获取到真实表格名，使用图片文件名
            table_name = Path(image_path).stem

        # ⭐⭐⭐ 关键修复：确保获取 DataFrame 数据但不直接返回 ⭐⭐⭐
        df_data = None
        if hasattr(result, 'df') and result.df is not None:
            df_data = result.df
            print(f"✅ 普通表格获取到 DataFrame 数据，形状: {df_data.shape}")
        else:
            print("⚠️ 普通表格没有获取到 DataFrame 数据，尝试从Excel文件读取")
            # 如果result中没有df，尝试从生成的Excel文件读取
            try:
                if Path(final_output_path).exists():
                    import pandas as pd
                    df_data = pd.read_excel(final_output_path, sheet_name=sheet_name)
                    print(f"✅ 从Excel文件读取到 DataFrame 数据，形状: {df_data.shape}")
                else:
                    print("❌ Excel文件不存在，无法读取数据")
            except Exception as e:
                print(f"❌ 从Excel文件读取数据失败: {e}")

        # ⭐⭐⭐ 统一返回格式 ⭐⭐⭐
        if result.status == "success" and Path(final_output_path).exists():
            # 构建前端可访问的URL
            excel_url = convert_to_excel_url(final_output_path)

            # ⭐⭐⭐ 关键修复：不直接返回 DataFrame 对象，而是保存到文件 ⭐⭐⭐
            # 如果有 DataFrame 数据，先保存到 Excel
            if df_data is not None and not df_data.empty:
                try:
                    # 使用 excel_storage_service 保存数据
                    from backend.services.excel_storage_service import ExcelStorageService
                    excel_service = ExcelStorageService()
                    excel_service.save_dataframe(
                        df=df_data,
                        excel_path=final_output_path,
                        sheet_name=sheet_name,
                        map_name=table_name,  # ⭐⭐⭐ 使用真实表格名 ⭐⭐⭐
                        image_data=image_path if image_path and os.path.exists(image_path) else None
                    )
                    print(f"✅ 已保存 DataFrame 数据到 Excel 文件")
                except Exception as save_error:
                    print(f"❌ 保存 DataFrame 数据失败: {save_error}")
                    # 即使保存失败，仍然继续处理，使用现有的Excel文件

            # ⭐⭐⭐ 关键修复：构建完整的返回结果，包含 recognizedData ⭐⭐⭐
            return _build_processing_response(
                image_path=image_path,
                output_path=final_output_path,
                sheet_name=sheet_name,
                excel_url=excel_url,
                result=result,
                df_data=df_data,
                table_type="non_financial",
                folder_name=folder_name,
                from_cache=False
            )
        else:
            # 处理失败的情况
            error_msg = result.error_message or "表格处理失败"
            print(f"❌ 普通表格处理失败: {error_msg}")

            # 检查是否生成了Excel文件但状态不是success
            excel_exists = Path(final_output_path).exists()
            if excel_exists:
                print("⚠️ Excel文件已生成但处理状态不是success，尝试读取现有数据")
                try:
                    # 尝试读取现有的Excel文件
                    import pandas as pd
                    df_data = pd.read_excel(final_output_path, sheet_name=sheet_name)
                    excel_url = convert_to_excel_url(final_output_path)

                    return _build_processing_response(
                        image_path=image_path,
                        output_path=final_output_path,
                        sheet_name=sheet_name,
                        excel_url=excel_url,
                        result=result,
                        df_data=df_data,
                        table_type="non_financial",
                        folder_name=folder_name,
                        from_cache=False
                    )
                except Exception as read_error:
                    print(f"❌ 读取现有Excel文件失败: {read_error}")

            return {
                "success": False,
                "error": error_msg,
                "errorCode": "PROCESS_FAILED"
            }

    except Exception as e:
        print(f"❌ _process_non_financial_table 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "errorCode": "SYSTEM_ERROR"
        }


async def _process_single_non_financial_table(process_data):
    """处理单个普通表格 - 返回扁平化结果"""
    try:
        image_path = process_data['image_path']
        output_path = process_data['output_path']
        sheet_name = process_data['sheet_name']
        bank_name = process_data['bank_name']
        file_name = process_data['file_name']
        table_index = process_data.get('table_index', 0)

        print(f"处理普通表格 #{table_index}: {image_path}")

        # 调用普通表格识别的核心逻辑
        result = await _process_non_financial_table(process_data)


        # ⭐⭐⭐ 关键修复：扁平化结果，避免嵌套结构 ⭐⭐⭐
        if result.get('success') and result.get('data'):
            # 提取内部结果
            inner_data = result['data']
            if inner_data.get('results') and len(inner_data['results']) > 0:
                inner_result = inner_data['results'][0]

                # ⭐⭐⭐ 修改：使用真实的表格名，而不是硬编码格式 ⭐⭐⭐
                table_name = inner_result.get('table_name')
                if not table_name or table_name.startswith('表格_'):
                    # 如果没有获取到真实表格名，使用图片文件名作为表格名
                    table_name = Path(image_path).stem

                # 返回扁平化结果
                return {
                    "success": True,
                    "image_path": image_path,
                    "status": inner_result.get('status', 'success'),
                    "status_text": inner_result.get('status_text', '成功'),
                    "complexity": inner_result.get('complexity', '普通表格'),
                    "table_name": table_name,  # ⭐⭐⭐ 使用真实表格名 ⭐⭐⭐
                    "sheet_name": sheet_name,
                    "error_message": inner_result.get('error_message', ''),
                    "assessment_reason": inner_result.get('assessment_reason', '普通表格模式'),
                    "is_non_financial": inner_result.get('is_non_financial', True),
                    "df": inner_result.get('df'),
                    "excel_url": inner_result.get('excel_url', '')
                }

        # 如果处理失败，返回错误
        return {
            "success": False,
            "error": result.get('error', '处理失败'),
            "errorCode": result.get('errorCode', 'PROCESS_FAILED')
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "errorCode": "SYSTEM_ERROR"
        }


def _check_excel_cache_with_validation(image_url, excel_path, table_name, table_type):
    """增强的缓存检查，验证文件完整性和数据有效性"""
    try:
        excel_path = Path(excel_path)
        if not excel_path.exists():
            return None

        print(f"✅ Excel文件已存在，验证数据完整性: {excel_path}")

        # 验证Excel文件是否可以正常读取
        import pandas as pd
        try:
            # 尝试读取Excel文件
            df = pd.read_excel(excel_path, sheet_name=table_name)

            # 检查数据是否为空
            if df.empty:
                print("⚠️ Excel文件存在但数据为空，需要重新识别")
                return None

            # 检查是否有有效的数据行
            if len(df) == 0:
                print("⚠️ Excel文件存在但没有数据行，需要重新识别")
                return None

            # 构建响应数据
            excel_url = convert_to_excel_url(str(excel_path))

            return _build_cache_response(
                image_path=image_url,
                output_path=str(excel_path),
                sheet_name=table_name,
                excel_url=excel_url,
                df=df,
                table_type=table_type
            )

        except Exception as e:
            print(f"❌ Excel文件损坏或无法读取: {e}")
            # 尝试读取第一个sheet
            try:
                df = pd.read_excel(excel_path, sheet_name=0)
                if df.empty:
                    return None

                excel_url = convert_to_excel_url(str(excel_path))
                actual_sheet_name = pd.ExcelFile(excel_path).sheet_names[0]

                return _build_cache_response(
                    image_path=image_url,
                    output_path=str(excel_path),
                    sheet_name=actual_sheet_name,
                    excel_url=excel_url,
                    df=df,
                    table_type=table_type
                )
            except Exception as e2:
                print(f"❌ 所有读取Excel的尝试都失败: {e2}")
                return None

    except Exception as e:
        print(f"❌ 缓存检查异常: {e}")
        return None


def recognize_table_internal():
    """识别表格并保存到指定路径 - 先检查Excel是否存在"""
    try:
        data = request.get_json()
        print(f"收到识别请求: {data}")

        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        # 验证必要参数
        required_fields = ['imageUrl', 'excelPath']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"缺少必要参数: {', '.join(missing_fields)}"
            }), 400

        image_url = data.get('imageUrl')
        excel_path = data.get('excelPath')
        table_name = data.get('tableName', '识别结果')
        index = data.get('index', 0)

        print(f"识别参数 - imageUrl: {image_url}, excelPath: {excel_path}")

        # 构建完整Excel路径
        excel_full_path = Path(excel_path)
        if not excel_full_path.is_absolute():
            excel_full_path = Path.cwd() / excel_path

        print(f"检查Excel文件是否存在: {excel_full_path}")

        # ⭐⭐⭐ 修改：使用增强的缓存检查 ⭐⭐⭐
        cache_result = _check_excel_cache(
            image_url,
            str(excel_full_path),
            table_name,
            "financial"
        )
        if cache_result:
            print("✅ 从缓存返回现有Excel数据")
            return jsonify(cache_result)

        # 2. 如果Excel不存在，进行LLM识别
        print("🔄 Excel文件不存在或无效，开始LLM识别流程")

        # 图片路径提取逻辑保持不变...
        image_path = image_url

        if image_url.startswith('http://'):
            from urllib.parse import urlparse
            parsed_url = urlparse(image_url)
            image_path = parsed_url.path
            if image_path.startswith('/'):
                image_path = image_path[1:]
            print(f"✅ 从URL提取路径: {image_path}")

        elif image_url.startswith('/'):
            image_path = image_url[1:]
            print(f"✅ 处理绝对路径: {image_path}")

        print(f"处理图片路径: {image_path}")

        # 检查图片文件是否存在
        image_full_path = Path(image_path)
        if not image_full_path.exists():
            static_path = Path("static") / image_path
            if static_path.exists():
                image_full_path = static_path
                print(f"✅ 在static目录找到图片: {static_path}")
            else:
                current_dir_path = Path.cwd() / image_path
                if current_dir_path.exists():
                    image_full_path = current_dir_path
                    print(f"✅ 在当前目录找到图片: {current_dir_path}")
                else:
                    print(f"❌ 图片文件不存在，尝试的路径:")
                    print(f"   - {image_full_path}")
                    print(f"   - {static_path}")
                    print(f"   - {current_dir_path}")
                    return jsonify({
                        "success": False,
                        "error": f"图片文件不存在: {image_path}"
                    }), 404

        print(f"✅ 最终使用的图片路径: {image_full_path}")

        # 确保Excel目录存在
        excel_full_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Excel保存路径: {excel_full_path}")

        # 调用 _process_single_image 异步函数进行LLM识别
        process_data = {
            'image_path': str(image_full_path),
            'output_path': str(excel_full_path),
            'sheet_name': table_name,
            'bank_name': '未知银行',
            'file_name': f"table_{index + 1}"
        }

        # ⭐⭐⭐ 修复异步调用 ⭐⭐⭐
        result = asyncio.run(_process_single_image(process_data))
        print(f"LLM识别结果: {result}")

        if result.get('success'):
            # ⭐⭐⭐ 直接返回统一格式的结果 ⭐⭐⭐
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', '识别失败'),
                "errorCode": result.get('errorCode', 'UNKNOWN_ERROR')
            }), 500

    except Exception as e:
        logger.error(f"表格识别失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"表格识别失败: {str(e)}",
            "errorCode": "SYSTEM_ERROR"
        }), 500


def _build_cache_response(image_path, output_path, sheet_name, excel_url, df, table_type="financial"):
    """构建缓存响应"""
    # 转换DataFrame为前端需要的格式
    headers = list(df.columns) if not df.empty else []
    data_list = []

    if not df.empty:
        for _, row in df.iterrows():
            row_data = {}
            for header in headers:
                cell_value = row[header]
                row_data[header] = str(cell_value) if pd.notna(cell_value) else ""
            data_list.append(row_data)

    is_non_financial = table_type == "non_financial"

    # 返回现有数据 - 包含完整的 recognizedData
    return {
        "success": True,
        "data": {
            "total": 1,
            "success": 1,
            "failed": 0,
            "non_financial": 1 if is_non_financial else 0,
            "results": [
                {
                    "image_path": image_path,
                    "status": "success",
                    "status_text": "从缓存加载",
                    "complexity": "unknown",
                    "table_name": sheet_name,
                    "sheet_name": sheet_name,
                    "error_message": "",
                    "assessment_reason": "从已存在的Excel文件加载",
                    "success": True,
                    "is_non_financial": is_non_financial,
                    "output_file": output_path,
                    "excel_url": excel_url
                }
            ],
            "output_file": output_path,
            "excel_url": excel_url,
            "table_type": table_type,
            "processing_completed": True,
            "message": "从已存在的Excel文件加载数据",
            "excel_saved": True,
            "from_cache": True
        },
        # ⭐⭐⭐ 关键修复：添加 recognizedData 字段 ⭐⭐⭐
        "recognizedData": {
            "headers": headers,
            "data": data_list,
            "tableName": sheet_name,
            "excelPath": output_path,
            "fromCache": True
        },
        "task_id": f"cached_{table_type}_{int(time.time())}",
        "processing_completed": True,
        "from_cache": True
    }


def _build_processing_response(image_path, output_path, sheet_name, excel_url, result, df_data,
                               table_type="financial", folder_name="", from_cache=False):
    """构建处理响应"""
    is_non_financial = table_type == "non_financial"

    # ⭐⭐⭐ 修改：使用真实的表格名 ⭐⭐⭐
    table_name = getattr(result, 'table_name', '')
    if not table_name or table_name.startswith('表格_'):
        # 如果没有获取到真实表格名，使用图片文件名
        table_name = Path(image_path).stem

    # 构建 recognizedData
    headers = []
    data_list = []
    if df_data is not None and not df_data.empty:
        headers = list(df_data.columns)
        for _, row in df_data.iterrows():
            row_data = {}
            for header in headers:
                cell_value = row[header]
                row_data[header] = str(cell_value) if pd.notna(cell_value) else ""
            data_list.append(row_data)

    # 构建响应
    response = {
        "success": True,
        "data": {
            "total": 1,
            "success": 1,
            "failed": 0,
            "non_financial": 1 if is_non_financial else 0,
            "results": [
                {
                    "image_path": image_path,
                    "status": result.status,
                    "status_text": "成功" if result.status == "success" else "非金融表格",
                    "complexity": getattr(result, 'complexity', 'unknown'),
                    "table_name": table_name,  # ⭐⭐⭐ 使用真实表格名 ⭐⭐⭐
                    "sheet_name": sheet_name,
                    "error_message": getattr(result, 'error_message', ''),
                    "assessment_reason": getattr(result, 'assessment_reason', ''),
                    "success": True,
                    "is_non_financial": is_non_financial,
                    "output_file": output_path,
                    "excel_url": excel_url
                }
            ],
            "output_file": output_path,
            "excel_url": excel_url,
            "table_type": table_type,
            "processing_completed": True,
            "message": "普通表格处理完成" if is_non_financial else "表格处理完成",
            "excel_saved": True,
            "from_cache": from_cache
        },
        # ⭐⭐⭐ 关键修复：添加 recognizedData 字段 ⭐⭐⭐
        "recognizedData": {
            "headers": headers,
            "data": data_list,
            "tableName": table_name,  # ⭐⭐⭐ 使用真实表格名 ⭐⭐⭐
            "excelPath": output_path,
            "fromCache": from_cache
        },
        "task_id": f"{table_type}_{int(time.time())}",
        "processing_completed": True,
        "from_cache": from_cache
    }

    # 保持兼容性
    response["excel_url"] = excel_url
    response["from_cache"] = from_cache
    if folder_name:
        response["tableName"] = f"{table_name} - {folder_name}"  # ⭐⭐⭐ 使用真实表格名 ⭐⭐⭐

    return response

