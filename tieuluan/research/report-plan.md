# Report scope and evidence

The three supplied PDFs have been extracted to UTF-8 text. They are examples of structure, not authoritative theory. Quynh's example concerns fashion retail, Nhi's example concerns a marketplace, and Huong's example concerns a different retail inventory domain. No marking rubric was supplied. The user later supplied cover details: PTIT, Vu Dinh Hieu, B23DCCE036, lecturer Tran Dinh Que.

## Deliverables
- An original academic English report, LaTeX source and compiled PDF.
- Editable Visual Paradigm 18 Community Edition project, with native UML models, default colours and styles.
- Exported diagrams embedded in the report; each export visually inspected and corrected before approval.
- Reproducible model creation material and a diagram review record.

## Case boundary
Atelier Fashion: fictional single-retailer direct-to-consumer fashion ecommerce. One warehouse, VND currency, online prepaid payments, authenticated checkout, partial returns and size/colour exchanges. No marketplace seller settlement, manufacturing, or perishable expiry management. Suppliers are stakeholders but have no direct system interface in this scope. One shipment per order in the first release. Payment, fulfilment, returns and refunds have distinct lifecycles.

## Planned report coverage
1. Introduction, method, evidence limitations and theoretical foundation.
2. Requirements identification: business background; as-is activities; stakeholders and needs; information catalogue; problems and causes; proposed system, boundary, objectives and feasibility; elicitation plan; functional/nonfunctional requirements; MoSCoW; business rules.
3. Requirements analysis: actors; customer and operations use-case views; fully specified use cases including alternatives and exceptions; activity diagrams; swimlane workflows; order and return lifecycles; domain concepts; analysis class models; traceability and validation.
4. System design: architecture, interaction sequences, database mapping and constraints, security, interface behaviour, transaction consistency, deployment and recovery.
5. Verification: requirement acceptance scenarios, negative/concurrency cases, consistency review, diagram reviews; conclusion, limitations, references.
6. Appendix: how each diagram was constructed in Visual Paradigm and how to rebuild LaTeX.

## Authoritative sources to examine
- OMG UML 2.5.1: https://www.omg.org/spec/UML/2.5.1
- Shopify variant and inventory documentation, as commercial pattern references, not evidence that the fictional retailer uses Shopify.
- Stripe payment lifecycle, webhook and idempotency documentation for asynchronous integration patterns.
- OWASP ASVS and W3C WCAG 2.2 for explicit security/accessibility targets.

## Final status

Completed: 72-page PDF, PTIT cover, 18 native diagrams, 20 FR, 9 NFR, 15 BR. Final evidence: completion-audit.md, diagram-review.md and final-artifact-audit.json.
