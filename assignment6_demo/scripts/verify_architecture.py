"""Check actual dependency directions without importing models or calling Azure."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inspect_source(relative, text):
    findings = []
    tree = ast.parse(text)
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        elif isinstance(node, ast.Import):
            names = [item.name for item in node.names]
        for name in names:
            if relative.startswith("data/") and name.startswith(("app.application", "app.main", "fastapi", "azure", "sentence_transformers")):
                findings.append({"file": relative, "line": node.lineno, "rule": "data_dependency_direction"})
            if relative == "domain.py" and name.startswith(("app.data", "app.application", "fastapi", "azure", "sentence_transformers")):
                findings.append({"file": relative, "line": node.lineno, "rule": "domain_independence"})
        if relative.startswith("data/") and isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"encode_texts", "encode_images", "validate_text", "recognize_once_async"}:
                findings.append({"file": relative, "line": node.lineno, "rule": "data_must_not_orchestrate_inference"})
    return findings


def main():
    assert inspect_source("data/example.py", "from app.application.search_service import SearchService")
    assert inspect_source("data/example.py", "encoder.encode_texts([])")
    app = ROOT / "backend/app"
    findings = []
    files = sorted(app.rglob("*.py"))
    for file in files:
        findings.extend(inspect_source(file.relative_to(app).as_posix(), file.read_text(encoding="utf-8")))
    report = {"passed": not findings, "scope": "AST import directions and Data inference orchestration; not full architecture conformance",
              "files_checked": len(files), "negative_fixtures_rejected": 2, "findings": findings,
              "limitations": ["No formal repository Protocol classes", "Order lookup remains in presentation helper",
                              "Image storage remains inside ProductRepository", "No Visual Paradigm .vpp artifact"]}
    (ROOT / "artifacts/backend/architecture.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
