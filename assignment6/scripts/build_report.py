"""Build a Unicode A4 report from Markdown and current experiment artifacts.

Explicit <!-- pagebreak --> markers preserve the 12-page report structure.
Artifact directives fail loudly when evidence is missing; no simulated numbers.
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]


def register_fonts():
    candidates = [
        (Path("C:/Windows/Fonts"), "arial.ttf", "arialbd.ttf", "ariali.ttf"),
        (Path("/usr/share/fonts/truetype/dejavu"), "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf"),
    ]
    for folder, regular, bold, italic in candidates:
        if all((folder / filename).is_file() for filename in (regular, bold, italic)):
            for name, filename in [("Report", regular), ("Report-Bold", bold), ("Report-Italic", italic)]:
                pdfmetrics.registerFont(TTFont(name, str(folder / filename)))
            pdfmetrics.registerFontFamily("Report", normal="Report", bold="Report-Bold", italic="Report-Italic", boldItalic="Report-Bold")
            return
    raise RuntimeError("Unicode Arial/DejaVu fonts not found. Install a Vietnamese-capable font before building.")


def inline(value):
    value = escape(str(value))
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`([^`]+)`", r'<font color="#245778">\1</font>', value)
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", value)
    return value


def load_json(relative):
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(f"Required report evidence is missing: {relative}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def table(rows, width, style, ratios=None):
    column_count = len(rows[0])
    if any(len(row) != column_count for row in rows):
        raise ValueError("Inconsistent Markdown table column count")
    ratios = ratios or [1] * column_count
    widths = [width * ratio / sum(ratios) for ratio in ratios]
    paragraphs = [[Paragraph(inline(cell), style) for cell in row] for row in rows]
    output = Table(paragraphs, colWidths=widths, repeatRows=1, hAlign="LEFT")
    output.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6eef4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#13364d")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#c2cbd1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fa")]),
    ]))
    return output


def artifact_directive(name, width, styles):
    metric = load_json("artifacts/evaluation/metrics.json")
    results = load_json("artifacts/evaluation/results.json")
    if isinstance(results, dict):
        results = results.get("results", results.get("queries", []))
    if name == "metrics":
        total, success = metric["total_queries"], metric["successful_queries"]
        rate = metric["success_rate"]
        primary = [row for row in results if row.get("group", "primary") == "primary"]
        if total != len(primary) or success != sum(bool(row["success"]) for row in primary):
            raise ValueError("Evaluation metrics do not match authoritative results")
        if total <= 0 or abs(rate - success / total) > 1e-8:
            raise ValueError("Invalid evaluation success rate")
        rows = [["Mode", "Queries", "Successful", "Success rate"]]
        for mode, group in metric["by_mode"].items():
            observed_mode = [row for row in primary if row["mode"] == mode]
            if group["total"] != len(observed_mode) or group["successful"] != sum(bool(row["success"]) for row in observed_mode):
                raise ValueError(f"Evaluation mode {mode} differs from results")
            rows.append([mode, group["total"], group["successful"], f'{group["success_rate"]:.2%}'])
        rows.append(["Tổng", total, success, f"{rate:.2%}"])
        items = [table(rows, width, styles["cell"], [2, 1, 1, 1.4]), Spacer(1, 9)]
        groups = metric.get("groups", {})
        for group_name, group in groups.items():
            observed = [row for row in results if row.get("group", "primary") == group_name]
            if group["total"] != len(observed) or group["successful"] != sum(bool(row["success"]) for row in observed):
                raise ValueError(f"Evaluation group {group_name} differs from results")
        other_groups = "; ".join(f'{name}: {group["successful"]}/{group["total"]} ({group["success_rate"]:.2%})' for name, group in groups.items() if name != "primary")
        if other_groups:
            items.append(Paragraph(inline("Nhóm riêng ngoài baseline: " + other_groups + ". Không gộp robustness error-handling vào retrieval accuracy."), styles["body"]))
        timing = metric.get("timing_ms", {})
        if timing:
            values = "; ".join(f"{key}: {float(timing[key]):.3f} ms" for key in ("mean", "p95", "max") if key in timing)
            items.append(Paragraph(inline("Thời gian processing local: " + values + ". Phạm vi đo là pipeline query sau khi khởi tạo services/index; không bao gồm cold startup và không đại diện tải production."), styles["body"]))
        return items
    if name == "results":
        rows = [["ID / mode", "Input", "Top-1", "Đúng?"]]
        for row in results:
            if row.get("group", "primary") != "primary":
                continue
            inp = row.get("input", "")
            if isinstance(inp, dict):
                inp = inp.get("query", Path(inp.get("image", "—")).name)
            rows.append([f'{row["id"]} / {row["mode"]}', str(inp), row.get("top_1_product_id", row.get("top_1", "—")), "Có" if row["success"] else "Không"])
        return [table(rows, width, styles["smallcell"], [1.4, 3.6, .8, .7]), Spacer(1, 7)]
    if name == "failures":
        failed = [row for row in results if not row["success"]]
        if not failed:
            return [Paragraph("Không quan sát query thất bại theo criterion đã công bố trong tập này. Điều này không chứng minh chất lượng trên ảnh/ngôn ngữ ngoài tập kiểm thử; cần bổ sung queries độc lập.", styles["body"])]
        items = []
        for row in failed:
            relevant = row.get("relevant_ids", [])
            top = row.get("top_1_product_id", row.get("top_1", "—"))
            inp = row.get("input", {})
            inp = inp.get("query", inp.get("image", inp)) if isinstance(inp, dict) else inp
            detail = f'Case {row["id"]} ({row["mode"]}, group={row.get("group", "—")}): input="{inp}"; ground truth={relevant}; Top-1={top}; Top-k={row.get("top_k_ids", [])}. {row.get("note", "")}'
            items.append(Paragraph(inline(detail), styles["body"]))
        return items
    if name.startswith("demo:"):
        mode = name.partition(":")[2]
        demos = load_json("artifacts/demo/demo_results.json")
        if isinstance(demos, dict):
            demos = demos.get("demonstrations", demos.get("results", []))
        demo = next(item for item in demos if item["query"]["type"] == mode)
        top = demo.get("results", [])[:2]
        inp = demo["query"].get("raw_input", demo["query"].get("query", ""))
        if mode == "image":
            try:
                inp = Path(str(inp)).relative_to(ROOT).as_posix()
            except ValueError:
                pass
        rows = [["Mode / input", "Top products và final score"]]
        rows.append([f"{mode}: {inp}", "; ".join(f'{p["product_id"]} {p["name"]} ({p["final_score"]:.6f})' for p in top) or "No results"])
        return [table(rows, width, styles["smallcell"], [1.5, 3.5])]
    if name == "dataset":
        products = load_json("data/products.json")
        if isinstance(products, dict):
            products = products.get("products", [])
        index = load_json("data/embeddings.json")
        if set(index["vectors"]) != {str(product["product_id"]) for product in products}:
            raise ValueError("Dataset and report index IDs differ")
        encoder = index["encoder"]
        statement = f'Dataset có {len(products)} products, IDs duy nhất: {len(set(p["product_id"] for p in products))}. Index {encoder["name"]} v{encoder["version"]} ({encoder["dimension"]} chiều) được lưu cùng vectors trong data/embeddings.json. Hình sản phẩm/query là synthetic illustrations được sinh local, không phải ảnh chụp thương mại.'
        return [Paragraph(inline(statement), styles["body"])]
    if name == "verification":
        coverage = load_json("artifacts/tests/coverage.json")
        suites = list(ET.parse(ROOT / "artifacts/tests/junit.xml").getroot().iter("testsuite"))
        if not suites:
            raise ValueError("Test report contains no testsuite evidence")
        counts = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites) for key in ("tests", "failures", "errors", "skipped")}
        passed = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
        total = coverage["totals"]
        files = sorted({Path(name.replace("\\", "/")).parts[0] for name in coverage["files"]})
        statement = f'Kiểm thử: {passed}/{counts["tests"]} tests pass, failures={counts["failures"]}, errors={counts["errors"]}, skipped={counts["skipped"]} (JUnit artifact). Line coverage {total["percent_covered"]:.2f}% trên {total["num_statements"]} statements thuộc {" và ".join(files)}. Không diễn giải line coverage thành branch coverage hay coverage toàn project/UI/VP.'
        return [Paragraph(inline(statement), styles["body"])]
    raise ValueError(f"Unknown report directive: {name}")


def build(input_path, output_path):
    register_fonts()
    styles = {
        "body": ParagraphStyle("BodyVI", fontName="Report", fontSize=10.2, leading=15, spaceAfter=8),
        "h1": ParagraphStyle("H1VI", fontName="Report-Bold", fontSize=19, leading=25, spaceAfter=14, textColor=colors.HexColor("#143b53")),
        "h2": ParagraphStyle("H2VI", fontName="Report-Bold", fontSize=12, leading=17, spaceBefore=8, spaceAfter=7, textColor=colors.HexColor("#143b53")),
        "cell": ParagraphStyle("CellVI", fontName="Report", fontSize=9, leading=12),
        "smallcell": ParagraphStyle("SmallCellVI", fontName="Report", fontSize=7.9, leading=10.4),
        "caption": ParagraphStyle("CaptionVI", fontName="Report-Italic", fontSize=8.4, leading=11, alignment=TA_CENTER, spaceAfter=10),
        "cover": ParagraphStyle("CoverVI", fontName="Report-Bold", fontSize=25, leading=34, alignment=TA_CENTER, spaceAfter=22, textColor=colors.HexColor("#143b53")),
    }
    source = input_path.read_text(encoding="utf-8-sig")
    pages = source.split("<!-- pagebreak -->")
    if len(pages) != 12:
        raise ValueError(f"Expected 12 explicit report pages, got {len(pages)}")
    width = A4[0] - 96
    story = []
    for page_index, page in enumerate(pages):
        if page_index:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 65))
        lines = page.strip().splitlines()
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            index += 1
            if not line:
                continue
            directive = re.fullmatch(r"\{\{([^}]+)\}\}", line)
            if directive:
                story.extend(artifact_directive(directive[1], width, styles))
                continue
            image_match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if image_match:
                caption, relative = image_match.groups()
                path = ROOT / relative
                if not path.is_file():
                    raise FileNotFoundError(f"Report image missing: {relative}")
                max_height = 125 if "screenshots/" in relative else 360
                visual = Image(str(path))
                ratio = min(width / visual.imageWidth, max_height / visual.imageHeight)
                visual.drawWidth = visual.imageWidth * ratio
                visual.drawHeight = visual.imageHeight * ratio
                visual.hAlign = "CENTER"
                story.append(KeepTogether([visual, Spacer(1, 4), Paragraph(inline(caption), styles["caption"])]))
                continue
            if line.startswith("|"):
                rows = []
                while True:
                    cells = [cell.strip() for cell in line.strip("|").split("|")]
                    if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                        rows.append(cells)
                    if index >= len(lines) or not lines[index].strip().startswith("|"):
                        break
                    line = lines[index].strip()
                    index += 1
                story.extend([table(rows, width, styles["cell"]), Spacer(1, 9)])
                continue
            if line.startswith("# "):
                story.append(Paragraph(inline(line[2:]), styles["cover"] if page_index == 0 else styles["h1"]))
            elif line.startswith("## "):
                story.append(Paragraph(inline(line[3:]), styles["h2"]))
            else:
                if line.startswith("- "):
                    line = "• " + line[2:]
                story.append(Paragraph(inline(line), styles["body"]))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#c2cbd1"))
        canvas.line(48, 38, A4[0] - 48, 38)
        canvas.setFont("Report", 8)
        canvas.setFillColor(colors.HexColor("#5e6a72"))
        canvas.drawString(48, 25, "Assignment 06 · Multimodal Search System for E-Commerce")
        canvas.drawRightString(A4[0] - 48, 25, str(document.page))
        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=48, rightMargin=48, topMargin=45, bottomMargin=50, title="Assignment 06 — Multimodal Search System for E-Commerce", author="Chưa cung cấp")
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    import pymupdf
    with pymupdf.open(output_path) as pdf:
        if len(pdf) != 12:
            raise RuntimeError(f"Report overflow: expected 12 pages, rendered {len(pdf)}; inspect layout and shorten content.")
        review_dir = output_path.parent / "review_pages"
        review_dir.mkdir(exist_ok=True)
        for index, page in enumerate(pdf):
            page.get_pixmap(matrix=pymupdf.Matrix(1.3, 1.3)).save(review_dir / f"page_{index + 1:02d}.png")
    print(f"Built {output_path}: 12 A4 pages; rendered all pages to {review_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "docs/report.md")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/report/Assignment_06_Report.pdf")
    args = parser.parse_args()
    build(args.input.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
