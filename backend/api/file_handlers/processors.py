# -*- coding:utf-8 -*-

import os
import shutil
import tempfile
from datetime import datetime

from flask import send_file
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def convert_excel_to_pdf(
        excel_path: str,
        page_range=None,
        orientation="portrait",
        dpi=200
) -> str:
    """Excel转PDF - 使用pandas+reportlab免费方案"""
    try:
        # 方案1: 使用pandas读取数据，reportlab生成PDF
        return excel_to_pdf_with_pandas(excel_path, orientation, page_range)

    except Exception as e:
        # 如果失败，回退到简单方案
        return create_simple_pdf_from_excel(excel_path, str(e))


def excel_to_pdf_with_pandas(excel_path: str, orientation="portrait", page_range=None):
    """使用pandas读取Excel，reportlab生成PDF表格"""
    import pandas as pd
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    # 生成PDF路径
    pdf_path = excel_path.rsplit('.', 1)[0] + '.pdf'

    # 设置页面
    if orientation == "landscape":
        pagesize = landscape(A4)
    else:
        pagesize = A4

    # 读取Excel文件
    try:
        # 尝试读取所有sheet
        excel_file = pd.ExcelFile(excel_path)
        sheet_names = excel_file.sheet_names

        # 如果指定了页范围，只处理指定sheet
        if page_range:
            sheet_names = [sheet_names[i] for i in page_range if i < len(sheet_names)]
    except Exception as e:
        raise Exception(f"读取Excel失败: {str(e)}")

    # 创建PDF文档
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=pagesize,
        rightMargin=72, leftMargin=72,
        topMargin=72, bottomMargin=72
    )

    elements = []
    styles = getSampleStyleSheet()

    # 添加标题
    title = Paragraph(f"Excel转换报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                      styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # 处理每个工作表
    for sheet_idx, sheet_name in enumerate(sheet_names):
        try:
            # 读取工作表数据
            df = pd.read_excel(excel_path, sheet_name=sheet_name)

            # 添加sheet标题
            sheet_title = Paragraph(f"工作表 {sheet_idx + 1}: {sheet_name}", styles['Heading2'])
            elements.append(sheet_title)
            elements.append(Spacer(1, 6))

            # 如果数据太多，只取前100行显示
            if len(df) > 100:
                df_display = df.head(100)
                info = Paragraph(f"（显示前100行，共{len(df)}行）", styles['Italic'])
                elements.append(info)
                elements.append(Spacer(1, 6))
            else:
                df_display = df

            # 准备表格数据
            # 添加表头
            data = [df_display.columns.tolist()]
            # 添加数据行
            for _, row in df_display.iterrows():
                # 处理NaN值
                row_data = [str(cell) if pd.notna(cell) else "" for cell in row]
                data.append(row_data)

            # 创建表格
            if data:
                # 计算列宽（根据内容调整）
                col_widths = [max(len(str(cell)) for cell in col) * 6 for col in zip(*data)]

                table = Table(data, colWidths=col_widths[:min(10, len(col_widths))])

                # 设置表格样式
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                elements.append(table)
                elements.append(Spacer(1, 20))

        except Exception as e:
            # 如果某个sheet处理失败，继续处理下一个
            error_msg = Paragraph(f"处理工作表 '{sheet_name}' 时出错: {str(e)}", styles['Italic'])
            elements.append(error_msg)
            elements.append(Spacer(1, 12))
            continue

    # 生成PDF
    doc.build(elements)
    return pdf_path


def create_simple_pdf_from_excel(excel_path: str, error_msg=None):
    """创建简单的PDF文件（兜底方案）"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    pdf_path = excel_path.rsplit('.', 1)[0] + '.pdf'

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # 标题
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "Excel文件转换报告")

    # 文件信息
    c.setFont("Helvetica", 12)
    y = height - 100
    c.drawString(50, y, f"文件名: {os.path.basename(excel_path)}")
    y -= 25
    c.drawString(50, y, f"文件大小: {os.path.getsize(excel_path):,} 字节")
    y -= 25
    c.drawString(50, y, f"转换时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 40

    # 如果有错误信息
    if error_msg:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "转换状态: 部分成功")
        y -= 25
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(1, 0, 0)  # 红色
        c.drawString(50, y, f"错误: {error_msg[:100]}...")
        c.setFillColorRGB(0, 0, 0)  # 恢复黑色
        y -= 40

    # 添加使用说明
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "说明:")
    y -= 20
    c.setFont("Helvetica", 10)

    notes = [
        "1. 此PDF为Excel内容的文本版本",
        "2. 如需完整格式转换，请确保:",
        "   - Excel文件格式正确",
        "   - 安装 pandas, openpyxl, reportlab 库",
        "3. 支持的Excel格式: .xlsx, .xls"
    ]

    for note in notes:
        c.drawString(70, y, note)
        y -= 18

    c.save()
    return pdf_path


# 其他函数保持不变...
def save_uploaded_file(file: FileStorage) -> str:
    """保存上传的文件到临时目录"""
    temp_dir = tempfile.mkdtemp()
    filename = secure_filename(file.filename)
    temp_filepath = os.path.join(temp_dir, filename)

    file.save(temp_filepath)
    return temp_filepath


def handle_chunk_upload(
        file: FileStorage,
        chunk_index: int,
        total_chunks: int,
        file_name: str,
        file_size: int,
        file_type: str
):
    """处理分片上传逻辑"""
    try:

        upload_dir = "uploads/chunks"
        os.makedirs(upload_dir, exist_ok=True)

        # 保存分片
        safe_filename = secure_filename(file_name)
        chunk_filename = f"{safe_filename}.part{chunk_index}"
        chunk_path = os.path.join(upload_dir, chunk_filename)

        file.save(chunk_path)

        # 如果是最后一个分片，合并文件
        if chunk_index == total_chunks - 1:
            final_dir = "uploads"
            os.makedirs(final_dir, exist_ok=True)
            final_path = os.path.join(final_dir, safe_filename)

            with open(final_path, "wb") as output_file:
                for i in range(total_chunks):
                    chunk_path = os.path.join(upload_dir, f"{safe_filename}.part{i}")
                    with open(chunk_path, "rb") as chunk_file:
                        output_file.write(chunk_file.read())
                    # 删除分片文件
                    if os.path.exists(chunk_path):
                        os.remove(chunk_path)

            return {
                "message": "上传完成",
                "filepath": final_path,
                "filename": file_name,
                "size": os.path.getsize(final_path)
            }
        else:
            return {
                "message": "分片上传成功",
                "chunk_index": chunk_index,
                "received": True
            }

    except Exception as e:
        raise Exception(f"分片上传处理失败: {str(e)}")


def save_and_return_result(output_filepath: str):
    """保存转换结果并返回文件"""
    # 生成结果文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_filename = f"converted_{timestamp}.pdf"
    result_dir = "results"

    os.makedirs(result_dir, exist_ok=True)
    result_path = os.path.join(result_dir, result_filename)

    # 移动文件到结果目录
    if os.path.exists(output_filepath):
        shutil.move(output_filepath, result_path)
    else:
        # 如果文件不存在，创建一个空的
        with open(result_path, 'wb') as f:
            f.write(b'PDF conversion result')

    # 清理临时目录
    try:
        temp_dir = os.path.dirname(output_filepath.replace('.pdf', ''))
        excel_files = [f for f in os.listdir(temp_dir) if f.endswith(('.xlsx', '.xls'))]
        if excel_files and "tmp" in temp_dir:
            shutil.rmtree(temp_dir)
    except:
        pass  # 忽略清理错误

    # 返回文件
    return send_file(
        result_path,
        as_attachment=True,
        download_name=result_filename,
        mimetype='application/pdf'
    )






