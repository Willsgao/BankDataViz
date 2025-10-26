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

if __name__ == "__main__":
    data = build_data(75)
    make_pdf(data)