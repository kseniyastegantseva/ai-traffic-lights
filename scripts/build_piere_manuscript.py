"""Build the editable Word manuscript from revised_manuscript.md and its figures."""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper" / "revised_manuscript.md"
OUTPUT = ROOT / "paper" / "PIERE_Revised_Article.docx"
INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))")


def shade(cell, fill: str) -> None:
    props = cell._tc.get_or_add_tcPr()
    element = OxmlElement("w:shd")
    element.set(qn("w:fill"), fill)
    props.append(element)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def add_inline(paragraph, text: str) -> None:
    tick = chr(96)
    text = re.sub(tick + r"([^" + tick + r"]+)" + tick, r"\1", text)
    cursor = 0
    for match in INLINE.finditer(text):
        if match.start() > cursor:
            paragraph.add_run(text[cursor:match.start()])
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("*"):
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        else:
            link = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            run = paragraph.add_run(f"{link.group(1)} ({link.group(2)})")
            run.font.color.rgb = RGBColor(31, 78, 121)
        cursor = match.end()
    if cursor < len(text):
        paragraph.add_run(text[cursor:])


def add_table(doc: Document, lines: list[str]) -> None:
    rows = [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in lines]
    if len(rows) < 2:
        return
    rows = [rows[0], *rows[2:]]  # omit Markdown separator row
    table = doc.add_table(rows=1, cols=len(rows[0]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for ridx, values in enumerate(rows):
        cells = table.rows[0].cells if ridx == 0 else table.add_row().cells
        for idx, value in enumerate(values):
            cell = cells[idx]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            add_inline(p, value.replace("**", ""))
            for run in p.runs:
                run.font.name = "Arial"
                run.font.size = Pt(7.5)
                if ridx == 0:
                    run.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)
            if ridx == 0:
                shade(cell, "1F4E78")
        if ridx == 0:
            set_repeat_table_header(table.rows[0])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    run._r.addnext(field)


def main() -> None:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.27)
    sec.page_height = Inches(11.69)
    sec.top_margin = Inches(.62)
    sec.bottom_margin = Inches(.62)
    sec.left_margin = Inches(.66)
    sec.right_margin = Inches(.66)
    sec.header_distance = Inches(.3)
    sec.footer_distance = Inches(.3)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.line_spacing = 1.05
    normal.paragraph_format.space_after = Pt(4)
    for name, size in (("Heading 1", 12), ("Heading 2", 10.5), ("Heading 3", 10)):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(8)
        style.paragraph_format.space_after = Pt(3)
        style.paragraph_format.keep_with_next = True
    title_style = doc.styles["Title"]
    title_style.font.name = "Arial"
    title_style.font.size = Pt(16)
    title_style.font.bold = True
    title_style.font.color.rgb = RGBColor(0, 0, 0)
    title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_style.paragraph_format.space_after = Pt(8)
    title_ppr = title_style._element.pPr
    if title_ppr is not None:
        border = title_ppr.find(qn("w:pBdr"))
        if border is not None:
            title_ppr.remove(border)
    add_page_number(sec.footer.paragraphs[0])

    raw = SOURCE.read_text(encoding="utf-8").splitlines()
    index = 0
    first_heading = True
    while index < len(raw):
        line = raw[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("| "):
            table_lines = []
            while index < len(raw) and raw[index].strip().startswith("|"):
                table_lines.append(raw[index].strip())
                index += 1
            add_table(doc, table_lines)
            continue
        image_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if image_match:
            image_path = (SOURCE.parent / image_match.group(2)).resolve()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(str(image_path), width=Inches(6.85))
            index += 1
            continue
        if line.startswith("# "):
            if first_heading:
                p = doc.add_paragraph(style="Title")
                p.add_run(line[2:])
                first_heading = False
            else:
                doc.add_heading(line[2:], level=1)
            index += 1
            continue
        if line.startswith("## "):
            heading = doc.add_heading(line[3:], level=1)
            if line == "## References":
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
        if line.startswith(("*Figure ", "*Figure")):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_together = True
            p.paragraph_format.space_after = Pt(7)
            add_inline(p, line.strip("*"))
            for run in p.runs:
                run.italic = True
                run.font.size = Pt(8)
            index += 1
            continue
        p = doc.add_paragraph()
        if line.startswith("Figure "):
            p.paragraph_format.keep_with_next = True
        if line.startswith("**Table I."):
            p.paragraph_format.page_break_before = True
        if line.startswith("**("):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_together = True
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(3)
        if line.startswith("When a baseline is absent"):
            p.paragraph_format.keep_with_next = True
        if line.startswith(("**Darya", "¹ Information", "Contact:")):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(3)
            for run in p.runs:
                run.font.size = Pt(8)
        add_inline(p, line)
        if line.startswith("**Keywords:**"):
            p.paragraph_format.space_after = Pt(8)
        index += 1

    doc.core_properties.title = "Queue-Aware Traffic Signal Phase Control with Image-Based Initial State Estimation"
    doc.core_properties.subject = "Revised research article based on PIERE paired simulation results"
    doc.core_properties.author = "Darya A. Limarenko; Kseniya M. Stegantseva; Elena Yu. Silantyeva"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
