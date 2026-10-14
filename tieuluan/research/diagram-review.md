# Visual Paradigm diagram review

All diagrams are created as native UML model/view elements by a local plugin running inside Visual Paradigm 18 Community Edition. Colours, fonts and connector style settings are not changed. The application watermark is retained. Native PNG export uses scale 2.

## 01 Customer use cases
- Initial export: rejected; system boundary hid use cases and captions were absent.
- Correction: model/view containment and caption reset. Native factory registration also required names to be set after creating the diagram view.
- Second review: actor generalisation pointed to Customer; corrected VP from/to semantics so the hollow triangle points to Visitor.
- Third review (22:41): names and shapes visible, no overlapping use-case shapes, all actors outside the boundary. Some connector default pins sit near ellipse outlines; explicit routing is still to be refined before final approval. Includes point from Place order to reused behaviours. Payment event processing is separate from browser checkout.
- Fourth review (22:52): explicit include endpoints separate the three connectors and captions; correct actor generalisation; no shape/label collisions. Approved for inclusion subject to final PDF review.

## 03 Search activity
- Initial visual review (22:42): labels and mutually exclusive guards visible; right-side retry routes avoid action boxes; no shape collisions.
- Semantic review: retry paths entered actions with a second incoming control flow. Explicit merge nodes are being added before input and SKU selection to avoid implicit synchronisation of mutually exclusive paths.
- Corrected export reviewed at 22:46: both merge nodes are present; guards remain legible; retry lines avoid action boxes and each other; no clipped labels. Approved for inclusion subject to final PDF legibility and cross-model review.
- PDF review found the original tall layout's text too small. Bounds were compacted in VP without changing font/style; positive-branch spacing increased after re-review found two labels touched action borders. Latest 22:52 export has clear labels and improved page-size readability.

## 04 Checkout swimlane
- Visual review (22:43): three native partitions render correctly; all action text fits; branches and cross-lane flows do not intersect unrelated shapes or labels.
- Behaviour: rejected checkout commits no order/hold; committed checkout creates a payment request; provider outcomes are verified/deduplicated. Timeout/late-payment resolution will be specified in the payment/order lifecycle model and accompanying text. This diagram abstracts that guarded update, not a complete payment state machine.
- Diagram approved for inclusion subject to cross-model consistency review.
- Compact layout reviewed at 22:52: reduced native shape/lane bounds improve PDF legibility. Increased committed-branch spacing removes caption/action collision. All cross-lane arrows avoid unrelated shapes; native default styling retained.

## Remaining diagrams and final review (14 October 2026)

| Export | Review and corrections |
|---|---|
| 02 Operations | Actor roles outside boundary, UC09–UC13 inside. Routed carrier registration around UC12. Added Customer Service's authorised permanent-failure closure via a bottom/side route that avoids UC13. Final native export reviewed: endpoints correct, names complete, no unrelated shape crossings. |
| 16 Back office | Cancellation, returns, refund, reporting, access roles checked. Finance has reporting participation; Administrator has access responsibility. No ellipse/connector collision. |
| 18 Supporting | Explicit native UC17/UC18 and Finance participation in UC05 complete the use-case catalogue. Actor labels and links visible. |
| 05 Inspection | Approval context, physical counting, validation and one-time restock stay in their responsible partitions. Invalid receipt terminates the attempt without stock commit. Guards fit gaps. |
| 14 Receiving | Valid/new and invalid/duplicate alternatives have distinct paths. No stock posting on rejected branch. Action text fits; connectors avoid action boxes. |
| 15 Remedy | Refund scheduling distinguished from completion. Exchange requires allocation; shortage awaits customer choice. Four guards and three attempt endings are visible. |
| 06 Order state | Short event labels avoid crowded guard/effect captions; detailed guards/effects moved to transition table. Expiry routed far left. Added permanent DeliveryFailed branch with a separate routed closeFailure transition; temporary failure policy specified in text. Final state boxes and captions reviewed. |
| 07 Catalogue class | Product vs SKU, chart optionality, warehouse balance and multiplicities checked. Corrected draft Product→Variant to 0..*, with publication invariant in text. Multiplicity labels clear of corners. |
| 08 Order class | Moved AddressSnapshot between rows and routed its link away from CartLine–Variant. Order→OrderLine routed along outside right, avoiding Variant. Shared model attributes remain visible after reopen/export. |
| 17 Reservation class | One order and SKU per hold, many holds possible; balance link and diagonal associations stay distinct. No cart reservation implied. |
| 09 After-sales class | Optional original shipment, per-payment refunds, line-level returns and optional replacement checked. Quantity/money caps stated in rules rather than invented multiplicities. All class names and attributes fit. |
| 10 Checkout sequence | Local steps 2–5 precede provider interaction. Proper calls and dashed replies; customer result remains PendingPayment. Message captions fit lifeline gaps. |
| 11 Callback sequence | Persist before acknowledgment; asynchronous processing; native opt fragment for closed-and-paid compensation. Moved provider lifeline and shortened guard to eliminate caption/lifeline collision. Final guard and message arrows reviewed. |
| 12 Components | Corrected VP canonical-name reuse after default Component labels appeared during regeneration. Eight actual component names now match source. Shortened money API label to avoid node contact. Dependencies and arrow directions checked. |
| 13 Deployment | Shifted nodes/routes right to prevent clipped left callback caption. Callback route avoids backup connection; shortened DB/TLS labels fit gaps. All node labels and endpoints visible. |

## Final saved-project and PDF evidence

- Saved, closed and reopened the modelling VP process (current PID 21776); completed a new native AUDIT and all 18 exports after reopen. Original empty user instance was left untouched.
- Compared 18 actual diagram titles against the export manifest and all 18 report figure keys. UC01–UC18 are actual native use cases. Canonical Class/Actor/UseCase/System/Component names have no duplicates or default placeholders; audited relationship endpoints are bound.
- Reviewed all 18 figure pages in the final report: physical pages 21, 23, 25, 30–36, 39, 41, 43, 45, 48, 50, 52, 57. No missing labels, clipped shapes, or unintended box crossings observed. Wide diagrams use landscape pages; exported PNGs remain available for closer review. The default CE watermark remains intact.
- Reviewed the cover, contents, abstract, representative requirement and transition tables, data mapping, validation, appendix and references. Corrected the references TOC page and removed a near-empty validation continuation page.
- Cover reviewed at page size: double frame, corner details, official PTIT logo, explicit institution/course/report/topic, Vu Dinh Hieu, B23DCCE036, Tran Dinh Que, Hanoi 2026.
- Final PDF: 72 physical pages, no overfull boxes, unresolved references/citations, or LaTeX errors; no extracted text outside page bounds. Benign fontconfig, image ICC and bibliography underfull warnings do not affect the reviewed rendering.
- This is artifact/design verification. The acceptance scenarios are specified tests for future implementation, not claimed production test results.
