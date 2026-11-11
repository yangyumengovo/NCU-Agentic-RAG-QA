from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import nsdecls, qn
from docx.oxml.shared import OxmlElement
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "基于RAG的高校制度文档智能问答系统_从零开始完整实施计划书.md"
OUTPUT = ROOT / "基于RAG的高校制度文档智能问答系统_从零开始完整实施计划书.docx"
ASSET_DIR = ROOT / "实施计划书资源"
ARCH_IMG = ASSET_DIR / "系统总体架构图.png"

BODY_FONT_CN = "宋体"
BODY_FONT_EN = "Aptos"
HEADING_FONT_CN = "微软雅黑"
HEADING_FONT_EN = "Arial"
MONO_FONT = "Consolas"

NAVY = "17365D"
BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
LIGHT_BLUE = "E8EEF5"
LIGHTER_BLUE = "F4F7FB"
LIGHT_GRAY = "F2F4F7"
MID_GRAY = "D7DEE8"
TEXT = "1F2937"
MUTED = "5E6B78"
WHITE = "FFFFFF"
RISK = "9B1C1C"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_width(cell, width_dxa: int) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(width_dxa))
    tc_w.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa: list[int], indent_dxa: int = 120) -> None:
    table.autofit = False
    tbl_pr = table._tbl.tblPr

    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(sum(widths_dxa)))
    tbl_w.set(qn("w:type"), "dxa")

    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent_dxa))
    tbl_ind.set(qn("w:type"), "dxa")

    tbl_layout = tbl_pr.find(qn("w:tblLayout"))
    if tbl_layout is None:
        tbl_layout = OxmlElement("w:tblLayout")
        tbl_pr.append(tbl_layout)
    tbl_layout.set(qn("w:type"), "fixed")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        for idx, cell in enumerate(row.cells):
            set_cell_width(cell, widths_dxa[idx])
            set_cell_margins(cell)


def set_run_font(run, *, cn=BODY_FONT_CN, en=BODY_FONT_EN, size=10.5,
                 bold=None, italic=None, color=TEXT) -> None:
    run.font.name = en
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.rFonts
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    r_fonts.set(qn("w:ascii"), en)
    r_fonts.set(qn("w:hAnsi"), en)
    r_fonts.set(qn("w:eastAsia"), cn)
    r_fonts.set(qn("w:cs"), en)


def set_paragraph_border(paragraph, *, side="bottom", color=MID_GRAY,
                         size="6", space="4", style="single") -> None:
    p = paragraph._p
    p_pr = p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    border = p_bdr.find(qn(f"w:{side}"))
    if border is None:
        border = OxmlElement(f"w:{side}")
        p_bdr.append(border)
    border.set(qn("w:val"), style)
    border.set(qn("w:sz"), size)
    border.set(qn("w:space"), space)
    border.set(qn("w:color"), color)


def set_paragraph_shading(paragraph, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = p_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        p_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def add_hyperlink(paragraph, text: str, url: str):
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), BLUE)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_pr.append(color)
    r_pr.append(underline)
    new_run.append(r_pr)
    text_node = OxmlElement("w:t")
    text_node.text = text
    new_run.append(text_node)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def add_rich_text(paragraph, text: str, *, size=10.5, color=TEXT,
                  bold=False, italic=False, font_cn=BODY_FONT_CN,
                  font_en=BODY_FONT_EN) -> None:
    url_pattern = re.compile(r"https?://[^\s）)\]，,；;]+")
    bold_pattern = re.compile(r"\*\*(.+?)\*\*")
    pos = 0

    def add_segment(segment: str, is_bold=False):
        if not segment:
            return
        u_pos = 0
        for match in url_pattern.finditer(segment):
            if match.start() > u_pos:
                run = paragraph.add_run(segment[u_pos:match.start()])
                set_run_font(run, cn=font_cn, en=font_en, size=size,
                             bold=(bold or is_bold), italic=italic, color=color)
            add_hyperlink(paragraph, match.group(0), match.group(0))
            u_pos = match.end()
        if u_pos < len(segment):
            run = paragraph.add_run(segment[u_pos:])
            set_run_font(run, cn=font_cn, en=font_en, size=size,
                         bold=(bold or is_bold), italic=italic, color=color)

    for match in bold_pattern.finditer(text):
        add_segment(text[pos:match.start()], False)
        add_segment(match.group(1), True)
        pos = match.end()
    add_segment(text[pos:], False)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr_text, fld_char2])
    set_run_font(run, size=9, color=MUTED)


def set_update_fields(doc: Document) -> None:
    settings = doc.settings._element
    node = settings.find(qn("w:updateFields"))
    if node is None:
        node = OxmlElement("w:updateFields")
        settings.append(node)
    node.set(qn("w:val"), "true")


def set_section_geometry(section, landscape=False) -> int:
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Cm(29.7)
        section.page_height = Cm(21.0)
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin = Cm(1.7)
        section.right_margin = Cm(1.7)
        usable_cm = 29.7 - 3.4
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.4)
        section.right_margin = Cm(2.2)
        usable_cm = 21.0 - 4.6
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(1.0)
    return int(usable_cm / 2.54 * 1440)


def setup_header_footer(section, *, first=False) -> None:
    section.different_first_page_header_footer = first
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    hp.paragraph_format.space_after = Pt(2)
    hp.paragraph_format.tab_stops.add_tab_stop(Cm(16.4))
    r1 = hp.add_run("毕业论文实施计划书")
    set_run_font(r1, cn=HEADING_FONT_CN, en=HEADING_FONT_EN, size=8.5,
                 bold=True, color=MUTED)
    r2 = hp.add_run("\t基于 RAG 的高校制度文档智能问答系统")
    set_run_font(r2, cn=HEADING_FONT_CN, en=HEADING_FONT_EN, size=8.5,
                 color=MUTED)

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_before = Pt(2)
    set_paragraph_border(fp, side="top", color=MID_GRAY, size="4", space="3")
    prefix = fp.add_run("第 ")
    set_run_font(prefix, size=9, color=MUTED)
    add_page_field(fp)
    suffix = fp.add_run(" 页")
    set_run_font(suffix, size=9, color=MUTED)

    if first:
        first_header = section.first_page_header
        first_header.is_linked_to_previous = False
        first_header.paragraphs[0].text = ""
        first_footer = section.first_page_footer
        first_footer.is_linked_to_previous = False
        first_footer.paragraphs[0].text = ""


def setup_styles(doc: Document) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = BODY_FONT_EN
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT_CN)
    normal._element.rPr.rFonts.set(qn("w:ascii"), BODY_FONT_EN)
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), BODY_FONT_EN)
    p_format = normal.paragraph_format
    p_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_format.space_before = Pt(0)
    p_format.space_after = Pt(6)
    p_format.line_spacing = 1.25
    p_format.widow_control = True

    heading_specs = {
        "Heading 1": (16, NAVY, 18, 9),
        "Heading 2": (13, BLUE, 13, 6),
        "Heading 3": (11.5, DARK_BLUE, 9, 4),
    }
    for name, (size, color, before, after) in heading_specs.items():
        style = styles[name]
        style.font.name = HEADING_FONT_EN
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), HEADING_FONT_CN)
        style._element.rPr.rFonts.set(qn("w:ascii"), HEADING_FONT_EN)
        style._element.rPr.rFonts.set(qn("w:hAnsi"), HEADING_FONT_EN)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.keep_together = True
        style.paragraph_format.widow_control = True

    if "Code Block" not in styles:
        code = styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
    else:
        code = styles["Code Block"]
    code.font.name = MONO_FONT
    code.font.size = Pt(8.5)
    code._element.rPr.rFonts.set(qn("w:eastAsia"), "等线")
    code.paragraph_format.left_indent = Cm(0.45)
    code.paragraph_format.right_indent = Cm(0.2)
    code.paragraph_format.space_before = Pt(4)
    code.paragraph_format.space_after = Pt(7)
    code.paragraph_format.line_spacing = 1.08

    if "Callout" not in styles:
        callout = styles.add_style("Callout", WD_STYLE_TYPE.PARAGRAPH)
    else:
        callout = styles["Callout"]
    callout.font.name = BODY_FONT_EN
    callout.font.size = Pt(10.5)
    callout._element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT_CN)
    callout.paragraph_format.left_indent = Cm(0.25)
    callout.paragraph_format.right_indent = Cm(0.15)
    callout.paragraph_format.space_before = Pt(6)
    callout.paragraph_format.space_after = Pt(8)
    callout.paragraph_format.line_spacing = 1.25


def add_numbering_definition(doc: Document, *, bullet: bool) -> int:
    numbering = doc.part.numbering_part.element
    abstract_ids = [
        int(el.get(qn("w:abstractNumId")))
        for el in numbering.findall(qn("w:abstractNum"))
    ]
    num_ids = [
        int(el.get(qn("w:numId")))
        for el in numbering.findall(qn("w:num"))
    ]
    abstract_id = max(abstract_ids, default=0) + 1
    num_id = max(num_ids, default=0) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)
    lvl = OxmlElement("w:lvl")
    lvl.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    lvl.append(start)
    num_fmt = OxmlElement("w:numFmt")
    num_fmt.set(qn("w:val"), "bullet" if bullet else "decimal")
    lvl.append(num_fmt)
    lvl_text = OxmlElement("w:lvlText")
    lvl_text.set(qn("w:val"), "•" if bullet else "%1.")
    lvl.append(lvl_text)
    lvl_jc = OxmlElement("w:lvlJc")
    lvl_jc.set(qn("w:val"), "left")
    lvl.append(lvl_jc)
    p_pr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "540")
    tabs.append(tab)
    p_pr.append(tabs)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "540")
    ind.set(qn("w:hanging"), "270")
    p_pr.append(ind)
    lvl.append(p_pr)
    r_pr = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), "Arial")
    fonts.set(qn("w:hAnsi"), "Arial")
    r_pr.append(fonts)
    lvl.append(r_pr)
    abstract.append(lvl)
    # OOXML requires every abstractNum to appear before the concrete num
    # instances. Appending an abstractNum after existing num nodes makes Word
    # repair the numbering part on open, which can collapse all lists into one.
    first_num = numbering.find(qn("w:num"))
    if first_num is None:
        numbering.append(abstract)
    else:
        numbering.insert(numbering.index(first_num), abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), str(abstract_id))
    num.append(abstract_ref)
    # Word may continue numbering across separate lists unless the concrete
    # numbering instance explicitly overrides the level start value.
    lvl_override = OxmlElement("w:lvlOverride")
    lvl_override.set(qn("w:ilvl"), "0")
    start_override = OxmlElement("w:startOverride")
    start_override.set(qn("w:val"), "1")
    lvl_override.append(start_override)
    num.append(lvl_override)
    numbering.append(num)
    return num_id


def apply_numbering(paragraph, num_id: int) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn("w:numPr"))
    if num_pr is None:
        num_pr = OxmlElement("w:numPr")
        p_pr.append(num_pr)
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    num_id_node = OxmlElement("w:numId")
    num_id_node.set(qn("w:val"), str(num_id))
    num_pr.extend([ilvl, num_id_node])


def add_list_item(doc: Document, text: str, num_id: int) -> None:
    p = doc.add_paragraph()
    apply_numbering(p, num_id)
    p.paragraph_format.left_indent = Cm(0.95)
    p.paragraph_format.first_line_indent = Cm(-0.47)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.widow_control = True
    add_rich_text(p, text)


def add_separator(doc: Document) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    set_paragraph_border(p, color=MID_GRAY, size="4", space="1")


def add_callout(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="Callout")
    set_paragraph_shading(p, LIGHTER_BLUE)
    set_paragraph_border(p, side="left", color=BLUE, size="18", space="7")
    add_rich_text(p, text, size=10.5, color=NAVY)


def add_code_block(doc: Document, lines: list[str]) -> None:
    p = doc.add_paragraph(style="Code Block")
    set_paragraph_shading(p, LIGHT_GRAY)
    set_paragraph_border(p, side="left", color=MID_GRAY, size="10", space="6")
    for idx, line in enumerate(lines):
        run = p.add_run(line)
        set_run_font(run, cn="等线", en=MONO_FONT, size=8.5, color=TEXT)
        if idx < len(lines) - 1:
            run.add_break()


def compute_col_widths(rows: list[list[str]], total_dxa: int) -> list[int]:
    cols = max(len(r) for r in rows)
    weights = []
    for c in range(cols):
        samples = [len(r[c]) if c < len(r) else 0 for r in rows[:20]]
        max_len = max(samples, default=1)
        avg_len = sum(samples) / max(len(samples), 1)
        weight = max(5.0, min(28.0, 0.55 * max_len + 0.45 * avg_len))
        weights.append(weight)

    min_dxa = 620 if cols >= 8 else 850
    available = total_dxa - min_dxa * cols
    if available < 0:
        return [total_dxa // cols] * cols
    weight_sum = sum(weights)
    widths = [min_dxa + int(available * w / weight_sum) for w in weights]
    widths[-1] += total_dxa - sum(widths)
    return widths


def normalize_table_rows(raw_lines: list[str]) -> list[list[str]]:
    rows = []
    for line in raw_lines:
        stripped = line.strip().strip("|")
        rows.append([cell.strip() for cell in stripped.split("|")])
    return rows


def add_markdown_table(doc: Document, raw_lines: list[str]) -> None:
    rows = normalize_table_rows(raw_lines)
    if len(rows) < 2:
        return
    rows.pop(1)
    col_count = max(len(row) for row in rows)
    for row in rows:
        row.extend([""] * (col_count - len(row)))

    landscape = col_count > 6
    if landscape:
        sec = doc.add_section(WD_SECTION.NEW_PAGE)
        total_dxa = set_section_geometry(sec, landscape=True)
        setup_header_footer(sec)
    else:
        sec = doc.sections[-1]
        total_dxa = int(
            (sec.page_width - sec.left_margin - sec.right_margin) / 635
        )

    widths = compute_col_widths(rows, total_dxa - 120)
    table = doc.add_table(rows=len(rows), cols=col_count)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    set_table_geometry(table, widths, indent_dxa=120)

    for r_idx, row in enumerate(rows):
        for c_idx, value in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if r_idx == 0:
                set_cell_shading(cell, LIGHT_BLUE)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.08
            short_value = len(value) <= 14 or re.fullmatch(r"[\d.%\-/：: ]+", value or "")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if short_value else WD_ALIGN_PARAGRAPH.LEFT
            add_rich_text(
                p,
                value,
                size=7.0 if col_count > 10 else (8.0 if col_count > 6 else 9.0),
                bold=(r_idx == 0),
                color=NAVY if r_idx == 0 else TEXT,
            )
    first_tr_pr = table.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    first_tr_pr.append(repeat)

    after = doc.add_paragraph()
    after.paragraph_format.space_after = Pt(2)

    if landscape:
        sec2 = doc.add_section(WD_SECTION.NEW_PAGE)
        set_section_geometry(sec2, landscape=False)
        setup_header_footer(sec2)


def add_toc(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("目录")
    set_run_font(run, cn=HEADING_FONT_CN, en=HEADING_FONT_EN, size=18,
                 bold=True, color=NAVY)

    toc_p = doc.add_paragraph()
    toc_p.paragraph_format.space_after = Pt(8)
    run = toc_p.add_run()
    fld_char = OxmlElement("w:fldChar")
    fld_char.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "目录将在打开文档或渲染时自动更新。"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char, instr, sep, text, end])
    set_run_font(run, size=10.5, color=MUTED)


def find_font(size: int, bold=False):
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf" if bold else "C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def pil_color(value: str) -> str:
    return value if value.startswith("#") else f"#{value}"


def draw_rounded_box(draw, xy, fill, outline, radius=24, width=3):
    draw.rounded_rectangle(
        xy,
        radius=radius,
        fill=pil_color(fill),
        outline=pil_color(outline),
        width=width,
    )


def multiline_center(draw, xy, text, font, fill, spacing=8):
    left, top, right, bottom = xy
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.multiline_text(
        ((left + right - w) / 2, (top + bottom - h) / 2),
        text,
        font=font,
        fill=pil_color(fill),
        spacing=spacing,
        align="center",
    )


def arrow(draw, start, end, color=BLUE, width=6):
    draw.line([start, end], fill=pil_color(color), width=width)
    x2, y2 = end
    x1, y1 = start
    if abs(x2 - x1) >= abs(y2 - y1):
        sign = 1 if x2 > x1 else -1
        pts = [(x2, y2), (x2 - 18 * sign, y2 - 12), (x2 - 18 * sign, y2 + 12)]
    else:
        sign = 1 if y2 > y1 else -1
        pts = [(x2, y2), (x2 - 12, y2 - 18 * sign), (x2 + 12, y2 - 18 * sign)]
    draw.polygon(pts, fill=pil_color(color))


def generate_architecture_diagram() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1800, 980), pil_color(WHITE))
    draw = ImageDraw.Draw(img)
    title_font = find_font(48, bold=True)
    h_font = find_font(31, bold=True)
    b_font = find_font(25, bold=False)
    small_font = find_font(21, bold=False)

    draw.text((80, 45), "系统总体架构与问答数据流", font=title_font, fill=pil_color(NAVY))
    draw.line((80, 115, 1720, 115), fill=pil_color(MID_GRAY), width=3)

    browser = (90, 255, 390, 545)
    backend = (560, 185, 960, 615)
    dify = (1130, 145, 1710, 655)
    mysql = (590, 745, 930, 915)
    vector = (1170, 745, 1490, 915)
    model = (1515, 745, 1740, 915)

    draw_rounded_box(draw, browser, "#F4F7FB", "#2E74B5")
    multiline_center(draw, (90, 275, 390, 365), "Vue 3 前端", h_font, NAVY)
    multiline_center(
        draw, (110, 365, 370, 525),
        "登录与权限\n流式问答\n来源证据卡片\n历史记录与反馈",
        b_font, TEXT, spacing=12,
    )

    draw_rounded_box(draw, backend, "#E8EEF5", "#1F4D78")
    multiline_center(draw, (560, 205, 960, 300), "Spring Boot 后端", h_font, NAVY)
    multiline_center(
        draw, (590, 305, 930, 595),
        "Spring Security + JWT\nChatService\nDifyClient\n会话与消息持久化\n文档与反馈管理\nSSE 流式代理",
        b_font, TEXT, spacing=14,
    )

    draw_rounded_box(draw, dify, "#F4F7FB", "#2E74B5")
    multiline_center(draw, (1130, 165, 1710, 255), "Dify 1.16 RAG 层", h_font, NAVY)
    inner_boxes = [
        ((1170, 285, 1420, 405), "问题规范化\n与条件判断"),
        ((1450, 285, 1670, 405), "知识检索\n元数据过滤"),
        ((1170, 455, 1420, 575), "混合召回\n与重排序"),
        ((1450, 455, 1670, 575), "提示词与\n回答生成"),
    ]
    for box, text in inner_boxes:
        draw_rounded_box(draw, box, WHITE, "#A8B8CC", radius=18, width=2)
        multiline_center(draw, box, text, b_font, TEXT, spacing=8)

    draw_rounded_box(draw, mysql, "#FFF8E8", "#B58B21")
    multiline_center(draw, mysql, "MySQL 8.4\n业务数据", h_font, "#6F5513")
    draw_rounded_box(draw, vector, "#F4F7FB", "#2E74B5")
    multiline_center(draw, vector, "Dify 管理的\n知识库与向量数据", b_font, NAVY)
    draw_rounded_box(draw, model, "#F4F7FB", "#2E74B5")
    multiline_center(draw, model, "LLM / Embedding\nReranker API", small_font, NAVY)

    arrow(draw, (390, 400), (560, 400))
    draw.text((420, 350), "HTTPS / SSE", font=small_font, fill=pil_color(MUTED))
    arrow(draw, (960, 400), (1130, 400))
    draw.text((985, 350), "Dify API", font=small_font, fill=pil_color(MUTED))
    arrow(draw, (760, 615), (760, 745))
    arrow(draw, (1330, 655), (1330, 745))
    arrow(draw, (1605, 655), (1605, 745))

    img.save(ARCH_IMG, quality=95)


def add_title_page(doc: Document) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(52)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run("南昌大学高等学历继续教育")
    set_run_font(r, cn=HEADING_FONT_CN, en=HEADING_FONT_EN, size=12,
                 bold=True, color=BLUE)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.05
    r = p.add_run("基于 RAG 的高校制度文档\n智能问答系统")
    set_run_font(r, cn=HEADING_FONT_CN, en=HEADING_FONT_EN, size=25,
                 bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(26)
    r = p.add_run("从零开始完整实施计划书")
    set_run_font(r, cn=HEADING_FONT_CN, en=HEADING_FONT_EN, size=18,
                 bold=False, color=DARK_BLUE)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(28)
    set_paragraph_border(p, side="left", color=BLUE, size="26", space="10")
    add_rich_text(
        p,
        "面向首次独立完成毕业设计的执行手册：从开题确认、技术选型、语料处理和系统开发，到对照实验、论文写作与答辩准备。",
        size=11.5,
        color=NAVY,
    )

    rows = [
        ("学生", "杨文", "专业", "计算机科学与技术"),
        ("项目类型", "毕业论文（设计）", "计划周期", "十周基准计划"),
        ("版本", "V1.0", "编制日期", "2026 年 7 月 23 日"),
    ]
    table = doc.add_table(rows=len(rows), cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    widths = [1200, 2450, 1350, 4240]
    set_table_geometry(table, widths, indent_dxa=120)
    for r_idx, row in enumerate(rows):
        for c_idx, value in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_shading(cell, LIGHT_BLUE if c_idx in (0, 2) else WHITE)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx in (0, 2) else WD_ALIGN_PARAGRAPH.LEFT
            add_rich_text(p, value, size=9.5, bold=c_idx in (0, 2),
                          color=NAVY if c_idx in (0, 2) else TEXT)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(68)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run("使用说明")
    set_run_font(r, cn=HEADING_FONT_CN, en=HEADING_FONT_EN, size=11,
                 bold=True, color=BLUE)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    add_rich_text(
        p,
        "按章节逐项执行并保存证据。软件版本、实验配置和进度日期应根据实际情况填写；任何实验结果都必须来自真实运行记录。",
        size=9.5,
        color=MUTED,
    )
    doc.add_page_break()


def parse_markdown(doc: Document, text: str, bullet_num_id: int) -> None:
    lines = text.splitlines()
    start = 0
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            start = idx + 1
            break
    i = start
    numbered_num_id = None
    previous_was_number = False
    architecture_inserted = False

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            previous_was_number = False
            i += 1
            continue

        if stripped == "---":
            add_separator(doc)
            previous_was_number = False
            i += 1
            continue

        if stripped.startswith("~~~"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("~~~"):
                code_lines.append(lines[i].rstrip())
                i += 1
            add_code_block(doc, code_lines)
            previous_was_number = False
            i += 1
            continue

        if "|" in stripped and i + 1 < len(lines):
            separator = lines[i + 1].strip()
            if re.match(r"^\|?\s*:?-{3,}", separator) and "|" in separator:
                table_lines = [line, lines[i + 1]]
                i += 2
                while i < len(lines) and "|" in lines[i] and lines[i].strip():
                    table_lines.append(lines[i])
                    i += 1
                add_markdown_table(doc, table_lines)
                previous_was_number = False
                continue

        if stripped.startswith("#### "):
            p = doc.add_paragraph(stripped[5:], style="Heading 3")
            p.paragraph_format.keep_with_next = True
            previous_was_number = False
            i += 1
            continue

        if stripped.startswith("### "):
            p = doc.add_paragraph(stripped[4:], style="Heading 2")
            p.paragraph_format.keep_with_next = True
            previous_was_number = False
            i += 1
            continue

        if stripped.startswith("## "):
            heading = stripped[3:]
            p = doc.add_paragraph(heading, style="Heading 1")
            set_paragraph_border(p, side="bottom", color=MID_GRAY, size="5", space="3")
            if heading.startswith("七、总体架构") and not architecture_inserted:
                if ARCH_IMG.exists():
                    pic_p = doc.add_paragraph()
                    pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    pic_p.paragraph_format.space_before = Pt(4)
                    pic_p.paragraph_format.space_after = Pt(8)
                    run = pic_p.add_run()
                    run.add_picture(str(ARCH_IMG), width=Cm(15.8))
                    cap = doc.add_paragraph()
                    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    cap.paragraph_format.space_after = Pt(8)
                    cap_run = cap.add_run("图 1  系统总体架构与问答数据流")
                    set_run_font(cap_run, size=9, color=MUTED)
                    architecture_inserted = True
            previous_was_number = False
            i += 1
            continue

        if stripped.startswith("> "):
            add_callout(doc, stripped[2:].strip())
            previous_was_number = False
            i += 1
            continue

        if stripped.startswith("- "):
            add_list_item(doc, stripped[2:].strip(), bullet_num_id)
            previous_was_number = False
            i += 1
            continue

        number_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if number_match:
            if not previous_was_number or numbered_num_id is None:
                numbered_num_id = add_numbering_definition(doc, bullet=False)
            add_list_item(doc, number_match.group(2), numbered_num_id)
            previous_was_number = True
            i += 1
            continue

        p = doc.add_paragraph()
        p.paragraph_format.widow_control = True
        p.paragraph_format.keep_together = False
        if re.match(r"^[A-Z]\d+\s", stripped) or stripped.endswith("："):
            p.paragraph_format.space_before = Pt(2)
        add_rich_text(p, stripped)
        previous_was_number = False
        i += 1


def build() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    generate_architecture_diagram()
    markdown = SOURCE.read_text(encoding="utf-8")

    doc = Document()
    doc.core_properties.title = "基于 RAG 的高校制度文档智能问答系统：从零开始完整实施计划书"
    doc.core_properties.subject = "毕业论文实施计划、RAG、Dify、Spring Boot、Vue"
    doc.core_properties.author = "杨文"
    doc.core_properties.comments = "根据开题报告、学校写作要求及 2026-07-23 技术资料编制"

    set_section_geometry(doc.sections[0], landscape=False)
    setup_header_footer(doc.sections[0], first=True)
    setup_styles(doc)
    set_update_fields(doc)
    bullet_num_id = add_numbering_definition(doc, bullet=True)

    add_title_page(doc)
    add_toc(doc)
    parse_markdown(doc, markdown, bullet_num_id)

    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
