# Atelier Fashion — Information System Analysis and Design

Academic English report for **Vu Dinh Hieu — B23DCCE036**, PTIT. Lecturer: **Tran Dinh Que**.

## Deliverables

- `deliverables/Atelier_Fashion_Ecommerce_Report.pdf`: final 72-page report.
- `deliverables/Atelier_Fashion_Source.zip`: LaTeX chapters, official cover logo, native project, exported diagrams, modelling source/specifications and review evidence.
- `diagrams/AtelierFashion.vpp`: editable Visual Paradigm 18 Community Edition project with 18 native diagrams.
- `report/main.tex`: main report source. Chapter files are in the same directory.

The report covers business investigation, requirements identification, 20 functional and 9 nonfunctional requirements, 15 business rules, 18 use cases, UML analysis models, system design, data constraints, acceptance traceability, limitations, sources, and diagram construction guidance. The retailer and numerical policies are explicit case assumptions.

## Rebuild the PDF

Preserve the sibling `report/` and `diagrams/` directories. Install Tectonic, open a terminal in `report/` and run:

```text
tectonic --keep-logs main.tex
```

Alternatively use a complete TeX distribution and run `pdflatex main.tex` until cross-references stabilise. Required packages are listed in `main.tex`. Tool binaries and third-party sample PDFs are excluded from the source archive.

## Edit the diagrams

Open `diagrams/AtelierFashion.vpp` in Visual Paradigm 18 CE. Choose a named diagram in Diagram Navigator; edit native UML elements and save. Export via Project → Export → Diagrams as Image (PNG). Keep default colors/fonts/styles and review node text, connectors, guards, multiplicities and the resulting PDF page. The CE watermark is retained.

`automation/FashionPlugin.java`, `plugin.xml`, the compiled plugin JAR and TSV specifications document the native Open API creation workflow. The plugin runs **inside VP**, not in a diagram renderer. For another workspace, update its `ROOT` constant, compile against that VP installation's `lib/openapi.jar`, and install the plugin using VP's plugin directory conventions. Generators submit `automation/job.tsv`; the plugin writes `done.txt` or `error.txt`. Do not submit a job while an earlier one is still pending. Manual editing of the delivered VPP does not require installing the plugin.

## Review evidence and sources

`research/diagram-review.md` records visual corrections and final review. `native-model-audit.tsv`, `export-manifest.tsv` and `final-artifact-audit.json` record saved native models, 18 exports and artifact checks. The final project was reopened and exported before the final PDF build. Tests in the report are proposed acceptance scenarios for an unimplemented system.

Authoritative theory and commercial documentation are cited in the report. Supplied student samples informed coverage and cover layout; their text and diagrams were not copied into the report. PTIT logo provenance is in `report/assets/README.md`.
