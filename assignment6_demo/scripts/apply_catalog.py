"""Import the visually reviewed 48-photo expansion, preserving the original 12 SKUs.

Requires runtime/import-work/photo-review.json: reviewed product IDs and SHA256s.
Run without --apply to validate a complete private staging copy first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    from app.data.product_repository import ProductRepository

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    proposal = ROOT / "runtime/import-work"
    products = read(proposal / "products-proposed.json")
    assets = read(proposal / "image-sources-proposed.json")["assets"]
    review = read(proposal / "photo-review.json")
    baseline = read(ROOT / "data/products.json")
    baseline_assets = read(ROOT / "data/image_sources.json")["assets"]
    new_ids = {f"P{number:03d}" for number in range(13, 61)}
    if len(products) != 48 or {p["product_id"] for p in products} != new_ids:
        raise ValueError("Expected exactly P013–P060, with no duplicate IDs.")
    if len(assets) != 48 or {a["product_id"] for a in assets} != new_ids:
        raise ValueError("Missing or duplicate asset provenance.")
    by_id = {item["product_id"]: item for item in baseline}
    base_asset_by_id = {item["product_id"]: item for item in baseline_assets}
    if not {f"P{n:03d}" for n in range(1, 13)} <= by_id.keys():
        raise ValueError("The original twelve products must exist.")
    reviewed = {item["product_id"]: item for item in review["photos"]}
    if set(reviewed) != new_ids or len(review["photos"]) != 48:
        raise ValueError("Every new image needs an explicit visual-review record.")
    for asset in assets:
        product_id = asset["product_id"]
        source = proposal / "images" / f"{product_id}.jpg"
        if not source.resolve().is_relative_to(proposal.resolve()):
            raise ValueError("Image source escaped the import workspace.")
        content = source.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        record = reviewed[product_id]
        if checksum != asset["sha256"] or len(content) != asset["bytes"]:
            raise ValueError(f"Image changed after acquisition: {product_id}")
        if record["sha256"] != checksum or record["status"] != "passed" or not record.get("notes"):
            raise ValueError(f"Missing reviewed photograph evidence: {product_id}")
        asset.update(real_photo_review="passed", review_evidence=review["evidence"], review_notes=record["notes"])
        if product_id in base_asset_by_id and base_asset_by_id[product_id]["sha256"] != checksum:
            raise ValueError(f"Refusing to replace an existing product image: {product_id}")
        base_asset_by_id[product_id] = asset
    for product in products:
        if any("Chờ kiểm tra" in str(value) or "sẽ được cập nhật" in str(value) for value in product.values()):
            raise ValueError(f"Unfinished metadata: {product['product_id']}")
        if product["product_id"] in by_id and by_id[product["product_id"]] != product:
            raise ValueError("Existing product snapshots differ; refusing silent overwrite.")
        by_id[product["product_id"]] = product
    combined = sorted(by_id.values(), key=lambda product: product["product_id"])
    manifest = {"schema_version": 1, "assets": sorted(base_asset_by_id.values(), key=lambda asset: asset["asset_id"])}
    counts = Counter(product["category"] for product in combined)
    if len(combined) != 60 or len(counts) != 12 or any(not 4 <= count <= 6 for count in counts.values()):
        raise ValueError("Expected 60 products in twelve categories, four to six each.")
    if len({a["sha256"] for a in manifest["assets"]}) != 60:
        raise ValueError("Duplicate product photograph hashes are forbidden.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    staging = ROOT / "runtime" / f"catalog-validation-{stamp}"
    (staging / "data/images").mkdir(parents=True)
    for product in combined:
        source = ROOT / product["image_path"] if product["product_id"] not in new_ids else proposal / "images" / f"{product['product_id']}.jpg"
        shutil.copyfile(source, staging / "data/images" / f"{product['product_id']}.jpg")
    write(staging / "data/products.json", combined)
    write(staging / "data/image_sources.json", manifest)
    ProductRepository(staging)  # Full schema, NFC, path, checksum, credit and image decoding validation.
    if args.apply:
        backup = ROOT / "runtime/import-backups" / stamp
        backup.mkdir(parents=True)
        for name in ("products.json", "image_sources.json"):
            shutil.copyfile(ROOT / "data" / name, backup / name)
        for product_id in sorted(new_ids):
            destination = ROOT / "data/images" / f"{product_id}.jpg"
            if not destination.exists():
                shutil.copyfile(proposal / "images" / f"{product_id}.jpg", destination)
            elif hashlib.sha256(destination.read_bytes()).hexdigest() != base_asset_by_id[product_id]["sha256"]:
                raise ValueError(f"Refusing to overwrite different image bytes: {product_id}")
        try:
            for name in ("image_sources.json", "products.json"):
                temporary = ROOT / "data" / f".{name}.{stamp}.tmp"
                shutil.copyfile(staging / "data" / name, temporary)
                os.replace(temporary, ROOT / "data" / name)
            ProductRepository(ROOT)
        except BaseException:
            for name in ("products.json", "image_sources.json"):
                shutil.copyfile(backup / name, ROOT / "data" / name)
            raise
    print(json.dumps({"applied": args.apply, "products": len(combined), "categories": dict(counts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
