"""Repair publication guards with real reviewed files; no inference-quality claim."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("catalog_repair", ROOT / "scripts/apply_catalog_repair.py")
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def test_applied_review_metadata_hashes_and_provenance():
    import hashlib
    from app.data.product_repository import ProductRepository

    plan = json.loads((ROOT / "data/catalog_repair_review.json").read_text(encoding="utf-8"))
    repo = ProductRepository(ROOT)
    manifest = json.loads((ROOT / "data/image_sources.json").read_text(encoding="utf-8"))
    assets = {a["product_id"]: a for a in manifest["assets"]}
    for row in plan:
        product = repo.get_by_id(row["product_id"])
        assert all(product[key] == value for key, value in row["metadata"].items())
        assert hashlib.sha256((ROOT / product["image_path"]).read_bytes()).hexdigest() == row["sha256"]
        assert assets[row["product_id"]]["review_evidence"] == "data/catalog_repair_review.json"
        assert assets[row["product_id"]]["review_notes"] == row["visual_notes"]


def test_repair_rejects_unreviewed_duplicate_and_stale_hash(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    plan = json.loads((ROOT / "data/catalog_repair_review.json").read_text(encoding="utf-8"))
    row = next(r for r in plan if not r.get("candidate_id"))
    repair.prepare(tmp_path, [row], [])
    for bad in [dict(row, status="pending"), dict(row, sha256="0" * 64), dict(row, visual_notes=""), dict(row, metadata={**row["metadata"], "price_vnd": 1})]:
        with pytest.raises(ValueError):
            repair.prepare(tmp_path, [bad], [])
    with pytest.raises(ValueError):
        repair.prepare(tmp_path, [row, row], [])


def test_repair_candidate_cannot_escape_workspace(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    plan = json.loads((ROOT / "data/catalog_repair_review.json").read_text(encoding="utf-8"))
    row = next(r for r in plan if r.get("candidate_id"))
    candidate = {"candidate_id": row["candidate_id"], "local_path": "../outside.jpg", "sha256": row["sha256"]}
    with pytest.raises(ValueError, match="escaped"):
        repair.prepare(tmp_path, [row], [candidate])
