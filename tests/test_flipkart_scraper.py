"""Flipkart scraper paging, with the page fetch replaced (no network)."""

import json

import pytest

import flipkart_scraper as fk


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fk.time, "sleep", lambda s: None)


def _page(*ids):
    products = [{"productInfo": {"value": {
        "titles": {"title": f"Phone {i}"},
        "pricing": {"finalPrice": {"value": 10000 + i}},
        "smartUrl": f"https://www.flipkart.com/p/{i}",
        "rating": {"average": 4.2, "count": 100},
        "media": {"images": [{"url": "https://img/{@width}/{@height}/x.jpg?q={@quality}"}]},
    }}} for i in ids]
    return f"<script>window.__INITIAL_STATE__ = {json.dumps({'slots': products})};</script>"


def _fake_fetch(pages: dict, calls: list):
    def fetch(url, attempts=3):
        calls.append((url, attempts))
        n = int(url.rsplit("&page=", 1)[1]) if "&page=" in url else 1
        return pages.get(n, "")
    return fetch


def test_flipkart_combines_pages_without_duplicates(monkeypatch):
    calls = []
    monkeypatch.setattr(fk, "_fetch", _fake_fetch({1: _page(1, 2), 2: _page(2, 3)}, calls))
    out = fk.scrape_flipkart("phone", max_results=10, pages=2)
    assert [p["title"] for p in out] == ["Phone 1", "Phone 2", "Phone 3"]
    assert out[0]["price"] == "₹10001" and out[0]["image"] == "https://img/400/400/x.jpg?q=70"
    assert calls == [(calls[0][0], 3), (calls[0][0] + "&page=2", 1)]   # later pages: one try only


def test_flipkart_keeps_page_one_when_page_two_fails(monkeypatch):
    calls = []
    monkeypatch.setattr(fk, "_fetch", _fake_fetch({1: _page(1, 2)}, calls))
    out = fk.scrape_flipkart("phone", max_results=10, pages=3)
    assert len(out) == 2 and len(calls) == 2


def test_flipkart_skips_page_two_when_page_one_is_enough(monkeypatch):
    calls = []
    monkeypatch.setattr(fk, "_fetch", _fake_fetch({1: _page(1, 2, 3), 2: _page(4)}, calls))
    assert len(fk.scrape_flipkart("phone", max_results=3, pages=2)) == 3
    assert len(calls) == 1


def test_flipkart_returns_nothing_when_page_one_fails(monkeypatch):
    monkeypatch.setattr(fk, "_fetch", _fake_fetch({}, []))
    assert fk.scrape_flipkart("phone", pages=2) == []
