"""Build the judge-ready Compound Zero detailed submission PDF.

The report is intentionally generated from checked-in evidence artifacts. Rerun
this script after refreshing UI screenshots or benchmark JSON files.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, Sequence

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
ASSETS = SUBMISSION / "assets"
OUTPUT = SUBMISSION / "Compound_Zero_Detailed_Submission.pdf"

PAGE_W, PAGE_H = A4
MARGIN = 36
CONTENT_W = PAGE_W - 2 * MARGIN
DOCUMENT_DATE = "22 July 2026"

BG = HexColor("#07110F")
BG_ALT = HexColor("#091512")
CARD = HexColor("#0D1B17")
CARD_2 = HexColor("#10221C")
LINE = HexColor("#1D3A31")
LINE_SOFT = HexColor("#183028")
GREEN = HexColor("#74E7BB")
GREEN_2 = HexColor("#A7F3D0")
AMBER = HexColor("#F5C35B")
ORANGE = HexColor("#FF914D")
RED = HexColor("#FF656D")
BLUE = HexColor("#74B9FF")
WHITE = HexColor("#F3F7F5")
MUTED = HexColor("#94A9A1")
MUTED_2 = HexColor("#667C74")


def load_json(relative: str) -> dict:
    with (ROOT / relative).open("r", encoding="utf-8") as handle:
        return json.load(handle)


METRICS = load_json("artifacts/metrics.json")
ROBUSTNESS = load_json("artifacts/robustness_metrics.json")
GEO = load_json("artifacts/geospatial_metrics.json")
ECON = load_json("artifacts/pilot_economics.json")
MODEL_CARD = load_json("artifacts/model_card.json")


def register_fonts() -> None:
    candidates = {
        "CZ-Regular": [
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ],
        "CZ-Semibold": [
            Path("C:/Windows/Fonts/seguisb.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ],
        "CZ-Bold": [
            Path("C:/Windows/Fonts/segoeuib.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ],
        "CZ-Mono": [
            Path("C:/Windows/Fonts/consola.ttf"),
            Path("C:/Windows/Fonts/cour.ttf"),
        ],
    }
    for name, paths in candidates.items():
        path = next((candidate for candidate in paths if candidate.exists()), None)
        if path is None:
            raise FileNotFoundError(f"No font candidate found for {name}")
        pdfmetrics.registerFont(TTFont(name, str(path)))


def alpha_color(color: Color, alpha: float) -> Color:
    return Color(color.red, color.green, color.blue, alpha=alpha)


def set_fill(c: canvas.Canvas, color: Color) -> None:
    c.setFillColor(color)


def draw_logo(c: canvas.Canvas, x: float, y: float, scale: float = 1.0) -> None:
    c.saveState()
    c.setStrokeColor(GREEN)
    c.setLineWidth(1.5 * scale)
    c.roundRect(x, y, 25 * scale, 25 * scale, 7 * scale, fill=0, stroke=1)
    c.circle(x + 12.5 * scale, y + 12.5 * scale, 6.2 * scale, fill=0, stroke=1)
    c.setStrokeColor(alpha_color(GREEN, 0.55))
    c.line(x + 4 * scale, y + 8 * scale, x + 21 * scale, y + 17 * scale)
    c.line(x + 5 * scale, y + 19 * scale, x + 20 * scale, y + 6 * scale)
    c.restoreState()


def wrap_lines(text: str, width: float, font: str, size: float) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if pdfmetrics.stringWidth(trial, font, size) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            if pdfmetrics.stringWidth(word, font, size) <= width:
                current = word
            else:
                chunk = ""
                for char in word:
                    trial_chunk = chunk + char
                    if pdfmetrics.stringWidth(trial_chunk, font, size) <= width:
                        chunk = trial_chunk
                    else:
                        if chunk:
                            lines.append(chunk)
                        chunk = char
                current = chunk
    if current:
        lines.append(current)
    return lines


def draw_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    *,
    font: str = "CZ-Regular",
    size: float = 9.2,
    leading: float | None = None,
    color: Color = WHITE,
    max_lines: int | None = None,
    align: str = "left",
) -> float:
    leading = leading or size * 1.34
    paragraphs = text.split("\n")
    lines: list[str] = []
    for index, paragraph in enumerate(paragraphs):
        if index and paragraph:
            lines.append("")
        lines.extend(wrap_lines(paragraph, width, font, size))
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        tail = lines[-1]
        while tail and pdfmetrics.stringWidth(tail + "...", font, size) > width:
            tail = tail[:-1]
        lines[-1] = tail.rstrip() + "..."
    c.setFont(font, size)
    c.setFillColor(color)
    for line in lines:
        if align == "center":
            c.drawCentredString(x + width / 2, y, line)
        elif align == "right":
            c.drawRightString(x + width, y, line)
        else:
            c.drawString(x, y, line)
        y -= leading
    return y


def draw_bullet(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    *,
    color: Color = WHITE,
    bullet_color: Color = GREEN,
    size: float = 8.7,
    leading: float = 11.4,
) -> float:
    c.setFillColor(bullet_color)
    c.circle(x + 3, y + 3, 1.9, fill=1, stroke=0)
    lines = wrap_lines(text, width - 15, "CZ-Regular", size)
    c.setFillColor(color)
    c.setFont("CZ-Regular", size)
    for line in lines:
        c.drawString(x + 14, y, line)
        y -= leading
    return y - 3


def draw_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: Color = CARD,
    stroke: Color = LINE,
    radius: float = 10,
) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, width, height, radius, fill=1, stroke=1)


def draw_chip(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    *,
    fill: Color = CARD_2,
    color: Color = GREEN,
    border: Color = LINE,
    font: str = "CZ-Semibold",
    size: float = 7.2,
    pad_x: float = 8,
    height: float = 18,
) -> float:
    width = pdfmetrics.stringWidth(text, font, size) + 2 * pad_x
    c.setFillColor(fill)
    c.setStrokeColor(border)
    c.roundRect(x, y, width, height, height / 2, fill=1, stroke=1)
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x + pad_x, y + (height - size) / 2 + 1.5, text)
    return width


def draw_metric(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    value: str,
    label: str,
    note: str,
    *,
    accent: Color = GREEN,
) -> None:
    draw_card(c, x, y, width, height)
    c.setFillColor(accent)
    c.rect(x, y, 3, height, fill=1, stroke=0)
    c.setFont("CZ-Bold", 21)
    c.setFillColor(WHITE)
    c.drawString(x + 13, y + height - 28, value)
    c.setFont("CZ-Semibold", 7.2)
    c.setFillColor(accent)
    c.drawString(x + 13, y + height - 43, label.upper())
    draw_text(c, note, x + 13, y + 15, width - 24, size=6.8, leading=8.2, color=MUTED, max_lines=2)


def draw_page_header(c: canvas.Canvas, section: str, title: str, subtitle: str, page_no: int) -> float:
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    draw_logo(c, MARGIN, PAGE_H - 49, 0.82)
    c.setFont("CZ-Semibold", 7.5)
    c.setFillColor(GREEN)
    c.drawString(MARGIN + 29, PAGE_H - 35, "COMPOUND ZERO")
    c.setFillColor(MUTED)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 35, f"DETAILED SUBMISSION  /  {page_no:02d}")
    c.setStrokeColor(LINE_SOFT)
    c.line(MARGIN, PAGE_H - 58, PAGE_W - MARGIN, PAGE_H - 58)
    c.setFont("CZ-Mono", 7.3)
    c.setFillColor(GREEN)
    c.drawString(MARGIN, PAGE_H - 82, section.upper())
    title_size = min(27.0, max(19.0, 27.0 * CONTENT_W / max(CONTENT_W, pdfmetrics.stringWidth(title, "CZ-Bold", 27))))
    c.setFont("CZ-Bold", title_size)
    c.setFillColor(WHITE)
    c.drawString(MARGIN, PAGE_H - 116, title)
    draw_text(c, subtitle, MARGIN, PAGE_H - 139, CONTENT_W, size=9.2, leading=12, color=MUTED, max_lines=2)
    return PAGE_H - 166


def draw_footer(c: canvas.Canvas, page_no: int, source_note: str = "") -> None:
    c.setStrokeColor(LINE_SOFT)
    c.line(MARGIN, 31, PAGE_W - MARGIN, 31)
    c.setFont("CZ-Mono", 6.3)
    c.setFillColor(MUTED_2)
    if source_note:
        c.drawString(MARGIN, 18, source_note[:103])
    c.setFillColor(GREEN)
    c.drawRightString(PAGE_W - MARGIN, 18, f"SIMULATED DATA  |  PROTOTYPE  |  NOT FIELD VALIDATION  |  {page_no:02d}")


def draw_section_label(c: canvas.Canvas, text: str, x: float, y: float, color: Color = GREEN) -> None:
    c.setFont("CZ-Mono", 7.2)
    c.setFillColor(color)
    c.drawString(x, y, text.upper())


def draw_image_fit(
    c: canvas.Canvas,
    path: Path,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    crop: str = "contain",
    radius: float = 10,
) -> None:
    if not path.exists():
        draw_card(c, x, y, width, height, fill=CARD_2, stroke=RED, radius=radius)
        draw_text(c, f"Missing screenshot: {path.name}", x + 12, y + height / 2, width - 24, color=RED)
        return
    image = ImageReader(str(path))
    iw, ih = image.getSize()
    scale = min(width / iw, height / ih) if crop == "contain" else max(width / iw, height / ih)
    draw_w, draw_h = iw * scale, ih * scale
    draw_x = x + (width - draw_w) / 2
    draw_y = y + (height - draw_h) / 2
    draw_card(c, x, y, width, height, fill=HexColor("#050B09"), stroke=LINE, radius=radius)
    c.saveState()
    path_clip = c.beginPath()
    path_clip.roundRect(x + 1, y + 1, width - 2, height - 2, max(1, radius - 1))
    c.clipPath(path_clip, stroke=0, fill=0)
    c.drawImage(image, draw_x, draw_y, draw_w, draw_h, preserveAspectRatio=True, mask="auto")
    c.restoreState()
    c.setStrokeColor(LINE)
    c.roundRect(x, y, width, height, radius, fill=0, stroke=1)


def draw_table(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    widths: Sequence[float],
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    row_height: float = 29,
    header_height: float = 28,
    font_size: float = 7.1,
    first_col_bold: bool = True,
    highlight_rows: Iterable[int] = (),
) -> float:
    total_w = sum(widths)
    highlight_set = set(highlight_rows)
    c.setFillColor(CARD_2)
    c.roundRect(x, y_top - header_height, total_w, header_height, 7, fill=1, stroke=0)
    xpos = x
    for width, header in zip(widths, headers):
        c.setFillColor(GREEN)
        c.setFont("CZ-Semibold", 6.4)
        c.drawString(xpos + 7, y_top - 18, header.upper())
        xpos += width
    y = y_top - header_height
    for row_index, row in enumerate(rows):
        y_next = y - row_height
        c.setFillColor(alpha_color(GREEN, 0.08) if row_index in highlight_set else CARD)
        c.rect(x, y_next, total_w, row_height, fill=1, stroke=0)
        c.setStrokeColor(LINE_SOFT)
        c.line(x, y_next, x + total_w, y_next)
        xpos = x
        for col_index, (width, value) in enumerate(zip(widths, row)):
            color = GREEN_2 if row_index in highlight_set else WHITE
            font = "CZ-Semibold" if first_col_bold and col_index == 0 else "CZ-Regular"
            lines = wrap_lines(str(value), width - 12, font, font_size)[:2]
            c.setFont(font, font_size)
            c.setFillColor(color if col_index == 0 else (GREEN if row_index in highlight_set else WHITE))
            line_y = y - 12
            for line in lines:
                c.drawString(xpos + 7, line_y, line)
                line_y -= font_size + 1.6
            xpos += width
        y = y_next
    c.setStrokeColor(LINE)
    c.roundRect(x, y, total_w, header_height + len(rows) * row_height, 7, fill=0, stroke=1)
    return y


def draw_horizontal_bar(
    c: canvas.Canvas,
    label: str,
    value: float,
    max_value: float,
    x: float,
    y: float,
    width: float,
    *,
    color: Color = GREEN,
    value_text: str | None = None,
) -> None:
    c.setFont("CZ-Semibold", 7.4)
    c.setFillColor(WHITE)
    c.drawString(x, y + 5, label)
    track_x = x + 103
    track_w = width - 151
    c.setFillColor(HexColor("#163027"))
    c.roundRect(track_x, y, track_w, 10, 5, fill=1, stroke=0)
    bar_w = max(2, track_w * max(0, min(value / max_value, 1)))
    c.setFillColor(color)
    c.roundRect(track_x, y, bar_w, 10, 5, fill=1, stroke=0)
    c.setFont("CZ-Mono", 7.1)
    c.setFillColor(color)
    c.drawRightString(x + width, y + 3, value_text or f"{value:.2f}")


def draw_arrow(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float, color: Color = LINE) -> None:
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.2)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 5
    left = (x2 - size * math.cos(angle - 0.55), y2 - size * math.sin(angle - 0.55))
    right = (x2 - size * math.cos(angle + 0.55), y2 - size * math.sin(angle + 0.55))
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(*left)
    p.lineTo(*right)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def draw_node(c: canvas.Canvas, x: float, y: float, width: float, height: float, title: str, note: str, accent: Color) -> None:
    draw_card(c, x, y, width, height, fill=CARD, stroke=alpha_color(accent, 0.45), radius=8)
    c.setFillColor(accent)
    c.circle(x + 13, y + height - 14, 3, fill=1, stroke=0)
    c.setFont("CZ-Semibold", 8)
    c.setFillColor(WHITE)
    c.drawString(x + 23, y + height - 18, title)
    draw_text(c, note, x + 11, y + height - 34, width - 22, size=6.7, leading=8.2, color=MUTED, max_lines=3)


def new_page(c: canvas.Canvas, page_no: int, section: str, title: str, subtitle: str) -> float:
    if page_no > 1:
        c.showPage()
    return draw_page_header(c, section, title, subtitle, page_no)


def build_pdf() -> Path:
    register_fonts()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUTPUT), pagesize=A4, pageCompression=1, invariant=1)
    c.setTitle("Compound Zero - Detailed Submission")
    c.setAuthor("Parth Katiyar")
    c.setSubject("ET AI Hackathon 2026 - PS1 detailed submission")
    c.setCreator("Compound Zero reproducible ReportLab build")

    # 01 - Cover
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(alpha_color(GREEN, 0.05))
    c.circle(PAGE_W - 8, PAGE_H - 42, 186, fill=1, stroke=0)
    draw_logo(c, MARGIN, PAGE_H - 68, 1.22)
    c.setFont("CZ-Semibold", 9)
    c.setFillColor(GREEN)
    c.drawString(MARGIN + 42, PAGE_H - 50, "COMPOUND ZERO")
    c.setFont("CZ-Mono", 7.5)
    c.setFillColor(MUTED)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 50, "ET AI HACKATHON 2026  /  PS1")
    c.setFont("CZ-Bold", 42)
    c.setFillColor(WHITE)
    c.drawString(MARGIN, PAGE_H - 139, "See the accident")
    c.setFillColor(GREEN)
    c.drawString(MARGIN, PAGE_H - 185, "before the alarm.")
    draw_text(
        c,
        "A human-gated industrial safety intelligence prototype that turns weak process, permit, barrier and personnel signals into one reviewable risk case.",
        MARGIN,
        PAGE_H - 218,
        455,
        size=11.2,
        leading=15,
        color=MUTED,
        max_lines=3,
    )
    chip_x = MARGIN
    for text_value in ["NO LLM IN RISK PATH", "MANUAL ONLY", "SIMULATED EVIDENCE"]:
        chip_x += draw_chip(c, text_value, chip_x, PAGE_H - 282) + 7
    draw_image_fit(c, ASSETS / "command-t18.png", MARGIN, 171, CONTENT_W, 294, crop="cover", radius=12)
    c.setFillColor(alpha_color(BG, 0.20))
    c.roundRect(MARGIN, 171, CONTENT_W, 294, 12, fill=1, stroke=0)
    draw_card(c, MARGIN + 18, 188, 213, 55, fill=alpha_color(BG_ALT, 0.94), stroke=LINE)
    c.setFont("CZ-Bold", 20)
    c.setFillColor(WHITE)
    c.drawString(MARGIN + 31, 219, "12 min")
    c.setFont("CZ-Semibold", 7)
    c.setFillColor(GREEN)
    c.drawString(MARGIN + 31, 203, "MEDIAN HELD-OUT WARNING LEAD")
    draw_card(c, MARGIN + 242, 188, 263, 55, fill=alpha_color(BG_ALT, 0.94), stroke=LINE)
    c.setFont("CZ-Bold", 20)
    c.setFillColor(WHITE)
    c.drawString(MARGIN + 255, 219, "13 + 52")
    c.setFont("CZ-Semibold", 7)
    c.setFillColor(GREEN)
    c.drawString(MARGIN + 255, 203, "DEVICE-ALARM STRATA REPORTED SEPARATELY")
    c.setFont("CZ-Regular", 8.2)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, 120, "Detailed submission  |  Prepared by Parth Katiyar  |  " + DOCUMENT_DATE)
    c.setFont("CZ-Mono", 6.8)
    c.setFillColor(GREEN)
    c.drawString(MARGIN, 94, "SIMULATED DATA  /  PROTOTYPE  /  NOT FIELD VALIDATION  /  NOT AUTONOMOUS CONTROL")
    c.setStrokeColor(LINE_SOFT)
    c.line(MARGIN, 72, PAGE_W - MARGIN, 72)
    c.setFont("CZ-Regular", 7.3)
    c.setFillColor(MUTED_2)
    c.drawString(MARGIN, 51, "Problem statement: AI-Powered Industrial Safety Intelligence for Zero-Harm Operations")
    c.drawRightString(PAGE_W - MARGIN, 51, "01")

    # 02 - Executive thesis
    y = new_page(
        c,
        2,
        "Executive thesis",
        "One risk case. Five witnesses.",
        "Compound Zero wins on disciplined evidence: an early-warning story judges can see, metrics they can reproduce, and safety limits the product cannot cross.",
    )
    draw_card(c, MARGIN, y - 118, CONTENT_W, 106, fill=CARD_2, stroke=alpha_color(GREEN, 0.45))
    draw_section_label(c, "THE BET", MARGIN + 18, y - 34)
    c.setFont("CZ-Bold", 15.5)
    c.setFillColor(WHITE)
    c.drawString(MARGIN + 18, y - 59, "The blind spot is not missing data.")
    c.setFillColor(GREEN)
    c.drawString(MARGIN + 18, y - 82, "It is missing interaction intelligence.")
    draw_text(
        c,
        "A gas trend below its device threshold can become urgent when extraction is impaired, hot work is active and people enter the same zone. Compound Zero detects that combination before treating any one sensor as decisive.",
        MARGIN + 330,
        y - 37,
        173,
        size=7.6,
        leading=9.6,
        color=MUTED,
        max_lines=6,
    )
    y2 = y - 147
    card_w = (CONTENT_W - 20) / 3
    thesis_cards = [
        ("01", "Inspectability", "Fixed-seed replay, typed factors, raw traces, dataset and model hashes.", GREEN),
        ("02", "Decision safety", "Advisory output, stream-quality abstention and no actuator route.", AMBER),
        ("03", "Transfer honesty", "LOSO exposes a 0% process-drift fold and turns it into a pilot gate.", RED),
    ]
    for index, (number, title, note, accent) in enumerate(thesis_cards):
        x = MARGIN + index * (card_w + 10)
        draw_card(c, x, y2 - 134, card_w, 124)
        c.setFont("CZ-Mono", 7)
        c.setFillColor(accent)
        c.drawString(x + 14, y2 - 30, number)
        c.setFont("CZ-Semibold", 11)
        c.setFillColor(WHITE)
        c.drawString(x + 14, y2 - 53, title)
        draw_text(c, note, x + 14, y2 - 75, card_w - 28, size=7.5, leading=10, color=MUTED, max_lines=5)
    draw_section_label(c, "JUDGING FIT", MARGIN, y2 - 166)
    criteria = [
        ("Innovation", 25, "compound correlation + evidence graph"),
        ("Business impact", 25, "lead time + editable economics"),
        ("Technical excellence", 20, "calibration + robustness + receipts"),
        ("Scalability", 15, "site-local inference + adapter plan"),
        ("User experience", 15, "five coherent operator workspaces"),
    ]
    base_y = y2 - 198
    for idx, (label, weight, note) in enumerate(criteria):
        row_y = base_y - idx * 43
        c.setFont("CZ-Semibold", 8.3)
        c.setFillColor(WHITE)
        c.drawString(MARGIN, row_y + 7, label)
        c.setFont("CZ-Mono", 7)
        c.setFillColor(GREEN)
        c.drawRightString(MARGIN + 116, row_y + 7, f"{weight}%")
        c.setFillColor(HexColor("#142A23"))
        c.roundRect(MARGIN + 130, row_y + 2, 150, 10, 5, fill=1, stroke=0)
        c.setFillColor(GREEN if idx < 3 else BLUE)
        c.roundRect(MARGIN + 130, row_y + 2, 150 * weight / 25, 10, 5, fill=1, stroke=0)
        c.setFont("CZ-Regular", 7.5)
        c.setFillColor(MUTED)
        c.drawString(MARGIN + 298, row_y + 6, note)
    draw_footer(c, 2, "Judging weights from the organiser brief")

    # 03 - PS1 fit
    y = new_page(
        c,
        3,
        "Problem statement fit",
        "The brief, translated into evidence.",
        "The prototype addresses the central compound-risk challenge while keeping every unimplemented connector and production control visible.",
    )
    requirements_rows = [
        ["IoT + SCADA", "Typed signals, trends, quality and fixed-seed replay", "Live historian adapter"],
        ["Permit to work", "Permit context, evidence binding and conflict checks", "Authorized PTW connector"],
        ["CCTV / location", "Anonymous event metadata; zone count and distance", "No raw video or biometrics"],
        ["Shift + maintenance", "Handover and extraction-barrier features", "CMMS / workforce adapters"],
        ["Compound detection", "Calibrated 28-feature full-fusion classifier", "Site calibration"],
        ["Pre-emptive response", "Human-gated dry-run plan and audit receipt", "No field actuation"],
        ["Geospatial layer", "Fictional plant polygons + uncertainty review", "Surveyed site validation"],
        ["Incident intelligence", "Local cited BM25 over 5 authored patterns", "No full regulatory RAG"],
    ]
    y = draw_table(
        c,
        MARGIN,
        y - 4,
        [105, 252, 166],
        ["Brief capability", "Implemented evidence", "Declared boundary"],
        requirements_rows,
        row_height=42,
        header_height=28,
        font_size=7.2,
    )
    draw_card(c, MARGIN, y - 126, CONTENT_W, 108, fill=CARD_2, stroke=alpha_color(AMBER, 0.45))
    draw_section_label(c, "WHY THIS IS CREDIBLE", MARGIN + 16, y - 41, AMBER)
    credibility = [
        "The same persisted model powers API replay and the measured benchmark.",
        "Device-alarm groups and no-device-alarm groups use separate denominators.",
        "The safety case says what is absent: field connectors, identity, durable audit and actuation.",
    ]
    yy = y - 65
    for item in credibility:
        yy = draw_bullet(c, item, MARGIN + 16, yy, CONTENT_W - 32, size=7.8, leading=10.4, bullet_color=AMBER)
    draw_footer(c, 3, "Traceability source: docs/requirements-traceability.md")

    # 04 - Product flow
    y = new_page(
        c,
        4,
        "Product experience",
        "Five workspaces. One safety case.",
        "The interface moves from operating picture to explanation, cross-system evidence, model proof and an exportable safety record.",
    )
    draw_image_fit(c, ASSETS / "command-t18.png", MARGIN, y - 305, CONTENT_W, 294, crop="cover", radius=10)
    stages = [
        ("1", "Replay twin", "See risk, people, permits and lead"),
        ("2", "Why now?", "Inspect typed evidence and traces"),
        ("3", "Intelligence", "Join vision, permits and patterns"),
        ("4", "Model evidence", "Compare baselines and limits"),
        ("5", "Safety case", "Record authority and evidence"),
    ]
    gap = 7
    stage_w = (CONTENT_W - gap * 4) / 5
    base_y = y - 390
    for idx, (num, title, note) in enumerate(stages):
        x = MARGIN + idx * (stage_w + gap)
        draw_card(c, x, base_y - 102, stage_w, 92, fill=CARD)
        c.setFillColor(GREEN)
        c.circle(x + 14, base_y - 28, 8, fill=1, stroke=0)
        c.setFillColor(BG)
        c.setFont("CZ-Bold", 7)
        c.drawCentredString(x + 14, base_y - 30, num)
        c.setFont("CZ-Semibold", 7.6)
        c.setFillColor(WHITE)
        c.drawString(x + 28, base_y - 31, title)
        draw_text(c, note, x + 10, base_y - 53, stage_w - 20, size=6.5, leading=8.2, color=MUTED, max_lines=4)
    draw_card(c, MARGIN, 54, CONTENT_W, 74, fill=CARD_2, stroke=alpha_color(GREEN, 0.4))
    draw_section_label(c, "DESIGN PRINCIPLE", MARGIN + 14, 106)
    c.setFont("CZ-Bold", 13)
    c.setFillColor(WHITE)
    c.drawString(MARGIN + 14, 82, "Explain evidence first. Propose controls second. Keep authority human.")
    draw_footer(c, 4, "UI image: submission/assets/command-t18.png")

    # 05 - Signature replay
    y = new_page(
        c,
        5,
        "Signature replay",
        "A warning while every device alarm is clear.",
        "Seed 24001 is a deterministic demonstration, not a reconstruction of a real incident. Harmful-state timing is authored for evaluation.",
    )
    draw_image_fit(c, ASSETS / "command-t09.png", MARGIN, y - 260, CONTENT_W, 248, crop="cover", radius=10)
    timeline_y = y - 320
    c.setStrokeColor(LINE)
    c.setLineWidth(2)
    c.line(MARGIN + 22, timeline_y, PAGE_W - MARGIN - 22, timeline_y)
    events = [
        (0, "T+00", "Barrier context", "EF-04 maintenance isolation", BLUE),
        (0.24, "T+09", "Early advisory", "Score 30; 13 min lead; 0 alarms", GREEN),
        (0.50, "T+18", "Critical case", "Score 100; 4 workers; 0 alarms", ORANGE),
        (0.73, "T+22", "Authored onset", "Harmful-state boundary", RED),
        (1.0, "DRY RUN", "Permit hold", "Projected 100 to 71; no actuation", AMBER),
    ]
    for pos, stamp, title, note, accent in events:
        xx = MARGIN + 22 + pos * (CONTENT_W - 44)
        c.setFillColor(accent)
        c.circle(xx, timeline_y, 5, fill=1, stroke=0)
        c.setFont("CZ-Mono", 6.7)
        c.drawCentredString(xx, timeline_y + 14, stamp)
        box_w = 88
        box_x = max(MARGIN, min(xx - box_w / 2, PAGE_W - MARGIN - box_w))
        draw_card(c, box_x, timeline_y - 84, box_w, 66, fill=CARD, stroke=alpha_color(accent, 0.35), radius=7)
        c.setFont("CZ-Semibold", 7.4)
        c.setFillColor(WHITE)
        c.drawString(box_x + 8, timeline_y - 38, title)
        draw_text(c, note, box_x + 8, timeline_y - 54, box_w - 16, size=5.9, leading=7.2, color=MUTED, max_lines=3)
    draw_card(c, MARGIN, 72, CONTENT_W, 114, fill=CARD_2, stroke=alpha_color(AMBER, 0.42))
    draw_section_label(c, "COUNTERFACTUAL BOUNDARY", MARGIN + 15, 160, AMBER)
    draw_text(
        c,
        "The permit-hold number is a deterministic scenario projection. It is not a causal estimate, does not preserve the original model probability or lead-time truth, and executes no plant action. The operator records only a dry-run decision.",
        MARGIN + 15,
        136,
        CONTENT_W - 30,
        size=8.1,
        leading=11,
        color=WHITE,
        max_lines=5,
    )
    draw_footer(c, 5, "Scenario: compound_hot_work, seed 24001; SIMULATED")

    # 06 - Architecture
    y = new_page(
        c,
        6,
        "Technical architecture",
        "Numeric risk path, evidence path, authority path.",
        "The model can fail without disabling physical alarms or silently crossing into plant control. Explanation is downstream of the score.",
    )
    lanes = [
        ("OFFLINE EVIDENCE", GREEN, [
            ("ScenarioBench", "9 types x 64 seeds x 48 min"),
            ("Grouped train", "whole-seed split + calibration"),
            ("Artifacts", "model + metrics + SHA-256"),
        ]),
        ("ONLINE RISK", BLUE, [
            ("Typed contract", "levels + trends + context"),
            ("28 features", "interactions + stream quality"),
            ("Calibrated score", "threshold + abstention"),
        ]),
        ("HUMAN AUTHORITY", AMBER, [
            ("Evidence case", "factors + sources + replay"),
            ("Response plan", "role gates, manual only"),
            ("Existing workflow", "operator / permit / SIS"),
        ]),
    ]
    lane_y = y - 108
    for lane_index, (label, accent, nodes) in enumerate(lanes):
        yy = lane_y - lane_index * 151
        draw_section_label(c, label, MARGIN, yy + 85, accent)
        node_w = 151
        node_h = 72
        for node_index, (title, note) in enumerate(nodes):
            xx = MARGIN + node_index * (node_w + 35)
            draw_node(c, xx, yy, node_w, node_h, title, note, accent)
            if node_index < len(nodes) - 1:
                draw_arrow(c, xx + node_w + 4, yy + node_h / 2, xx + node_w + 31, yy + node_h / 2, alpha_color(accent, 0.6))
    draw_card(c, MARGIN, 81, 254, 97, fill=CARD_2, stroke=alpha_color(GREEN, 0.4))
    draw_section_label(c, "IMPLEMENTED NOW", MARGIN + 14, 153)
    yy = 133
    for item in ["FastAPI persisted-model replay", "React five-workspace command center", "Local BM25 + deterministic audit"]:
        yy = draw_bullet(c, item, MARGIN + 14, yy, 224, size=7.2, leading=9.2)
    draw_card(c, MARGIN + 267, 81, 256, 97, fill=CARD_2, stroke=alpha_color(RED, 0.4))
    draw_section_label(c, "HARD BOUNDARY", MARGIN + 281, 153, RED)
    yy = 133
    for item in ["No LLM in scoring or policy", "No actuator client or route", "Physical alarms and SIS stay independent"]:
        yy = draw_bullet(c, item, MARGIN + 281, yy, 226, size=7.2, leading=9.2, bullet_color=RED)
    draw_footer(c, 6, "Architecture source: docs/architecture.md")

    # 07 - Risk engine
    y = new_page(
        c,
        7,
        "Model and data",
        "Reproducible by construction.",
        "The prototype uses calibrated gradient boosting over deterministic simulated replays. No generator or language model participates in the decision path.",
    )
    dataset = METRICS["dataset"]
    split = METRICS["split"]
    metrics_row_y = y - 93
    mw = (CONTENT_W - 24) / 4
    metric_specs = [
        ("27,648", "ROWS", "9 scenario families", GREEN),
        ("576", "REPLAYS", "64 deterministic seeds", BLUE),
        ("5,616", "TEST ROWS", "13 held-out seeds", AMBER),
        ("0", "SPLIT OVERLAP", "train / calibrate / test", GREEN),
    ]
    for idx, spec in enumerate(metric_specs):
        draw_metric(c, MARGIN + idx * (mw + 8), metrics_row_y, mw, 80, *spec[:3], accent=spec[3])
    draw_section_label(c, "FEATURE CONTRACT", MARGIN, metrics_row_y - 31)
    groups = [
        ("Process", "LEL, H2S, CO, oxygen, pressure; levels and slopes"),
        ("Barriers", "ventilation impairment, isolation and stream quality"),
        ("Work context", "hot work, confined space, handover and overlaps"),
        ("Exposure", "worker count, proximity and anonymous event confidence"),
        ("Interactions", "gas x hot work, gas x worker, barrier x gas and more"),
    ]
    yy = metrics_row_y - 59
    for idx, (title, note) in enumerate(groups):
        x = MARGIN + (idx % 2) * 264
        if idx == 4:
            x = MARGIN
        if idx % 2 == 0 and idx > 0:
            yy -= 66
        width = CONTENT_W if idx == 4 else 254
        draw_card(c, x, yy - 50, width, 48, fill=CARD)
        c.setFont("CZ-Semibold", 7.7)
        c.setFillColor(GREEN if idx != 2 else AMBER)
        c.drawString(x + 11, yy - 20, title)
        draw_text(c, note, x + 74, yy - 18, width - 85, size=6.7, leading=8.2, color=MUTED, max_lines=3)
    model_y = yy - 88
    draw_section_label(c, "MODEL RECEIPT", MARGIN, model_y)
    receipt_rows = [
        ["Engine", "Histogram gradient boosting + sigmoid calibration"],
        ["Decision threshold", f"{MODEL_CARD['decision_threshold']:.3f}, selected on calibration only"],
        ["Dataset SHA-256", MODEL_CARD["dataset_sha256"]],
        ["Model SHA-256", MODEL_CARD["model_artifact_sha256"]],
        ["Artifact bytes", f"{MODEL_CARD['model_artifact_bytes']:,}"],
    ]
    draw_table(c, MARGIN, model_y - 14, [126, 397], ["Field", "Recorded value"], receipt_rows, row_height=29, header_height=24, font_size=6.5)
    draw_card(c, MARGIN, 45, CONTENT_W, 60, fill=CARD_2, stroke=alpha_color(AMBER, 0.4))
    draw_text(c, "Joblib artifacts are unsafe if untrusted. The API verifies the expected SHA-256 before deserialization; production still requires a signed registry and restricted write path.", MARGIN + 14, 82, CONTENT_W - 28, size=7.2, leading=9.2, color=WHITE, max_lines=4)
    draw_footer(c, 7, f"Dataset fingerprint: {dataset['sha256'][:18]}...  |  model_card.json")

    # 08 - Quantitative evidence
    y = new_page(
        c,
        8,
        "Held-out evidence",
        "Context closes the blind spot.",
        "The test split contains 5,616 rows and 65 event replays. Results are reproducible on authored simulated scenarios and are not a field-performance claim.",
    )
    methods = METRICS["methods"]
    table_rows = []
    for key, label in [("single_sensor", "Single sensor"), ("process_only", "Process only"), ("full_fusion", "Full fusion")]:
        event = methods[key]["event"]
        row = methods[key]["row"]
        table_rows.append([
            label,
            f"{event['event_recall'] * 100:.1f}%",
            f"{event['event_false_negative_rate'] * 100:.1f}%",
            f"{event['median_warning_lead_minutes']:.0f} min",
            f"{event['false_alarm_episodes_per_24h']:.2f}",
            f"{row['average_precision']:.3f}",
            f"{row['brier_score']:.3f}",
        ])
    y_table = draw_table(c, MARGIN, y - 2, [111, 63, 58, 62, 83, 72, 74], ["Method", "Event recall", "Event FNR", "Lead", "FA / 24 h", "Row AP", "Brier"], table_rows, row_height=39, header_height=32, font_size=7.0, highlight_rows=[2])
    draw_section_label(c, "EVENT RECALL", MARGIN, y_table - 34)
    bars_y = y_table - 65
    draw_horizontal_bar(c, "Single sensor", 0.2, 1.0, MARGIN, bars_y, CONTENT_W, color=MUTED, value_text="20%")
    draw_horizontal_bar(c, "Process only", 1.0, 1.0, MARGIN, bars_y - 34, CONTENT_W, color=AMBER, value_text="100%")
    draw_horizontal_bar(c, "Full fusion", 1.0, 1.0, MARGIN, bars_y - 68, CONTENT_W, color=GREEN, value_text="100%")
    insight_y = bars_y - 105
    draw_card(c, MARGIN, insight_y - 101, 252, 91, fill=CARD_2, stroke=alpha_color(GREEN, 0.42))
    draw_section_label(c, "FALSE-NEGATIVE DELTA", MARGIN + 14, insight_y - 33)
    c.setFont("CZ-Bold", 25)
    c.setFillColor(GREEN)
    c.drawString(MARGIN + 14, insight_y - 66, "-80 pp")
    draw_text(c, "Full fusion versus device baseline at event level.", MARGIN + 115, insight_y - 45, 122, size=7.2, leading=9.2, color=MUTED, max_lines=4)
    draw_card(c, MARGIN + 271, insight_y - 101, 252, 91, fill=CARD_2, stroke=alpha_color(GREEN, 0.42))
    draw_section_label(c, "FALSE-ALARM DELTA", MARGIN + 285, insight_y - 33)
    c.setFont("CZ-Bold", 25)
    c.setFillColor(GREEN)
    c.drawString(MARGIN + 285, insight_y - 66, "-86.7%")
    draw_text(c, "Full fusion versus process-only episodes per simulated 24 h.", MARGIN + 395, insight_y - 45, 127, size=7.2, leading=9.2, color=MUTED, max_lines=4)
    draw_card(c, MARGIN, 66, CONTENT_W, 82, fill=CARD, stroke=alpha_color(AMBER, 0.35))
    draw_text(c, "Interpretation: ablation supports the compound-risk hypothesis inside ScenarioBench. The result does not establish site transfer, operational utility, safe alert thresholds or real incident prevention.", MARGIN + 14, 119, CONTENT_W - 28, size=7.6, leading=10.2, color=WHITE, max_lines=4)
    draw_footer(c, 8, "Direct source: artifacts/metrics.json")

    # 09 - Device strata
    y = new_page(
        c,
        9,
        "Baseline comparison",
        "Never fold 'no device alarm' into 'earlier'.",
        "The comparison window ends at each authored harmful-state onset. Two different questions therefore use two different denominators.",
    )
    cx = PAGE_W / 2
    c.setStrokeColor(LINE)
    c.setLineWidth(1.2)
    c.line(cx, y - 20, cx, y - 325)
    draw_section_label(c, "STRATUM A", MARGIN, y - 28, GREEN)
    c.setFont("CZ-Bold", 30)
    c.setFillColor(WHITE)
    c.drawString(MARGIN, y - 69, "13 / 13")
    c.setFont("CZ-Semibold", 11)
    c.setFillColor(GREEN)
    c.drawString(MARGIN, y - 94, "DETECTED BEFORE DEVICE ALARM")
    draw_text(c, "Only event replays where a device alarm exists by harmful-state onset belong in this denominator.", MARGIN, y - 120, 228, size=8.1, leading=10.8, color=MUTED, max_lines=5)
    draw_horizontal_bar(c, "Full fusion", 13, 13, MARGIN, y - 194, 225, color=GREEN, value_text="100%")
    draw_horizontal_bar(c, "Device baseline", 0, 13, MARGIN, y - 230, 225, color=MUTED, value_text="0% earlier")
    draw_section_label(c, "STRATUM B", cx + 19, y - 28, AMBER)
    c.setFont("CZ-Bold", 30)
    c.setFillColor(WHITE)
    c.drawString(cx + 19, y - 69, "52 / 52")
    c.setFont("CZ-Semibold", 11)
    c.setFillColor(AMBER)
    c.drawString(cx + 19, y - 94, "DETECTED WITH NO DEVICE ALARM")
    draw_text(c, "These event replays have no device alarm by onset. They answer detection, not earlier-than-device timing.", cx + 19, y - 120, 228, size=8.1, leading=10.8, color=MUTED, max_lines=5)
    draw_horizontal_bar(c, "Full fusion", 52, 52, cx + 19, y - 194, 225, color=AMBER, value_text="100%")
    draw_horizontal_bar(c, "Device baseline", 0, 52, cx + 19, y - 230, 225, color=MUTED, value_text="0 detected")
    draw_card(c, MARGIN, y - 443, CONTENT_W, 91, fill=CARD_2, stroke=alpha_color(GREEN, 0.45))
    draw_section_label(c, "WHY THIS MATTERS", MARGIN + 15, y - 380)
    draw_text(c, "A folded rate would overstate the comparison by calling an absent device alarm a timing win. Compound Zero reports the 13 comparable groups and 52 no-alarm groups separately, then shows the device baseline's 13 / 65 event recall.", MARGIN + 15, y - 404, CONTENT_W - 30, size=8.1, leading=10.8, color=WHITE, max_lines=5)
    draw_card(c, MARGIN, 73, CONTENT_W, 111, fill=CARD, stroke=alpha_color(AMBER, 0.35))
    draw_section_label(c, "DENOMINATOR RECEIPT", MARGIN + 15, 157, AMBER)
    draw_text(c, "65 authored event groups = 13 with a device alarm by onset + 52 without one. Full fusion detects 65 / 65; the single-device rule detects 13 / 65. These are simulated group-level results.", MARGIN + 15, 133, CONTENT_W - 30, size=8.2, leading=11, color=WHITE, max_lines=5)
    draw_footer(c, 9, "Direct source: metrics.json / methods.*.event")

    # 10 - Robustness
    y = new_page(
        c,
        10,
        "Robustness and limits",
        "The failure we found matters.",
        "A frozen-model stress suite and true scenario-type holdout reveal where the strong base split does not transfer.",
    )
    base_eval = ROBUSTNESS["stress_suite"]["cases"]["baseline"]["evaluation"]
    loso = ROBUSTNESS["leave_one_scenario_type_out"]["event_fold_recall_summary"]
    metric_y = y - 93
    rw = (CONTENT_W - 16) / 3
    draw_metric(c, MARGIN, metric_y, rw, 80, "100%", "BASE EVENT RECALL", "65 held-out simulated events", accent=GREEN)
    draw_metric(c, MARGIN + rw + 8, metric_y, rw, 80, "0.006", "BASE ECE", "10 equal-width probability bins", accent=BLUE)
    draw_metric(c, MARGIN + 2 * (rw + 8), metric_y, rw, 80, "80%", "LOSO MACRO RECALL", "5 event-bearing scenario folds", accent=AMBER)
    draw_section_label(c, "LEAVE-ONE-SCENARIO-TYPE-OUT", MARGIN, metric_y - 31)
    fold_rows = [[name.replace("_", " "), f"{value * 100:.0f}%", "Unseen scenario family"] for name, value in loso["by_scenario_type"].items()]
    table_end = draw_table(c, MARGIN, metric_y - 43, [255, 90, 178], ["Held-out scenario type", "Event recall", "Training relation"], fold_rows, row_height=32, header_height=26, font_size=7.0, highlight_rows=[4])
    draw_card(c, MARGIN, table_end - 105, CONTENT_W, 89, fill=alpha_color(RED, 0.07), stroke=alpha_color(RED, 0.65))
    draw_section_label(c, "FAILURE: PROCESS_DRIFT = 0%", MARGIN + 15, table_end - 42, RED)
    draw_text(c, "The model misses the event-bearing process_drift family when that entire family is absent from training. This blocks any transfer claim and makes unseen operating modes, local drift and shadow-mode replay mandatory pilot gates.", MARGIN + 15, table_end - 66, CONTENT_W - 30, size=7.8, leading=10.4, color=WHITE, max_lines=5)
    draw_section_label(c, "FROZEN-MODEL STRESS", MARGIN, table_end - 134)
    stress_cases = ROBUSTNESS["stress_suite"]["cases"]
    stress_rows = []
    selected_stress = [
        ("baseline", "Baseline"),
        ("missing__barrier_and_shift_stream", "Barrier + shift missing"),
        ("missing__process_sensor_stream", "Process stream missing"),
        ("missing__process_sensor_packet_dropout_20pct", "20% packet dropout"),
        ("sensor_noise__gaussian_sigma_0_05", "Sensor noise sigma 0.05"),
    ]
    for key, label in selected_stress:
        event = stress_cases[key]["evaluation"]["event"]
        stress_rows.append([label, f"{event['event_recall'] * 100:.0f}%", f"{event['median_warning_lead_minutes']:.0f} min", f"{event['false_alarm_episodes_per_24h']:.2f}"])
    draw_table(c, MARGIN, table_end - 146, [247, 83, 87, 106], ["Stress", "Recall", "Median lead", "FA / 24 h"], stress_rows, row_height=29, header_height=25, font_size=6.8, highlight_rows=[1, 2])
    draw_footer(c, 10, "Direct source: artifacts/robustness_metrics.json")

    # 11 - Geospatial benchmark
    y = new_page(
        c,
        11,
        "Geospatial evidence",
        "Uncertainty becomes review, not false precision.",
        "GeoEvidenceBench tests fictional site-local polygons and nearest authored hazards on a boundary-heavy software-conformance fixture.",
    )
    # Stylized geometry panel.
    draw_card(c, MARGIN, y - 272, 254, 258, fill=HexColor("#081511"), stroke=LINE)
    draw_section_label(c, "FICTIONAL PLANT-LOCAL METRES", MARGIN + 14, y - 38)
    c.setStrokeColor(LINE_SOFT)
    for gx in range(7):
        xx = MARGIN + 18 + gx * 34
        c.line(xx, y - 250, xx, y - 54)
    for gy in range(7):
        yy = y - 60 - gy * 31
        c.line(MARGIN + 18, yy, MARGIN + 237, yy)
    zones = [
        (MARGIN + 40, y - 140, 77, 61, GREEN, "C7"),
        (MARGIN + 129, y - 116, 75, 47, AMBER, "C4"),
        (MARGIN + 95, y - 223, 92, 54, BLUE, "M1"),
    ]
    for zx, zy, zw, zh, color, label in zones:
        c.setFillColor(alpha_color(color, 0.09))
        c.setStrokeColor(alpha_color(color, 0.75))
        c.roundRect(zx, zy, zw, zh, 8, fill=1, stroke=1)
        c.setFillColor(color)
        c.setFont("CZ-Mono", 6.7)
        c.drawString(zx + 7, zy + zh - 13, label)
    hx, hy = MARGIN + 118, y - 154
    c.setStrokeColor(RED)
    c.setLineWidth(1.2)
    c.circle(hx, hy, 10, fill=0, stroke=1)
    c.line(hx - 4, hy, hx + 4, hy)
    c.line(hx, hy - 4, hx, hy + 4)
    c.setFillColor(alpha_color(AMBER, 0.11))
    c.setStrokeColor(alpha_color(AMBER, 0.45))
    c.circle(hx + 24, hy + 16, 33, fill=1, stroke=1)
    c.setFillColor(AMBER)
    c.circle(hx + 24, hy + 16, 4, fill=1, stroke=0)
    c.setFont("CZ-Regular", 6.5)
    c.setFillColor(MUTED)
    c.drawString(MARGIN + 23, y - 260, "Declared error bound routes boundary overlap to human review.")
    panel_x = MARGIN + 270
    draw_metric(c, panel_x, y - 83, 253, 69, "337", "SIMULATED CASES", "141 positive / 196 negative", accent=GREEN)
    draw_metric(c, panel_x, y - 160, 253, 69, "0.907 m", "DISTANCE MAE", "p95 absolute error 2.255 m", accent=BLUE)
    draw_metric(c, panel_x, y - 237, 253, 69, "1.000", "CERTAIN-EXPOSURE PRECISION", "on this authored fixture", accent=AMBER)
    draw_section_label(c, "CLASSIFICATION TRADE-OFF", MARGIN, y - 306)
    geo_rows = [
        ["Point estimate", f"{GEO['methods']['point_estimate_baseline']['recall']:.3f}", f"{GEO['methods']['point_estimate_baseline']['false_negative_rate']:.3f}", f"{GEO['methods']['point_estimate_baseline']['false_positive_rate']:.3f}", "Decide from reported point"],
        ["Uncertainty review", f"{GEO['methods']['uncertainty_aware_review']['recall']:.3f}", f"{GEO['methods']['uncertainty_aware_review']['false_negative_rate']:.3f}", f"{GEO['methods']['uncertainty_aware_review']['false_positive_rate']:.3f}", "Route possible overlap"],
    ]
    table_end = draw_table(c, MARGIN, y - 319, [136, 72, 72, 72, 171], ["Method", "Recall", "FNR", "FPR", "Policy"], geo_rows, row_height=38, header_height=27, font_size=7.0, highlight_rows=[1])
    draw_card(c, MARGIN, table_end - 123, CONTENT_W, 105, fill=CARD_2, stroke=alpha_color(AMBER, 0.4))
    draw_section_label(c, "BOUNDARY", MARGIN + 14, table_end - 48, AMBER)
    draw_text(c, "Review recall rises from 0.816 to 1.000 while false-positive review rate rises from 0.168 to 0.454. That is workload, not hidden accuracy. No surveyed coordinates, plume physics, representative prevalence or field geospatial performance is claimed.", MARGIN + 14, table_end - 72, CONTENT_W - 28, size=7.6, leading=10.1, color=WHITE, max_lines=5)
    draw_footer(c, 11, "Direct source: artifacts/geospatial_metrics.json")

    # 12 - Explainability and intelligence
    y = new_page(
        c,
        12,
        "Evidence experience",
        "Weak facts become one reviewable case.",
        "Structured factors, timestamps and typed edges give an operator a path from score to source without pretending feature contribution is causality.",
    )
    draw_image_fit(c, ASSETS / "evidence-t18.png", MARGIN, y - 296, CONTENT_W, 284, crop="cover", radius=10)
    draw_card(c, MARGIN, y - 392, 252, 77, fill=CARD_2, stroke=alpha_color(GREEN, 0.4))
    draw_section_label(c, "WHAT IS SHOWN", MARGIN + 14, y - 341)
    draw_text(c, "Sensor, permit, asset, people and policy evidence with typed relationships and source timestamps.", MARGIN + 14, y - 364, 224, size=7.4, leading=9.6, color=WHITE, max_lines=4)
    draw_card(c, MARGIN + 271, y - 392, 252, 77, fill=CARD_2, stroke=alpha_color(AMBER, 0.4))
    draw_section_label(c, "WHAT IS NOT SHOWN", MARGIN + 285, y - 341, AMBER)
    draw_text(c, "No causal SHAP claim, opaque narrative, legal conclusion or language-model decision.", MARGIN + 285, y - 364, 224, size=7.4, leading=9.6, color=WHITE, max_lines=4)
    draw_section_label(c, "CROSS-SYSTEM INTELLIGENCE", MARGIN, y - 428)
    service_specs = [
        ("Observe", "Anonymous CCTV event metadata only", GREEN),
        ("Correlate", "Numeric fusion, no raw frames", BLUE),
        ("Interrogate", "Local cited BM25, no generator", AMBER),
        ("Authorize", "Role-gated manual response", ORANGE),
    ]
    sw = (CONTENT_W - 21) / 4
    for idx, (title, note, accent) in enumerate(service_specs):
        x = MARGIN + idx * (sw + 7)
        draw_card(c, x, 66, sw, 113, fill=CARD)
        c.setFillColor(accent)
        c.circle(x + 15, 157, 5, fill=1, stroke=0)
        c.setFont("CZ-Semibold", 8.3)
        c.setFillColor(WHITE)
        c.drawString(x + 27, 153, title)
        draw_text(c, note, x + 11, 128, sw - 22, size=6.7, leading=8.4, color=MUTED, max_lines=5)
    draw_footer(c, 12, "UI image: submission/assets/evidence-t18.png")

    # 13 - Human authority
    y = new_page(
        c,
        13,
        "Safety and authority",
        "Machine proposes. People authorize.",
        "Consequence determines the role gate. Every prototype action remains a record or browser dry run; no equipment, access-control or emergency system is invoked.",
    )
    draw_image_fit(c, ASSETS / "response-studio.png", MARGIN, y - 238, CONTENT_W, 225, crop="cover", radius=10)
    draw_section_label(c, "AUTHORITY LADDER", MARGIN, y - 273)
    ladder_rows = [
        ["Advisory display", "May notify", "No physical-world change"],
        ["Permit hold", "Permit authority", "Reversible workflow; prototype dry run"],
        ["Evacuation", "Incident command", "Existing emergency procedure"],
        ["Process isolation", "Dual authorization", "Existing control system only"],
        ["Shutdown / interlock", "SIS / operations", "Not implemented; remains independent"],
    ]
    table_end = draw_table(c, MARGIN, y - 286, [151, 143, 229], ["Action class", "Required authority", "Prototype / production boundary"], ladder_rows, row_height=36, header_height=27, font_size=6.9, highlight_rows=[1])
    draw_card(c, MARGIN, table_end - 103, 255, 84, fill=CARD_2, stroke=alpha_color(GREEN, 0.4))
    draw_section_label(c, "SAFE FAILURE", MARGIN + 14, table_end - 45)
    draw_text(c, "Stream quality below 0.80 causes abstention and suppresses model prediction. Existing alarms never depend on the AI path.", MARGIN + 14, table_end - 67, 227, size=7.2, leading=9.3, color=WHITE, max_lines=4)
    draw_card(c, MARGIN + 269, table_end - 103, 254, 84, fill=CARD_2, stroke=alpha_color(RED, 0.4))
    draw_section_label(c, "CURRENT GAP", MARGIN + 283, table_end - 45, RED)
    draw_text(c, "No SSO, durable signed ledger, TLS, live connector, production freshness policy or tested failover exists yet.", MARGIN + 283, table_end - 67, 226, size=7.2, leading=9.3, color=WHITE, max_lines=4)
    draw_footer(c, 13, "Safety case source: docs/security-safety.md")

    # 14 - Current law advisory mapping
    y = new_page(
        c,
        14,
        "Current-law advisory map",
        "Navigation aids, never a compliance verdict.",
        "The map uses current central primary sources as of 22 July 2026. Applicability, state rules and sector obligations require a qualified owner with authorized text.",
    )
    legal_rows = [
        ["OSH&WC Code s18 + Second Schedule", "Safety standards; items 16, 18 and 23 cover dangerous fumes/gases, explosive atmospheres and danger prohibition", "Evidence categories only"],
        ["OSH&WC Code s84", "Hazard information, measures for hazardous substances and on-site emergency planning for covered hazardous-process factories", "Supports evidence completeness"],
        ["OSH&WC Code s89", "Worker notice of imminent danger and immediate remedial action / referral route", "Supports escalation design"],
        ["First Schedule", "Includes integrated steel, coke/fuel-gas and highly flammable gas industries", "Applicability remains site-specific"],
        ["Central Rules, 2026", "G.S.R. 345(E), 8 May 2026; effective on Gazette publication", "Current central rules reference"],
        ["OISD-STD-105 catalogue", "Public metadata for work permit system", "Normative text not bundled"],
    ]
    table_end = draw_table(c, MARGIN, y - 2, [138, 260, 125], ["Primary reference", "Advisory mapping", "Boundary"], legal_rows, row_height=57, header_height=30, font_size=6.6)
    draw_card(c, MARGIN, table_end - 131, CONTENT_W, 113, fill=alpha_color(AMBER, 0.06), stroke=alpha_color(AMBER, 0.55))
    draw_section_label(c, "IMPORTANT PTW LIMIT", MARGIN + 14, table_end - 45, AMBER)
    draw_text(
        c,
        "A text review of the 2026 Central Rules identified no general central rule explicitly labelled 'hot work', 'work permit' or 'permit to work'. This is not a legal conclusion. State rules, site procedures, sector regulations, licence conditions and authorized OISD standards may govern the work.",
        MARGIN + 14,
        table_end - 69,
        CONTENT_W - 28,
        size=7.5,
        leading=10,
        color=WHITE,
        max_lines=6,
    )
    links = [
        ("OSH&WC Code, 2020", "https://labour.gov.in/sites/default/files/osh_gazette.pdf"),
        ("Commencement S.O. 5321(E), 21 Nov 2025", "https://labour.gov.in/sites/default/files/e-noti-osh-1.pdf"),
        ("OSH&WC Central Rules, 2026 - G.S.R. 345(E)", "https://www.labour.gov.in/static/uploads/2026/05/ee246f790cad0b8e99c3828f34fa09a6.pdf"),
    ]
    link_y = 82
    for label, url in links:
        c.setFont("CZ-Semibold", 6.8)
        c.setFillColor(GREEN)
        c.drawString(MARGIN, link_y, label)
        width = pdfmetrics.stringWidth(label, "CZ-Semibold", 6.8)
        c.linkURL(url, (MARGIN, link_y - 2, MARGIN + width, link_y + 8), relative=0)
        link_y -= 16
    draw_footer(c, 14, "Not legal advice, certification or conformity assessment")

    # 15 - Pilot economics
    y = new_page(
        c,
        15,
        "Pilot economics",
        "A sensitivity model that is allowed to fail.",
        "The editable low/base/high cases value workflow capacity and nuisance-hold exposure only. They exclude human harm and prevented-incident valuation.",
    )
    econ_results = {item["scenario"]: item for item in ECON["results"]}
    econ_rows = []
    for key in ["low", "base", "high"]:
        item = econ_results[key]
        benefit = item["annualized_quantified_benefit"]["realized_total_inr"]
        indicators = item["costs_and_indicators"]
        payback = indicators["simple_payback_months"]
        econ_rows.append([
            key.title(),
            f"INR {benefit:,.0f}",
            f"INR {indicators['annual_net_after_operating_cost_inr']:,.0f}",
            "Not reached" if payback is None else f"{payback:.1f} mo",
            f"{indicators['undiscounted_benefit_cost_ratio']:.2f}",
        ])
    table_end = draw_table(c, MARGIN, y - 2, [74, 126, 127, 102, 94], ["Case", "Annual benefit", "Net after OpEx", "Payback", "3-year BCR"], econ_rows, row_height=43, header_height=30, font_size=7.1, highlight_rows=[1])
    draw_section_label(c, "BASE-CASE COMPONENTS", MARGIN, table_end - 35)
    base = econ_results["base"]
    components = base["annualized_quantified_benefit"]["realized_components_inr"]
    labels = [
        ("Permit reconciliation", components["permit_reconciliation_capacity_inr"], GREEN),
        ("Alert triage", components["alert_triage_capacity_inr"], BLUE),
        ("False-alarm review", components["false_alarm_deep_review_capacity_inr"], AMBER),
        ("Investigation", components["investigation_capacity_inr"], ORANGE),
        ("Nuisance holds", components["nuisance_downtime_exposure_inr"], RED),
    ]
    max_component = max(value for _, value, _ in labels)
    bars_y = table_end - 70
    for idx, (label, value, accent) in enumerate(labels):
        draw_horizontal_bar(c, label, value, max_component, MARGIN, bars_y - idx * 34, CONTENT_W, color=accent, value_text=f"INR {value / 1000:.0f}k")
    draw_card(c, MARGIN, 71, CONTENT_W, 124, fill=CARD_2, stroke=alpha_color(AMBER, 0.45))
    draw_section_label(c, "ETHICAL AND FINANCE BOUNDARY", MARGIN + 14, 169, AMBER)
    boundaries = [
        "No value is assigned to injury, death, catastrophic loss or a prevented incident.",
        "Benefits are illustrative capacity and nuisance-downtime exposure, not guaranteed cash savings.",
        "The low case does not pay back; the high case is an upside bound, not a forecast.",
    ]
    yy = 147
    for item in boundaries:
        yy = draw_bullet(c, item, MARGIN + 14, yy, CONTENT_W - 28, size=7.4, leading=9.6, bullet_color=AMBER)
    draw_footer(c, 15, "Direct source: artifacts/pilot_economics.json")

    # 16 - Scale and pilot
    y = new_page(
        c,
        16,
        "Scalability and pilot",
        "Ninety days to earn the right to continue.",
        "The next phase is a read-only shadow pilot with measurable stop conditions, not a shortcut from prototype to production control.",
    )
    phases = [
        ("01", "Weeks 0-2", "Discover", ["Hazard register + owners", "Data contracts + retention", "Baseline alert burden"]),
        ("02", "Weeks 3-5", "Connect read-only", ["Historian / PTW / CMMS", "Event-time + freshness", "Signed source receipts"]),
        ("03", "Weeks 6-9", "Shadow and calibrate", ["No operator action", "Local replay + thresholds", "Drift / missingness tests"]),
        ("04", "Weeks 10-13", "Tabletop and decide", ["Human factors exercise", "Safe degraded mode", "Proceed / revise / stop"]),
    ]
    pw = (CONTENT_W - 27) / 4
    top_y = y - 171
    for idx, (num, period, title, bullets) in enumerate(phases):
        x = MARGIN + idx * (pw + 9)
        draw_card(c, x, top_y, pw, 157, fill=CARD, stroke=alpha_color(GREEN if idx < 3 else AMBER, 0.38))
        c.setFont("CZ-Mono", 7)
        c.setFillColor(GREEN if idx < 3 else AMBER)
        c.drawString(x + 12, top_y + 132, num)
        c.setFont("CZ-Semibold", 7.2)
        c.setFillColor(MUTED)
        c.drawRightString(x + pw - 12, top_y + 132, period)
        c.setFont("CZ-Bold", 11)
        c.setFillColor(WHITE)
        c.drawString(x + 12, top_y + 105, title)
        yy = top_y + 81
        for item in bullets:
            yy = draw_bullet(c, item, x + 12, yy, pw - 24, size=6.6, leading=8.3, bullet_color=GREEN if idx < 3 else AMBER)
    draw_section_label(c, "TARGET DEPLOYMENT SHAPE", MARGIN, top_y - 35)
    nodes = [
        ("OT sources", "read-only adapters", BLUE),
        ("Site edge", "event time + quality", GREEN),
        ("Risk service", "signed local model", GREEN),
        ("Evidence store", "durable + redacted", AMBER),
        ("Human workflow", "RBAC + dual control", ORANGE),
    ]
    nw = 88
    node_y = top_y - 142
    for idx, (title, note, accent) in enumerate(nodes):
        x = MARGIN + idx * 107
        draw_node(c, x, node_y, nw, 72, title, note, accent)
        if idx < len(nodes) - 1:
            draw_arrow(c, x + nw + 4, node_y + 36, x + 103, node_y + 36, LINE)
    draw_card(c, MARGIN, 66, CONTENT_W, 115, fill=CARD_2, stroke=alpha_color(RED, 0.42))
    draw_section_label(c, "FIELD GATES", MARGIN + 14, 154, RED)
    gates = [
        "Process-drift family and local operating modes must pass held-out shadow replay.",
        "Alarm burden under dropout / noise must stay inside an owner-approved budget.",
        "AI failure must not alter detector, SIS, permit or emergency authority.",
    ]
    yy = 132
    for item in gates:
        yy = draw_bullet(c, item, MARGIN + 14, yy, CONTENT_W - 28, size=7.4, leading=9.5, bullet_color=RED)
    draw_footer(c, 16, "Pilot target: read-only, site-local, human-gated shadow mode")

    # 17 - Requirements and judging matrix
    y = new_page(
        c,
        17,
        "Submission traceability",
        "Every judging criterion has an artifact.",
        "This matrix points judges to inspectable evidence and names the proof still required before any field claim.",
    )
    judge_rows = [
        ["Innovation 25%", "Interaction model, typed evidence graph, uncertainty review, human authority", "Replay twin; Why now?; Intelligence"],
        ["Business impact 25%", "12 min simulated median lead; workflow sensitivity model", "metrics.json; pilot_economics.json"],
        ["Technical excellence 20%", "Whole-seed split, calibration, model hash, LOSO, stress suite", "model_card.json; robustness_metrics.json"],
        ["Scalability 15%", "Stateless inference base, site-local target, read-only adapter plan", "architecture.md; Docker / CI"],
        ["User experience 15%", "Five workspaces, deterministic replay, evidence export and dry-run studio", "apps/web; demo video"],
    ]
    table_end = draw_table(c, MARGIN, y - 2, [121, 263, 139], ["Criterion", "Implemented evidence", "Where to inspect"], judge_rows, row_height=50, header_height=28, font_size=6.6)
    draw_section_label(c, "EVALUATION FOCUS", MARGIN, table_end - 35)
    focus_rows = [
        ["Compound detection", "Full fusion recall 1.00 vs device 0.20", "Simulated held-out event groups"],
        ["Lead time", "12 min vs device 5 min", "Authored harmful-state timing"],
        ["Geospatial", "Review recall 1.00; certain precision 1.00", "Boundary-heavy conformance only"],
        ["Regulatory coverage", "Current-law advisory map", "No control-by-control assessment"],
        ["False negatives", "0.80 absolute event-FNR reduction", "Not site-transfer evidence"],
    ]
    draw_table(c, MARGIN, table_end - 44, [151, 205, 167], ["Focus", "Measured / implemented", "Boundary"], focus_rows, row_height=31, header_height=25, font_size=6.5, highlight_rows=[0, 4])
    draw_card(c, MARGIN, 53, CONTENT_W, 74, fill=CARD_2, stroke=alpha_color(GREEN, 0.38))
    draw_text(c, "Deliverables: working prototype, architecture diagram, presentation deck, detailed document and demo-video production package. The repository is the verification surface; this report is a map, not a substitute for inspection.", MARGIN + 14, 101, CONTENT_W - 28, size=7.2, leading=9.2, color=WHITE, max_lines=5)
    draw_footer(c, 17, "Requirements source: organiser brief + docs/requirements-traceability.md")

    # 18 - Boundaries and evidence index
    y = new_page(
        c,
        18,
        "Claim boundaries and evidence",
        "Strong enough to inspect. Honest enough to trust.",
        "The project distinguishes what exists now, what is simulated, and what a qualified site owner must validate next.",
    )
    draw_section_label(c, "NOT CLAIMED", MARGIN, y - 12, RED)
    not_claimed = [
        "Field-validated or certified safety performance.",
        "Autonomous evacuation, shutdown, isolation, interlock or permit authority.",
        "Live SCADA, PTW, CMMS, worker-location or raw CCTV integration.",
        "A complete legal / OISD corpus or a compliance determination.",
        "A causal intervention estimate, plume model or surveyed plant geometry.",
        "Guaranteed ROI, prevented incidents or monetary valuation of human harm.",
    ]
    left_y = y - 42
    for item in not_claimed:
        left_y = draw_bullet(c, item, MARGIN, left_y, 244, size=7.5, leading=9.8, bullet_color=RED)
    draw_section_label(c, "CHECKED-IN EVIDENCE", MARGIN + 278, y - 12)
    evidence_paths = [
        "artifacts/metrics.json",
        "artifacts/robustness_metrics.json",
        "artifacts/geospatial_metrics.json",
        "artifacts/pilot_economics.json",
        "artifacts/model_card.json",
        "data/scenario_bench/metadata.json",
        "docs/security-safety.md",
        "docs/requirements-traceability.md",
    ]
    right_y = y - 42
    for item in evidence_paths:
        c.setFont("CZ-Mono", 7.1)
        c.setFillColor(GREEN)
        c.drawString(MARGIN + 278, right_y, item)
        right_y -= 22
    draw_card(c, MARGIN, y - 350, CONTENT_W, 103, fill=CARD_2, stroke=alpha_color(GREEN, 0.42))
    draw_section_label(c, "REPRODUCE", MARGIN + 14, y - 276)
    commands = [
        "python -m ml.train",
        "python -m ml.robustness_bench --output artifacts/robustness_metrics.json",
        "python -m ml.geospatial_bench --output artifacts/geospatial_metrics.json",
        "python -m ml.pilot_economics --output artifacts/pilot_economics.json",
        "python -m pytest -q  |  pnpm test  |  pnpm typecheck  |  pnpm build",
    ]
    command_y = y - 300
    for command in commands:
        c.setFont("CZ-Mono", 6.6)
        c.setFillColor(WHITE)
        c.drawString(MARGIN + 14, command_y, command)
        command_y -= 15
    draw_section_label(c, "PRIMARY SOURCE LEDGER", MARGIN, y - 386, AMBER)
    sources = [
        ("Occupational Safety, Health and Working Conditions Code, 2020", "https://labour.gov.in/sites/default/files/osh_gazette.pdf"),
        ("S.O. 5321(E) commencement notification, 21 November 2025", "https://labour.gov.in/sites/default/files/e-noti-osh-1.pdf"),
        ("OSH&WC (Central) Rules, 2026 - G.S.R. 345(E), 8 May 2026", "https://www.labour.gov.in/static/uploads/2026/05/ee246f790cad0b8e99c3828f34fa09a6.pdf"),
        ("OISD standards catalogue", "https://www.oisd.gov.in/en-in/oisd-standards-list"),
        ("ISO 45001 overview", "https://www.iso.org/standard/63787.html"),
        ("Compound Zero public repository", "https://github.com/Fyxod/compound-zero"),
    ]
    source_y = y - 414
    for index, (label, url) in enumerate(sources, 1):
        c.setFont("CZ-Semibold", 7.0)
        c.setFillColor(WHITE)
        prefix = f"{index}. {label}"
        c.drawString(MARGIN, source_y, prefix)
        text_w = pdfmetrics.stringWidth(prefix, "CZ-Semibold", 7.0)
        c.linkURL(url, (MARGIN, source_y - 2, min(PAGE_W - MARGIN, MARGIN + text_w), source_y + 8), relative=0)
        c.setFont("CZ-Regular", 5.8)
        c.setFillColor(MUTED_2)
        c.drawString(MARGIN + 15, source_y - 12, url)
        source_y -= 36
    c.setStrokeColor(LINE_SOFT)
    c.line(MARGIN, 59, PAGE_W - MARGIN, 59)
    c.setFont("CZ-Bold", 13)
    c.setFillColor(WHITE)
    c.drawString(MARGIN, 38, "See the accident before the alarm.")
    c.setFont("CZ-Mono", 6.4)
    c.setFillColor(GREEN)
    c.drawRightString(PAGE_W - MARGIN, 38, "END  /  18")

    c.save()
    return OUTPUT


if __name__ == "__main__":
    output = build_pdf()
    print(output)
