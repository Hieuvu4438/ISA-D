# Assignment 06 report

The current complete English report is written in [report.tex](report.tex) and compiled with XeLaTeX. The PDF is `artifacts/report/Assignment_06_Report.pdf`. The previous twelve-page Vietnamese Markdown report has been superseded following the user's explicit request for a detailed English LaTeX paper without a page limit.

The report retains the assignment's eleven recommended sections in order and includes all three approved UML exports, all three VP screenshots, all four Python demonstration screenshots, all twelve product illustrations and all three readable query images. Images and the native VP project are preserved unchanged.

The Python implementation is explained in the main report. A complete source appendix includes every Python file in the project: runtime, data access, preparation/evaluation/report/delivery tools, desktop helpers and tests. Tables and listings are generated from actual files and saved execution evidence. All 21 evaluation cases, separate success denominators and two observed failures are included. Full dataset/configuration fixtures accompany the appendix.

Build from the assignment root:

```powershell
.\.venv\Scripts\python.exe scripts/build_report.py --input docs/report.tex --output artifacts/report/Assignment_06_Report.pdf
```

Install `requirements-dev.txt`, expose `xelatex` on PATH, and provide Times New Roman, Arial and Consolas fonts. MiKTeX/TeX Live must have the standard packages used in the source. The builder compiles three passes and checks references, layout, black text, embedded fonts, required sections, images, full source-file captions and preserved asset hashes. It saves `build_audit.json` and renders pages for visual review. Search runtime does not require LaTeX or Visual Paradigm.

See [report_requirements_audit.md](report_requirements_audit.md) for the original-assignment and user-request coverage review.

The current cover follows the supplied DIP report format in English. It identifies **Vu Dinh Hieu**, student ID **B23DCCE036**, class **E23TTNT02**, instructor **Tran Dinh Que**, and **Posts and Telecommunications Institute of Technology**. Supplied cover artwork is stored in `docs/cover/background.png` and `docs/cover/logo.png`. The abstract moves to its own page after the cover. These details were supplied for this update rather than inferred from a Windows account or software license.

The earlier verified report snapshot had 91 pages; it precedes this cover revision. The revised PDF is expected to have one additional abstract page, but its final page count, image inventory and SHA-256 must come from the new build audit. Rebuild the PDF and submission package after the cover/assets change; do not reuse earlier hashes as evidence for the revised delivery.
