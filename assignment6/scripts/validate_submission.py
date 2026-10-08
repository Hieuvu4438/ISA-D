"""Verify assignment deliverables from files and actual service behaviour."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pymupdf as fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.product_repository import ProductRepository
from data.vector_index import VectorIndex

REQUIRED = [
    "README.md",
    "main.py",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "docs/requirements.md",
    "docs/use_cases.md",
    "docs/architecture.md",
    "docs/traceability.md",
    "docs/report.md",
    "docs/report.tex",
    "docs/report_requirements_audit.md",
    "docs/decisions_and_limitations.md",
    "docs/testing/prototype.tdd.md",
    "data/products.json",
    "data/orders.json",
    "data/embeddings.json",
    "evaluation/queries.json",
    "models/Assignment_06_Multimodal_Search.vpp",
    "artifacts/report/Assignment_06_Report.pdf",
    "artifacts/diagrams/use_case.png",
    "artifacts/diagrams/three_layer_architecture.png",
    "artifacts/diagrams/voice_sequence.png",
    "artifacts/screenshots/vp_use_case.png",
    "artifacts/screenshots/vp_architecture.png",
    "artifacts/screenshots/vp_sequence.png",
    "artifacts/screenshots/demo_text.png",
    "artifacts/screenshots/demo_voice.png",
    "artifacts/screenshots/demo_image.png",
    "artifacts/demo/demo_output.txt",
    "artifacts/demo/demo_results.json",
    "artifacts/evaluation/metrics.json",
    "artifacts/evaluation/results.json",
    "artifacts/evaluation/results.csv",
    "artifacts/tests/junit.xml",
    "artifacts/tests/coverage.json",
    "artifacts/tests/test_output.txt",
    "artifacts/tests/lint.txt",
    "artifacts/tests/typecheck.txt",
    "artifacts/tests/pip-check.txt",
    "artifacts/automation/model_inventory.json",
    "artifacts/automation/reopened_inventory.json",
    "artifacts/automation/verify_result.txt",
    "scripts/prepare_dataset.py",
    "scripts/build_index.py",
    "scripts/run_evaluation.py",
    "scripts/build_report.py",
    "scripts/report_facts.py",
    "scripts/validate_submission.py",
    "scripts/package_submission.py",
]


def load_json(root, relative):
    return json.loads((root / relative).read_text(encoding="utf-8-sig"))


def read_evidence_text(path):
    data = path.read_bytes()
    return data.decode("utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")


def validate(root=ROOT):
    root = Path(root).resolve()
    checks = []

    def check(name, function):
        try:
            details = function()
            checks.append({"name": name, "passed": True, "details": details})
        except (
            AssertionError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            ET.ParseError,
            fitz.FileDataError,
            fitz.FileNotFoundError,
        ) as exc:
            checks.append({"name": name, "passed": False, "error": str(exc)})

    def required_files():
        missing = [p for p in REQUIRED if not (root / p).is_file() or (root / p).stat().st_size == 0]
        assert not missing, "Missing or empty required files: " + ", ".join(missing)
        assert list((root / "tests").glob("test_*.py")), "No tests present"
        return {"required_files": len(REQUIRED)}

    check("Required submission groups and evidence", required_files)

    def catalogue_and_index():
        products = ProductRepository(root=root).all_products()
        assert len(products) >= 10, "Fewer than 10 products"
        index = VectorIndex(root / "data/embeddings.json", products, root)
        for product in products:
            with Image.open(root / product["image"]) as image:
                image.verify()
        return {"products": len(products), "encoder": index.encoder, "source_fingerprint_valid": True}

    check("Dataset, real images, and matching pixel index", catalogue_and_index)

    def report():
        report_path = root / "artifacts/report/Assignment_06_Report.pdf"
        assert report_path.is_file(), "Final PDF is not present yet"
        with fitz.open(report_path) as pdf:
            assert len(pdf) >= 11, f"Detailed report is unexpectedly short: {len(pdf)} pages"
            empty = [i + 1 for i in range(len(pdf)) if not str(pdf[i].get_text("text")).strip()]
            assert not empty, f"Empty report pages: {empty}"
            embedded_images = sum(len(pdf[i].get_images()) for i in range(len(pdf)))
            audit = load_json(root, "artifacts/report/build_audit.json")
            assert audit["format"] == "assignment06-latex-report-v2", "Expected the complete LaTeX report"
            assert audit["pages"] == len(pdf) and audit["language"] == "English"
            assert hashlib.sha256(report_path.read_bytes()).hexdigest() == audit["pdf_sha256"], "Stale PDF audit"
            for relative, expected in audit["input_sha256"].items():
                assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, f"Stale report source: {relative}"
            assert audit["all_required_sections_present"] and len(audit["section_pages"]) == 11
            assert audit["approved_UML_and_images_unchanged"] and audit["latex_layout_and_references_clean"]
            assert audit["all_approved_image_pixels_matched"] and len(audit["figure_xrefs"]) == 25
            assert not audit["nonblack_text"] and not audit["text_outside_safe_bounds"]
            assert all(audit["embedded_fonts"].values()), "Unembedded report font"
            assert embedded_images >= 25 and audit["unique_embedded_images"] >= 25, "Missing approved figures"
            paths = {r["path"] for r in audit["python_listings"]}
            actual = {p.relative_to(root).as_posix() for folder in ["application", "presentation", "data", "scripts", "tests"]
                      for p in (root / folder).rglob("*.py") if "__pycache__" not in p.parts}
            actual.add("main.py")
            assert paths == actual, "Complete Python listing inventory is missing files"
            return {"pages": len(pdf), "embedded_images": embedded_images, "nonempty_text_pages": True,
                    "English_LaTeX": True, "full_Python_files": len(paths), "page_limit": None}

    check("Complete English LaTeX PDF, full Python listings and approved visual evidence", report)

    def diagrams_and_screenshots():
        relatives = [p for p in REQUIRED if p.endswith(".png")]
        sizes = {}
        for relative in relatives:
            with Image.open(root / relative) as image:
                assert image.width >= 400 and image.height >= 250, f"Unreadably small image: {relative}"
                sizes[relative] = [image.width, image.height]
                image.verify()
        return sizes

    check("UML exports and real screenshot image files", diagrams_and_screenshots)

    def native_model_evidence():
        path = root / "models/Assignment_06_Multimodal_Search.vpp"
        assert path.stat().st_size > 10_000, "VPP is unexpectedly small"
        inventory = load_json(root, "artifacts/automation/model_inventory.json")
        reopened = load_json(root, "artifacts/automation/reopened_inventory.json")
        assert inventory == reopened, "Final inventory differs from reopened project inventory"
        assert "PASS reopened native diagrams=3" in read_evidence_text(
            root / "artifacts/automation/verify_result.txt"
        ), "Native project reopen did not pass"
        diagrams = {d["name"]: d for d in inventory["diagrams"]}
        expected = {"UC_Multimodal_Ecommerce_Search", "CMP_Three_Layer_Architecture", "SEQ_Voice_Product_Search"}
        assert expected <= diagrams.keys(), "Required native diagrams are missing"
        uc = diagrams["UC_Multimodal_Ecommerce_Search"]
        names = {s["name"] for s in uc["shapes"]}
        assert {
            "Customer",
            "Search Product",
            "Search by Keyword",
            "Search by Voice",
            "Search by Image",
            "Search Order",
            "View Product",
            "View Order",
        } <= names, "Required actor/use cases missing"
        generalizations = [c for c in uc["connectors"] if c["type"] == "Generalization"]
        associations = [c for c in uc["connectors"] if c["type"] == "Association"]
        # VP API Generalization.from is the general end, where the triangle points.
        assert len(generalizations) == 3 and {(c["from"], c["to"]) for c in generalizations} == {
            ("Search Product", mode) for mode in ["Search by Keyword", "Search by Voice", "Search by Image"]
        }, "Incorrect use-case general/special ends"
        assert len(associations) == 4 and {(c["from"], c["to"]) for c in associations} == {
            ("Customer", name) for name in ["Search Product", "Search Order", "View Product", "View Order"]
        }, "Incorrect Customer associations"
        component = diagrams["CMP_Three_Layer_Architecture"]
        package_names = {s["name"] for s in component["shapes"] if s["type"] == "Package"}
        assert {"Presentation Layer", "Application / Intelligence Layer", "Data Layer"} <= package_names, (
            "Required layer packages missing"
        )
        ownership = {s["name"]: s["parent"] for s in component["shapes"] if s["type"] == "Component"}
        expected_ownership = {
            **{name: "Presentation Layer" for name in ["SearchUI", "VoiceInput", "ImageUpload", "SearchResultView"]},
            **{
                name: "Application / Intelligence Layer"
                for name in [
                    "QueryService",
                    "SpeechService",
                    "ImageService",
                    "SearchService",
                    "RankingService",
                    "OrderService",
                ]
            },
            **{
                name: "Data Layer"
                for name in [
                    "ProductRepository",
                    "OrderRepository",
                    "VectorIndex",
                    "ProductDatabase",
                    "OrderDatabase",
                    "ImageStorage",
                ]
            },
        }
        assert ownership == expected_ownership, "Incorrect component names/package ownership"
        forbidden = [
            c
            for c in component["connectors"]
            if c["type"] == "Dependency"
            and ownership.get(c["from"]) == "Presentation Layer"
            and ownership.get(c["to"]) == "Data Layer"
        ]
        assert not forbidden, "Direct Presentation-to-Data dependency found"
        seq = diagrams["SEQ_Voice_Product_Search"]
        participant_types = Counter(s["type"] for s in seq["shapes"])
        assert (
            participant_types["InteractionActor"] == 1
            and participant_types["InteractionLifeLine"] == 6
            and participant_types["Activation"] == 6
        ), "Voice participants missing"
        messages = {c["name"] for c in seq["connectors"]}
        assert len(seq["connectors"]) == 14 and all(c["type"] == "Message" for c in seq["connectors"]), (
            "Voice sequence needs exactly 14 native messages"
        )
        assert {
            "transcribe(transcriptInput)",
            "voice_query(transcript)",
            "search(query)",
            "all_products()",
            "rank(candidates, query)",
        } <= messages, "Voice messages missing"
        return {
            "native_diagram_names": sorted(expected),
            "use_case_elements": len(names),
            "generalizations": len(generalizations),
            "customer_associations": len(associations),
            "component_package_ownership": ownership,
            "presentation_to_data_dependencies": len(forbidden),
            "voice_messages": len(seq["connectors"]),
            "voice_participant_counts": dict(participant_types),
            "note": "Inventory verifies native model types; GUI reopen/layout verification is recorded separately by root.",
        }

    check("Native VP model inventory and required UML semantics", native_model_evidence)

    def demos():
        payload = load_json(root, "artifacts/demo/demo_results.json")
        modes = {r["query"]["type"] for r in payload}
        assert {"text", "voice", "image", "multimodal", "order"} <= modes, "Required demo modalities missing"
        for item in payload:
            if "results" in item:
                assert item["results"] and item["processing"], "Demo needs actual processing/results"
                assert all("final_score" in r for r in item["results"]), "Ranking scores missing"
        assert "simulated speech-to-text" in read_evidence_text(root / "artifacts/demo/demo_output.txt"), (
            "Voice simulation is not disclosed"
        )
        return {"modes": sorted(modes), "queries": len(payload)}

    check("Three mandatory demo modes, fusion, order, and scores", demos)

    def evaluation():
        ground_truth = load_json(root, "evaluation/queries.json")
        metrics = load_json(root, "artifacts/evaluation/metrics.json")
        rows = load_json(root, "artifacts/evaluation/results.json")
        expected_sha = hashlib.sha256((root / "evaluation/queries.json").read_bytes()).hexdigest()
        assert metrics["ground_truth_sha256"] == expected_sha, "Evaluation used different labels"
        assert {c["id"] for c in ground_truth["queries"]} == {r["id"] for r in rows}, "Evaluation is missing cases"
        primary = [r for r in rows if r["group"] == "primary"]
        assert len(primary) >= 12, "At least 12 primary retrieval queries required"
        assert Counter(r["mode"] for r in primary) == {"text": 4, "voice": 4, "image": 4}, (
            "Primary mode breakdown incorrect"
        )
        for group, summary in metrics["groups"].items():
            selected = [r for r in rows if r["group"] == group]
            successful = sum(r["success"] for r in selected)
            assert summary["total"] == len(selected) and summary["successful"] == successful, (
                f"Incorrect {group} denominator/count"
            )
            assert abs(summary["success_rate"] - successful / len(selected)) < 1e-12, f"Incorrect {group} rate"
        assert metrics["total_queries"] == len(primary), "Primary metric denominator mismatch"
        assert metrics["successful_queries"] == sum(r["success"] for r in primary), "Primary numerator mismatch"
        assert metrics["incorrect_examples"], "Observed failure examples must be retained"
        return {
            "primary": metrics["groups"]["primary"],
            "separate_groups": metrics["groups"],
            "ground_truth_sha256": expected_sha,
        }

    check("Frozen ground truth, metrics, separate denominators, and failures", evaluation)

    def tests_and_checks():
        junit = ET.parse(root / "artifacts/tests/junit.xml").getroot()
        suites = [junit] if junit.tag == "testsuite" else list(junit.iter("testsuite"))
        total = sum(int(s.get("tests", 0)) for s in suites)
        failures = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
        skipped = sum(int(s.get("skipped", 0)) for s in suites)
        assert total >= 70 and failures == 0 and skipped == 0, (
            f"Unmet tests: total={total}, failures/errors={failures}, skipped={skipped}"
        )
        coverage = load_json(root, "artifacts/tests/coverage.json")["totals"]["percent_covered"]
        assert coverage >= 80, f"Application/data coverage {coverage} <80%"
        for path, marker in [
            ("lint.txt", "All checks passed!"),
            ("typecheck.txt", "0 errors"),
            ("pip-check.txt", "No broken requirements found"),
        ]:
            assert marker in read_evidence_text(root / "artifacts/tests" / path), f"{path} does not show PASS"
        return {"tests": total, "failures": failures, "skipped": skipped, "application_data_line_coverage": coverage}

    check("Test, coverage, lint, typecheck, and dependency consistency evidence", tests_and_checks)
    return {"passed": all(c["passed"] for c in checks), "root": str(root), "checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.root)
    serialized = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    raise SystemExit(0 if result["passed"] else 1)
