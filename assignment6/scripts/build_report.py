"""Build the complete English LaTeX report, with exact Python source listings."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.report_facts import prepare_report_inputs

SECTIONS = [
    "Introduction", "Problem Description", "Requirements Analysis", "Use Case Model",
    "Three-Layer Architecture", "UML Sequence Diagram", "Python Implementation",
    "Multimodal Search Method", "Experimental Results", "Discussion", "Conclusion",
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(source, output, engine="xelatex"):
    executable = shutil.which(engine)
    if not executable:
        raise RuntimeError("XeLaTeX is required. Install MiKTeX or TeX Live and expose xelatex on PATH.")
    source, output = Path(source).resolve(), Path(output).resolve()
    if source.suffix.lower() != ".tex":
        raise ValueError("The current report source is docs/report.tex; Markdown is no longer the report input.")
    if not source.is_file():
        raise FileNotFoundError(source)
    work = ROOT / "artifacts/report/latex_build"
    work.mkdir(parents=True, exist_ok=True)
    inputs = prepare_report_inputs(ROOT, work)
    inputs["input_sha256"][source.relative_to(ROOT).as_posix()] = sha256(source)
    job = "Assignment_06_Report"
    command = [executable, "-disable-installer", "-interaction=nonstopmode", "-halt-on-error",
               "-file-line-error", f"-output-directory={work}", f"-jobname={job}", str(source)]
    for number in range(1, 4):
        completed = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8", errors="replace",
                                   capture_output=True, timeout=240)
        (work / f"compile_pass_{number}.txt").write_text(completed.stdout + completed.stderr, encoding="utf-8")
        if completed.returncode:
            raise RuntimeError(f"XeLaTeX pass {number} failed. See {work / f'compile_pass_{number}.txt'}\n"
                               + completed.stdout[-2500:])
        print(f"XeLaTeX pass {number}/3 complete", flush=True)
    log = (work / f"{job}.log").read_text(encoding="utf-8", errors="replace")
    bad = [line for line in log.splitlines() if "Overfull \\" in line or "Missing character:" in line or
           re.search(r"(?:Reference|Citation).*undefined|There were undefined|Label\(s\) may have changed", line)]
    if bad:
        raise RuntimeError("Resolve LaTeX layout/reference warnings before publishing: " + "\n".join(bad[:30]))
    compiled = work / f"{job}.pdf"
    with pymupdf.open(compiled) as pdf:
        pages = len(pdf)
        outline = pdf.get_toc()
        titles = [entry[1] for entry in outline]
        section_pages = {}
        for index, heading in enumerate(SECTIONS, 1):
            matches = [entry for entry in outline if entry[1] == f"{index} {heading}"]
            if not matches:
                raise ValueError(f"Missing required report section: {heading}; outline={titles[:20]}")
            section_pages[heading] = matches[0][2]
        empty, nonblack, outside = [], [], []
        fonts, seen_images = set(), set()
        for index, page in enumerate(pdf):
            if not page.get_text().strip():
                empty.append(index + 1)
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        fonts.add(span["font"])
                        if span["color"] != 0:
                            nonblack.append({"page": index + 1, "text": span["text"]})
                        x, y, right, bottom = span["bbox"]
                        if x < 15 or right > page.rect.width - 15 or y < 12 or bottom > page.rect.height - 12:
                            outside.append({"page": index + 1, "text": span["text"], "bbox": list(span["bbox"])})
            for item in page.get_images():
                seen_images.add(item[0])
        if empty or nonblack or outside:
            raise ValueError(f"PDF audit failed: empty={empty}, nonblack={nonblack[:3]}, bounds={outside[:3]}")
        if len(seen_images) < len(inputs["figures"]):
            raise ValueError("Not all approved figures were embedded in the PDF")
        def decoded_fingerprint(image):
            return (image.size, hashlib.sha256(image.convert("RGB").tobytes()).hexdigest())
        embedded_pixels = {}
        for xref in seen_images:
            with Image.open(io.BytesIO(pdf.extract_image(xref)["image"])) as decoded:
                embedded_pixels[decoded_fingerprint(decoded)] = xref
        figure_mapping = {}
        for relative in inputs["figures"]:
            with Image.open(ROOT / relative) as original:
                identity = decoded_fingerprint(original)
            if identity not in embedded_pixels:
                raise ValueError("Approved figure pixels were not preserved in PDF: " + relative)
            figure_mapping[relative] = embedded_pixels[identity]
        embedded_fonts = {}
        for page in pdf:
            for item in page.get_fonts(full=True):
                embedded_fonts[item[3]] = bool(pdf.extract_font(item[0])[3])
        if not all(embedded_fonts.values()):
            raise ValueError("PDF contains a font that is not embedded")
        text = "\n".join(page.get_text() for page in pdf)
        for record in inputs["python_listings"]:
            if record["path"] not in text:
                raise ValueError("Source listing caption is missing: " + record["path"])
        audit = {
            "format": "assignment06-latex-report-v2", "pdf": output.relative_to(ROOT).as_posix(),
            "language": "English", "engine": "XeLaTeX", "page_limit": None, "pages": pages,
            "section_pages": section_pages, "all_required_sections_present": True,
            "page_sizes": [list(page.rect) for page in pdf], "drawn_fonts": sorted(fonts),
            "embedded_fonts": embedded_fonts, "nonblack_text": nonblack, "text_outside_safe_bounds": outside,
            "unique_embedded_images": len(seen_images), "figures": inputs["figures"],
            "all_approved_image_pixels_matched": True, "figure_xrefs": figure_mapping,
            "python_listings": inputs["python_listings"], "python_listing_count": len(inputs["python_listings"]),
            "complete_python_line_count": sum(r["lines"] for r in inputs["python_listings"]),
            "evaluation": inputs["evaluation"], "tests": inputs["tests"],
            "input_sha256": inputs["input_sha256"], "approved_UML_and_images_unchanged": True,
            "preserved_assets": inputs["preserved_assets"], "latex_layout_and_references_clean": True,
            "pdf_sha256": sha256(compiled),
        }
        review = output.parent / "review_pages"
        review.mkdir(parents=True, exist_ok=True)
        for index, page in enumerate(pdf):
            page.get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25)).save(review / f"page_{index + 1:03d}.png")
    for name, expected in inputs["preserved_assets"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError("An approved asset changed during the report build: " + name)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(compiled, output)
    except PermissionError as exc:
        raise PermissionError(f"The compiled PDF is ready at {compiled}; close only the old report in its viewer "
                              "and run this build again to publish it.") from exc
    (output.parent / "build_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")
    print(f"Built {output}: {pages} pages, {len(inputs['python_listings'])} complete Python files, "
          f"{len(inputs['figures'])} approved images; black text, embedded fonts, clean references.")
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "docs/report.tex")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/report/Assignment_06_Report.pdf")
    parser.add_argument("--engine", default="xelatex")
    args = parser.parse_args()
    build(args.input, args.output, args.engine)


if __name__ == "__main__":
    main()
