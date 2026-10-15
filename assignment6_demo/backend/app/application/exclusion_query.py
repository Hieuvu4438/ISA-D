"""Explicit metadata exclusions, independent of lexical/embedding similarity."""
from dataclasses import dataclass
import re
import unicodedata

from app.domain import AppError, normalize_text

PARSER_VERSION = "metadata_exclusions_v1"
MARKERS = ("ngoai tru", "loai tru", "khong chon", "khong lay", "khong muon", "khong can", "khong phai", "khong thich", "tru", "khong", "except", "excluding", "exclude", "without", "not")
FIELDS = {"mau": "color", "color": "color", "thuong hieu": "brand", "brand": "brand", "hang": "brand", "danh muc": "category", "loai": "category", "category": "category"}
COLOR_ALIASES = {"black": "đen", "white": "trắng", "red": "đỏ", "blue": "xanh dương", "green": "xanh lá", "yellow": "vàng", "pink": "hồng", "brown": "nâu", "grey": "xám", "gray": "xám", "beige": "be", "orange": "cam", "purple": "tím"}
BASE_COLORS = ("đen", "trắng", "đỏ", "xanh", "vàng", "hồng", "nâu", "xám", "be", "cam", "tím", "bạc", "kem", "rêu", "xanh lá", "xanh dương")


def _source(text):
    folded, positions = [], []
    for index, char in enumerate(text):
        for value in unicodedata.normalize("NFKD", char.lower().replace("đ", "d")):
            if not unicodedata.combining(value):
                folded.append(value)
                positions.append(index)
    return "".join(folded), positions


def words(text):
    return tuple(re.findall(r"[a-z0-9]+", _source(text)[0]))


def _contains(value, phrase):
    value = tuple(word for token in words(value) for word in words(COLOR_ALIASES.get(token, token)))
    phrase = tuple(word for token in words(phrase) for word in words(COLOR_ALIASES.get(token, token)))
    return any(value[i:i + len(phrase)] == phrase for i in range(len(value) - len(phrase) + 1))


def _error(field):
    raise AppError(422, "EXCLUSION_QUERY_AMBIGUOUS", "Chưa rõ điều kiện loại trừ. Hãy viết riêng, ví dụ: áo thun, không màu đỏ và đen; hoặc tắt tự hiểu loại trừ.", field)


@dataclass
class ExclusionPlan:
    enabled: bool
    lexical_text: str
    clauses: list[dict]

    def matches(self, product):
        return not any(_contains(product[c["field"]], c["value"]) if c["field"] == "color" else words(product[c["field"]]) == words(c["value"]) for c in self.clauses)

    def validate_filters(self, filters, field="options.filters"):
        for clause in self.clauses:
            value = getattr(filters, clause["field"])
            if value is not None and (_contains(value, clause["value"]) if clause["field"] == "color" else words(value) == words(clause["value"])):
                raise AppError(422, "EXCLUSION_FILTER_CONFLICT", "Điều kiện loại trừ mâu thuẫn với bộ lọc đã chọn. Hãy sửa mô tả hoặc bộ lọc.", f"{field}.{clause['field']}")

    def public(self):
        return {"enabled": self.enabled, "parser_version": PARSER_VERSION, "applied": bool(self.clauses), "clauses": self.clauses, "lexical_text": self.lexical_text}


class ExclusionInterpreter:
    def __init__(self, products, categories):
        entities = {}

        def add(alias, field, value):
            key = words(alias)
            if key:
                choices = entities.setdefault(key, set())
                if not any(name == field and words(existing) == words(value) for name, existing in choices):
                    choices.add((field, value))

        for product in products:
            add(product["brand"], "brand", product["brand"])
            for component in re.split(r",|\b(?:và|and)\b", product["color"], flags=re.I):
                value = COLOR_ALIASES.get(component.strip().lower(), component.strip())
                add(component, "color", value)
        for value in BASE_COLORS:
            add(value, "color", value)
        for alias, value in COLOR_ALIASES.items():
            add(alias, "color", value)
        for category, aliases in categories.items():
            for alias in (*aliases, category):
                add(alias, "category", category)
        self.entities = sorted(entities.items(), key=lambda pair: (-len(pair[0]), pair[0]))

    def interpret(self, text, enabled=True, field="text"):
        text = normalize_text(text or "")
        if len(text) > 500:
            raise AppError(422, "TEXT_TOO_LONG", "Mô tả tối đa 500 ký tự.", field)
        if not enabled:
            return ExclusionPlan(False, text, [])
        folded, positions = _source(text)
        tokens = list(re.finditer(r"[a-z0-9]+|[,;]", folded))
        values = [t.group() for t in tokens]

        def at(index, phrase):
            return tuple(values[index:index + len(phrase)]) == phrase

        def entity(index, required=None):
            for key, choices in self.entities:
                selected = [(name, value) for name, value in choices if required is None or required == name]
                if selected and at(index, key):
                    if len(selected) != 1:
                        _error(field)
                    return index + len(key), *selected[0]
            return None

        clauses, masked, i = [], list(text), 0
        markers = sorted((words(m) for m in MARKERS), key=len, reverse=True)
        fields = sorted(((words(k), v) for k, v in FIELDS.items()), key=lambda item: -len(item[0]))
        while i < len(tokens):
            marker = next((m for m in markers if at(i, m)), None)
            if marker is None:
                i += 1
                continue
            start, j, required = i, i + len(marker), None
            for key, name in fields:
                if at(j, key):
                    j, required = j + len(key), name
                    break
            found = entity(j, required)
            if found is None:
                # Ordinary attributes such as "không tay" remain semantic text.
                # Explicit operators/fields cannot silently drop an unknown value.
                if required or marker not in (("khong",), ("not",), ("without",)) or values[j:j + 1] in (["khong"], ["not"], ["chi"], ["only"]):
                    _error(field)
                i = j
                continue
            end, name, value = found
            parsed = [(name, value)]
            while end < len(tokens) and values[end] in ("va", "hoac", "hay", "and", "or", ","):
                connector = end
                next_index = end + 1
                if next_index == len(tokens):
                    break
                if any(at(next_index, m) for m in markers):
                    end = next_index
                    break
                next_required = name
                for key, next_field in fields:
                    if at(next_index, key):
                        next_index, next_required = next_index + len(key), next_field
                        break
                more = entity(next_index, next_required)
                if more is None:
                    if values[connector] != ",":
                        _error(field)
                    break
                end, next_name, value = more
                if next_name != name:
                    _error(field)
                parsed.append((next_name, value))
            if end < len(tokens) and values[end] not in (",", ";", "nhung", "but") and not any(at(end, m) for m in markers):
                _error(field)
            a, b = positions[tokens[start].start()], positions[tokens[end - 1].end() - 1] + 1
            if re.search(r"[()\[\]{}]", text[a:b]):
                _error(field)
            for name, value in parsed:
                clause = {"text": text[a:b], "field": name, "value": value}
                if not any(c["field"] == name and c["value"] == value for c in clauses):
                    clauses.append(clause)
            masked[a:b] = " " * (b - a)
            i = end
        lexical_text = normalize_text(re.sub(r"(?:^|\s)[,;]+(?=\s|$)", " ", "".join(masked))).strip(" ,;")
        return ExclusionPlan(True, lexical_text, clauses)
