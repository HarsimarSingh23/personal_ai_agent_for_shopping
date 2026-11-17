"""Other-stores search (Croma, Reliance Digital, web fallback) and query helpers.

No network: every outside call is replaced with canned data.
"""

import pytest

import ddg_scraper
import store_scraper
from products import is_relevant, query_keywords, split_budget


# ── Query helpers ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query, expected", [
    ("wireless earbuds under 3000", ("wireless earbuds", 3000.0)),
    ("earbuds under ₹3,000", ("earbuds", 3000.0)),
    ("laptop under 50k", ("laptop", 50000.0)),
    ("phone below 1.5 lakh", ("phone", 150000.0)),
    ("laptop under 50000 rupees", ("laptop", 50000.0)),
    ("tv within rs 30000 for bedroom", ("tv for bedroom", 30000.0)),
    ("samsung galaxy s24", ("samsung galaxy s24", None)),
])
def test_split_budget(query, expected):
    assert split_budget(query) == expected


@pytest.mark.parametrize("query, expected", [
    ("wireless earbuds under 3000", ["wireless", "earbud"]),
    ("men running shoes size 9", ["men", "running", "shoe"]),
    ("smart watches", ["smart", "watch"]),
    ("iphone 15 128gb", ["iphone", "15", "128gb"]),
    ("smart tv", ["smart", "tv"]),
])
def test_query_keywords(query, expected):
    assert query_keywords(query) == expected


@pytest.mark.parametrize("query, title, expected", [
    ("running shoes", "Origin OMS1 Shoe Rack Dehumidifier", False),
    ("running shoes", "Buy Men Running Shoes Online", True),
    ("wireless earbuds", "Croma IE165 TWS Earbuds with Passive Noise Cancellation", True),  # TWS = wireless
    ("wireless earbuds", "JBL Wave Beam 2 Ear Buds Wireless", True),                         # "Ear Buds"
    ("laptop under 50000", "DELL Thin & Light Notebook (8GB, 512GB)", True),                 # notebook = laptop
    ("iphone 15", "Apple iPhone 15 (128GB, Black)", True),
    ("iphone 15", "Apple iPhone 16 (128GB, Black)", False),
    ("smart tv", "Croma Led TVs Online", False),
])
def test_is_relevant(query, title, expected):
    assert is_relevant(query_keywords(query), title) is expected


# ── Croma / Reliance Digital ─────────────────────────────────────────────────

def _croma_item(name, price, rating=0, count=0, code="1"):
    return {"name": name, "url": f"/p/{code}", "price": {"value": price}, "averageRating": rating,
            "numberOfRatings": count, "plpImage": f"https://img/{code}.png"}


CROMA_PAGE = {"products": [
    _croma_item("Apple AirPods 5 with Charging Case", 14900, 5.0, 2, "a1"),            # over budget
    _croma_item("Croma IE165 TWS Earbuds", 949, 4.46, 50, "c1"),
    _croma_item("Origin Shoe Rack Dehumidifier", 999, code="x1"),                      # not relevant
    _croma_item("noise Pop Buds TWS Earbuds (Black)", 1099, 4.1, 18, "n1"),
    _croma_item("noise Pop Buds TWS Earbuds (Blue)", 1099, 4.1, 18, "n2"),             # colour variant
    {"name": "Broken item without price", "url": "/p/b"},
]}


def test_croma_filters_budget_relevance_and_colour_variants(monkeypatch):
    calls = []
    monkeypatch.setattr(store_scraper, "_get_json", lambda url: calls.append(url) or CROMA_PAGE)
    out = store_scraper.scrape_croma("wireless earbuds under 3000")

    assert [p["title"] for p in out] == ["Croma IE165 TWS Earbuds", "noise Pop Buds TWS Earbuds (Black)"]
    assert out[0] == {
        "title": "Croma IE165 TWS Earbuds", "price": "₹949", "rating": "4.5", "reviews_count": "50",
        "url": "https://www.croma.com/p/c1", "image": "https://img/c1.png", "source": "Croma",
    }
    assert len(calls) == 2                      # budget → two pages
    assert "under" not in calls[0] and "wireless%20earbuds" in calls[0]


def test_croma_hides_zero_ratings(monkeypatch):
    monkeypatch.setattr(store_scraper, "_get_json", lambda url: {"products": [_croma_item("Apple iPhone 15", 59900)]})
    [item] = store_scraper.scrape_croma("iphone 15")
    assert item["rating"] == "N/A" and item["reviews_count"] == "N/A"


def test_reliance_parses_products(monkeypatch):
    data = {"items": [
        {"name": "Noise Buds X2 Truly Wireless Earbuds", "slug": "noise-buds-x2",
         "price": {"effective": {"min": 1599}}, "medias": [{"type": "image", "url": "https://img/r1.jpg"}],
         "rating": 0, "sellable": True},
        {"name": "Unsellable Wireless Earbuds", "slug": "gone", "price": {"effective": {"min": 999}}, "sellable": False},
    ]}
    monkeypatch.setattr(store_scraper, "_get_json", lambda url: data)
    out = store_scraper.scrape_reliance("wireless earbuds under 3000")
    assert out == [{
        "title": "Noise Buds X2 Truly Wireless Earbuds", "price": "₹1599", "rating": "N/A", "reviews_count": "N/A",
        "url": "https://www.reliancedigital.in/product/noise-buds-x2", "image": "https://img/r1.jpg",
        "source": "Reliance Digital",
    }]


def test_other_stores_survive_one_shop_failing(monkeypatch):
    def broken(query):
        raise ConnectionError("down")
    monkeypatch.setattr(store_scraper, "_STORES", {
        "Croma": broken,
        "Reliance Digital": lambda q: [{"title": "R1"}, {"title": "R2"}],
    })
    monkeypatch.setattr(store_scraper, "scrape_ddg", lambda q: pytest.fail("web search not needed"))
    assert [p["title"] for p in store_scraper.scrape_other_stores("tv")] == ["R1", "R2"]


def test_other_stores_alternate_between_shops(monkeypatch):
    monkeypatch.setattr(store_scraper, "_STORES", {
        "Croma": lambda q: [{"title": "C1"}, {"title": "C2"}, {"title": "C3"}],
        "Reliance Digital": lambda q: [{"title": "R1"}],
    })
    assert [p["title"] for p in store_scraper.scrape_other_stores("tv")] == ["C1", "R1", "C2", "C3"]


def test_other_stores_fall_back_to_web_search(monkeypatch):
    monkeypatch.setattr(store_scraper, "_STORES", {"Croma": lambda q: [], "Reliance Digital": lambda q: []})
    monkeypatch.setattr(store_scraper, "scrape_ddg", lambda q: [{"title": f"web: {q}"}])
    assert store_scraper.scrape_other_stores("running shoes") == [{"title": "web: running shoes"}]


# ── Web-search fallback ──────────────────────────────────────────────────────

@pytest.mark.parametrize("text, expected", [
    ("boAt Airdopes 141 at ₹1,299 only", "₹1,299"),
    ("Best earbuds under ₹3,000", None),
    ("Truly Wireless Earbuds | Upto RS. 3000 OFF", None),
    ("Flat ₹500 off — now ₹2,499", "₹2,499"),
    ("Prices from ₹, see store", None),
    ("", None),
])
def test_extract_price_skips_budgets_and_discounts(text, expected):
    assert ddg_scraper._extract_price(text) == expected


@pytest.mark.parametrize("url, expected", [
    ("https://www.croma.com/p/123", "Croma"),
    ("https://www.myntra.com/men-running-shoes", "Myntra"),
    ("https://store.reliancedigital.in/nizamabad", None),     # store locator
    ("https://www.smartprix.com/earbuds", None),              # not a shop
])
def test_shop_for(url, expected):
    assert ddg_scraper._shop_for(url) == expected


class _FakeDDGS:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def text(self, query, max_results=10):
        if "site:" in query:
            raise RuntimeError("No results found")
        return [
            {"href": "https://www.myntra.com/men-running-shoes", "title": "Buy Men Running Shoes Online", "body": "From ₹999"},
            {"href": "https://www.croma.com/unboxed/best-running-shoes", "title": "Running shoes guide", "body": ""},
            {"href": "https://www.smartprix.com/running-shoes", "title": "Running Shoes Prices", "body": ""},
            {"href": "https://www.croma.com/croma-led-tvs/bc/1", "title": "Buy Croma LED TVs", "body": ""},
            {"href": "https://www.amazon.in/running-shoes", "title": "Men Running Shoes", "body": ""},
        ]


def test_web_search_keeps_only_relevant_shop_pages(monkeypatch):
    monkeypatch.setattr(ddg_scraper, "DDGS", _FakeDDGS)
    out = ddg_scraper.scrape_ddg("men running shoes")
    assert [(p["source"], p["url"], p["price"]) for p in out] == [
        ("Myntra", "https://www.myntra.com/men-running-shoes", "₹999"),
    ]


def test_croma_keeps_page_one_when_page_two_fails(monkeypatch):
    def get_json(url):
        if "currentPage=0" in url:
            return {"products": [_croma_item("Apple iPhone 15 (128GB, Black)", 59900, code="p1")]}
        raise ConnectionError("page 2 down")
    monkeypatch.setattr(store_scraper, "_get_json", get_json)
    assert [p["title"] for p in store_scraper.scrape_croma("iphone 15")] == ["Apple iPhone 15 (128GB, Black)"]


def test_reliance_asks_for_more_products_in_one_request(monkeypatch):
    urls = []
    monkeypatch.setattr(store_scraper, "_get_json", lambda url: urls.append(url) or {"items": []})
    store_scraper.scrape_reliance("tv")
    assert len(urls) == 1 and f"page_size={min(100, 40 * store_scraper.PAGES)}" in urls[0]


@pytest.mark.parametrize("query, expected", [
    ("gaming laptop 50-60k", ("gaming laptop", 60000.0)),
    ("50k-60k study gaming laptop", ("study gaming laptop", 60000.0)),
    ("laptop between 50000 and 60000", ("laptop", 60000.0)),
    ("₹50,000-₹60,000 laptop", ("laptop", 60000.0)),
    ("phone 1-2 lakh", ("phone", 200000.0)),
    ("laptop 8-16GB ram", ("laptop 8-16GB ram", None)),          # not a price
    ("power bank 10000-20000 mah", ("power bank 10000-20000 mah", None)),
    ("fridge 200-300 litres", ("fridge 200-300 litres", None)),
])
def test_split_budget_price_ranges_use_the_upper_limit(query, expected):
    assert split_budget(query) == expected
