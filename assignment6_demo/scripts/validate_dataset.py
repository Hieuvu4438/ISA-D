"""Validate demo data, downloaded-photo provenance, checksums and order totals."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    from app.data.order_repository import OrderRepository
    from app.data.product_repository import ProductRepository

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    products = ProductRepository(root)
    orders = OrderRepository(root)
    manifest = json.loads((root / "data/image_sources.json").read_text(encoding="utf-8"))
    assets = {asset["asset_id"]: asset for asset in manifest["assets"]}
    records = []
    for product in products.products:
        asset = assets[product["image_asset_id"]]
        path = root / product["image_path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != asset["sha256"] or path.stat().st_size != asset["bytes"]:
            raise ValueError(f"Checksum/size mismatch: {product['product_id']}")
        if asset.get("real_photo_review") != "passed":
            raise ValueError(f"Missing photo review: {product['product_id']}")
        for field in ("source_page", "download_url", "author", "license", "license_url"):
            if not asset.get(field):
                raise ValueError(f"Missing provenance {field}: {product['product_id']}")
        records.append({"product_id": product["product_id"], "sha256": digest})
    report = {
        "status": "passed",
        "product_count": len(products.products),
        "order_count": len(orders.orders),
        "catalog_fingerprint": products.fingerprint,
        "photos": records,
    }
    query_manifest = root / "evaluation/query_image_sources.json"
    if query_manifest.is_file():
        query_assets = json.loads(query_manifest.read_text(encoding="utf-8"))["assets"]
        for asset in query_assets:
            path = (root / asset["local_path"]).resolve()
            if not path.is_relative_to(root / "data/queries"):
                raise ValueError("Query photo path must stay under data/queries")
            if (
                hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]
                or path.stat().st_size != asset["bytes"]
            ):
                raise ValueError(f"Query photo checksum mismatch: {asset['asset_id']}")
            if asset.get("real_photo_review") != "passed" or not all(
                asset.get(key) for key in ("source_page", "author", "license", "license_url")
            ):
                raise ValueError(f"Query photo provenance missing: {asset['asset_id']}")
        report["query_photo_count"] = len(query_assets)
    target = root / "artifacts/backend/dataset-validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "photos"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
