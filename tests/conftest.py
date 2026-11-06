import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Configure the app for tests *before* any project module is imported.
_tmp = tempfile.mkdtemp(prefix="shopping-agent-tests-")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{Path(_tmp, 'test.db').as_posix()}",
    "APP_ENV": "test",
    "LLM_PROVIDER": "nvidia",
    "NVIDIA_API_KEY": "test-key",
    "AGENT_MONITOR": "0",
    "API_KEY": "",
    "LOG_LEVEL": "WARNING",
})

AMAZON = [
    {"title": "Sony WH-1000XM5 Wireless Headphones", "price": "₹26,990", "rating": "4.4 out of 5 stars",
     "reviews_count": "(12,345)", "url": "https://www.amazon.in/dp/A1", "image": "https://img/a1.jpg"},
    {"title": "Headphone Carry Case", "price": "₹499", "rating": "4.1 out of 5 stars",
     "reviews_count": "1.2K", "url": "https://www.amazon.in/dp/A2", "image": "N/A"},
]
FLIPKART = [
    {"title": "boAt Rockerz 550", "price": "₹1799", "rating": "4.2", "reviews_count": "98000",
     "url": "https://www.flipkart.com/p/F1", "image": "https://img/f1.jpg", "source": "flipkart"},
]
WEB = [
    {"title": "JBL Tune 760NC", "price": "Rs. 5,999", "rating": "N/A", "reviews_count": "N/A",
     "url": "https://www.croma.com/jbl", "image": "https://icon", "source": "Croma"},
]


@pytest.fixture()
def client(monkeypatch):
    """A TestClient with scrapers and LLM calls replaced by fakes."""
    from fastapi.testclient import TestClient

    import api
    import pipeline

    monkeypatch.setattr(pipeline, "translate_query", lambda q: "wireless headphones")
    monkeypatch.setattr(pipeline, "scrape_amazon", lambda q: [dict(p) for p in AMAZON])
    monkeypatch.setattr(pipeline, "scrape_flipkart", lambda q: [dict(p) for p in FLIPKART])
    monkeypatch.setattr(pipeline, "scrape_ddg", lambda q: [dict(p) for p in WEB])
    monkeypatch.setattr(
        pipeline, "recommend",
        lambda q, products: {"product": products[0], "reason": "Best balance of price and reviews."},
    )
    api.limiter.reset()
    with TestClient(api.app) as c:
        yield c
    api.limiter.reset()
