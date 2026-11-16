"""Amazon scraper parsing, on a small saved-style search page (no network)."""

import pytest

import scraper


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda s: None)

CARD = """
<div data-component-type="s-search-result" data-asin="{asin}">
  <h2 aria-label="{title}"><span>{title}</span></h2>
  <span class="a-price"><span class="a-offscreen">{price}</span></span>
  <a class="a-popover-trigger"><i class="a-icon-star"><span class="a-icon-alt">4.3 out of 5 stars</span></i></a>
  {reviews}
  <a class="a-link-normal s-no-outline" href="/dp/{asin}"><img class="s-image" src="https://img/{asin}.jpg"></a>
</div>
"""

REVIEWS_2026 = ('<a class="a-link-normal s-underline-text" aria-label="53,496 ratings" '
                'href="/dp/B1#customerReviews"><span>(53.4K)</span></a>')
REVIEWS_OLD = '<span class="a-size-base s-underline-text">1,264</span>'

PAGE = "<html><body>" + "".join([
    CARD.format(asin="B1", title="OnePlus Nord Buds 3r TWS Earbuds", price="₹1,999", reviews=REVIEWS_2026),
    CARD.format(asin="B2", title="boAt Airdopes 141", price="₹1,199", reviews=REVIEWS_OLD),
    CARD.format(asin="B3", title="Unrated Earbuds", price="₹186", reviews=""),
]) + "</body></html>"


class _Response:
    status_code = 200
    text = PAGE


class _Session:
    def __init__(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        return _Response()


def test_amazon_cards_are_parsed_with_review_counts(monkeypatch):
    monkeypatch.setattr(scraper.requests, "Session", _Session)
    out = scraper.scrape("wireless earbuds")

    assert [p["title"] for p in out] == ["OnePlus Nord Buds 3r TWS Earbuds", "boAt Airdopes 141", "Unrated Earbuds"]
    first = out[0]
    assert first["reviews_count"] == "53,496 ratings"     # exact number from the aria-label, not "(53.4K)"
    assert first["price"] == "₹1,999"
    assert first["rating"] == "4.3 out of 5 stars"
    assert first["url"] == "https://www.amazon.in/dp/B1"
    assert first["image"] == "https://img/B1.jpg"
    assert out[1]["reviews_count"] == "1,264"              # older markup still works
    assert out[2]["reviews_count"] == "N/A"


def test_amazon_review_count_normalises_to_a_number(monkeypatch):
    from products import normalize
    monkeypatch.setattr(scraper.requests, "Session", _Session)
    first = normalize(scraper.scrape("wireless earbuds")[0], "amazon")
    assert first["reviews_value"] == 53496
    assert first["rating_value"] == 4.3


BRAND_SPLIT_PAGE = """<html><body>
<div data-component-type="s-search-result" data-asin="AD1" class="s-result-item AdHolder">
  <h2 class="a-size-mini s-line-clamp-1"><span>Apple</span></h2>
  <h2 class="a-size-medium a-color-base a-text-normal"><span>iPhone 16 128 GB</span></h2>
  <span class="a-price"><span class="a-offscreen">₹79,990</span></span>
</div>
<div data-component-type="s-search-result" data-asin="P1" class="s-result-item">
  <h2 class="a-size-mini s-line-clamp-1"><span>Apple</span></h2>
  <h2 class="a-size-medium a-color-base a-text-normal"><span>iPhone 15 (128 GB) - Black</span></h2>
  <span class="a-price"><span class="a-offscreen">₹59,900</span></span>
</div>
<div data-component-type="s-search-result" data-asin="P2" class="s-result-item">
  <h2 class="a-size-mini s-line-clamp-1"><span>vivo</span></h2>
  <h2 class="a-size-medium a-color-base a-text-normal"><span>vivo V80 5G (8GB RAM)</span></h2>
  <span class="a-price"><span class="a-offscreen">₹62,999</span></span>
</div>
</body></html>"""


def test_brand_heading_is_joined_and_sponsored_cards_skipped(monkeypatch):
    class Response:
        status_code = 200
        text = BRAND_SPLIT_PAGE

    class Session(_Session):
        def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(scraper.requests, "Session", Session)
    assert [p["title"] for p in scraper.scrape("iphone 15")] == [
        "Apple iPhone 15 (128 GB) - Black",     # brand added, not just "Apple"
        "vivo V80 5G (8GB RAM)",                # brand already in the name
    ]


def _paged_session(pages: dict, calls: list):
    """A fake session that serves `pages[n]` for "&page=n" (page 1 has no page parameter)."""
    class Response:
        def __init__(self, text, status=200):
            self.text, self.status_code = text, status

    class Session(_Session):
        def get(self, url, *args, **kwargs):
            calls.append(url)
            n = int(url.rsplit("&page=", 1)[1]) if "&page=" in url else 1
            body = pages.get(n)
            return Response(body) if body else Response("<html>Robot Check: enter the captcha</html>", 503)

    return Session


def _page(*asins):
    return "<html><body>" + "".join(
        CARD.format(asin=a, title=f"Earbuds {a}", price="₹999", reviews="") for a in asins) + "</body></html>"


def test_amazon_reads_the_second_page(monkeypatch):
    calls = []
    monkeypatch.setattr(scraper.requests, "Session", _paged_session({1: _page("A1", "A2"), 2: _page("A2", "A3")}, calls))
    out = scraper.scrape("earbuds", pages=2)
    assert [p["title"] for p in out] == ["Earbuds A1", "Earbuds A2", "Earbuds A3"]   # A2 not repeated
    assert calls[1].endswith("&page=2")


def test_amazon_keeps_page_one_when_page_two_is_blocked(monkeypatch):
    calls = []
    monkeypatch.setattr(scraper.requests, "Session", _paged_session({1: _page("A1", "A2")}, calls))
    out = scraper.scrape("earbuds", pages=3)
    assert [p["title"] for p in out] == ["Earbuds A1", "Earbuds A2"]
    assert len(calls) == 2            # page 2 tried once, no retries, page 3 not tried


def test_amazon_stops_at_the_result_limit(monkeypatch):
    calls = []
    monkeypatch.setattr(scraper.requests, "Session", _paged_session({1: _page("A1", "A2", "A3"), 2: _page("A4")}, calls))
    out = scraper.scrape("earbuds", max_results=2, pages=2)
    assert len(out) == 2 and len(calls) == 1      # limit reached on page 1, so page 2 is skipped
