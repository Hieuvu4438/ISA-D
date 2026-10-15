"""Package only the built frontend with a same-origin proxy to the demo backend."""
import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", required=True, help="Public HTTPS tunnel origin, without a path")
    parser.add_argument("--update-proxy", action="store_true", help="Update only the proxy in an existing site package")
    arguments = parser.parse_args()
    url = urlsplit(arguments.backend_url)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.path not in ("", "/") or url.query or url.fragment):
        parser.error("backend-url must be a public HTTPS origin without credentials or a path")
    backend = arguments.backend_url.rstrip("/")
    root = Path(__file__).resolve().parents[1]
    source, destination = root / "frontend/dist", root / "runtime/public-demo/site"
    if not (source / "index.html").is_file():
        parser.error("Build frontend first: npm run build in frontend")
    # A new package directory avoids publishing stale assets from an earlier build.
    if destination.exists() and not arguments.update_proxy:
        parser.error("Site package exists; use a fresh runtime/public-demo/site directory before repackaging")
    if arguments.update_proxy:
        if not (destination / "index.html").is_file():
            parser.error("No existing site package to update")
    else:
        shutil.copytree(source, destination)
    config = {
        "$schema": "https://openapi.vercel.sh/vercel.json", "version": 2,
        "framework": None, "buildCommand": "", "installCommand": "", "outputDirectory": ".",
        "routes": [
            {"src": "/api/(.*)", "dest": backend + "/api/$1", "headers": {"Cache-Control": "no-store"}},
            {"src": "/health/(.*)", "dest": backend + "/health/$1", "headers": {"Cache-Control": "no-store"}},
            {"handle": "filesystem"},
            {"src": "/(.*)", "dest": "/index.html"},
        ],
    }
    (destination / "vercel.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print("Vercel site package ready: runtime/public-demo/site (frontend assets and proxy configuration only)")


if __name__ == "__main__":
    main()
