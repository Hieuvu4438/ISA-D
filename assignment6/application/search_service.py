"""Retrieval produces candidates; RankingService owns ordering and top-k."""

from application.query_service import tokenize


class SearchService:
    def __init__(self, repository, index, ranking):
        self.repository, self.index, self.ranking = repository, index, ranking

    def _retrieve(self, query):
        if query.get("type") not in {"text", "voice", "image", "multimodal"}:
            raise ValueError("unsupported query type")
        tokens = set(query["tokens"])
        image_scores = self.index.score(query["embedding"]) if query["embedding"] is not None else {}
        candidates = []
        before_filter = 0
        for p in self.repository.all_products():
            searchable = set(
                tokenize(" ".join(str(p[k]) for k in ["name", "brand", "category", "color", "description"]))
            )
            matches = sorted(tokens & searchable)
            # Fusion union: every image-index member is a candidate even with zero text match.
            if query["type"] in {"text", "voice"} and tokens and not matches:
                continue
            before_filter += 1
            filters = query["filters"]
            if filters["category"] is not None and p["category"] != filters["category"]:
                continue
            if filters["max_price_exclusive"] is not None and p["price"] >= filters["max_price_exclusive"]:
                continue
            if filters["max_price_inclusive"] is not None and p["price"] > filters["max_price_inclusive"]:
                continue
            candidates.append(
                {
                    "product_id": p["product_id"],
                    "name": p["name"],
                    "brand": p["brand"],
                    "category": p["category"],
                    "color": p["color"],
                    "price": p["price"],
                    "stock": p["stock"],
                    "description": p["description"],
                    "image_path": p["image"],
                    "raw_text_score": len(matches),
                    "text_score": len(matches) / len(tokens) if tokens else 0.0,
                    "image_score": image_scores.get(p["product_id"], 0.0),
                    "business_score": 0.0,
                    "matched_terms": matches,
                }
            )
        return candidates, before_filter

    def retrieve_candidates(self, query):
        return self._retrieve(query)[0]

    def search(self, query):
        candidates, before_filter = self._retrieve(query)
        ranked = self.ranking.rank(candidates, query)
        processing = {
            "modality": query["type"],
            "normalized_query": query["query"],
            "tokens": query["tokens"],
            "filters": query["filters"],
            "candidates_before_filter": before_filter,
            "candidates_after_filter": len(candidates),
            "encoder": query["encoder"],
            "ranking_weights": query["weights"],
            "top_k": query["top_k"],
            "simulated_stt": query["type"] == "voice",
            "retrieval": "whole-word OR matching; explicit category inferred; image candidates union",
            "ranking": "weighted normalized scores; product_id ascending breaks ties; no business boost",
        }
        return {"query": query, "processing": processing, "results": ranked}

    def view_product(self, product_id):
        if not isinstance(product_id, int) or isinstance(product_id, bool) or product_id <= 0:
            raise ValueError("product-id must be a positive integer")
        product = self.repository.get_by_id(product_id)
        return {"product": product, "message": "Product found" if product else "Product not found"}
