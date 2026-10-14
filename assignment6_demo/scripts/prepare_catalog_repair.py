"""Acquire repair candidates and official Commons provenance; never mark photos reviewed."""
import argparse
import hashlib
import html
import json
import re
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
API = "https://commons.wikimedia.org/w/api.php"
QUERIES = {
    "running_shoes": 'filetype:bitmap intitle:"running shoes"',
    "trail_shoes": 'filetype:bitmap intitle:"trail shoes"',
    "casual_shoes": 'filetype:bitmap intitle:sneakers',
    "boots": 'filetype:bitmap intitle:"leather boots"',
    "sandals": 'filetype:bitmap intitle:sandals -intitle:egyptian -intitle:roman -intitle:ancient',
    "bag": 'filetype:bitmap intitle:handbag -intitle:Prada -intitle:tooled',
    "backpack": 'filetype:bitmap intitle:backpack -intitle:backpacking -intitle:worn-out',
    "tote_bag": 'filetype:bitmap intitle:"tote bag"',
    "t_shirt": 'filetype:bitmap intitle:"T-shirt" -intitle:LCA -intitle:stain -intitle:Colton -intitle:YourSIGN',
    "jacket": 'filetype:bitmap intitle:"leather jacket" -intitle:cross -intitle:making -intitle:worn',
    "watch": 'filetype:bitmap intitle:wristwatch -intitle:making',
    "sunglasses": 'filetype:bitmap intitle:sunglasses -intitle:portrait -intitle:blind -intitle:Jane',
}


def clean(value):
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", value)).split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", choices=QUERIES, action="append")
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--acquire-reviewed", action="store_true", help="Recreate exactly the hash-pinned reviewed candidates")
    args = parser.parse_args()
    output = ROOT / "runtime/catalog-repair"
    (output / "images").mkdir(parents=True, exist_ok=True)
    records_path = output / "candidates.json"
    records = json.loads(records_path.read_text(encoding="utf-8")) if records_path.exists() else []
    existing = json.loads((ROOT / "data/image_sources.json").read_text(encoding="utf-8"))["assets"]
    pages = {row["source_page"] for row in existing + records}
    hashes = {row["sha256"] for row in existing + records}
    session = requests.Session()
    session.headers["User-Agent"] = "CortisEducationalCatalogReview/1.0 (photograph provenance audit)"
    if args.acquire_reviewed:
        reviewed = json.loads((ROOT / "data/catalog_repair_candidates.json").read_text(encoding="utf-8"))
        for row in reviewed:
            destination = (ROOT / row["local_path"]).resolve()
            if not destination.is_relative_to(output / "images"):
                raise ValueError("Reviewed candidate escaped acquisition directory")
            if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() == row["sha256"]:
                continue
            response = session.get(row["download_url"], timeout=30)
            response.raise_for_status()
            if hashlib.sha256(response.content).hexdigest() != row["sha256"]:
                raise ValueError("Source bytes changed; review required before applying")
            destination.write_bytes(response.content)
        print(f"Recreated {len(reviewed)} exact reviewed candidate files; catalog unchanged")
        return
    failures = []
    for category in args.category or QUERIES:
        response = session.get(API, params={"action": "query", "format": "json", "generator": "search",
            "gsrsearch": QUERIES[category], "gsrnamespace": 6, "gsrlimit": 50, "prop": "imageinfo",
            "iiprop": "url|extmetadata|size", "iiurlwidth": 640}, timeout=30)
        response.raise_for_status()
        downloaded = sum(row["category_hint"] == category for row in records)
        for page in sorted(response.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0)):
            if downloaded >= args.limit:
                break
            try:
                info = page["imageinfo"][0]
                meta = info.get("extmetadata", {})
                def field(name, meta=meta):
                    return clean(meta.get(name, {}).get("value", ""))
                source = info["descriptionurl"]
                description = field("ImageDescription")
                if source in pages or re.search(r"AI.generated|midjourney|stable diffusion|DALL.E|illustration|drawing|rendering|3D render", description, re.IGNORECASE):
                    continue
                license_name, license_url, author = field("LicenseShortName"), field("LicenseUrl"), field("Artist")
                if not author or not license_name or not license_url:
                    continue
                if license_url.startswith("//"):
                    license_url = "https:" + license_url
                if not license_url.startswith("https://"):
                    continue
                url = info.get("thumburl", info["url"])
                image_response = session.get(url, timeout=30)
                image_response.raise_for_status()
                raw = image_response.content
                with Image.open(BytesIO(raw)) as image:
                    if image.format not in ("JPEG", "PNG", "WEBP") or max(image.size) > 8192 or image.width * image.height > 16_000_000:
                        continue
                    image.load()
                    fmt, size = image.format, image.size
                checksum = hashlib.sha256(raw).hexdigest()
                if checksum in hashes:
                    continue
                candidate_id = f"R{len(records) + 1:03}"
                suffix = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[fmt]
                path = output / "images" / f"{candidate_id}.{suffix}"
                path.write_bytes(raw)
                records.append({"candidate_id": candidate_id, "category_hint": category, "source_title": page["title"],
                    "source_page": source, "original_url": info["url"], "download_url": url, "author": author,
                    "license": license_name, "license_url": license_url, "source_description": description,
                    "retrieved_at": datetime.now(UTC).isoformat(), "sha256": checksum, "bytes": len(raw),
                    "format": fmt, "width": size[0], "height": size[1], "local_path": path.relative_to(ROOT).as_posix(),
                    "transformations": "Commons server thumbnail; local bytes unmodified", "real_photo_review": "pending"})
                pages.add(source); hashes.add(checksum); downloaded += 1
                records_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except (requests.RequestException, ValueError, KeyError, OSError) as exc:
                failures.append({"title": page.get("title"), "reason": type(exc).__name__})
        print(f"{category}: {downloaded} candidates, all pending visual review", flush=True)
    (output / "acquisition-errors.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")
    print(f"Total candidates: {len(records)}")


if __name__ == "__main__":
    main()
