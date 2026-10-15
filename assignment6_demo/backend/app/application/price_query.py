"""Bounded deterministic VND range parsing; separate from semantic similarity."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
import re
import unicodedata

from app.domain import AppError, normalize_text

PARSER_VERSION = "vi_vnd_price_v1"
MAX_PRICE = 1_000_000_000
UNITS = {"trieu": 1_000_000, "tr": 1_000_000, "million": 1_000_000,
         "nghin": 1000, "ngan": 1000, "k": 1000, "thousand": 1000,
         "vnd": 1, "dong": 1, "d": 1, "₫": 1}
DIGITS = {"khong": 0, "mot": 1, "hai": 2, "ba": 3, "bon": 4, "tu": 4, "nam": 5, "lam": 5, "sau": 6, "bay": 7, "tam": 8, "chin": 9}
NUMBER_WORD = r"(?:khong|mot|hai|ba|bon|tu|nam|lam|sau|bay|tam|chin|muoi|tram|linh|le)"
NUMBER = r"(?:[+-]?[0-9]+(?:[.,][0-9]+)*(?: [0-9]{3})*|" + NUMBER_WORD + r"(?:\s+" + NUMBER_WORD + r"){0,6})"
UNIT = r"(?:trieu|million|thousand|nghin|ngan|vnd|dong(?!\s+ho\b)|tr|k|d|₫)"
OPERATORS = {
    "khong qua": "lte", "khong hon": "lte", "khong dat hon": "lte", "toi da": "lte", "at most": "lte", "no more than": "lte",
    "khong duoi": "gte", "khong it hon": "gte", "khong re hon": "gte", "it nhat": "gte", "toi thieu": "gte", "at least": "gte",
    "duoi": "lt", "it hon": "lt", "re hon": "lt", "under": "lt", "less than": "lt", "below": "lt",
    "tren": "gt", "hon": "gt", "dat hon": "gt", "over": "gt", "more than": "gt", "above": "gt",
    "den": "lte", "toi": "lte", "up to": "lte", "tu": "gte", "from": "gte",
    "<": "lt", ">": "gt", "<=": "lte", ">=": "gte", "≤": "lte", "≥": "gte",
}


def _money(name):
    return (rf"(?P<{name}_number>{NUMBER})\s*(?P<{name}_unit>{UNIT})?"
            rf"(?:(?P<{name}_half>\s+ruoi)|\s*(?P<{name}_extra>{NUMBER})\s*(?P<{name}_extra_unit>{UNIT}))?"
            r"(?![\w]|[.,][0-9])")


PREFIX = r"(?:(?:gia|ngan sach|price|budget)\s+)?"
RANGE = re.compile(r"(?<!\w)" + PREFIX + r"(?:tu|between)\s+" + _money("a") + r"\s+(?:den|toi|and)\s+" + _money("b"))
SINGLE = re.compile(r"(?<!\w)" + PREFIX + r"(?P<op>" + "|".join(re.escape(op) for op in sorted(OPERATORS, key=len, reverse=True)) + r")\s*" + _money("a"))
MONEY_MENTION = re.compile(r"(?<!\w)" + NUMBER + r"\s*" + UNIT + r"(?!\w)")


def _source(text):
    folded, positions = [], []
    for index, char in enumerate(text):
        for value in unicodedata.normalize("NFD", char.lower().replace("đ", "d")):
            if not unicodedata.combining(value):
                folded.append(value)
                positions.append(index)
    return "".join(folded), positions


def _error(code, message, field):
    raise AppError(422, code, message, field)


def _number(raw, scaled, field):
    if len(raw) > 32:
        _error("PRICE_VALUE_UNSUPPORTED", "Giá nằm ngoài giới hạn hỗ trợ 0–1.000.000.000 VND.", field)
    try:
        # Unscaled VND permits conventional thousands groups; scaled units allow
        # only unambiguous one/two-digit fractions. Never guess what 1.500tr means.
        if raw[0].isalpha():
            value = Decimal(_vietnamese_integer(raw))
        elif " " in raw:
            if not re.fullmatch(r"[+]?[0-9]{1,3}(?: [0-9]{3})+", raw):
                raise ValueError("grouping")
            value = Decimal(raw.replace(" ", ""))
        elif "." in raw or "," in raw:
            if not scaled and re.fullmatch(r"[+]?[0-9]{1,3}(?:\.[0-9]{3})+|[+]?[0-9]{1,3}(?:,[0-9]{3})+", raw):
                value = Decimal(raw.replace(".", "").replace(",", ""))
            elif re.fullmatch(r"[+]?[0-9]+[.,][0-9]{1,2}", raw):
                value = Decimal(raw.replace(",", "."))
            else:
                raise ValueError("ambiguous separators")
        else:
            value = Decimal(raw)
    except (InvalidOperation, ValueError):
        _error("PRICE_QUERY_AMBIGUOUS", "Cách viết giá chưa rõ. Dùng 1,5 triệu hoặc 1.500.000 VND và ghi đủ đơn vị.", field)
    return value


def _vietnamese_integer(raw):
    """Strict 0..999 spoken integer grammar; malformed phrases never guessed."""
    words = raw.split()
    if len(words) == 1:
        if words[0] in DIGITS:
            return DIGITS[words[0]]
        if words[0] in ("muoi", "tram"):
            return 10 if words[0] == "muoi" else 100
    hundreds = 0
    if len(words) >= 2 and words[0] in DIGITS and DIGITS[words[0]] > 0 and words[1] == "tram":
        hundreds = DIGITS[words[0]] * 100
        words = words[2:]
        if not words:
            return hundreds
        if words[0] in ("linh", "le"):
            if len(words) != 2 or words[1] not in DIGITS or DIGITS[words[1]] == 0:
                raise ValueError("spoken zero connector")
            return hundreds + DIGITS[words[1]]
    if words and words[0] == "muoi":
        tens, rest = 10, words[1:]
    elif len(words) >= 2 and words[0] in DIGITS and DIGITS[words[0]] >= 2 and words[1] == "muoi":
        tens, rest = DIGITS[words[0]] * 10, words[2:]
    else:
        raise ValueError("spoken number")
    if not rest:
        return hundreds + tens
    if len(rest) == 1 and rest[0] in DIGITS and DIGITS[rest[0]] > 0:
        return hundreds + tens + DIGITS[rest[0]]
    raise ValueError("spoken remainder")


def _amount(match, name, field, inherited=None):
    unit = match.group(name + "_unit") or inherited
    scale = UNITS[unit] if unit else 1
    number = _number(match.group(name + "_number"), scale > 1, field)
    if not unit and number < 1000:
        _error("PRICE_QUERY_AMBIGUOUS", "Hãy ghi đơn vị giá, ví dụ dưới 500 nghìn hoặc dưới 1 triệu.", field)
    value = number * scale
    if match.group(name + "_half"):
        if scale == 1 or number != number.to_integral_value():
            _error("PRICE_QUERY_AMBIGUOUS", "Giá có phần rưỡi cần đơn vị nghìn hoặc triệu và phần đầu nguyên.", field)
        value += Decimal("0.5") * scale
    if match.group(name + "_extra"):
        extra_scale = UNITS[match.group(name + "_extra_unit")]
        extra = _number(match.group(name + "_extra"), extra_scale > 1, field) * extra_scale
        if extra_scale >= scale or not 0 <= extra < scale:
            _error("PRICE_QUERY_AMBIGUOUS", "Giá ghép chưa rõ. Hãy viết một giá với đầy đủ đơn vị.", field)
        value += extra
    if not 0 <= value <= MAX_PRICE:
        _error("PRICE_VALUE_UNSUPPORTED", "Giá nằm ngoài giới hạn hỗ trợ 0–1.000.000.000 VND.", field)
    return value


def _ceil(value):
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def _floor(value):
    return int(value.to_integral_value(rounding=ROUND_FLOOR))


@dataclass
class PricePlan:
    enabled: bool
    lexical_text: str
    clauses: list[dict]
    min_price: int | None = None
    max_price: int | None = None

    def merge(self, filters, field="options.filters"):
        lower = max(v for v in (filters.min_price, self.min_price, 0) if v is not None)
        upper = min(v for v in (filters.max_price, self.max_price, MAX_PRICE) if v is not None)
        if lower > upper:
            _error("PRICE_FILTER_CONFLICT", "Điều kiện giá trong mô tả mâu thuẫn với bộ lọc. Hãy điều chỉnh trước khi tìm lại.", field)
        return filters.model_copy(update={"min_price": lower if self.min_price is not None else filters.min_price,
                                          "max_price": upper if self.max_price is not None else filters.max_price})

    def public(self, effective_filters):
        return {"enabled": self.enabled, "parser_version": PARSER_VERSION, "applied": bool(self.clauses),
                "clauses": self.clauses, "inferred_filters": {"min_price": self.min_price, "max_price": self.max_price},
                "effective_filters": effective_filters.model_dump(), "lexical_text": self.lexical_text}


def interpret_price(text, enabled=True, field="text"):
    text = normalize_text(text or "")
    if len(text) > 500:
        _error("TEXT_TOO_LONG", "Mô tả tối đa 500 ký tự.", field)
    if not enabled:
        return PricePlan(False, text, [])
    folded, positions = _source(text)
    if re.search(r"[$€£]\s*" + NUMBER + r"|(?<!\w)" + NUMBER + r"\s*(?:usd|eur|gbp|jpy|dollars?|euros?)(?!\w)", folded):
        _error("PRICE_CURRENCY_UNSUPPORTED", "Tìm kiếm giá chỉ hỗ trợ VND. Hãy nhập giới hạn bằng đồng Việt Nam.", field)
    matches = []
    occupied = set()
    for pattern, is_range in [(RANGE, True), (SINGLE, False)]:
        for match in pattern.finditer(folded):
            if any(i in occupied for i in range(match.start(), match.end())):
                continue
            # Unsupported scopes must not invert or soften a comparison silently.
            prefix = folded[:match.start()]
            suffix = folded[match.end():]
            if re.search(r"\b(?:khong(?: phai)?|not|khoang|tam|xap xi|approximately|about|khong muon|khong can)\s*$", prefix) or re.match(r"\s+(?:ruoi|hoac|or)\b", suffix):
                _error("PRICE_QUERY_AMBIGUOUS", "Điều kiện giá có phủ định, xấp xỉ hoặc lựa chọn chưa rõ. Hãy dùng bộ lọc giá hoặc viết lại giới hạn.", field)
            if is_range:
                a = _amount(match, "a", field, match.group("b_unit"))
                b = _amount(match, "b", field, match.group("a_unit"))
                lower, upper = _ceil(a), _floor(b)
            else:
                value = _amount(match, "a", field)
                op = OPERATORS[match.group("op")]
                lower = _floor(value) + 1 if op == "gt" else _ceil(value) if op == "gte" else None
                upper = _ceil(value) - 1 if op == "lt" else _floor(value) if op == "lte" else None
            if (lower is not None and lower > MAX_PRICE) or (upper is not None and upper < 0) or (lower is not None and upper is not None and lower > upper):
                _error("PRICE_QUERY_CONFLICT", "Khoảng giá không có giá trị VND hợp lệ. Hãy kiểm tra lại hai giới hạn.", field)
            matches.append((match.start(), match.end(), lower, upper))
            occupied.update(range(match.start(), match.end()))
    for mention in MONEY_MENTION.finditer(folded):
        if not all(i in occupied for i in range(mention.start(), mention.end())):
            _error("PRICE_QUERY_AMBIGUOUS", "Giá trong mô tả chưa có giới hạn rõ. Ví dụ: dưới 1 triệu, hoặc từ 500 nghìn đến 1,5 triệu.", field)
    for context in re.finditer(r"\b(?:gia|ngan sach|price|budget)\s+(?:duoi|tren|tu|toi da|toi thieu|under|over|between)\b", folded):
        if not all(i in occupied for i in range(context.start(), context.end())):
            _error("PRICE_QUERY_AMBIGUOUS", "Chưa hiểu đầy đủ điều kiện giá. Hãy ghi giá và đơn vị rõ ràng hoặc dùng bộ lọc.", field)
    matches.sort()
    clauses, masked = [], list(text)
    lower, upper = None, None
    previous_end = 0
    for start, end, minimum, maximum in matches:
        if previous_end and re.search(r"\b(?:hoac|hay|or)\b", folded[previous_end:start]):
            _error("PRICE_QUERY_AMBIGUOUS", "Chưa hỗ trợ nhiều khoảng giá nối bằng hoặc. Hãy chọn một khoảng trong bộ lọc.", field)
        a, b = positions[start], positions[end - 1] + 1
        clauses.append({"text": text[a:b], "min_price": minimum, "max_price": maximum})
        masked[a:b] = " " * (b - a)
        lower = max(v for v in (lower, minimum) if v is not None) if lower is not None or minimum is not None else None
        upper = min(v for v in (upper, maximum) if v is not None) if upper is not None or maximum is not None else None
        previous_end = end
    if lower is not None and upper is not None and lower > upper:
        _error("PRICE_QUERY_CONFLICT", "Các điều kiện giá trong mô tả mâu thuẫn. Hãy chọn một khoảng giá hợp lệ.", field)
    return PricePlan(True, normalize_text("".join(masked)), clauses, lower, upper)
