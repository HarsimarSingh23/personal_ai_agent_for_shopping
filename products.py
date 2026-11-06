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

_NA = "N/A"

ACCESSORY_KEYWORDS = (
    "bag", "case", "cover", "sleeve", "backpack", "charger", "adapter",
    "stand", "skin", "cable", "screen guard", "tempered glass", "protector",
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


def wants_accessory(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in ACCESSORY_KEYWORDS)


_ACCESSORY_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in ACCESSORY_KEYWORDS) + r")(?:es|s)?\b"
)


def is_accessory(title: str) -> bool:
    """Whole-word match, so 'standard' or 'showcase' are not accessories."""
    return bool(_ACCESSORY_RE.search(title.lower()))
