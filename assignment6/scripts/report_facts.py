"""Generate report tables/listings from authoritative artifacts, never fabricated results."""

import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def escape(value):
    mapping = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
               "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(mapping.get(char, char) for char in str(value))


def table(headers, rows, widths):
    columns = "".join(r">{\raggedright\arraybackslash}p{" + width + "}" for width in widths)
    header = " & ".join(r"\textbf{" + escape(h) + "}" for h in headers) + r" \\"
    body = [r"\begingroup\small\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.2}",
            r"\begin{longtable}{" + columns + "}", r"\toprule", header, r"\midrule\endfirsthead",
            r"\toprule", header, r"\midrule\endhead", r"\bottomrule\endfoot"]
    body += [" & ".join(escape(cell) for cell in row) + r" \\" for row in rows]
    return "\n".join(body + [r"\end{longtable}\endgroup"])


def prepare_report_inputs(root, work):
    root, work = Path(root).resolve(), Path(work).resolve()
    hashes = {}

    def load(relative):
        path = root / relative
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return json.loads(path.read_text(encoding="utf-8-sig"))

    products = load("data/products.json")
    orders = load("data/orders.json")
    metrics = load("artifacts/evaluation/metrics.json")
    rows = load("artifacts/evaluation/results.json")
    truth = load("evaluation/queries.json")
    demos = load("artifacts/demo/demo_results.json")
    junit_path = root / "artifacts/tests/junit.xml"
    junit = ET.parse(junit_path).getroot()
    suites = [junit] if junit.tag == "testsuite" else list(junit.iter("testsuite"))
    tests = {k: sum(int(s.get(k, 0)) for s in suites) for k in ["tests", "failures", "errors", "skipped"]}
    coverage = load("artifacts/tests/coverage.json")["totals"]
    tests.update(application_data_coverage=coverage["percent_covered"], statements=coverage["num_statements"])
    if tests["failures"] or tests["errors"] or tests["skipped"]:
        raise ValueError("Test evidence is not fully passing")
    if {r["id"] for r in rows} != {q["id"] for q in truth["queries"]}:
        raise ValueError("Evaluation rows do not match the frozen query set")
    if metrics["ground_truth_sha256"] != hashes["evaluation/queries.json"]:
        raise ValueError("Frozen ground truth fingerprint mismatch")
    for group, summary in metrics["groups"].items():
        selected = [r for r in rows if r["group"] == group]
        successful = sum(bool(r["success"]) for r in selected)
        if (summary["total"], summary["successful"], summary["success_rate"]) != (
            len(selected), successful, successful / len(selected)
        ):
            raise ValueError("Evaluation summary mismatch: " + group)
    primary = metrics["groups"]["primary"]
    if (metrics["total_queries"], metrics["successful_queries"], metrics["success_rate"]) != (
        primary["total"], primary["successful"], primary["success_rate"]
    ):
        raise ValueError("Primary denominator mismatch")

    def write(name, content):
        (work / name).write_text(content + "\n", encoding="utf-8")

    write("query_example.json", json.dumps(demos[0]["query"], indent=2, ensure_ascii=False))
    write("result_example.json", json.dumps(demos[0]["results"][0], indent=2, ensure_ascii=False))

    def macro(name, value):
        return "\\newcommand{\\" + name + "}{" + escape(value) + "}"

    write("facts.tex", "\n".join([
        macro("ProductCount", len(products)), macro("OrderCount", len(orders)),
        macro("TestCount", tests["tests"]), macro("StatementCount", tests["statements"]),
        macro("CoveragePercent", f"{tests['application_data_coverage']:.2f}%"),
        macro("MeanLatency", f"{metrics['timing_ms']['mean']:.3f}"),
        macro("PninetyfiveLatency", f"{metrics['timing_ms']['p95']:.3f}"), macro("EvaluationRowCount", len(rows)),
    ]))
    write("products_table.tex", table(
        ["ID", "Product", "Category / color", "USD", "Stock"],
        [(p["product_id"], p["name"], p["category"] + " / " + p["color"], f"{p['price']:.2f}", p["stock"]) for p in products],
        ["0.7cm", "6.0cm", "4.0cm", "1.4cm", "1.1cm"]))
    write("orders_table.tex", table(
        ["Order", "Customer", "Date", "Status", "Total USD"],
        [(o["order_id"], o["customer_id"], o["date"], o["status"], f"{o['total']:.2f}") for o in orders],
        ["1.7cm", "2.0cm", "2.8cm", "4.4cm", "2.3cm"]))
    write("metrics_table.tex", table(
        ["Evaluation group", "Cases", "Successful", "Success rate"],
        [(group.title(), m["total"], m["successful"], f"{100*m['success_rate']:.2f}%") for group, m in metrics["groups"].items()],
        ["6cm", "2cm", "2.5cm", "3.0cm"]))
    write("mode_table.tex", table(
        ["Primary modality", "Cases", "Successful", "Top-1 success"],
        [(mode.title(), m["total"], m["successful"], f"{100*m['success_rate']:.2f}%") for mode, m in metrics["by_mode"].items()],
        ["6cm", "2cm", "2.5cm", "3cm"]))
    result_rows = []
    ground_truth = {q["id"]: q for q in truth["queries"]}
    for r in rows:
        q = ground_truth[r["id"]]
        input_text = q.get("query") or q.get("image") or q.get("order_id") or "zero vector (88D)"
        if q.get("query") == "":
            input_text = "empty text"
        expectation = ", ".join(map(str, q.get("relevant_ids", [])))
        if not expectation:
            expectation = q.get("expected_order") or next(
                (text for key, text in [("expected_error", "expected error"), ("expected_empty_order", "empty order"),
                                       ("expected_zero_scores", "zero scores")] if q.get(key)), "empty results")
        actual = str(r["top_1_product_id"]) if r["top_1_product_id"] is not None else (
            "error" if r.get("error") else r.get("actual_order_id") or "none")
        result_rows.append((r["id"], r["mode"], input_text, expectation, actual, "PASS" if r["success"] else "FAIL"))
    write("evaluation_table.tex", table(
        ["ID", "Mode", "Input", "Relevant / expected", "Actual top-1", "Verdict"], result_rows,
        ["0.65cm", "1.7cm", "5.0cm", "3.25cm", "1.5cm", "1.2cm"]))
    demo_sections = []
    for demo in demos:
        mode = demo["query"]["type"]
        demo_sections.append(r"\subsubsection{" + escape(mode.title()) + " demonstration output}")
        if "results" in demo:
            raw_input = demo["query"]["raw_input"].replace(str(root) + "\\", "").replace(str(root) + "/", "")
            demo_sections.append(r"\textbf{Input:} \texttt{" + escape(raw_input) + "}.")
            processing = demo["processing"]
            demo_sections.append(escape(
                f"Normalized query: {processing['normalized_query'] or '(image only)'}. "
                f"Tokens: {', '.join(processing['tokens']) or 'none'}. "
                f"Candidates before / after filtering: {processing['candidates_before_filter']} / "
                f"{processing['candidates_after_filter']}; top-k: {processing['top_k']}. "
                f"Category: {processing['filters']['category'] or 'none'}; "
                f"text/image weights: {processing['ranking_weights']['text']} / {processing['ranking_weights']['image']}."
            ))
            demo_sections.append(table(
                ["Rank / ID", "Product", "Text", "Image", "Final"],
                [(f"{p['rank']} / {p['product_id']}", p["name"], f"{p['text_score']:.6f}",
                  f"{p['image_score']:.6f}", f"{p['final_score']:.6f}") for p in demo["results"]],
                ["1.5cm", "6.0cm", "2.0cm", "2.0cm", "2.0cm"]))
        else:
            demo_sections.append("Order O001 belongs to C001; observed status: " + escape(demo["order"]["status"]) +
                                 ", total USD " + escape(demo["order"]["total"]) + ".")
    write("demo_tables.tex", "\n".join(demo_sections))

    figures = [f"artifacts/diagrams/{name}.png" for name in ["use_case", "three_layer_architecture", "voice_sequence"]]
    figures += [p.relative_to(root).as_posix() for p in sorted((root / "artifacts/screenshots").glob("*.png"))]
    figures += [p["image"] for p in products]
    figures += ["data/queries/" + name + ".png" for name in ["black_shoe_query", "blue_shoe_query", "brown_bag_query"]]
    galleries = []
    for start in range(0, len(products), 6):
        galleries.append(r"\begin{figure}[p]\centering")
        for i, product in enumerate(products[start:start+6]):
            galleries.append(r"\begin{minipage}[t]{0.31\textwidth}\centering\includegraphics[width=\linewidth]{" +
                             product["image"] + "}\\\\[3pt]\\small " +
                             escape(f"{product['product_id']:02d}. {product['name']}") + r"\end{minipage}")
            galleries.append(r"\hfill" if i % 3 != 2 else r"\par\vspace{10pt}")
        galleries.append(r"\caption{Original synthetic catalogue illustrations, products " + str(start+1) +
                         "--" + str(min(start+6, len(products))) + r". Images are preserved from the approved dataset.}\end{figure}")
    write("catalogue_gallery.tex", "\n".join(galleries))

    listings, listing_tex = [], []
    groups = {
        "Entry point and presentation": [root / "main.py", *sorted((root / "presentation").glob("*.py"))],
        "Application and intelligence": sorted((root / "application").glob("*.py")),
        "Data access and vector index": sorted((root / "data").glob("*.py")),
        "Dataset, evaluation, report and delivery utilities": sorted((root / "scripts").glob("*.py")),
        "Desktop evidence and Visual Paradigm launcher": sorted((root / "scripts/desktop").glob("*.py")),
        "Complete automated test suite": sorted((root / "tests").glob("*.py")),
    }
    for heading, paths in groups.items():
        listing_tex.append((r"\clearpage" if listings else "") + r"\subsection{" + heading + "}")
        for path in paths:
            relative = path.relative_to(root).as_posix()
            snapshot = work / "code_snapshot" / relative
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, snapshot)
            data = path.read_bytes()
            hashes[relative] = hashlib.sha256(data).hexdigest()
            record = {"path": relative, "lines": len(data.decode("utf-8-sig").splitlines()), "sha256": hashes[relative]}
            listings.append(record)
            listing_tex.append(r"\subsubsection{\texorpdfstring{\texttt{" + escape(relative) + "}}{" + escape(relative) + "}}")
            listing_tex.append("This listing contains the complete file (" + str(record["lines"]) + " source lines).")
            listing_tex.append(r"\CodeFile{" + escape(relative) + "}{" + snapshot.relative_to(root).as_posix() + "}")
    write("python_listings.tex", "\n".join(listing_tex))
    fixture_tex = []
    for relative in ["data/products.json", "data/orders.json", "data/dataset_metadata.json", "evaluation/queries.json",
                     "requirements.txt", "requirements-dev.txt", "requirements-automation.txt", "pyproject.toml"]:
        hashes[relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        fixture_tex.append(r"\subsection{\texorpdfstring{\texttt{" + escape(relative) + "}}{" + escape(relative) + "}}")
        fixture_tex.append(r"\lstinputlisting[language={},caption={" + escape(relative) + "}]{" + relative + "}")
    write("fixture_listings.tex", "\n".join(fixture_tex))
    preserved = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                 for name in figures + ["models/Assignment_06_Multimodal_Search.vpp"]}
    hashes.update(preserved)
    hashes["artifacts/tests/junit.xml"] = hashlib.sha256(junit_path.read_bytes()).hexdigest()
    (work / "listing_manifest.json").write_text(json.dumps(listings, indent=2) + "\n", encoding="utf-8")
    return {"input_sha256": hashes, "figures": figures, "python_listings": listings,
            "preserved_assets": preserved, "evaluation": metrics, "tests": tests}
