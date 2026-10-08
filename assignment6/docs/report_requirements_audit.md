# Requirements Audit — Final Detailed English LaTeX Report

Scope: read-only review of current `docs/report.tex`, full assignment extraction, report generator, live Python/data, native inventories, demonstrations/evaluation/test evidence and final PDF/build audit. Only this audit, AGENT_PROGRESS.md and SELF_EVALUATION.md were edited. The user-requested English detailed report has no page limit; the eleven recommended content parts remain required. Earlier condensed report is superseded.

## Eleven required parts

| Brief part, pp. 20–21 | Current report | Coverage inspected |
|---|---|---|
| Introduction | Section 1 | Customer modalities, common-query principle, goals/contributions and scope |
| Problem Description | Section 2 | Customer/system boundary, inputs/process/outputs, exclusions and brief ambiguities |
| Requirements Analysis | Section 3 | Customer, twelve FR, eight NFR, data/input validation and traceability |
| Use Case Model | Section 4 | Seven text specifications, native boundary/actor/associations/generalizations, export/VP screenshot |
| Three-Layer Architecture | Section 5 | Responsibilities, dependencies, physical mapping, injection, storage and retrieval/ranking separation |
| UML Sequence Diagram | Section 6 | Seven participants/fourteen messages, simulated-STT note, message-to-code mapping and alternatives |
| Python Implementation | Section 7 | CLI/composition root, adapters, repositories, common query, speech/image/index, retrieval/filter/rank, generators and commands |
| Multimodal Search Method | Section 8 | Lexical score, 88D block normalization, cosine/zero norm/clamp, candidate union/filter/fusion, tie-break/top-k, worked examples/complexity |
| Experimental Results | Section 9 | All 21 cases, group/mode counts/rates, full demo products/scores, four Python screenshots, tests/coverage/latency/failures |
| Discussion | Section 10 | Findings, validity, simulation, production exclusions, trade-offs and future work |
| Conclusion | Section 11 | Connected requirements/UML/code, correct success scope, deliverables and identity status |

All eleven main sections appear in the required order. Appendices cover compliance/delivery, complete Python source, dataset/images and exact fixtures/configuration. **No substantive missing named report part was found.**

## Task-by-task and supporting coverage

| Brief item | Pages | Current evidence | Disposition |
|---|---|---|---|
| T1 description, actors, ≥5 FR, NFR, modalities/outputs | 17–18 | Sections 2–3, twelve FR/eight NFR and tables | Covered |
| T2 Customer + seven named use cases | 7–8, 18 | Section 4, native inventory/export/VP screenshot and seven text flows | Covered |
| T3 three layer/packages/dependencies | 8–9, 18 | Section 5, native package ownership, sixteen components, dependency/source explanation | Covered; no Presentation→Data |
| T4 voice sequence seven named participants | 9, 18 | Section 6, fourteen messages, native export/screenshot and code mapping | Covered; transcript explicitly simulated |
| T5 repository/text/voice/image/ranking | 9–15, 19 | Sections 7–8, actual source and complete Appendix B, JUnit/coverage | Covered |
| T6 three queries input/process/products/scores | 19 | Section 9 saved full demo tables and text/voice/image screenshots, fusion/order supplements | Covered |
| ≥10 products | 11 | Twelve validated records/images, catalogue appendix | Covered |
| Total/success/rate/incorrect examples | 20 | All 21 rows; primary12/12, extension2/2, challenge0/2, robustness5/5; C01/C02 retained | Covered, separate denominators |
| VP and Python running screenshots | 21 | Three VP plus four Python result-viewer screenshots | Covered, viewer accurately labeled |
| Seven submission groups/README | 21 | Appendix A lists PDF/native/source/data/images/README/demo; README/manifests/examples exist | Content covered; root refreshes package gates |
| Separate UI/business logic | 4, 22 | Source/import-boundary test and injected services | Covered |
| Common query | 5, 22 | Validated dictionary across product modes | Covered; order is a separate exact lookup |
| Retrieval vs ranking | 6, 22 | Unsorted `_retrieve` candidates/statistics, RankingService final scores/order/top-k | Covered |
| Start simple/AI limits | 22–23 | Lexical/pixel baseline, simulation/production limitations | Covered |
| Selected optional work | 15–16, 19 | Fusion, price/category filtering and order status | Covered; other extensions not falsely claimed |

The full 23-page extraction `artifacts/assignment_06_requirements_extracted.txt` was read, including submission/rubric/principles. Assignment 05 editorial leftovers are resolved to Assignment 06; stricter Task 6 three-mode requirement is met. Approximate page guidance is overridden by the user's detailed no-limit/full-source request.

## Full source and image audit

Independent discovery found **28 project Python files** across main.py, Presentation, Application, Data, scripts including desktop helpers, and tests. The listing set matches exactly, without missing or extra paths. Final audit records **2,645 lines**. Every live file's SHA-256 matches its listing record; every code snapshot is byte-identical to live source. Complete files include initializers, runtime/services, generators, evaluation/report/delivery/model-launch/capture utilities and complete tests. Section 7 explains implementation responsibilities; Appendix B reproduces full numbered source rather than selected examples. Java/XML native automation is not Python and does not inflate this count.

All **25 readable original images** are included: three native exports; three VP screenshots; four Python screenshots; twelve catalogue illustrations; three derived query images. Final PDF audit matches decoded original pixels and preserved model/image hashes. Invalid corrupt.png is explicitly described and correctly not embedded. Numeric vector arrays remain delivered embeddings.json, with format/explanation and full Python builders/consumers in the report; this is disclosed rather than mislabeled omitted code.

## Verified snapshot before the supplied cover update

- Final canonical PDF: `artifacts/report/Assignment_06_Report.pdf`, **91 pages**, English/XeLaTeX, no page limit.
- SHA-256: `818a31566ac78f9e2f2727e34ecb843f97be273fdea812399ae7140af261c8c7`.
- Independent current-state checks confirm PDF hash equals final audit; live report.tex hash equals input hash; all source/listing/snapshot hashes match; all preserved image/model hashes match.
- Final build audit establishes eleven section bookmarks, fonts embedded, black text, clean bounds/references and exact original-image pixel preservation. It records all 28 Python files and 25 images.
- Test evidence: 78 pass, no failures/errors/skips, Application/Data line coverage100%/264statements. Scope is explicitly not branch/all-project/UI/VP coverage.
- Root reports current validator 8/8 PASS. Prototype owns final visual/source review. This worker inspected content/hash evidence and does not claim its own full visual/GUI review.

Real ASR, learned/semantic embeddings, vector database, stock boost, natural-language latest-order, OrderItem management, web UI and authenticated production context are explicitly outside implemented scope; none is a missing required baseline task.

**Result:** substantive report content and final source/asset freshness pass this audit. Root refreshes FINAL_VERIFICATION, ZIP/manifest and extracted-source smoke after owned docs freeze; current package completion must be proven from that refreshed snapshot, not older package artifacts. No LMS submission is claimed.

## Current supplied-cover revision

Supplied student: **Vu Dinh Hieu**, **B23DCCE036**, class **E23TTNT02**; instructor: **Tran Dinh Que**; institution: **Posts and Telecommunications Institute of Technology**. These details replace historical missing-identity labels. Root adapts the DIP main.tex cover format in English and copies supplied artwork to `docs/cover/background.png` and `docs/cover/logo.png`. The abstract moves to its own page after the cover.

The 91-page/28-file/25-image/hash snapshot above was verified before this revision and remains historical evidence. The cover adds two readable artwork assets and a separate abstract page; expected revised count is not a verified final count. Root must rebuild and review the revised cover/abstract, current source/image inventory and new PDF hash, then refresh package/manifest/smoke evidence. This worker does not edit TEX/Python/assets/PDF or claim those operations itself. Main-section/task/source coverage remains applicable; freshness certification requires the new audit.
