"""Composition root and reproducible offline CLI for Assignment 06."""

import argparse
import json
from pathlib import Path
import sys

from application.image_service import ImageService
from application.order_service import OrderService
from application.query_service import QueryService
from application.ranking_service import RankingService
from application.search_service import SearchService
from application.speech_service import SpeechService
from data.order_repository import OrderRepository
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex
from presentation.result_view import SearchResultView
from presentation.search_ui import SearchUI

ROOT = Path(__file__).resolve().parent


def build_services(root=None):
    root = Path(root or ROOT)
    repository = ProductRepository(root=root)
    index = VectorIndex(root / "data/embeddings.json", repository.all_products(), root)
    return SearchUI(
        QueryService(),
        SpeechService(),
        ImageService(),
        SearchService(repository, index, RankingService()),
        OrderService(OrderRepository(root / "data/orders.json")),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline multimodal product search; voice is simulated STT.")
    parser.add_argument("--mode", choices=["text", "voice", "image", "multimodal", "order", "product"])
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--query")
    parser.add_argument("--image")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--category", choices=["shoes", "bag", "clothing"])
    parser.add_argument("--max-price", type=float, help="exclusive upper price limit in USD")
    parser.add_argument("--text-weight", type=float, default=0.5)
    parser.add_argument("--order-id")
    parser.add_argument("--customer-id")
    parser.add_argument("--product-id", type=int)
    parser.add_argument("--json", action="store_true", help="machine-readable JSON on stdout")
    parser.add_argument("--output", type=Path, help="write the JSON result to this path")
    args = parser.parse_args(argv)
    try:
        ui = build_services()
        options = {"top_k": args.top_k, "category": args.category, "max_price": args.max_price}
        path = Path(args.image) if args.image else None
        if path is not None and not path.is_absolute():
            path = ROOT / path
        if args.demo or args.mode is None:
            payload = [
                ui.search_text("black shoes"),
                ui.search_voice("find black running shoes"),
                ui.search_image(ROOT / "data/queries/black_shoe_query.png"),
                ui.search_multimodal("black shoes", ROOT / "data/queries/black_shoe_query.png"),
                ui.search_order("O001", "C001"),
            ]
        elif args.mode == "text":
            payload = ui.search_text(args.query, **options)
        elif args.mode == "voice":
            payload = ui.search_voice(args.query, **options)
        elif args.mode in {"image", "multimodal"}:
            if path is None:
                raise ValueError("--image is required for image and multimodal mode")
            payload = (
                ui.search_image(path, **options)
                if args.mode == "image"
                else ui.search_multimodal(args.query, path, text_weight=args.text_weight, **options)
            )
        elif args.mode == "order":
            payload = ui.search_order(args.order_id, args.customer_id)
        else:
            payload = ui.view_product(args.product_id)
        serialized = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")
        print(serialized if args.json else SearchResultView().render(payload))
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
