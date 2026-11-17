"""
products.py — Normalisation helpers shared by every scraper.

Scrapers return loosely formatted strings ("₹1,299.00", "4.3 out of 5 stars",
"(1.2K)"). This module turns them into one consistent product shape with
numeric companions so clients can sort and compare reliably:

    title, price, rating, reviews_count, url, image, source     (display strings)
    price_value, rating_value, reviews_value                     (numbers or None)
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

_NA = "N/A"

ACCESSORY_KEYWORDS = (
    "bag", "case", "cover", "sleeve", "backpack", "charger", "adapter",
    "stand", "skin", "cable", "screen guard", "tempered glass", "protector",
    "adaptor", "carrycase", "pouch",
)

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_RATING = re.compile(r"(\d+(?:\.\d+)?)")
_COUNT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([kKmMlL]?)")
_RUPEE_PRICE = re.compile(r"^(?:₹|rs\.?|inr)?\s*[\d,]+(?:\.\d+)?$", re.IGNORECASE)


def _clean(value) -> str:
    if value is None:
        return _NA
    text = str(value).strip()
    return text or _NA


def parse_price(value) -> float | None:
    """'₹1,29,999.00' → 129999.0. Returns None when no number is present."""
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = _clean(value)
    if text == _NA:
        return None
    match = _NUMBER.search(text)
    if not match:
        return None
    try:
        number = float(match.group(0).replace(",", ""))
    except ValueError:
        return None
    return number if number > 0 else None


def parse_rating(value) -> float | None:
    """'4.3 out of 5 stars' → 4.3. Only values in 0–5 are accepted."""
    if isinstance(value, (int, float)):
        return float(value) if 0 < value <= 5 else None
    text = _clean(value)
    if text == _NA:
        return None
    match = _RATING.search(text)
    if not match:
        return None
    rating = float(match.group(1))
    return rating if 0 < rating <= 5 else None


def parse_count(value) -> int | None:
    """'(1.2K)' → 1200, '12,345' → 12345, '2.5L' (lakh) → 250000."""
    if isinstance(value, int):
        return value if value >= 0 else None
    text = _clean(value)
    if text == _NA:
        return None
    match = _COUNT.search(text)
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    multiplier = {"k": 1_000, "m": 1_000_000, "l": 100_000}.get(match.group(2).lower(), 1)
    return int(number * multiplier)


def format_inr(value: float) -> str:
    """Format a rupee amount with Indian digit grouping: 129999 → '₹1,29,999'."""
    whole = int(round(value))
    digits = str(abs(whole))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return f"{'-' if whole < 0 else ''}₹{digits}"


def normalize(product: dict, source: str | None = None) -> dict:
    """Return a copy of `product` in the canonical shape."""
    raw_price = product.get("price")
    price_value = parse_price(raw_price)
    price = _clean(raw_price)
    # Re-format rupee prices ("₹12999", "Rs. 5,999") so every source displays alike.
    if price_value is not None and (price == _NA or _RUPEE_PRICE.match(price)):
        price = format_inr(price_value)

    url = _clean(product.get("url"))
    image = _clean(product.get("image"))
    return {
        "title":         _clean(product.get("title")),
        "price":         price,
        "rating":        _clean(product.get("rating")),
        "reviews_count": _clean(product.get("reviews_count")),
        "url":           url if url.startswith("http") else _NA,
        "image":         image if image.startswith("http") else _NA,
        "source":        _clean(source or product.get("source") or "web"),
        "price_value":   price_value,
        "rating_value":  parse_rating(product.get("rating")),
        "reviews_value": parse_count(product.get("reviews_count")),
    }


def normalize_all(products: list[dict], source: str | None = None) -> list[dict]:
    """Normalise a list, dropping untitled rows and duplicate URLs."""
    seen: set[str] = set()
    out: list[dict] = []
    for raw in products or []:
        if not isinstance(raw, dict):
            continue
        item = normalize(raw, source)
        if item["title"] == _NA:
            continue
        key = item["url"] if item["url"] != _NA else item["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


# ── Query helpers (used by the store scrapers) ──────────────────────────────

_BUDGET = re.compile(
    r"\b(?:under|below|upto|up\s+to|within|less\s+than|max|budget(?:\s+of)?)\s*"
    r"(?:rs\.?|₹|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?)?\b",
    re.IGNORECASE,
)
_QUERY_STOPWORDS = {
    "buy", "online", "india", "best", "price", "prices", "cheap", "with", "for", "and", "the",
    "from", "new", "latest", "top", "good", "rupees", "around", "size", "pack", "set",
    "of", "in", "to", "on", "by", "an", "is", "my", "me", "it", "or", "rs", "inr", "want", "need",
    # Who/what it is for — the chat adds these ("college laptop", "gym earbuds"), but
    # product names never contain them.
    "college", "school", "office", "gym", "call", "calls", "home", "kid", "kids", "student",
    "students", "daily", "use", "travel", "gift", "beginner", "beginners", "work", "study",
    "mic", "mics",
}
# A title using any of these words also counts as a match for the key word.
_SYNONYMS = {
    "wireless": ("tws", "bluetooth"),
    "earbud": ("buds", "tws", "airpods", "earphone"),
    "earphone": ("earbud", "buds", "headphone", "neckband"),
    "headphone": ("headset", "earphone"),
    "laptop": ("notebook", "macbook", "chromebook"),
    "phone": ("mobile", "smartphone", "iphone"),
    "mobile": ("phone", "smartphone", "iphone"),
    "smartphone": ("phone", "mobile", "iphone"),
    "tv": ("television",),
    "television": ("tv",),
    "fridge": ("refrigerator",),
    "refrigerator": ("fridge",),
    "watch": ("smartwatch",),
    "smartwatch": ("watch",),
}


# A price range such as "50-60k", "50k to 60k" or "between 50000 and 60000".
_RANGE = re.compile(
    r"\b(?:between\s+)?(?:rs\.?|₹|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?)?\s*"
    r"(?:-|–|to|and)\s*(?:rs\.?|₹|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?)?(?!\w)",
    re.IGNORECASE,
)


# Units that make a range a spec, not a price ("10000-20000 mAh", "128-256 GB").
_SPEC_UNIT = re.compile(r"\s*(mah|gb|tb|mb|w|watts?|hz|inch|inches|cm|mm|kg|litres?|liters?|l)\b", re.IGNORECASE)


def _rupees(number: str, unit: str | None) -> float:
    unit = (unit or "").lower()
    factor = 1_000 if unit in {"k", "thousand"} else 100_000 if unit.startswith(("lakh", "lac")) else 1
    return float(number.replace(",", "")) * factor


def split_budget(query: str) -> tuple[str, float | None]:
    """'earbuds under ₹3,000' → ('earbuds', 3000.0); '…under 1.5 lakh' → 150000.

    A range uses its upper limit: 'gaming laptop 50-60k' → ('gaming laptop', 60000.0).
    Small ranges like '8-16 GB' or '5-6 inch' are not prices and are left alone.
    """
    match = _BUDGET.search(query)
    if match:
        amount = _rupees(match.group(1), match.group(2))
    else:
        match = _RANGE.search(query)
        if not match:
            return query.strip(), None
        amount = _rupees(match.group(3), match.group(4) or match.group(2))
        if amount < 1_000 or _SPEC_UNIT.match(query[match.end():]):
            return query.strip(), None
    cleaned = " ".join((query[:match.start()] + " " + query[match.end():]).split())
    cleaned = re.sub(r"\b(?:rs\.?|inr|rupees)\s*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = " ".join(w for w in cleaned.split() if w != "₹")
    return cleaned, (amount if amount > 0 else None)


def query_keywords(query: str) -> list[str]:
    """Words that say what the product is: 'men running shoes' → men, running, shoe."""
    words = re.findall(r"[a-z0-9]+", split_budget(query)[0].lower())
    keep = []
    for w in words:
        has_letter = any(c.isalpha() for c in w)
        if w in _QUERY_STOPWORDS or (has_letter and len(w) < 2):
            continue
        if not has_letter and not 2 <= len(w) <= 4:   # "15" in "iphone 15" counts, "9" does not
            continue
        keep.append(_singular(w) if has_letter else w)
    return keep


def _singular(word: str) -> str:
    """shoes → shoe, watches → watch, batteries → battery; wireless stays."""
    if len(word) <= 3:
        return word
    if word.endswith(("ches", "shes", "sses", "xes")):
        return word[:-2]
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def is_relevant(keywords: list[str], title: str, url: str = "") -> bool:
    """True when the title/link mentions enough of the query's product words.

    Two words → both must appear; longer queries → at least half. This drops
    a "shoe rack" for "running shoes" but keeps "Noise Buds Earbuds" for
    "wireless earbuds".
    """
    if not keywords:
        return True
    text = f"{title} {urlparse(url).path}".lower().replace("-", " ").replace("_", " ")
    compact = re.sub(r"[^a-z0-9]", "", text)
    hits = sum(
        1 for kw in keywords
        if any(re.search(rf"\b{re.escape(w)}", text) or (len(w) >= 5 and w in compact)
               for w in (kw, *_SYNONYMS.get(kw, ())))
    )
    needed = len(keywords) if len(keywords) <= 2 else (len(keywords) + 1) // 2
    return hits >= needed


def wants_accessory(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in ACCESSORY_KEYWORDS)


_ACCESSORY_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in ACCESSORY_KEYWORDS) + r")(?:es|s)?\b"
)


def is_accessory(title: str) -> bool:
    """Whole-word match, so 'standard' or 'showcase' are not accessories."""
    return bool(_ACCESSORY_RE.search(title.lower()))
