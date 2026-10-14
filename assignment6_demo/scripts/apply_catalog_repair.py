"""Validate an explicit hash-bound visual review plan before updating catalog assets."""
import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.data.order_repository import OrderRepository
from app.data.product_repository import ProductRepository

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(root, plan, candidates):
    products = json.loads((root / "data/products.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "data/image_sources.json").read_text(encoding="utf-8"))
    by_id = {p["product_id"]: p for p in products}
    assets = {a["product_id"]: a for a in manifest["assets"]}
    candidates = {c["candidate_id"]: c for c in candidates}
    replacements, changes, ids = {}, [], set()
    for row in plan:
        pid = row["product_id"]
        if pid in ids or pid not in by_id or row["status"] != "passed" or not row.get("visual_notes"):
            raise ValueError("Missing/duplicate/invalid visual review record")
        ids.add(pid)
        product = by_id[pid]
        old = {"product": dict(product), "asset": dict(assets[pid])}
        candidate = candidates[row["candidate_id"]] if row.get("candidate_id") else None
        source = root / (candidate["local_path"] if candidate else product["image_path"])
        source = source.resolve()
        allowed = root / ("runtime/catalog-repair/images" if candidate else "data/images")
        if not source.is_relative_to(allowed.resolve()) or not source.is_file():
            raise ValueError("Repair source escaped allowed image directory")
        checksum = hashlib.sha256(source.read_bytes()).hexdigest()
        if row["sha256"] != checksum or candidate and candidate["sha256"] != checksum:
            raise ValueError("Image changed after visual review")
        if set(row["metadata"]) != {"name", "brand", "color", "description"}:
            raise ValueError("Only reviewed descriptive metadata may change")
        product.update(row["metadata"])
        if candidate:
            # Preserve canonical product ID and its local media route; format is decoded, not inferred from suffix.
            replacements[pid] = source
            assets[pid] = {**{key: candidate[key] for key in ("source_title", "source_page", "original_url", "download_url", "author", "license", "license_url", "retrieved_at", "sha256", "bytes", "format", "width", "height", "transformations")},
                          "asset_id": pid, "product_id": pid, "local_path": product["image_path"]}
        assets[pid].update(real_photo_review="passed", review_evidence="data/catalog_repair_review.json", review_notes=row["visual_notes"])
        changes.append({"product_id": pid, "before": old, "after": {"product": dict(product), "asset": dict(assets[pid])}, "visual_notes": row["visual_notes"]})
    manifest["assets"] = sorted(assets.values(), key=lambda a: a["asset_id"])
    return products, manifest, replacements, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plan = json.loads((ROOT / "data/catalog_repair_review.json").read_text(encoding="utf-8"))
    candidates = json.loads((ROOT / "data/catalog_repair_candidates.json").read_text(encoding="utf-8"))
    products, manifest, replacements, changes = prepare(ROOT, plan, candidates)
    with tempfile.TemporaryDirectory(prefix="repair-validation-", dir=ROOT / "runtime") as tmp:
        staging = Path(tmp)
        shutil.copytree(ROOT / "data", staging / "data")
        for pid, source in replacements.items():
            shutil.copyfile(source, staging / "data/images" / f"{pid}.jpg")
        write(staging / "data/products.json", products)
        write(staging / "data/image_sources.json", manifest)
        validated = ProductRepository(staging)
        OrderRepository(staging)
        report = {"applied": args.apply, "reviewed_product_count": len(changes), "replaced_image_count": len(replacements),
                  "catalog_fingerprint": validated.fingerprint, "changes": changes,
                  "full_catalog_visual_gate_verified": False, "index_rebuild_required": args.apply}
        if args.apply:
            backup = ROOT / "runtime/catalog-repair/backups" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            backup.mkdir(parents=True)
            shutil.copytree(ROOT / "data", backup / "data")
            try:
                for pid, source in replacements.items():
                    shutil.copyfile(source, ROOT / "data/images" / f"{pid}.jpg")
                write(ROOT / "data/products.json", products)
                write(ROOT / "data/image_sources.json", manifest)
                ProductRepository(ROOT)
                OrderRepository(ROOT)
            except Exception:
                shutil.copytree(backup / "data", ROOT / "data", dirs_exist_ok=True)
                raise
        target = ROOT / "artifacts/validation/catalog-repair-applied.json" if args.apply else ROOT / "artifacts/validation/catalog-repair-preview.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        write(target, report)
        print(json.dumps({k: v for k, v in report.items() if k != "changes"}))


if __name__ == "__main__":
    main()
