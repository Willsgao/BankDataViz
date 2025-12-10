import pandas as pd
import os
from pathlib import Path
import re


def merge_excel_sheets_by_type(folder_path, output_folder="output"):
    """
    合并指定文件夹下的Excel文件

    参数:
        folder_path: 包含Excel文件的文件夹路径
        output_folder: 输出文件夹路径
    """
    # 创建输出文件夹
    output_dir = Path(output_folder)
    output_dir.mkdir(exist_ok=True)

    # 定义输出文件路径
    final_output = output_dir / "merged_final.xlsx"
    final_data_output = output_dir / "merged_final_final_data.xlsx"

    # 用字典存储不同类型文件的内容
    final_files = {}  # 存储 _final.xlsx 文件
    final_data_files = {}  # 存储 _final_final_data.xlsx 文件

    # 正则表达式匹配文件名中的页码
    pattern = r'_(\d{3})_final'

    # 遍历文件夹中的所有Excel文件
    for file_path in Path(folder_path).glob("*.xlsx"):
        file_name = file_path.name

        # 检查文件类型并提取页码
        if "_final_final_data.xlsx" in file_name:
            # 提取中间的三位数字页码（如002）
            match = re.search(pattern, file_name)
            if match:
                page_num = int(match.group(1))  # 转换为整数，002 → 2
                final_data_files[page_num] = file_path
            else:
                print(f"警告: 无法从文件名 {file_name} 中提取页码")

        elif "_final.xlsx" in file_name and "_final_final_data.xlsx" not in file_name:
            # 提取中间的三位数字页码
            match = re.search(pattern, file_name)
            if match:
                page_num = int(match.group(1))  # 转换为整数
                final_files[page_num] = file_path
            else:
                print(f"警告: 无法从文件名 {file_name} 中提取页码")

    # 打印找到的文件信息
    print(f"找到 {len(final_files)} 个 _final.xlsx 文件:")
    for page in sorted(final_files.keys()):
        print(f"  页码 {page:03d}: {final_files[page].name}")

    print(f"\n找到 {len(final_data_files)} 个 _final_final_data.xlsx 文件:")
    for page in sorted(final_data_files.keys()):
        print(f"  页码 {page:03d}: {final_data_files[page].name}")

    # 合并 _final.xlsx 文件
    if final_files:
        with pd.ExcelWriter(final_output, engine='openpyxl') as writer:
            for page_num in sorted(final_files.keys()):
                file_path = final_files[page_num]
                sheet_name = f"P{page_num}_sheet"
                try:
                    # 读取Excel文件
                    df = pd.read_excel(file_path)
                    print(f"正在处理: {file_path.name} → sheet: {sheet_name} ({len(df)}行, {len(df.columns)}列)")

                    # 写入到合并的Excel中
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                except Exception as e:
                    print(f"错误: 处理文件 {file_path.name} 时出错: {e}")

        print(f"\n✅ 已保存 _final.xlsx 文件到: {final_output}")

    # 合并 _final_final_data.xlsx 文件
    if final_data_files:
        with pd.ExcelWriter(final_data_output, engine='openpyxl') as writer:
            for page_num in sorted(final_data_files.keys()):
                file_path = final_data_files[page_num]
                sheet_name = f"P{page_num}_sheet"
                try:
                    # 读取Excel文件
                    df = pd.read_excel(file_path)
                    print(f"正在处理: {file_path.name} → sheet: {sheet_name} ({len(df)}行, {len(df.columns)}列)")

                    # 写入到合并的Excel中
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                except Exception as e:
                    print(f"错误: 处理文件 {file_path.name} 时出错: {e}")

        print(f"✅ 已保存 _final_final_data.xlsx 文件到: {final_data_output}")

    # 返回结果统计
    return {
        "final_files_count": len(final_files),
        "final_data_files_count": len(final_data_files),
        "final_output": str(final_output),
        "final_data_output": str(final_data_output)
    }


# 使用示例
if __name__ == "__main__":
    # 设置包含Excel文件的文件夹路径
    folder_path = r"F:\wills\codes\DocuVista\test_codes\table_analyzer_codes\outputs"  # 修改为你的文件夹路径

    # 检查文件夹是否存在
    if not Path(folder_path).exists():
        print(f"错误: 文件夹 '{folder_path}' 不存在！")
        print("请创建文件夹并放入Excel文件，或修改folder_path变量为正确的路径")
    else:
        # 执行合并
        result = merge_excel_sheets_by_type(folder_path, output_folder="output")

        # 打印总结
        print("\n" + "=" * 50)
        print("合并完成！")
        print("=" * 50)
        print(f"1. 合并了 {result['final_files_count']} 个 _final.xlsx 文件到:")
        print(f"   {result['final_output']}")
        print(f"\n2. 合并了 {result['final_data_files_count']} 个 _final_final_data.xlsx 文件到:")
        print(f"   {result['final_data_output']}")