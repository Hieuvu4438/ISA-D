# End-to-end execution brief: From Analysis to Design

## Revision 2 — current execution priority (24 September 2026)

The user has explicitly prioritized speed and the **new** assignment's final images. Do not redraw or export the previous-test analysis/data-model images. The earlier audit below remains background and traceability only. Deliver the editable `eComDesign/eComDesign.vpp`, six final native VP design exports (`01` through `06`) with a white background, two Spring examples with honest run evidence, actual folder screenshot, and the English LaTeX PDF report. The older `.vpp` files remain untouched. This revision supersedes the earlier repair/export phases and acceptance criteria AC-002/AC-003 as work items; the report may briefly describe known old-model issues without claiming they were repaired.

## 1. Goal and authoritative inputs

Complete the e-commerce assignment in `storage/TỪ PHÂN TÍCH ĐẾN THIẾT KẾ.pdf` as an editable Visual Paradigm project, exported diagrams, a working Spring example set, folder evidence, and an English LaTeX PDF report. Repair the 17 September analysis and data model early so that the design has a sound baseline.

Authoritative local inputs:

- `storage/ĐỀ KIỂM TRA 01-17.09.pdf`: previous analysis diagram, attributes/relationships, data model multiplicities/labels/ORM persistence, and three-folder submission structure.
- `storage/TỪ PHÂN TÍCH ĐẾN THIẾT KẾ.pdf`: explain DAO and MVC; provide and run two Java/Spring examples; produce e-commerce design class diagram in four transformations: methods, usage dependencies, DAO, and three MVC layers. Cart is the worked example; Customer and Item must also be completed. The `order` package contains Order, Payment, and Shipment.
- `eComAnalysis/eComAnalysis.vpp`, `eComDataModel/eComDataModel.vpp`, `eComDataModel/eComDataModel(1).vpp`, `eComDataModel/eComDataModel(2).vpp`: editable previous submissions. The files are Visual Paradigm SQLite projects, not images. `(2)` includes an additional generated ER diagram, but its ORM conversion introduced generic `ID` attributes and duplicate product attributes; it is not automatically the best source.
- `eComAnalysis/eComAnalysis.jpg`, `eComDataModel/eComDataModel.jpg`, and `B23DCCE036 - Vũ Đình Hiếu.docx`: visual/reports from the previous attempt, for comparison only.

Identity already documented in the previous report: Vu Dinh Hieu, B23DCCE036, class E23TTNT02-B; instructor Tran Dinh Que. Omit the old report's date of birth and phone number because they are unnecessary for this assignment.

## 2. Current-state audit and repair decisions

The existing analysis contains 20 classes and 21 associations. It covers Customer, identity/address/account information, Cart/CartItem, Order/OrderItem, Shipping/payment, Product and several product subtypes. The current data-model image is crowded and contains inconsistent names and semantics:

| Existing issue | Required correction |
| --- | --- |
| `payment`, `CustomerNew`, `CustomerVIP`, and the product subtype vocabulary are inconsistent with the design brief | Use `Payment`, `NewCustomer`, `VipCustomer`, and a stable `Item` vocabulary in the design. Preserve a traceability note where `Product` in the old model maps to `Item` in the new model. |
| `Product` has overlapping subtype copies of `productId`, `productName`, `unitPrice`, and `stockQty`; later ORM conversion adds a generic `ID` to every class | Use one identifier in the base product/item table and subtype-specific fields only. Document the chosen table mapping and primary/foreign keys. |
| Optionality and ownership are unclear: customer/cart `0..1`, cart item `0..*`, order item `1..*`, payment `0..1` are mixed with unqualified labels | Put explicit multiplicity at both ends; describe lifecycle assumptions and distinguish a draft cart/order from a submitted order. |
| Some `refers to` associations crisscross the diagram, obscuring which line item refers to which product | Replace with named, unambiguous `CartItem -> Item` and `OrderItem -> Item` references. |
| Analysis and data diagrams contain direct associations/inheritance that are unsuitable as design-time service dependencies | Keep domain associations in the corrected analysis/data views; use dashed UML `Usage` dependencies for method calls in the design view. |
| Previous report has mostly screenshots and little written explanation | Write complete English explanations, traceability, cardinality rationale, code/run evidence, and figures. |

Repair policy: retain original files and backups; create final named `.vpp` files through Visual Paradigm Save As or an application-supported project API. Prefer correcting a copy of the richest consistent baseline, then make the analysis, data model, and design appear as separately named diagrams in the final project. Never claim a feature or run succeeded without checking the saved artifact.

## 3. Target deliverables and structure

The existing `eComDesign/` directory is the third folder required by the prior test; the prompt calls it `eCom` informally, but this exact folder name matches the assignment. Final layout:

```text
VDHIEU/
  ASSIGNMENT_EXECUTION_PLAN.md
  eComAnalysis/
    eComAnalysis.vpp                 # repaired editable analysis version
    exports/eComAnalysis.png
  eComDataModel/
    eComDataModel.vpp                # repaired editable data version
    exports/eComDataModel.png
  eComDesign/
    eComDesign.vpp                   # editable integrated design version
    exports/01-methods.png
    exports/02-usage.png
    exports/03-dao.png
    exports/04-mvc-overview.png
    exports/05-customer-detail.png
    exports/06-item-order-detail.png
  spring-examples/                  # runnable source and run instructions
  report/
    main.tex                        # reproducible English LaTeX source
    figures/                        # selected clean VP exports/evidence
    From_Analysis_to_Design_Vu_Dinh_Hieu.pdf
  evidence/
    folder-structure.png             # screenshot of actual folders/files
    visual-paradigm-project.png     # application screenshot with final project
    spring-run-*.png                 # actual build/run and HTTP responses
```

If Visual Paradigm CE limits an export or API feature, record the exact limitation and use the closest native GUI output. Do not substitute drawn images for evidence that the `.vpp` project was edited and opened.

## 4. Model contract

### Corrected analysis and data model

Use domain entities `Customer`, `FullName`, `Address`, `Account`, `Cart`, `CartItem`, `Order`, `OrderItem`, `Item` (mapping from old `Product`), `Payment`, and `Shipment` (mapping from old `Shipping`). Product and payment/customer subtype tables may remain only if their purpose, keys, and optionality are clear. Core rules:

1. A customer owns zero or one active cart; a cart belongs to exactly one customer. A cart contains zero or more cart items; each cart item belongs to one cart and references one item.
2. A customer can place zero or more orders; every order has one customer. A submitted order has one or more order items; each order item belongs to one order and references one item. State when a draft order may temporarily have zero lines.
3. An order can have zero or one payment and zero or one shipment before completion. Each payment/shipment belongs to exactly one order in this assignment's simplified model. Completion constraints should be stated in text instead of silently changing all associations to mandatory.
4. `CartItem` and `OrderItem` are association entities holding quantity and captured unit price; `OrderItem` preserves purchase-time price. Item price and stock remain on Item.
5. ORM-persistable entities have a single explicit key, consistent types, and foreign keys matching the associations. Explain `1`, `0..1`, `0..*`, and `1..*` with examples.

### Design transformation

Create independently readable diagrams named `01 Methods`, `02 Usage`, `03 DAO`, `04 MVC Overview`, and detail diagrams if the overview becomes unreadable. Each diagram must show actual UML model elements, not a pasted screenshot.

- Step 1: add domain operations (e.g., `Customer.updateProfile`, `Cart.addItem`, `Cart.updateQuantity`, `Cart.removeItem`, `Cart.calculateTotal`, `Order.place`, `Payment.record`, `Shipment.schedule`). Include parameter and return types, plus invariants such as positive quantities and totals derived from line items. The brief's `getCust(Customer)` example is explained as a pedagogical form; prefer `getCustomer(): Customer` for an idiomatic read operation.
- Step 2: show dashed `<<use>>` dependencies only when a method consumes another class or its data, with direction from user to used element. Keep structural containment where it expresses lifecycle; distinguish it from design-time usage.
- Step 3: define `CartDAO`, `CustomerDAO`, `ItemDAO`, and optionally `OrderDAO`, `PaymentDAO`, `ShipmentDAO` interfaces; implementations realize interfaces, and persistence operations use IDs and typed entities. Domain objects do not call DAO implementations directly.
- Step 4: package the model into `model.customer`, `model.item`, `model.order`, and `model.cart`; add `controller` and `interface` layers. Use the brief's package name `order`, containing `Order`, `Payment`, and `Shipment`. Clearly label `interface` as UI/boundary to avoid confusion with Java `interface`. Controllers depend on services/DAO contracts as shown; interface -> controller -> model is the request path, with response in reverse.

### Spring examples

Build two distinct, small runnable examples tied to the diagrams: a Cart operation (add/update/read) and a Customer/Item operation (e.g., register/update customer or list an item). Use Spring Boot with in-memory repositories so no database or credentials are needed. Include source, build/run command, HTTP requests, expected responses, and captured real output. Explain how controller, model, and DAO/repository map to the design. If package download/build fails, preserve exact output and describe the limit rather than fabricate screenshots.

## 5. Execution sequence

1. **Trace and baseline (fast):** inventory all `.vpp` diagrams/classes/relations and inspect both original images; identify the version with most useful data. Preserve originals. Record a before/after defect list. Do this before spending time on the report.
2. **Write this brief:** retain exact source paths, model choices, diagram list, evidence list, and acceptance checks. Update this document if a discovered tool constraint changes the method or scope.
3. **Repair analysis:** open the selected source in Visual Paradigm, Save As to the final analysis path, fix names/types/associations, save, reopen, export a clean full diagram image.
4. **Repair data model:** Save As to the final data path, fix multiplicities and relationship labels, implement key/ORM rules, save/reopen/export. Check relation-end semantics and no duplicate generic IDs.
5. **Construct design in Visual Paradigm:** Save As the data model into `eComDesign/eComDesign.vpp`; build the four transformations and detail diagrams using the native editor or its Open API inside the running app. Export each as PNG/SVG/PDF from VP and inspect legibility.
6. **Implement and run the two Spring examples:** build, launch locally, exercise requests, capture terminal and response evidence.
7. **Capture submission evidence:** screenshot the actual directory tree and the final project open in VP. Copy selected images to `report/figures` without editing their modeling content.
8. **Write LaTeX report:** English, black text on white pages; title/abstract, requirements interpretation, previous-model fixes, domain/relationship table, DAO/MVC explanation, four steps and figures, Spring source extracts and run results, folder evidence, limitations, references. Compile and inspect each page for clipped diagrams and legibility.
9. **Final verification:** check every `.vpp` opens in Visual Paradigm, all referenced figures exist, PDF compiles without broken references, two examples run, and final folder screenshot matches disk. List any demonstrable unmet criterion explicitly.

## 6. Acceptance checks

| ID | Observable result | Verification | Priority |
| --- | --- | --- | --- |
| AC-001 | All three named `.vpp` files exist, open in VP, and contain diagrams appropriate to their phase | VP open/reopen plus project inventory | Required |
| AC-002 | Analysis repair has consistent names, attributes, domain relations, and no ambiguous `refers to` crossings | Inspect native diagram and exported image | Required |
| AC-003 | Data model shows end multiplicities, relation labels, ORM/key handling, and an explanation of `1..*` and `1..1` | VP image plus report table | Required |
| AC-004 | Design contains all four specified steps, native class elements, DAO for Cart/Customer/Item, and MVC packages with Order/Payment/Shipment | VP model inspection and six exports | Required |
| AC-005 | The two Java/Spring examples build, run, and produce captured responses matching the report | Build log and local HTTP calls | Required |
| AC-006 | Report PDF is English, readable, white background/black text, includes clean VP exports and actual folder screenshot | PDF page inspection/text extraction | Required |
| AC-007 | Original previous-version `.vpp` and `.bak` files remain recoverable, and final deliverables are clearly distinguished | File inventory/hash comparison | Required |

## 7. Tools, traceability, and reporting rules

- Visual Paradigm Community Edition 18.0 is installed locally. Its project files are SQLite containers with model and diagram definitions. Official VP documentation describes the Open API for native class diagram editing and `ExportDiagramImage` CLI for diagram image export. Use the application's native save/render path and verify the result in the GUI.
- MiKTeX `xelatex`/`latexmk` and Python with PyMuPDF are installed. Use LaTeX for the report and PyMuPDF only for inspection/render verification.
- Trace old `Product` -> design `Item`, old `Shipping` -> design `Shipment`, old `payment` -> `Payment`, and old `CartItem`/`OrderItem` -> association entities. Explain each semantic change in the report.
- Treat the embedded screenshots in the current PDF as examples, not as proof of this project's completed diagrams. They contain only partial Cart work and no Customer/Item DAO or complete MVC realization.
- Cite the two assignment PDFs as local primary sources and Visual Paradigm/Spring official documentation for product/framework behavior. No invented run output, screenshots, relationships, or source claims.
