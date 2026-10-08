"""Acquire an explicitly curated Wikimedia photo batch without changing the catalog.

Example:
  python scripts/import_catalog.py --plan runtime/import-work/catalog-plan.json

The plan is reviewed before download. Outputs stay in runtime/import-work; a
separate integration step is required after visual review. Images are downloaded
as published Wikimedia JPEGs, never generated, recolored, or re-encoded.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "CortisDemoAssetImporter/1.0 (educational demo; source attribution)"
API = "https://commons.wikimedia.org/w/api.php"


def clean(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]*>", " ", value)).strip()


def metadata_field(metadata: dict, key: str) -> str:
    return clean(metadata.get(key, {}).get("value", ""))


def request(session: requests.Session, url: str, **kwargs) -> requests.Response:
    for attempt in range(5):
        response = session.get(url, timeout=60, **kwargs)
        if response.status_code not in {429, 502, 503, 504}:
            response.raise_for_status()
            return response
        retry = response.headers.get("Retry-After", "")
        delay = min(int(retry), 120) if retry.isdigit() else 20 * (attempt + 1)
        print(f"Remote server busy; retry in {delay}s", flush=True)
        time.sleep(delay)
    response.raise_for_status()
    return response


def metadata(session: requests.Session, title: str) -> dict:
    response = request(
        session,
        API,
        params={
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "iiurlwidth": 960,
            "format": "json",
        },
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    if not page.get("imageinfo"):
        raise ValueError(f"Missing image metadata: {title}")
    return page


def contact_sheets(records: list[dict], output: Path) -> None:
    for offset in range(0, len(records), 16):
        batch = records[offset : offset + 16]
        sheet = Image.new("RGB", (1280, 1240), "#f6f5f3")
        draw = ImageDraw.Draw(sheet)
        for index, record in enumerate(batch):
            x, y = (index % 4) * 320, (index // 4) * 310
            image = Image.open(output / "images" / f"{record['product_id']}.jpg")
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((300, 258))
            sheet.paste(
                image, (x + (320 - image.width) // 2, y + 5 + (258 - image.height) // 2)
            )
            draw.text((x + 10, y + 268), record["product_id"], fill="#211c22")
            label = record["source_title"].replace("File:", "")
            draw.text((x + 10, y + 286), label[:43], fill="#211c22")
        sheet.save(output / f"contact-sheet-{offset // 16 + 1}.jpg", quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "runtime/import-work")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "runtime"):
        raise ValueError(
            "Acquisition output must stay under this project's runtime directory"
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "images").mkdir(exist_ok=True)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    existing_assets = json.loads(
        (ROOT / "data/image_sources.json").read_text(encoding="utf-8")
    )["assets"]
    prior_manifest = output / "image-sources-proposed.json"
    prior_assets = {}
    if prior_manifest.exists():
        prior_assets = {
            asset["product_id"]: asset
            for asset in json.loads(prior_manifest.read_text(encoding="utf-8"))[
                "assets"
            ]
        }
    planned_ids = {entry["product_id"] for entry in plan}
    if len(planned_ids) != len(plan):
        raise ValueError("The import plan contains duplicate product identifiers")
    comparison_assets = [
        asset for asset in existing_assets if asset["product_id"] not in planned_ids
    ]
    known_hashes = {asset["sha256"] for asset in comparison_assets}
    known_pages = {
        asset["source_page"].replace("_", " ") for asset in comparison_assets
    }
    records, products, assets, failures = [], [], [], []
    network_downloads, cached_downloads = 0, 0
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    for entry in plan:
        product_id = entry["product_id"]
        if not re.fullmatch(r"P[0-9]{3}", product_id):
            raise ValueError("Invalid planned product identifier")
        try:
            page = entry.get("wikimedia_metadata") or metadata(
                session, entry["source_title"]
            )
            if page["title"] != entry["source_title"]:
                raise ValueError(
                    "Cached source metadata does not match the requested file"
                )
            info = page["imageinfo"][0]
            meta = info.get("extmetadata", {})
            description = metadata_field(meta, "ImageDescription")
            if re.search(
                r"AI.generated|artificial intelligence|midjourney|stable diffusion|DALL.E|illustration|drawing|screenshot",
                description,
                re.IGNORECASE,
            ):
                raise ValueError(
                    "Source metadata indicates a non-photographic or generated asset"
                )
            source_page = info["descriptionurl"]
            if source_page.replace("_", " ") in known_pages:
                raise ValueError("Duplicate existing source page")
            author = metadata_field(meta, "Artist")
            license_name = metadata_field(meta, "LicenseShortName")
            license_url = metadata_field(meta, "LicenseUrl")
            if license_url.startswith("http://creativecommons.org/"):
                license_url = license_url.replace("http://creativecommons.org/", "https://creativecommons.org/", 1)
            if license_name == "Public domain" and not license_url:
                license_url = source_page + "#Licensing"
            if not author or not license_name or not license_url:
                raise ValueError("Incomplete reusable-image provenance")
            url = info.get("thumburl", info["url"]).split("?")[0]
            if urlparse(url).hostname not in {
                "upload.wikimedia.org",
                "thumb.wikimedia.org",
            }:
                raise ValueError("Unexpected image host")
            image_path = output / "images" / f"{product_id}.jpg"
            prior_asset = prior_assets.get(product_id, {})
            if (
                image_path.exists()
                and prior_asset.get("download_url") == url
                and hashlib.sha256(image_path.read_bytes()).hexdigest()
                == prior_asset.get("sha256")
            ):
                payload = image_path.read_bytes()
                cached_downloads += 1
            else:
                response = request(session, url)
                payload = response.content
                network_downloads += 1
                if len(payload) > 10 * 1024 * 1024:
                    raise ValueError("Photo exceeds acquisition size limit")
            image = Image.open(BytesIO(payload))
            image.load()
            if image.format != "JPEG" or min(image.size) < 250:
                raise ValueError("Expected a photographic JPEG of at least 250 px")
            digest = hashlib.sha256(payload).hexdigest()
            if digest in known_hashes:
                raise ValueError("Duplicate photo checksum")
            image_path.write_bytes(payload)
            known_hashes.add(digest)
            known_pages.add(source_page.replace("_", " "))
            asset = {
                "asset_id": product_id,
                "product_id": product_id,
                "local_path": f"data/images/{product_id}.jpg",
                "source_page": source_page,
                "download_url": url,
                "original_url": info["url"],
                "author": author,
                "license": license_name,
                "license_url": license_url,
                "description": description,
                "retrieved_at": datetime.now(UTC).date().isoformat(),
                "sha256": digest,
                "bytes": len(payload),
                "transformations": "Wikimedia thumbnail when available; no local visual edits",
                "real_photo_review": "pending",
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "review_evidence": "",
                "review_notes": "",
            }
            product = {
                key: entry[key]
                for key in [
                    "product_id",
                    "name",
                    "brand",
                    "category",
                    "color",
                    "price_vnd",
                    "stock_quantity",
                    "description",
                ]
            }
            product.update(image_path=asset["local_path"], image_asset_id=product_id)
            records.append({"product_id": product_id, "source_title": page["title"]})
            products.append(product)
            assets.append(asset)
            print(f"Acquired {product_id}: {page['title']}", flush=True)
            time.sleep(0.25)
        except (
            requests.RequestException,
            UnidentifiedImageError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as error:
            failures.append(
                {
                    "product_id": product_id,
                    "source_title": entry["source_title"],
                    "error": str(error),
                }
            )
            print(f"Failed {product_id}: {error}", flush=True)
    (output / "products-proposed.json").write_text(
        json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "image-sources-proposed.json").write_text(
        json.dumps(
            {"schema_version": 1, "assets": assets}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    (output / "download-report.json").write_text(
        json.dumps(
            {
                "acquired": len(products),
                "network_downloads": network_downloads,
                "cached_downloads": cached_downloads,
                "failures": failures,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    contact_sheets(records, output)
    print(
        json.dumps(
            {
                "acquired": len(products),
                "network_downloads": network_downloads,
                "cached_downloads": cached_downloads,
                "failed": len(failures),
            }
        )
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
