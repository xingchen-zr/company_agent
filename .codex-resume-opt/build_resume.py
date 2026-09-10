from __future__ import annotations

import io
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


SOURCE = Path(r"C:\Users\lenovo\Desktop\董星晨的个人简历.docx")
OUTPUT = Path(r"C:\Users\lenovo\Desktop\董星晨的个人简历_优化版.docx")

FONT_CN = "微软雅黑"
FONT_EN = "Arial"
BLACK = "111111"
MUTED = "595959"
ACCENT = "1F5A78"


def set_cell_margins(cell, top=0, start=0, bottom=0, end=0):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def remove_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        node = borders.find(tag)
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        node.set(qn("w:val"), "nil")


def set_repeat_font(run, size, *, bold=False, color=BLACK):
    run.font.name = FONT_EN
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), FONT_EN)
    r_fonts.set(qn("w:hAnsi"), FONT_EN)
    r_fonts.set(qn("w:eastAsia"), FONT_CN)


def set_para(paragraph, *, before=0, after=0, line=1.15, keep=False):
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing_rule = WD_LINE_SPACING.SINGLE
    fmt.line_spacing = line
    fmt.keep_with_next = keep


def remove_paragraph_borders(paragraph):
    p_pr = paragraph._p.get_or_add_pPr()
    borders = p_pr.find(qn("w:pBdr"))
    if borders is not None:
        p_pr.remove(borders)


def add_text(paragraph, text, size=9.2, *, bold=False, color=BLACK):
    run = paragraph.add_run(text)
    set_repeat_font(run, size, bold=bold, color=color)
    return run


def add_section_heading(doc, text):
    p = doc.add_paragraph(style="Heading 1")
    set_para(p, before=7, after=2.5, line=1.0, keep=True)
    p.paragraph_format.keep_together = True
    add_text(p, text, 11.5, bold=True, color=BLACK)
    return p


def add_bullet(doc, text, *, size=8.65, after=1.3):
    p = doc.add_paragraph()
    set_para(p, after=after, line=1.14)
    p.paragraph_format.left_indent = Cm(0.42)
    p.paragraph_format.first_line_indent = Cm(-0.32)
    add_text(p, "•  ", size, bold=True, color=ACCENT)
    add_text(p, text, size)
    return p


def extract_portrait():
    with zipfile.ZipFile(SOURCE) as archive:
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
        if not media:
            return None
        # The supplied resume contains one portrait image.
        return io.BytesIO(archive.read(media[0]))


def build():
    doc = Document()
    section = doc.sections[0]
    section.start_type = WD_SECTION_START.NEW_PAGE
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.25)
    section.bottom_margin = Cm(1.15)
    section.left_margin = Cm(1.45)
    section.right_margin = Cm(1.45)

    normal = doc.styles["Normal"]
    normal.font.name = FONT_EN
    normal.font.size = Pt(9.2)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    normal.paragraph_format.space_after = Pt(0)

    title_style = doc.styles["Title"]
    title_style.font.name = FONT_EN
    title_style.font.size = Pt(25)
    title_style.font.bold = True
    title_style.font.color.rgb = RGBColor.from_string(BLACK)
    title_style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    title_style_p_pr = title_style._element.get_or_add_pPr()
    title_style_borders = title_style_p_pr.find(qn("w:pBdr"))
    if title_style_borders is not None:
        title_style_p_pr.remove(title_style_borders)

    for style_name in ("Heading 1", "Heading 2"):
        style = doc.styles[style_name]
        style.font.name = FONT_EN
        style.font.color.rgb = RGBColor.from_string(BLACK)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)

    header = doc.add_table(rows=1, cols=2)
    header.autofit = False
    header.columns[0].width = Cm(15.6)
    header.columns[1].width = Cm(2.5)
    remove_table_borders(header)
    left, right = header.rows[0].cells
    left.width = Cm(15.6)
    right.width = Cm(2.5)
    left.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    right.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    set_cell_margins(left, 0, 0, 0, 100)
    set_cell_margins(right, 0, 80, 0, 0)

    title = left.paragraphs[0]
    title.style = doc.styles["Title"]
    set_para(title, after=2, line=1.0)
    remove_paragraph_borders(title)
    add_text(title, "董星晨", 25, bold=True)

    role = left.add_paragraph()
    set_para(role, after=5, line=1.0)
    add_text(role, "AI 应用开发实习生  /  AI 产品实习生", 11.2, bold=True, color=ACCENT)

    contact = left.add_paragraph()
    set_para(contact, after=1, line=1.0)
    add_text(contact, "18656018213  |  d18656018213@outlook.com  |  合肥  |  三天内到岗", 8.8, color=MUTED)

    portrait = extract_portrait()
    if portrait:
        p = right.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        set_para(p, line=1.0)
        p.add_run().add_picture(portrait, width=Cm(2.45), height=Cm(3.25))

    add_section_heading(doc, "教育背景")
    p = doc.add_paragraph()
    set_para(p, after=1.5, line=1.0)
    add_text(p, "安徽建筑大学", 9.7, bold=True)
    add_text(p, "  |  本科在读  |  2023.09–2027.06", 9.4, color=MUTED)

    add_section_heading(doc, "项目经历")
    p = doc.add_paragraph()
    set_para(p, after=1, line=1.0, keep=True)
    add_text(p, "企业制度知识库问答 Agent", 10.3, bold=True)
    add_text(p, "  |  独立开发", 9, color=MUTED)
    p = doc.add_paragraph()
    set_para(p, after=2, line=1.0, keep=True)
    add_text(p, "Python  FastAPI  LangChain  DeepSeek  Ollama  Chroma  BM25  Redis", 8.2, color=ACCENT)
    add_bullet(doc, "完成制度文档加载、递归切分、Ollama Embedding 与 Chroma 持久化，并将检索封装为 LangChain 工具供 Agent 按需调用。")
    add_bullet(doc, "在向量召回基础上实现 BM25 中文词法索引，通过加权 RRF 融合、相关性阈值和内容去重返回候选；建立 Top1、Hit@3、Recall@K、MRR 与无答案拒答评测口径。")
    add_bullet(doc, "使用 FastAPI StreamingResponse 输出流式回答；通过 Cookie 传递会话 ID，使用 Redis 保存最近 10 轮对话并设置 48 小时过期。")
    add_bullet(doc, "实现会话级附件上传与归属校验，支持 PDF、DOCX、XLSX、TXT、MD、CSV 文本提取；图片经视觉模型识别后与制度检索结果共同交给主模型回答。")
    add_bullet(doc, "补充请求 ID、检索耗时、工具调用、历史读写和异常日志；以 22 项单元及接口测试覆盖附件校验、跨会话访问、图片分析和混合检索。", after=2.2)

    p = doc.add_paragraph()
    set_para(p, before=1.2, after=1, line=1.0, keep=True)
    add_text(p, "基于 CSV 岗位数据的 AI 求职问答", 10.3, bold=True)
    add_text(p, "  |  独立开发", 9, color=MUTED)
    p = doc.add_paragraph()
    set_para(p, after=2, line=1.0, keep=True)
    add_text(p, "Python  Pandas  LangChain  RAG  FastAPI  Streamlit", 8.2, color=ACCENT)
    add_bullet(doc, "使用 Pandas 清洗并结构化 CSV 岗位数据，为条件筛选和问答检索建立统一数据源。")
    add_bullet(doc, "结合 LangChain 与 RAG 完成岗位信息检索，支持用户通过自然语言查询符合条件和预期的岗位。")
    add_bullet(doc, "使用 FastAPI 提供问答接口，通过 Streamlit 搭建交互页面，完成数据处理、检索、回答与结果展示流程。", after=2.0)

    add_section_heading(doc, "专业技能")
    for label, content in (
        ("Python 与后端", "掌握 Python、面向对象、模块化与异常处理；能够使用 FastAPI、Pydantic 开发接口和流式响应。"),
        ("大模型应用", "能够使用 LangChain 构建 Agent、工具调用和 RAG 流程，理解 Prompt、上下文管理、混合检索与评测指标。"),
        ("数据与工程", "使用 Pandas 处理结构化数据，使用 Chroma 和 BM25 构建索引，使用 Redis 管理会话；具备基础 HTML、CSS、JavaScript 能力。"),
    ):
        p = doc.add_paragraph()
        set_para(p, after=1.4, line=1.1)
        add_text(p, f"{label}  ", 8.8, bold=True, color=ACCENT)
        add_text(p, content, 8.7)

    add_section_heading(doc, "个人优势")
    p = doc.add_paragraph()
    set_para(p, after=0, line=1.14)
    add_text(p, "能够独立完成小型 AI 应用的文档处理、检索设计、Agent 编排、接口开发、前端联调和日志排查。重视可验证结果，能够通过测试与检索指标定位问题，并明确原型与生产系统之间的边界。", 8.8)

    # Avoid an extra blank paragraph after the layout table and ensure metadata is neutral.
    doc.core_properties.title = "董星晨个人简历"
    doc.core_properties.subject = "AI 应用开发与 AI 产品实习求职简历"
    doc.core_properties.author = "董星晨"
    doc.core_properties.keywords = "Python, FastAPI, LangChain, RAG, Chroma, BM25, Redis"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
