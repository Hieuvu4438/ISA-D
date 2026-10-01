"""One validated query contract for all three input modalities."""

import math
import re

import numpy as np

STOPWORDS = {"find", "show", "me", "a", "an", "the", "please", "for", "dollar", "dollars", "usd"}
ALIASES = {"shoe": "shoes", "bags": "bag", "backpacks": "backpack", "shirts": "shirt"}
CATEGORIES = {"shoes", "bag", "clothing"}
ENCODER = {"name": "rgbhist-gray-thumbnail", "version": "1.0", "dimension": 88}


def tokenize(text):
    return list(dict.fromkeys(ALIASES.get(t, t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS))


class QueryService:
    def _base(
        self,
        mode,
        raw_input,
        text="",
        embedding=None,
        top_k=5,
        category=None,
        max_price=None,
        customer_id=None,
        text_weight=None,
    ):
        if not isinstance(top_k, int) or isinstance(top_k, bool) or not 1 <= top_k <= 100:
            raise ValueError("top-k must be an integer from 1 to 100")
        if category is not None and category not in CATEGORIES:
            raise ValueError("category must be shoes, bag, or clothing")
        filters = {"category": category, "max_price_exclusive": None, "max_price_inclusive": None}
        if max_price is not None:
            if (
                isinstance(max_price, bool)
                or not isinstance(max_price, (int, float))
                or not math.isfinite(max_price)
                or max_price < 0
            ):
                raise ValueError("max-price must be a finite nonnegative number")
            filters["max_price_exclusive"] = float(max_price)
        normalized = ""
        terms = []
        if mode in {"text", "voice", "multimodal"}:
            if not isinstance(text, str) or not text.strip() or len(text) > 2000:
                raise ValueError("query must contain 1–2000 characters")
            normalized = text.lower().strip()
            pattern = r"\b(under|below|at most)\s+(\d+(?:\.\d+)?)\b"
            for match in re.finditer(pattern, normalized):
                key = "max_price_inclusive" if match[1] == "at most" else "max_price_exclusive"
                price = float(match[2])
                if not math.isfinite(price):
                    raise ValueError("extracted price must be finite")
                filters[key] = min(filters[key], price) if filters[key] is not None else price
            lexical = re.sub(pattern, "", normalized)
            terms = tokenize(lexical)
            inferred = (
                "shoes"
                if "shoes" in terms
                else "bag"
                if {"bag", "backpack"} & set(terms)
                else "clothing"
                if {"shirt", "jacket", "clothing"} & set(terms)
                else None
            )
            if inferred and category and inferred != category:
                raise ValueError("explicit category conflicts with query category")
            filters["category"] = category or inferred
            if not terms and not any(v is not None for v in filters.values()):
                raise ValueError("query has no searchable terms or filters")
        vector = None
        if mode in {"image", "multimodal"}:
            try:
                arr = np.asarray(embedding, dtype=float)
            except (TypeError, ValueError) as exc:
                raise ValueError("embedding must contain finite numeric values") from exc
            if arr.shape != (88,) or not np.isfinite(arr).all():
                raise ValueError("embedding must contain exactly 88 finite numbers")
            vector = arr.tolist()
        weight = 0.5 if mode == "multimodal" and text_weight is None else text_weight
        if mode == "multimodal":
            if (
                isinstance(weight, bool)
                or not isinstance(weight, (int, float))
                or not math.isfinite(weight)
                or not 0 <= weight <= 1
            ):
                raise ValueError("text-weight must be a finite number between 0 and 1")
            weights = {"text": float(weight), "image": 1 - float(weight)}
        else:
            weights = {"text": 0.0 if mode == "image" else 1.0, "image": 1.0 if mode == "image" else 0.0}
        return {
            "type": mode,
            "raw_input": str(raw_input),
            "query": normalized,
            "tokens": terms,
            "embedding": vector,
            "filters": filters,
            "top_k": top_k,
            "weights": weights,
            "customer_id": customer_id,
            "encoder": ENCODER if vector is not None else None,
        }

    def text_query(self, text, **kwargs):
        return self._base("text", text, text=text, **kwargs)

    def voice_query(self, transcript, **kwargs):
        return self._base("voice", transcript, text=transcript, **kwargs)

    def image_query(self, embedding, raw_input="", **kwargs):
        return self._base("image", raw_input, embedding=embedding, **kwargs)

    def multimodal_query(self, text, embedding, raw_input=None, text_weight=0.5, **kwargs):
        return self._base(
            "multimodal", raw_input or text, text=text, embedding=embedding, text_weight=text_weight, **kwargs
        )
