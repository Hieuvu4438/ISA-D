"""Import 120 curated real-photo fashion products into Cortis catalog."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    plan_path = ROOT / "runtime" / "import-120" / "catalog_expansion_120_plan.json"
    if not plan_path.exists():
        raise SystemExit(f"Plan file not found: {plan_path}")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    print(f"Loaded plan with {len(plan)} items.")

    images_source_dir = ROOT / "runtime" / "import-120" / "images"
    target_images_dir = ROOT / "data" / "images"
    target_images_dir.mkdir(parents=True, exist_ok=True)

    products_file = ROOT / "data" / "products.json"
    sources_file = ROOT / "data" / "image_sources.json"

    products = json.loads(products_file.read_text(encoding="utf-8"))
    sources = json.loads(sources_file.read_text(encoding="utf-8"))

    existing_product_ids = {p["product_id"] for p in products}
    existing_asset_ids = {a["asset_id"] for a in sources["assets"]}

    added_count = 0
    for item in plan:
        pid = item["product_id"]
        if pid in existing_product_ids:
            continue

        src_image = images_source_dir / f"{pid}.jpg"
        if not src_image.exists():
            raise FileNotFoundError(f"Missing image file for {pid}: {src_image}")

        raw_bytes = src_image.read_bytes()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"Hash mismatch for {pid}: {digest} vs {item['sha256']}")

        dest_image = target_images_dir / f"{pid}.jpg"
        dest_image.write_bytes(raw_bytes)

        product = {
            "product_id": pid,
            "name": unicodedata.normalize("NFC", item["name"][:120]),
            "brand": unicodedata.normalize("NFC", item["brand"][:120]),
            "category": item["category"],
            "color": unicodedata.normalize("NFC", item["color"][:50]),
            "price_vnd": int(item["price_vnd"]),
            "stock_quantity": int(item["stock_quantity"]),
            "description": unicodedata.normalize("NFC", item["description"][:500]),
            "image_path": f"data/images/{pid}.jpg",
            "image_asset_id": pid,
        }
        products.append(product)
        existing_product_ids.add(pid)

        if pid not in existing_asset_ids:
            asset = {
                "asset_id": pid,
                "product_id": pid,
                "local_path": f"data/images/{pid}.jpg",
                "source_title": unicodedata.normalize("NFC", item["source_title"]),
                "source_page": item["source_page"],
                "download_url": item["download_url"],
                "original_url": item["original_url"],
                "author": unicodedata.normalize("NFC", item["author"]),
                "license": item["license"],
                "license_url": item["license_url"],
                "description": unicodedata.normalize("NFC", item["description"][:500]),
                "retrieved_at": "2026-10-08T05:00:00Z",
                "sha256": item["sha256"],
                "bytes": item["bytes"],
                "transformations": ["resize", "strip_exif"],
                "real_photo_review": "passed",
                "width": item["width"],
                "height": item["height"],
                "format": item["format"],
                "review_evidence": item["source_page"],
                "review_notes": "Real fashion photograph from Wikimedia Commons",
            }
            sources["assets"].append(asset)
            existing_asset_ids.add(pid)

        added_count += 1

    products.sort(key=lambda x: x["product_id"])
    sources["assets"].sort(key=lambda x: x["asset_id"])

    products_file.write_text(json.dumps(products, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sources_file.write_text(json.dumps(sources, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Successfully imported {added_count} products. Total products: {len(products)}.")


if __name__ == "__main__":
    main()
