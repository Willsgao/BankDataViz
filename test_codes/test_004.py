# make_score_pdf_cn_v2.py
import random, os, urllib.request
from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ===== 0. 字体路径 & 下载 =====
FONT_LOCAL = "SourceHanSansSC-Regular.ttf"
FONT_URL = "https://fastly.jsdelivr.net/npm/nerd-fonts@3.0.0/fonts/SourceHanSansSC/SourceHanSansSC-Regular.ttf"

if not os.path.exists(FONT_LOCAL):
    print("⏬ 正在下载中文字体...")
    try:
        urllib.request.urlretrieve(FONT_URL, FONT_LOCAL)
        print("✅ 字体下载完成")
    except Exception as e:
        print("⚠️ 下载失败，请手动把字体文件放到:", os.path.abspath(FONT_LOCAL))
        exit(1)

pdfmetrics.registerFont(TTFont("SourceHanSans", FONT_LOCAL))


# ===== 1. 生成"读后续写"25 分制数据 =====
def build_continuation_writing_data(n=45):
    """
    模拟读后续写得分，总分 25 分
    维度及满分：
        内容相关度 8 分
        语言表达   7 分
        文章结构   6 分
        卷面书写   2 分
        字数维度   2 分
    返回带表头的二维列表，可直接喂给原 make_pdf()
    """
    fake = Faker('zh_CN')

    # 各维度按"正态偏优"方式生成，避免满分也避免过低
    def clamp(lo, hi): return lambda v: max(lo, min(hi, int(v)))

    content = [clamp(4, 8)(random.normalvariate(6.5, 1.2)) for _ in range(n)]  # 内容相关度
    language = [clamp(4, 7)(random.normalvariate(5.5, 1.0)) for _ in range(n)]  # 语言表达
    structure = [clamp(3, 6)(random.normalvariate(4.8, 1.0)) for _ in range(n)]  # 文章结构
    handwriting = [clamp(0, 2)(random.normalvariate(1.6, 0.5)) for _ in range(n)]  # 卷面书写
    word_cnt = [clamp(0, 2)(random.normalvariate(1.7, 0.4)) for _ in range(n)]  # 字数维度

    total = [c + l + s + h + w for c, l, s, h, w in
             zip(content, language, structure, handwriting, word_cnt)]

    # 等级
    level = ["A" if t >= 21 else "B" if t >= 17 else "C" for t in total]

    # 整体评语库
    comments = [
                   "情节合理，语言流畅，书写工整。",
                   "内容贴合原文，句式丰富，卷面清爽。",
                   "故事完整，结构紧凑，表达有亮点。",
                   "续写与原文衔接自然，词汇灵活。",
                   "细节生动，结尾有力，略有小错。",
                   "主题明确，逻辑清晰，书写再工整些更佳。",
                   "情节略显突兀，语言可读性较好。",
                   "内容基本相关，结构需更紧凑。",
                   "句式较单一，字数刚好，书写可提高。",
                   "偏离原文少许，但表达尚清楚。"
               ] * 10
    random.shuffle(comments)

    # 组装成字典
    data = {
        "序号": list(range(1, n + 1)),
        "学生姓名": [fake.name() for _ in range(n)],
        "内容相关度": content,
        "语言表达": language,
        "文章结构": structure,
        "卷面书写": handwriting,
        "字数维度": word_cnt,
        "总分": total,
        "等级": level,
        "教师评语": comments[:n]
    }

    # 转成与原脚本兼容的"表头 + 数据行"格式
    return [data.keys()] + [list(row) for row in zip(*data.values())]


# ===== 2. 智能分页计算（纵向布局优化） =====
def calculate_optimal_rows_per_page(data_rows, min_rows=20, max_rows=35):
    """
    根据数据行数智能计算每页最佳行数（纵向布局）
    """
    total_rows = len(data_rows)

    if total_rows <= max_rows:
        return total_rows  # 数据少，一页显示完

    # 尝试找到最合适的分页方式
    for rows in range(max_rows, min_rows - 1, -1):
        pages = (total_rows + rows - 1) // rows  # 向上取整
        remainder = total_rows % rows

        # 如果最后一页的行数不太少（至少min_rows），就采用这个分页
        if remainder == 0 or remainder >= min_rows:
            return rows

    # 如果找不到理想分页，使用默认值
    return 28


# ===== 3. 表格数据处理函数 =====
def wrap_table_data(table_data):
    """
    将表格数据中的长文本转换为支持自动换行的Paragraph对象
    特别是评语列（第9列，索引8）
    """
    wrapped_data = []

    for row_idx, row in enumerate(table_data):
        wrapped_row = []
        for col_idx, cell in enumerate(row):
            # 表头行保持原样
            if row_idx == 0:
                wrapped_row.append(str(cell))
            else:
                # 评语列（第9列）使用Paragraph实现自动换行
                if col_idx == 9:  # 评语列索引
                    # 创建支持换行的Paragraph - 移除wordWrap参数
                    style = ParagraphStyle(
                        'cell_style',
                        fontName="SourceHanSans",
                        fontSize=8,
                        leading=9,  # 行距
                        alignment=0  # 左对齐
                        # wordWrap参数已移除，Paragraph默认支持自动换行
                    )
                    wrapped_row.append(Paragraph(str(cell), style))
                else:
                    # 其他列保持原样
                    wrapped_row.append(str(cell))
        wrapped_data.append(wrapped_row)

    return wrapped_data


# ===== 4. 生成多个班级的单一PDF（纵向布局） =====
def make_all_classes_single_pdf(class_num=5, class_names=None, students_per_class=None, filename="所有班级英语读后续写评分表.pdf"):
    """
    生成包含所有班级的单一PDF文件（纵向布局）

    Args:
        class_num: 班级数量
        class_names: 班级名称列表
        students_per_class: 每个班级的学生人数列表
        filename: 输出文件名
    """
    if class_names is None:
        class_names = [f"高二({i})班" for i in range(1, class_num+1)]

    if students_per_class is None:
        # 每个班级随机45-50人
        students_per_class = [random.randint(45, 50) for _ in class_names]

    print(f"📊 开始生成 {len(class_names)} 个班级的评分表到单一PDF...")

    # 准备所有数据
    all_classes_data = []
    for i, class_name in enumerate(class_names):
        n_students = students_per_class[i]
        print(f"🎯 正在生成 {class_name} 的数据，共 {n_students} 人...")

        # 生成该班级的数据
        class_data = build_continuation_writing_data(n_students)
        all_classes_data.append((class_name, class_data))

    # 生成单一PDF
    make_single_pdf_with_all_classes(all_classes_data, filename)

    print(f"✅ 所有班级的PDF文件已生成：{os.path.abspath(filename)}")


def make_single_pdf_with_all_classes(all_classes_data, filename):
    """
    将多个班级的数据生成到同一个PDF中（纵向布局）

    Args:
        all_classes_data: 列表，每个元素为 (班级名称, 表格数据)
        filename: 输出文件名
    """
    # 纵向 A4
    pagesize = A4  # 使用默认纵向A4
    doc = SimpleDocTemplate(filename,
                            pagesize=pagesize,
                            topMargin=1.5 * cm,
                            bottomMargin=1.5 * cm,
                            leftMargin=1 * cm,
                            rightMargin=1 * cm)

    # 定义样式
    main_title_style = ParagraphStyle('main_title',
                                      fontName="SourceHanSans",
                                      fontSize=16,
                                      alignment=1,  # 居中
                                      spaceAfter=12,
                                      textColor=colors.darkblue)

    class_title_style = ParagraphStyle('class_title',
                                       fontName="SourceHanSans",
                                       fontSize=14,
                                       alignment=1,  # 居中
                                       spaceAfter=8,
                                       textColor=colors.darkred)

    elements = []

    # 主标题
    main_title = Paragraph("2025 年春季高二英语读后续写评分汇总表", main_title_style)
    elements.append(main_title)
    elements.append(Spacer(1, 0.8 * cm))

    # 表格列宽（纵向布局需要调整列宽）
    col_widths = [
        0.8 * cm,  # 序号
        2.2 * cm,  # 学生姓名
        1.5 * cm,  # 内容相关度
        1.5 * cm,  # 语言表达
        1.5 * cm,  # 文章结构
        1.2 * cm,  # 卷面书写
        1.2 * cm,  # 字数维度
        1.2 * cm,  # 总分
        0.8 * cm,  # 等级
        4.5 * cm  # 教师评语
    ]

    # 处理每个班级的数据
    for class_idx, (class_name, table_data) in enumerate(all_classes_data):
        # 如果不是第一个班级，添加分页符
        if class_idx > 0:
            elements.append(PageBreak())
            # 新页面的主标题
            elements.append(main_title)
            elements.append(Spacer(1, 0.8 * cm))

        # 班级标题
        class_title = Paragraph(f"{class_name} 评分表", class_title_style)
        elements.append(class_title)
        elements.append(Spacer(1, 0.3 * cm))

        # 表头行 & 数据行拆分
        header_row = table_data[0]
        data_rows = table_data[1:]

        # 智能计算每页最佳行数（纵向布局可以显示更多行）
        optimal_rows = calculate_optimal_rows_per_page(data_rows)
        print(f"   {class_name} 使用每页 {optimal_rows} 行")

        # 分页处理
        total_pages = (len(data_rows) + optimal_rows - 1) // optimal_rows

        for page_num in range(total_pages):
            start_idx = page_num * optimal_rows
            end_idx = start_idx + optimal_rows
            page_data = data_rows[start_idx:end_idx]

            # 当前页的数据（包含表头）
            current_page_data = [header_row] + page_data

            # 对数据进行自动换行处理
            wrapped_data = wrap_table_data(current_page_data)

            # 创建表格
            t = Table(wrapped_data, colWidths=col_widths, repeatRows=1)  # repeatRows=1 表示表头每页重复

            # 设置表格样式
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, -1), "SourceHanSans"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),  # 表头字体稍小
                ("FONTSIZE", (0, 1), (-1, -1), 8),  # 数据字体更小
                ("GRID", (0, 0), (-1, -1), 0.3, colors.black),  # 细线
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.lightgrey]),
            ]))
            elements.append(t)

            # 如果不是最后一页，添加分页符
            if page_num < total_pages - 1:
                elements.append(PageBreak())
                # 新页面显示班级标题和表头
                elements.append(main_title)
                elements.append(Spacer(1, 0.8 * cm))
                elements.append(class_title)
                elements.append(Spacer(1, 0.3 * cm))

    # 页码函数
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFont("SourceHanSans", 9)
        canvas.drawCentredString(A4[0] / 2, 1 * cm, f"第 {page_num} 页")  # 纵向A4宽度是A4[0]
        canvas.restoreState()

    # 构建PDF
    doc.build(elements,
              onFirstPage=add_page_number,
              onLaterPages=add_page_number)


# ===== 5. 生成单个班级PDF（纵向布局） =====
def make_single_class_pdf(table_data, class_name, filename, rows_per_page=28):
    """
    生成单个班级的PDF文件（纵向布局）
    """
    pagesize = A4  # 纵向A4
    doc = SimpleDocTemplate(filename,
                            pagesize=pagesize,
                            topMargin=1.5 * cm,
                            bottomMargin=1.5 * cm,
                            leftMargin=1 * cm,
                            rightMargin=1 * cm)

    # 定义样式
    title_style = ParagraphStyle('title',
                                 fontName="SourceHanSans",
                                 fontSize=14,
                                 alignment=1,
                                 spaceAfter=12)

    elements = []

    # 标题
    title_text = f"2025 年春季{class_name}英语读后续写评分表"
    title_para = Paragraph(title_text, title_style)
    elements.append(title_para)
    elements.append(Spacer(1, 0.5 * cm))

    # 表头行 & 数据行拆分
    header_row = table_data[0]
    data_rows = table_data[1:]

    # 纵向布局的列宽
    col_widths = [
        0.8 * cm,  # 序号
        1.9 * cm,  # 学生姓名
        1.8 * cm,  # 内容相关度
        1.5 * cm,  # 语言表达
        1.5 * cm,  # 文章结构
        1.5 * cm,  # 卷面书写
        1.5 * cm,  # 字数维度
        1.2 * cm,  # 总分
        0.8 * cm,  # 等级
        4.5 * cm  # 教师评语
    ]

    # 分页处理
    for start in range(0, len(data_rows), rows_per_page):
        chunk = [header_row] + data_rows[start:start + rows_per_page]

        # 对数据进行自动换行处理
        wrapped_data = wrap_table_data(chunk)

        t = Table(wrapped_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, -1), "SourceHanSans"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.lightgrey]),
        ]))
        elements.append(t)

        # 不是最后一页就手动分页
        if start + rows_per_page < len(data_rows):
            elements.append(PageBreak())
            # 每页顶部再写一次标题
            elements.append(title_para)
            elements.append(Spacer(1, 0.5 * cm))

    # 页码函数
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFont("SourceHanSans", 9)
        canvas.drawCentredString(A4[0] / 2, 1 * cm, f"第 {page_num} 页")
        canvas.restoreState()

    # 构建PDF
    doc.build(elements,
              onFirstPage=add_page_number,
              onLaterPages=add_page_number)
    print(f"✅ {class_name} PDF 已生成：{os.path.abspath(filename)}")


# ===== 6. 保留原函数供兼容 =====
def make_continuation_pdf_with_header(table_data, class_name="高二班级",
                                      filename="英语读后续写评分表.pdf",
                                      rows_per_page=28):
    """原函数的兼容版本"""
    make_single_class_pdf(table_data, class_name, filename, rows_per_page)


# ----------------- 主程序入口 -----------------
if __name__ == "__main__":
    # 方法1: 生成所有班级到单一PDF（默认3个班，每班45-50人）
    make_all_classes_single_pdf(3, filename="英语读后续写评分表_多班级_7.pdf")

    # 方法2: 自定义班级名称和学生人数
    # custom_classes = ['高二(1)班', '高二(2)班', '高二(3)班', '实验班', '重点班']
    # custom_students = [48, 46, 49, 45, 47]  # 每个班级的具体人数
    # make_all_classes_single_pdf(class_names=custom_classes,
    #                           students_per_class=custom_students,
    #                           filename="自定义班级评分表.pdf")

    # 方法3: 只生成单个班级（兼容原代码）
    # data = build_continuation_writing_data(47)
    # make_single_class_pdf(data, "高二(1)班", "单班评分表.pdf")