import pytest

from products import format_inr, is_accessory, normalize, normalize_all, parse_count, parse_price, parse_rating


@pytest.mark.parametrize("raw, expected", [
    ("₹1,29,999.00", 129999.0),
    ("Rs. 5,999", 5999.0),
    ("₹1799", 1799.0),
    (2499, 2499.0),
    ("N/A", None),
    ("", None),
    (None, None),
    ("Free", None),
])
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("4.4 out of 5 stars", 4.4),
    ("4.2", 4.2),
    (3.9, 3.9),
    ("N/A", None),
    ("12", None),  # out of range
])
def test_parse_rating(raw, expected):
    assert parse_rating(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("(12,345)", 12345),
    ("1.2K", 1200),
    ("2.5L", 250000),
    ("98000", 98000),
    ("N/A", None),
])
def test_parse_count(raw, expected):
    assert parse_count(raw) == expected


def test_format_inr_uses_indian_grouping():
    assert format_inr(999) == "₹999"
    assert format_inr(1799) == "₹1,799"
    assert format_inr(129999) == "₹1,29,999"
    assert format_inr(12345678) == "₹1,23,45,678"


def test_normalize_adds_numeric_fields_and_formats_price():
    p = normalize({"title": "X", "price": "₹12999", "rating": "4.5", "reviews_count": "1,000",
                   "url": "https://x", "image": "relative.jpg"}, "flipkart")
    assert p["price"] == "₹12,999"
    assert p["price_value"] == 12999.0
    assert p["rating_value"] == 4.5
    assert p["reviews_value"] == 1000
    assert p["source"] == "flipkart"
    assert p["image"] == "N/A"  # non-http images are dropped


def test_normalize_all_dedupes_and_drops_untitled():
    items = [
        {"title": "A", "url": "https://a"},
        {"title": "A again", "url": "https://a"},
        {"title": "", "url": "https://b"},
        "not a dict",
    ]
    assert [p["title"] for p in normalize_all(items, "amazon")] == ["A"]


@pytest.mark.parametrize("title, expected", [
    ("Laptop Sleeve 15 inch", True),
    ("Phone Cases pack of 2", True),
    ("Dell Inspiron Standard Laptop", False),  # 'stand' inside 'standard'
    ("Glass showcase cabinet", False),
])
def test_is_accessory_matches_whole_words(title, expected):
    assert is_accessory(title) is expected
