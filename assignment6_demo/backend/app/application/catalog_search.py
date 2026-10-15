"""Deterministic lexical retrieval and faceted browsing; not an AI encoder."""
from collections import Counter
from dataclasses import dataclass
import math
import re
import unicodedata

from app.domain import AppError, Filters, normalize_text
from app.data.product_repository import CATEGORIES, digest
from app.application.price_query import interpret_price, PARSER_VERSION

LEXICAL_VERSION = "bm25_vi_alias_typo_v2_price"
STOPWORDS = frozenset("toi can tim muon mot chiec cai san pham co cho va la de voi ban minh".split())
ALIASES = {
    "running_shoes": ("giay chay bo", "running shoes", "running shoe"),
    "trail_shoes": ("giay chay dia hinh", "giay dia hinh", "trail shoes", "trail shoe"),
    "casual_shoes": ("giay thuong ngay", "giay casual", "sneakers", "sneaker"),
    "boots": ("giay boots", "boots", "boot"),
    "sandals": ("dep va sandal", "dep", "sandals", "sandal"),
    "backpack": ("balo", "ba lo", "backpacks", "backpack"),
    "tote_bag": ("tui tote", "tote bag", "tote"),
    "bag": ("tui xach", "handbag", "handbags"),
    "t_shirt": ("ao thun", "ao phong", "t shirt", "t shirts", "tshirt", "tee"),
    "jacket": ("ao khoac", "jacket", "jackets"),
    "watch": ("dong ho", "watch", "watches"),
    "sunglasses": ("kinh mat", "kinh ram", "sunglasses", "sunglass"),
}
COLORS = {"black": "den", "white": "trang", "red": "do", "blue": "xanh", "yellow": "vang", "pink": "hong", "brown": "nau", "grey": "xam", "gray": "xam"}


def fold(text):
    text = unicodedata.normalize("NFKD", text.casefold()).replace("đ", "d")
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in text if not unicodedata.combining(c))))


def analyze(text):
    value = fold(text)
    # Long phrases first: "trail running" must not also become ordinary running.
    for category, phrase in sorted(((key, phrase) for key, phrases in ALIASES.items() for phrase in phrases), key=lambda pair: -len(pair[1])):
        value = re.sub(r"\b" + re.escape(phrase) + r"\b", f" cat_{category} ", value)
    return [COLORS.get(token, token) for token in value.split() if token not in STOPWORDS]


def one_edit(a, b):
    """One insertion/deletion/substitution or adjacent transposition, no fuzzy SKU."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        mismatches = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        return len(mismatches) == 1 or (len(mismatches) == 2 and mismatches[1] == mismatches[0] + 1
                                      and a[mismatches[0]] == b[mismatches[1]] and a[mismatches[1]] == b[mismatches[0]])
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


@dataclass
class LexicalQuery:
    terms: list[str]
    corrections: list[dict]
    exact_id: str | None


def matches(product, filters):
    return ((filters.category is None or product["category"] == filters.category)
            and (filters.brand is None or product["brand"] == filters.brand)
            and (filters.color is None or product["color"] == filters.color)
            and (filters.min_price is None or product["price_vnd"] >= filters.min_price)
            and (filters.max_price is None or product["price_vnd"] <= filters.max_price)
            and (not filters.in_stock or product["stock_quantity"] > 0))


class CatalogSearch:
    def __init__(self, repository):
        self.repository = repository
        self.inventory = None
        self.products = repository.products
        self.by_id = {p["product_id"]: p for p in self.products}
        self.counts = {}
        self.df = Counter()
        for p in self.products:
            terms = analyze(f"{p['name']} {p['brand']} {CATEGORIES[p['category']]} {p['color']} {p['description']}")
            terms.extend([f"cat_{p['category']}"] * 2)
            self.counts[p["product_id"]] = Counter(terms)
            self.df.update(set(terms))
        # Include alias spelling in typo vocabulary before canonicalizing corrections.
        self.vocabulary = set(self.df) | {word for phrases in ALIASES.values() for phrase in phrases for word in phrase.split()}
        self.average_length = sum(sum(c.values()) for c in self.counts.values()) / max(len(self.products), 1) or 1
        self.fingerprint = digest({"catalog": repository.fingerprint, "version": LEXICAL_VERSION,
                                   "aliases": ALIASES, "colors": COLORS, "stopwords": sorted(STOPWORDS),
                                   "k1": 1.2, "b": 0.75, "rrf_constant": 60})
        self.fingerprint = digest({"lexical": self.fingerprint, "price_parser": PARSER_VERSION})

    def prepare(self, text):
        text = normalize_text(text)
        if len(text) > 500:
            raise AppError(422, "TEXT_TOO_LONG", "Mô tả tối đa 500 ký tự.", "q")
        exact = text.upper() if re.fullmatch(r"p[0-9]{3}", text, flags=re.I) else None
        terms, corrections = [], []
        raw = fold(text).split()
        if len(raw) > 64:
            raise AppError(422, "TEXT_TOO_LONG", "Tìm từ khóa tối đa 64 từ.", "q")
        corrected = []
        for token in raw:
            choices = []
            if token not in self.vocabulary and 4 <= len(token) <= 24 and token.isalpha():
                choices = sorted(word for word in self.vocabulary if word.isalpha() and one_edit(token, word))
            replacement = choices[0] if len(choices) == 1 else token
            if replacement != token:
                corrections.append({"input": token, "matched": replacement})
            corrected.append(replacement)
        terms.extend(analyze(" ".join(corrected)))
        return LexicalQuery(list(dict.fromkeys(terms)), corrections, exact)

    def scores(self, plan):
        if plan.exact_id:
            return {plan.exact_id: 1.0} if plan.exact_id in self.by_id else {}
        scores = {}
        n = len(self.products)
        for product_id, counts in self.counts.items():
            length = sum(counts.values())
            score = 0.0
            for term in plan.terms:
                tf = counts[term]
                if tf:
                    idf = math.log1p((n - self.df[term] + 0.5) / (self.df[term] + 0.5))
                    score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / self.average_length))
            if score > 0:
                scores[product_id] = score
        return scores

    def validate_filters(self, filters):
        for name in ("brand", "color"):
            value = getattr(filters, name)
            if value is not None and value not in {p[name] for p in self.products}:
                raise AppError(422, "VALIDATION_ERROR", "Giá trị lọc không thuộc danh mục.", f"filters.{name}")

    def browse(self, text, filters, sort, offset, limit, parse_price=True):
        self.validate_filters(filters)
        requested_filters = filters
        price_plan = interpret_price(text, parse_price, "q")
        filters = price_plan.merge(filters, "filters")
        plan = self.prepare(price_plan.lexical_text)
        scores = self.scores(plan)
        stock, revision = self.inventory.snapshot() if self.inventory else ({}, None)
        price_only = bool(price_plan.clauses) and not plan.terms
        universe = [dict(p, stock_quantity=stock.get(p["product_id"], 0)) if self.inventory else p for p in self.products if price_only or not price_plan.lexical_text.strip() or p["product_id"] in scores]
        eligible = [p for p in universe if matches(p, filters)]
        # Disjunctive facets: all other active filters remain applied, counts before pagination.
        facets = {}
        for field in ("category", "brand", "color"):
            relaxed = filters.model_copy(update={field: None})
            counts = Counter(p[field] for p in universe if matches(p, relaxed))
            all_values = sorted({p[field] for p in self.products})
            facets[field] = [{"value": value, "count": counts[value]} for value in all_values]
        eligible.sort(key=lambda p: self.sort_key(p, sort, scores))
        return {"products": [self.repository.summary(p) for p in eligible[offset:offset + limit]],
                "total": len(eligible), "offset": offset, "limit": limit,
                "query": {"text": normalize_text(text), "sort": sort, "filters": requested_filters.model_dump()},
                "price_interpretation": price_plan.public(filters),
                "facets": facets, "corrections": plan.corrections,
                "empty_reason": None if eligible else "catalog_empty" if not self.products else "filters" if universe else "no_matches",
                "catalog_fingerprint": self.repository.fingerprint, "lexical_fingerprint": self.fingerprint,
                "inventory_revision": revision,
                "retrieval": "exact_sku" if plan.exact_id else "bm25" if text.strip() else "catalog"}

    @staticmethod
    def sort_key(p, sort, scores):
        if sort == "price_asc":
            return p["price_vnd"], p["product_id"]
        if sort == "price_desc":
            return -p["price_vnd"], p["product_id"]
        if sort == "name":
            return fold(p["name"]), p["product_id"]
        return -scores.get(p["product_id"], 0), p["product_id"]

    def suggestions(self, text, limit=6, parse_price=True):
        if len(normalize_text(text)) < 2:
            return []
        price_plan = interpret_price(text, parse_price, "q")
        filters = price_plan.merge(Filters(), "filters")
        plan = self.prepare(price_plan.lexical_text)
        scores = self.scores(plan)
        value = fold(price_plan.lexical_text)
        rows = []
        for p in self.products:
            if not matches(p, filters):
                continue
            prefix = p["product_id"].casefold().startswith(value) or fold(p["name"]).startswith(value)
            if prefix or p["product_id"] in scores:
                rows.append((not prefix, -scores.get(p["product_id"], 0), p["product_id"], p))
        rows.sort(key=lambda row: row[:3])
        stock = self.inventory.snapshot()[0] if self.inventory else {}
        return [self.repository.summary(dict(row[3], stock_quantity=stock.get(row[3]["product_id"], 0)) if self.inventory else row[3]) for row in rows[:limit]]

    def fuse(self, candidates, text):
        plan = self.prepare(text)
        scores = self.scores(plan)
        if plan.exact_id:
            return [dict(c, rank_score=1.0, lexical_score=1.0) for c in candidates if c["product_id"] == plan.exact_id], plan
        semantic = sorted(candidates, key=lambda c: (-c["score"], c["product_id"]))
        lexical = sorted((c for c in candidates if c["product_id"] in scores), key=lambda c: (-scores[c["product_id"]], c["product_id"]))
        ranks = {c["product_id"]: 1 / (60 + rank) for rank, c in enumerate(semantic, 1)}
        for rank, c in enumerate(lexical, 1):
            ranks[c["product_id"]] += 1 / (60 + rank)
        return [dict(c, rank_score=ranks[c["product_id"]], lexical_score=scores.get(c["product_id"], 0.0)) for c in candidates], plan
