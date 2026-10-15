import json
import math
from pathlib import Path
from time import perf_counter

import numpy as np

from app.domain import AppError
from app.data.product_repository import digest
from app.data.vector_index import SCORING_VERSION
from app.application.ranking_service import RankingService
from app.application.catalog_search import CatalogSearch, matches
from app.application.price_query import interpret_price


class SearchService:
    def __init__(self, repository, encoder, index, root):
        self.repository = repository
        self.encoder = encoder
        self.index = index
        self.inventory = None
        self.lexical = CatalogSearch(repository) if repository else None
        self._policies = []
        self.policy_fingerprint = None
        if index.available:
            try:
                policy = json.loads(
                    (Path(root) / f"runtime/policies/relevance_{index.fingerprint}.json").read_text(encoding="utf-8")
                )
                payload = {k: v for k, v in policy.items() if k != "fingerprint"}
                if (
                    policy["schema_version"] != 1
                    or policy["index_fingerprint"] != index.fingerprint
                    or policy["model_fingerprint"] != encoder.model_fingerprint
                    or policy["scoring_version"] != SCORING_VERSION
                    or digest(payload) != policy["fingerprint"]
                ):
                    raise ValueError("policy snapshot")
                for entry in policy["policies"]:
                    if (
                        entry["mode"] not in ("text", "image", "multimodal")
                        or type(entry["threshold"]) not in (int, float)
                        or not math.isfinite(entry["threshold"])
                        or not -1 <= entry["threshold"] <= 1
                    ):
                        raise ValueError("threshold")
                    weight = entry.get("text_weight")
                    if entry["mode"] == "multimodal" and (type(weight) not in (int, float) or not 0.1 <= weight <= 0.9):
                        raise ValueError("policy weight")
                self._policies = policy["policies"]
                self.policy_fingerprint = policy["fingerprint"]
            except (OSError, ValueError, KeyError, TypeError):
                pass

    @property
    def available(self):
        return self.encoder.available and self.index.available

    @property
    def reason_code(self):
        return (
            None if self.available else ("MODEL_UNAVAILABLE" if not self.encoder.available else self.index.error_code)
        )

    @property
    def policies(self):
        return list(self._policies)

    def _policy(self, query):
        mode = "text" if query.mode == "voice" else query.mode
        for entry in self._policies:
            if entry["mode"] == mode and (mode != "multimodal" or entry.get("text_weight") == query.text_weight):
                return entry
        raise AppError(
            503,
            "RELEVANCE_POLICY_UNAVAILABLE",
            "Chưa có ngưỡng liên quan cho truy vấn này; hãy chọn sản phẩm gần nhất.",
        )

    def validate_request(self, options, mode, text=None, text_weight=None):
        from types import SimpleNamespace

        try:
            self.lexical.validate_filters(options.filters)
        except AppError as exc:
            exc.field = f"options.{exc.field}" if exc.field else None
            raise
        if text is not None:
            plan = interpret_price(text, options.interpret_price)
            plan.merge(options.filters)
            if options.search_strategy == "hybrid":
                self.lexical.prepare(plan.lexical_text)
        if options.result_policy == "relevant":
            self._policy(SimpleNamespace(mode=mode, text_weight=text_weight))

    def search(self, query):
        if not self.available:
            raise AppError(503, self.reason_code, "Tìm kiếm chưa sẵn sàng.")
        options = query.options
        policy = self._policy(query) if options.result_policy == "relevant" else None
        timings = {"validation": query.validation_ms, "encoding": query.encoding_ms}
        trace = [
            {"step": "validation", "status": "ok", "input_count": 1, "output_count": 1},
            {"step": "encoding", "status": "ok", "input_count": 1, "output_count": 1},
        ]
        mark = perf_counter()
        candidates = self.index.retrieve(query.vector)
        timings["retrieval"] = (perf_counter() - mark) * 1000
        trace.append({"step": "retrieval", "status": "ok", "input_count": 1, "output_count": len(candidates)})
        products = {p["product_id"]: p for p in self.repository.products}
        stock, inventory_revision, sizes = self.inventory.snapshot_with_variants() if self.inventory else ({}, None, {})
        if self.inventory:
            for p in products.values():
                p["stock_quantity"] = stock.get(p["product_id"], 0)
                p["_variants"] = sizes.get(p["product_id"], [])
        if any(c["product_id"] not in products for c in candidates):
            raise AppError(503, "INDEX_OUT_OF_SYNC", "Chỉ mục không khớp dữ liệu sản phẩm.")
        mark = perf_counter()
        text = query.input_summary.get("text")
        price_plan = interpret_price(text, options.interpret_price and text is not None)
        filters = price_plan.merge(options.filters)
        self.lexical.validate_filters(filters)
        eligible = []
        for candidate in candidates:
            p = products[candidate["product_id"]]
            if not matches(p, filters):
                continue
            eligible.append(candidate)
        timings["filtering"] = (perf_counter() - mark) * 1000
        trace.append(
            {"step": "filtering", "status": "ok", "input_count": len(candidates), "output_count": len(eligible)}
        )
        empty_reason = "catalog_empty" if not candidates else ("filters" if not eligible else None)
        before = len(eligible)
        mark = perf_counter()
        if policy:
            eligible = [c for c in eligible if c["score"] >= policy["threshold"]]
            if before and not eligible:
                empty_reason = "threshold"
        timings["threshold"] = (perf_counter() - mark) * 1000 if policy else 0
        trace.append(
            {
                "step": "threshold",
                "status": "ok" if policy else "skipped",
                "input_count": before,
                "output_count": len(eligible),
            }
        )
        mark = perf_counter()
        hybrid = options.search_strategy == "hybrid" and query.input_summary.get("text") is not None
        plan = None
        if hybrid:
            eligible, plan = self.lexical.fuse(eligible, price_plan.lexical_text)
            if before and not eligible:
                empty_reason = "no_matches" if plan.exact_id else empty_reason
        if options.sort != "relevance":
            selected = sorted(eligible, key=lambda c: self.lexical.sort_key(products[c["product_id"]], options.sort, {}))[:options.top_k]
        elif hybrid:
            selected = sorted(eligible, key=lambda c: (-c["rank_score"], c["product_id"]))[:options.top_k]
        else:
            selected = RankingService.rank(eligible, options.top_k)
        timings["ranking"] = (perf_counter() - mark) * 1000
        trace.append({"step": "ranking", "status": "ok", "input_count": len(eligible), "output_count": len(selected)})
        mark = perf_counter()
        results = []
        for rank, c in enumerate(selected, 1):
            v = self.index.product_vectors[c["row"]]
            components = {
                name: float(np.clip(np.dot(vector, v), -1, 1)) if vector is not None else None
                for name, vector in [("text", query.text_vector), ("image", query.image_vector)]
            }
            results.append(
                {
                    "rank": rank,
                    "product": self.repository.summary(products[c["product_id"]]),
                    "score": c["score"],
                    "component_scores": components,
                    "rank_score": c.get("rank_score", c["score"]),
                    "lexical_score": c.get("lexical_score"),
                }
            )
        timings["hydration"] = (perf_counter() - mark) * 1000
        trace.append({"step": "hydration", "status": "ok", "input_count": len(selected), "output_count": len(results)})
        timings["total"] = (perf_counter() - query.started_at) * 1000
        return {
            "query": {
                "mode": query.mode,
                **query.input_summary,
                "voice_source": query.voice_source,
                "text_weight": query.text_weight,
                "options": options.model_dump(),
            },
            "results": results,
            "meta": {
                "model_fingerprint": self.encoder.model_fingerprint,
                "index_fingerprint": self.index.fingerprint,
                "catalog_fingerprint": self.repository.fingerprint,
                "result_policy": options.result_policy,
                "threshold": policy["threshold"] if policy else None,
                "policy_fingerprint": self.policy_fingerprint if policy else None,
                "empty_reason": empty_reason,
                "timing_ms": timings,
                "trace": trace,
                "ranking_strategy": "exact_sku" if plan and plan.exact_id else "rrf" if hybrid else "semantic",
                "sort": options.sort,
                "lexical_fingerprint": self.lexical.fingerprint if hybrid else None,
                "corrections": plan.corrections if plan else [],
                "inventory_revision": inventory_revision,
                "price_interpretation": price_plan.public(filters),
            },
        }
