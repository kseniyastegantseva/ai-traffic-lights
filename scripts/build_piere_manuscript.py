"""Build the English or Russian PIERE article DOCX from its Markdown source."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))")
COLUMN_WIDTHS = {
    4: (1.36, 0.49, 0.79, 0.73),
    5: (1.12, 0.36, 0.48, 0.98, 0.43),
    6: (1.12, 0.44, 0.44, 0.49, 0.44, 0.44),
}


def set_cell_margins(cell, top: int = 45, start: int = 48, bottom: int = 45, end: int = 48) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "5")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "D9D9D9")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def add_inline(paragraph, text: str) -> None:
    cursor = 0
    for match in INLINE.finditer(text):
        if match.start() > cursor:
            paragraph.add_run(text[cursor : match.start()])
        token = match.group(0)
        if token.startswith("**"):
            paragraph.add_run(token[2:-2]).bold = True
        elif token.startswith("*"):
            paragraph.add_run(token[1:-1]).italic = True
        else:
            link = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            paragraph.add_run(f"{link.group(1)} ({link.group(2)})")
        cursor = match.end()
    if cursor < len(text):
        paragraph.add_run(text[cursor:])


def add_table(doc: Document, lines: list[str], width: float) -> None:
    source_rows = [
        [part.strip() for part in line.strip().strip("|").split("|")]
        for line in lines
    ]
    rows = [row for row in source_rows if not all(re.fullmatch(r":?-{3,}:?", c) for c in row)]
    if len(rows) < 2:
        return
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.style = "Table Grid"
    widths = COLUMN_WIDTHS.get(len(rows[0]))
    if widths is None or abs(sum(widths) - width) > 0.1:
        widths = tuple(width / len(rows[0]) for _ in rows[0])
    for idx, col_width in enumerate(widths):
        table.columns[idx].width = Inches(col_width)
    for row_idx, values in enumerate(rows):
        row = table.rows[row_idx]
        prevent_row_split(row)
        if row_idx == 0:
            set_repeat_table_header(row)
        for col_idx, value in enumerate(values):
            cell = row.cells[col_idx]
            cell.width = Inches(widths[col_idx])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            if row_idx == 0:
                set_cell_shading(cell, "1F4E78")
            elif row_idx % 2 == 0:
                set_cell_shading(cell, "F2F6FA")
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            if col_idx > 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_inline(p, value)
            for run in p.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(9)
                if row_idx == 0:
                    run.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)
                else:
                    run.font.color.rgb = RGBColor(0, 0, 0)
    set_table_borders(table)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(1)
    spacer.paragraph_format.space_before = Pt(0)


def set_page_layout(section, columns: int = 1) -> None:
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.63)
    section.bottom_margin = Inches(0.62)
    section.left_margin = Inches(0.64)
    section.right_margin = Inches(0.64)
    section.header_distance = Inches(0.28)
    section.footer_distance = Inches(0.28)
    cols = section._sectPr.xpath("./w:cols")
    node = cols[0] if cols else OxmlElement("w:cols")
    node.set(qn("w:num"), str(columns))
    node.set(qn("w:space"), "360")
    if not cols:
        section._sectPr.append(node)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    run._r.addnext(field)


def build(source: Path, output: Path, language: str) -> None:
    doc = Document()
    section = doc.sections[0]
    set_page_layout(section, columns=1)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.2)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.line_spacing = 1.0
    normal.paragraph_format.space_after = Pt(3)
    for style_name, size in (("Heading 1", 10.2), ("Heading 2", 10), ("Heading 3", 10)):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(5)
        style.paragraph_format.space_after = Pt(2)
        style.paragraph_format.keep_with_next = True
    title_style = doc.styles["Title"]
    title_style.font.name = "Times New Roman"
    title_style.font.size = Pt(24)
    title_style.font.bold = True
    title_style.font.color.rgb = RGBColor(0, 0, 0)
    title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_style.paragraph_format.space_after = Pt(5)
    title_ppr = title_style._element.pPr
    if title_ppr is not None:
        border = title_ppr.find(qn("w:pBdr"))
        if border is not None:
            title_ppr.remove(border)
    add_page_number(section.footer.paragraphs[0])

    raw = source.read_text(encoding="utf-8").splitlines()
    index = 0
    two_columns = False
    content_width = 7.0
    column_width = 3.37
    while index < len(raw):
        line = raw[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("## 1.") and not two_columns:
            section = doc.add_section(WD_SECTION.CONTINUOUS)
            set_page_layout(section, columns=2)
            two_columns = True
        if line.startswith("|"):
            table_lines = []
            while index < len(raw) and raw[index].strip().startswith("|"):
                table_lines.append(raw[index].strip())
                index += 1
            add_table(doc, table_lines, column_width if two_columns else content_width)
            continue
        image_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if image_match:
            image_path = (source.parent / image_match.group(2)).resolve()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(str(image_path), width=Inches(3.28 if two_columns else 6.85))
            index += 1
            continue
        if line.startswith("# "):
            p = doc.add_paragraph(style="Title")
            p.add_run(line[2:])
            index += 1
            continue
        if line.startswith("## "):
            heading = doc.add_heading(line[3:], level=1)
            if line.lower() in ("## references", "## литература"):
                heading.paragraph_format.page_break_before = True
                heading.paragraph_format.space_before = Pt(5)
            if language == "en" and line.startswith("## 6. Limitations"):
                heading.paragraph_format.page_break_before = True
            index += 1
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=2)
            index += 1
            continue
        if line.startswith("#### "):
            doc.add_heading(line[5:], level=3)
            index += 1
            continue
        if line.startswith(("*Fig.", "*Рис.", "*Table", "*Табл.")):
            p = doc.add_paragraph()
            p.paragraph_format.keep_together = True
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.keep_with_next = line.startswith(("*Table", "*Табл."))
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_inline(p, line)
            for run in p.runs:
                run.italic = True
                run.font.size = Pt(9)
            index += 1
            continue
        p = doc.add_paragraph()
        if line.startswith("**("):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_together = True
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
        if line.startswith("**") and index < 6:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            for run in p.runs:
                run.font.size = Pt(10)
        if line.startswith(("**Keywords:", "**Ключевые слова:")):
            p.paragraph_format.space_after = Pt(7)
        add_inline(p, line)
        if line.startswith(("**Darya", "**Дарья")):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.size = Pt(9)
        if line.startswith(("¹ Information", "¹ Кафедра", "Correspondence:", "Для переписки:")):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(3)
            for run in p.runs:
                run.font.size = Pt(9)
        index += 1

    doc.core_properties.title = raw[0].removeprefix("# ")
    doc.core_properties.subject = "PIERE article manuscript"
    doc.core_properties.author = "Darya A. Limarenko; Kseniya M. Stegantseva; Elena Yu. Silantyeva"
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    print(f"Wrote {output} ({output.stat().st_size / 1024:.1f} KiB); language={language}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("en", "ru"), default="en")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    suffix = "" if args.language == "en" else "_RU"
    source = args.source or ROOT / "paper" / f"revised_manuscript{suffix.lower()}.md"
    if args.language == "en":
        source = args.source or ROOT / "paper" / "revised_manuscript.md"
    output = args.output or ROOT / "paper" / f"PIERE_Revised_Article{suffix}.docx"
    build(source.resolve(), output.resolve(), args.language)


if __name__ == "__main__":
    main()
