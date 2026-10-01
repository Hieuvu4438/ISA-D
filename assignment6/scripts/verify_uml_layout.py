"""Audit VP-exported geometry; sequence lifeline crossings are intentional UML."""

import argparse
import hashlib
from itertools import combinations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLACK = "java.awt.Color[r=0,g=0,b=0]"
VP_FILL = "java.awt.Color[r=122,g=207,b=245]"  # Observed native factory default.


def segments(points):
    return [(a, b) for a, b in zip(points, points[1:]) if a != b]


def intersection(first, second):
    a, b = first
    c, d = second
    horizontal = a[1] == b[1]
    other_horizontal = c[1] == d[1]
    if horizontal == other_horizontal:
        fixed, moving = (1, 0) if horizontal else (0, 1)
        if a[fixed] != c[fixed]:
            return None
        lo = max(min(a[moving], b[moving]), min(c[moving], d[moving]))
        hi = min(max(a[moving], b[moving]), max(c[moving], d[moving]))
        if lo < hi:
            return "collinear overlap"
        if lo == hi:
            return "touch"
        return None
    h, v = (first, second) if horizontal else (second, first)
    x, y = v[0][0], h[0][1]
    if min(h[0][0], h[1][0]) <= x <= max(h[0][0], h[1][0]) and min(
        v[0][1], v[1][1]
    ) <= y <= max(v[0][1], v[1][1]):
        return "crossing"
    return None


def penetrates(segment, bounds):
    a, b = segment
    x, y, w, h = bounds
    if a[1] == b[1]:
        return y < a[1] < y + h and max(min(a[0], b[0]), x) < min(
            max(a[0], b[0]), x + w
        )
    return x < a[0] < x + w and max(min(a[1], b[1]), y) < min(
        max(a[1], b[1]), y + h
    )


def semantic_signature(inventory):
    return {
        d["id"]: {
            "name": d["name"],
            "shapes": sorted(
                (s["id"], s["type"], s["name"], s["parent"]) for s in d["shapes"]
            ),
            "relationships": sorted(
                (c["id"], c["type"], c["name"], c["from"], c["to"])
                for c in d["connectors"]
            ),
        }
        for d in inventory["diagrams"]
    }


def audit(inventory, baseline=None):
    findings = []
    details = []
    expected = {"UC_": (9, 7), "SEQ_": (14, 14), "CMP_": (20, 15)}
    if len(inventory["diagrams"]) != 3:
        findings.append("Expected exactly three native diagrams")
    for diagram in inventory["diagrams"]:
        name = diagram["name"]
        prefix = next((p for p in expected if name.startswith(p)), None)
        if prefix is None or expected[prefix] != (
            len(diagram["shapes"]), len(diagram["connectors"])
        ):
            findings.append(f"{name}: unexpected object counts")
        for shape in diagram["shapes"]:
            if shape["fill"] != VP_FILL or any(
                shape[key] != BLACK for key in ("line_color", "font_color")
            ):
                findings.append(f"{name}: nondefault shape colors: {shape['name']}")
        for connector in diagram["connectors"]:
            label = f"{connector['from']} -> {connector['to']} ({connector['name']})"
            if any(connector[key] != BLACK for key in ("line_color", "font_color")):
                findings.append(f"{name}: nondefault connector colors: {label}")
            points = connector["points"]
            if len(points) < 2 or any(
                a[0] != b[0] and a[1] != b[1] for a, b in segments(points)
            ):
                findings.append(f"{name}: connector is not orthogonal: {label}")
        pair_findings = []
        # Lifelines intersect messages by design; audit only UC/component crossings.
        if prefix in {"UC_", "CMP_"}:
            for first, second in combinations(diagram["connectors"], 2):
                issues = {
                    hit
                    for a in segments(first["points"])
                    for b in segments(second["points"])
                    if (hit := intersection(a, b))
                }
                if issues:
                    pair_findings.append(
                        {"first": first["id"], "second": second["id"], "issues": sorted(issues)}
                    )
            for connector in diagram["connectors"]:
                for shape in diagram["shapes"]:
                    if shape["type"] in {"Package", "System", "NOTE"} or shape[
                        "name"
                    ] in {connector["from"], connector["to"]}:
                        continue
                    if any(penetrates(s, shape["bounds"]) for s in segments(connector["points"])):
                        findings.append(f"{name}: edge {connector['id']} crosses {shape['name']}")
            if pair_findings:
                findings.append(f"{name}: {len(pair_findings)} connector pairs cross/overlap/touch")
        details.append(
            {"diagram": name, "shapes": len(diagram["shapes"]),
             "connectors": len(diagram["connectors"]), "connector_conflicts": pair_findings}
        )
    unchanged = semantic_signature(baseline) == semantic_signature(inventory) if baseline else None
    if unchanged is False:
        findings.append("Native model IDs or UML semantics changed")
    return {
        "passed": not findings, "native_semantics_compared": baseline is not None,
        "native_semantics_unchanged": unchanged, "fill_default_observed_in_VP": "#7ACFF5",
        "outline_and_text_default": "#000000", "diagrams": details, "findings": findings,
        "scope": "Axis-aligned connectors in all diagrams; intersections and nonendpoint box penetration in UC/CMP. Sequence lifeline intersections are intentional.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=ROOT / "artifacts/automation/model_inventory.json")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/tests/uml_layout_audit.json")
    args = parser.parse_args()
    result = audit(json.loads(args.inventory.read_text(encoding="utf-8")),
                   json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None)
    result["inventory_sha256"] = hashlib.sha256(args.inventory.read_bytes()).hexdigest()
    native = ROOT / "models/Assignment_06_Multimodal_Search.vpp"
    result["native_project_sha256"] = hashlib.sha256(native.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
