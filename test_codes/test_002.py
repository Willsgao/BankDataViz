# make_score_pdf_cn_v2.py
import random, os, urllib.request
from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
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

# ===== 1. 生成数据 =====
def build_data(n=80):
    fake = Faker('zh_CN')
    data = {"序号": list(range(1, n+1)),
            "学生姓名": [fake.name() for _ in range(n)],
            "语法得分": [random.randint(18, 27) for _ in range(n)],
            "内容得分": [random.randint(19, 26) for _ in range(n)],
            "逻辑得分": [random.randint(18, 26) for _ in range(n)]}
    data["总分"] = [g+c+l for g,c,l in zip(data["语法得分"], data["内容得分"], data["逻辑得分"])]
    data["等级"] = ["A" if s>=73 else "B" if s>=65 else "C" for s in data["总分"]]
    comments = ["结构严谨，用词精准", "论证清晰，结尾有力", "句式可再丰富",
                "主谓一致需注意", "数据引用恰当"] * 20
    data["教师评语"] = comments[:n]
    return [data.keys()] + [list(row) for row in zip(*data.values())]


# ===== 2. 生成 PDF =====
def make_pdf(table_data, filename="英语作文评分表4.pdf"):
    pagesize = (A4[1], A4[0])  # 横向
    doc = SimpleDocTemplate(filename, pagesize=pagesize,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=1 * cm, rightMargin=1 * cm)
    cn_style = ParagraphStyle('cn', fontName="SourceHanSans", fontSize=12, alignment=1)
    page_num_style = ParagraphStyle('page_num', fontName="SourceHanSans", fontSize=10, alignment=1)

    elements = []

    # 只在第一页添加标题
    elements.append(Paragraph("2025 年春季高二英语作文评分表", cn_style))
    elements.append(Spacer(1, 0.5 * cm))

    # 添加表格（让ReportLab自动分页）
    t = Table(table_data, colWidths=[1 * cm, 3 * cm, 2 * cm, 2 * cm, 2 * cm, 2 * cm, 1.5 * cm, 5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "SourceHanSans"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    elements.append(t)

    # 在每页底部添加页码（使用onFirstPage和onLaterPages）
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFont("SourceHanSans", 10)
        canvas.drawCentredString(A4[1] / 2, 1 * cm, f"第 {page_num} 页")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"✅ 中文无乱码 PDF 已生成：{os.path.abspath(filename)}")


# ===== 1. 生成“读后续写”25 分制数据 =====
def build_continuation_writing_data(n=80):
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

    # 各维度按“正态偏优”方式生成，避免满分也避免过低
    def clamp(lo, hi): return lambda v: max(lo, min(hi, int(v)))
    content   = [clamp(4, 8)(random.normalvariate(6.5, 1.2)) for _ in range(n)]   # 内容相关度
    language  = [clamp(4, 7)(random.normalvariate(5.5, 1.0)) for _ in range(n)]   # 语言表达
    structure = [clamp(3, 6)(random.normalvariate(4.8, 1.0)) for _ in range(n)]   # 文章结构
    handwriting=[clamp(0, 2)(random.normalvariate(1.6, 0.5)) for _ in range(n)]  # 卷面书写
    word_cnt  = [clamp(0, 2)(random.normalvariate(1.7, 0.4)) for _ in range(n)]   # 字数维度

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

    # 转成与原脚本兼容的“表头 + 数据行”格式
    return [data.keys()] + [list(row) for row in zip(*data.values())]


# ===== 2. 生成“读后续写”25 分制 PDF =====
def make_continuation_pdf(table_data,
                          filename="英语读后续写评分表5.pdf"):
    """
    table_data：由 build_continuation_writing_data() 生成的 9 列表格（含表头）
    列顺序：序号 / 姓名 / 内容相关度(8) / 语言表达(7) / 文章结构(6) / 卷面书写(2) / 字数维度(2) / 总分 / 等级 / 评语
    """
    # 横向 A4
    pagesize = (A4[1], A4[0])
    doc = SimpleDocTemplate(filename,
                            pagesize=pagesize,
                            topMargin=1.5*cm,
                            bottomMargin=1.5*cm,
                            leftMargin=1*cm,
                            rightMargin=1*cm)

    # 复用原字体
    cn_style = ParagraphStyle('cn',
                              fontName="SourceHanSans",
                              fontSize=12,
                              alignment=1)          # 居中
    page_num_style = ParagraphStyle('page_num',
                                    fontName="SourceHanSans",
                                    fontSize=10,
                                    alignment=1)

    elements = []

    # 标题
    elements.append(Paragraph("2025 年春季高二英语读后续写评分表", cn_style))
    elements.append(Spacer(1, 0.5*cm))

    # 列宽（单位 cm）—— 总宽 29.7 cm，横向 A4 可用宽度约 27.7 cm
    col_widths = [1*cm,          # 序号
                  2.8*cm,        # 学生姓名
                  2*cm,          # 内容相关度
                  2*cm,          # 语言表达
                  2*cm,          # 文章结构
                  1.5*cm,        # 卷面书写
                  1.5*cm,        # 字数维度
                  1.8*cm,        # 总分
                  1.2*cm,        # 等级
                  6*cm]          # 教师评语

    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME",   (0, 0), (-1, -1), "SourceHanSans"),
        ("FONTSIZE",   (0, 0), (-1, 0), 10),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.lightgrey]),
    ]))
    elements.append(t)

    # 页脚页码
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFont("SourceHanSans", 10)
        canvas.drawCentredString(A4[1]/2, 1*cm, f"第 {page_num} 页")
        canvas.restoreState()

    doc.build(elements,
              onFirstPage=add_page_number,
              onLaterPages=add_page_number)
    print(f"✅ 读后续写 25 分制 PDF 已生成：{os.path.abspath(filename)}")


# ===== 3. 每页重复表头的 25 分制 PDF =====
def make_continuation_pdf_with_header(table_data,
                                      filename="英语读后续写评分表.pdf",
                                      rows_per_page=25):
    """
    table_data：含表头的 9 列二维列表
    rows_per_page：每页数据行数（不含表头）
    """
    from reportlab.platypus import PageBreak

    pagesize = (A4[1], A4[0])
    doc = SimpleDocTemplate(filename,
                            pagesize=pagesize,
                            topMargin=1.5*cm,
                            bottomMargin=1.5*cm,
                            leftMargin=1*cm,
                            rightMargin=1*cm)

    cn_style = ParagraphStyle('cn',
                              fontName="SourceHanSans",
                              fontSize=12,
                              alignment=1)
    page_num_style = ParagraphStyle('page_num',
                                    fontName="SourceHanSans",
                                    fontSize=10,
                                    alignment=1)

    elements = []
    header_txt = "2025 年春季高二英语读后续写评分表"
    header_para = Paragraph(header_txt, cn_style)
    elements.append(header_para)
    elements.append(Spacer(1, 0.5*cm))

    # 表头行 & 数据行拆分
    header_row = table_data[0]
    data_rows  = table_data[1:]

    col_widths = [1*cm, 2.8*cm,
                  2*cm, 2*cm, 2*cm,
                  1.5*cm, 1.5*cm,
                  1.8*cm, 1.2*cm,
                  6*cm]

    # 按 rows_per_page 切片
    for start in range(0, len(data_rows), rows_per_page):
        chunk = [header_row] + data_rows[start:start+rows_per_page]
        t = Table(chunk, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME",   (0, 0), (-1, -1), "SourceHanSans"),
            ("FONTSIZE",   (0, 0), (-1, 0), 10),
            ("FONTSIZE",   (0, 1), (-1, -1), 9),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.black),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.lightgrey]),
        ]))
        elements.append(t)
        # 不是最后一页就手动分页
        if start + rows_per_page < len(data_rows):
            elements.append(PageBreak())
            # 每页顶部再写一次标题
            elements.append(header_para)
            elements.append(Spacer(1, 0.5*cm))

    # 页码
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFont("SourceHanSans", 10)
        canvas.drawCentredString(A4[1]/2, 1*cm, f"第 {page_num} 页")
        canvas.restoreState()

    doc.build(elements,
              onFirstPage=add_page_number,
              onLaterPages=add_page_number)
    print(f"✅ 每页带表头 PDF 已生成：{os.path.abspath(filename)}")



# ----------------- 主程序入口仅需替换原函数 -----------------
if __name__ == "__main__":
    data = build_continuation_writing_data(100)   # 生成 75 人的读后续写成绩
    # make_pdf(data)                               # 复用原 PDF 生成逻辑
    make_continuation_pdf_with_header(data)

