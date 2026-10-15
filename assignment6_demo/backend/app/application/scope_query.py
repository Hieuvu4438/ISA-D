"""Conservative exact metadata scope recognition, separate from similarity."""
from dataclasses import dataclass
import re

from app.application.exclusion_query import BASE_COLORS, COLOR_ALIASES, ExclusionInterpreter, _contains, _source, words
from app.domain import AppError, normalize_text

PARSER_VERSION = "brand_category_color_scope_v2"
BRAND_PREFIXES = (("thuong", "hieu"), ("brand",), ("hang",))
REQUEST_FILLERS = frozenset("hoac hay or toi can tim mua muon cho minh mot chiec cai san pham xin giup voi nhe loai cua".split())
UNCERTAIN = re.compile(r"\b(?:khong|not|without|except|excluding|exclude|tru|giong|like|versus|vs|instead|thay vi)\b")


@dataclass
class ScopePlan:
    enabled: bool
    lexical_text: str
    clauses: list[dict]
    warnings: list[str]

    def values(self, field):
        return {words(c["value"]) for c in self.clauses if c["field"] == field}

    def matches(self, product):
        colors = [c["value"] for c in self.clauses if c["field"] == "color"]
        return (all(not self.values(field) or words(product[field]) in self.values(field) for field in ("brand", "category"))
                and (not colors or any(_contains(product["color"], color) for color in colors)))

    def validate(self, filters, exclusions, field="options.filters"):
        for name in ("brand", "category", "color"):
            selected = getattr(filters, name)
            allowed = self.values(name)
            selected_matches = (any(_contains(selected, c["value"]) for c in self.clauses if c["field"] == name)
                                if name == "color" and selected is not None else words(selected or "") in allowed)
            if allowed and selected is not None and not selected_matches:
                raise AppError(422, "SCOPE_FILTER_CONFLICT", "Hãng, loại hoặc màu sản phẩm trong mô tả mâu thuẫn với bộ lọc. Hãy sửa mô tả, bộ lọc hoặc tắt tự hiểu phạm vi.", f"{field}.{name}")
            excluded = {words(c["value"]) for c in exclusions.clauses if c["field"] == name}
            all_excluded = (all(any(_contains(c["value"], e["value"]) for e in exclusions.clauses if e["field"] == name)
                                for c in self.clauses if c["field"] == name) if name == "color" else allowed <= excluded)
            if allowed and all_excluded:
                raise AppError(422, "SCOPE_EXCLUSION_CONFLICT", "Phạm vi tìm kiếm đã bị loại trừ hết trong mô tả. Hãy sửa lại các điều kiện.", "q" if field == "filters" else "text")

    def public(self):
        return {"enabled": self.enabled, "parser_version": PARSER_VERSION, "applied": bool(self.clauses), "clauses": self.clauses, "lexical_text": self.lexical_text, "warnings": self.warnings}


class ScopeInterpreter:
    def __init__(self, products, categories):
        entities = {}
        for field, aliases in [("brand", {p["brand"]: (p["brand"],) for p in products}), ("category", categories)]:
            for value, names in aliases.items():
                for alias in names:
                    choices = entities.setdefault(words(alias), set())
                    if not any(name == field and words(existing) == words(value) for name, existing in choices):
                        choices.add((field, value))
        for key, choices in ExclusionInterpreter(products, categories).entities:
            for name, value in choices:
                if name == "color":
                    entities.setdefault(key, set()).add((name, value))
        self.entities = sorted(entities.items(), key=lambda item: (-len(item[0]), item[0]))
        self.color_words = {words(value) for value in (*BASE_COLORS, *COLOR_ALIASES)}

    def interpret(self, text, enabled=True, field="text"):
        text = normalize_text(text or "")
        if len(text) > 500:
            raise AppError(422, "TEXT_TOO_LONG", "Mô tả tối đa 500 ký tự.", field)
        if not enabled:
            return ScopePlan(False, text, [], [])
        folded, positions = _source(text)
        tokens = list(re.finditer(r"[a-z0-9]+", folded))
        values = tuple(t.group() for t in tokens)
        if values and values[-1] in ("mau", "color", "colour"):
            return ScopePlan(True, text, [], ["Chưa có tên màu sau từ chỉ màu. Hãy nhập thêm tên màu hoặc chọn bộ lọc."])
        color_ambiguity = "Chưa rõ các lựa chọn màu trong mô tả. Hãy nối các màu bằng hoặc/or hoặc chọn bộ lọc màu."
        if values and values[-1] in ("hoac", "hay", "or", "va", "and") and any(v in ("mau", "color", "colour") for v in values):
            return ScopePlan(True, text, [], [color_ambiguity])
        if UNCERTAIN.search(" ".join(values)):
            return ScopePlan(True, text, [], ["Chưa tự giới hạn hãng/loại vì mô tả còn phủ định hoặc so sánh chưa rõ. Hãy chọn bộ lọc để giới hạn."])
        found, i = [], 0
        while i < len(tokens):
            explicit_brand = next((prefix for prefix in BRAND_PREFIXES if i >= len(prefix) and values[i - len(prefix):i] == prefix), None)
            color_marker = i > 0 and values[i - 1] in ("mau", "color", "colour")
            color_continuation = (bool(found) and found[-1]["field"] == "color" and (
                i > found[-1]["end"] and set(values[found[-1]["end"]:i]) <= {"hoac", "hay", "or", "va", "and"}
                or i == found[-1]["end"] and any(values[i:i + len(key)] == key and any(name == "color" for name, _ in choices) for key, choices in self.entities)))
            required = "brand" if explicit_brand else "color" if color_marker or color_continuation else None
            match = next(((key, [(name, value) for name, value in choices if name == required or required is None and name != "color"])
                          for key, choices in self.entities if key and values[i:i + len(key)] == key
                          and any(name == required or required is None and name != "color" for name, _ in choices)), None)
            if match is None:
                if color_marker:
                    return ScopePlan(True, text, [], ["Chưa nhận diện được màu trong mô tả. Hãy chọn bộ lọc màu hoặc sửa lại tên màu."])
                if color_continuation and values[i] not in ("mau", "color", "colour"):
                    return ScopePlan(True, text, [], [color_ambiguity])
                i += 1
                continue
            key, choices = match
            if len(choices) == 1:
                name, value = choices[0]
                # "On" is also an ordinary preposition; short brands need a field marker.
                if name != "brand" or explicit_brand or len("".join(key)) > 2 and key not in self.color_words:
                    a, b = positions[tokens[i].start()], positions[tokens[i + len(key) - 1].end() - 1] + 1
                    found.append({"text": text[a:b], "field": name, "value": value, "start": i - len(explicit_brand) if explicit_brand else i - 1 if color_marker else i, "end": i + len(key)})
            i += len(key)
        clauses, masked, warnings = [], list(text), []
        ambiguous = "Có nhiều hãng, loại hoặc màu sản phẩm chưa rõ phạm vi. Chỉ tự gộp các lựa chọn nối trực tiếp bằng hoặc/or; hãy chọn bộ lọc nếu cần."
        for a, b in zip(found, found[1:]):
            between = set(values[a["end"]:b["start"]])
            if a["field"] != b["field"] and between and between <= {"hoac", "hay", "or"}:
                return ScopePlan(True, text, [], [ambiguous])
        for name in ("brand", "category", "color"):
            rows = [row for row in found if row["field"] == name]
            distinct = {words(row["value"]) for row in rows}
            if len(distinct) > 1 and any(not set(values[a["end"]:b["start"]]) <= {"hoac", "hay", "or"} or not set(values[a["end"]:b["start"]]) for a, b in zip(rows, rows[1:])):
                return ScopePlan(True, text, [], [ambiguous])
            for row in rows:
                if not any(c["field"] == name and words(c["value"]) == words(row["value"]) for c in clauses):
                    clauses.append({k: row[k] for k in ("text", "field", "value")})
                a, b = positions[tokens[row["start"]].start()], positions[tokens[row["end"] - 1].end() - 1] + 1
                masked[a:b] = " " * (b - a)
        lexical_text = normalize_text("".join(masked)).strip(" ,;")
        if clauses and set(words(lexical_text)) <= REQUEST_FILLERS:
            lexical_text = ""
        return ScopePlan(True, lexical_text, clauses, list(dict.fromkeys(warnings)))
