import time
import uuid

import api
import pipeline
from config import settings

DEVICE_A = {"X-Client-ID": "device-aaaaaaaa"}
DEVICE_B = {"X-Client-ID": "device-bbbbbbbb"}


def test_health_reports_db_and_llm(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["db"] == "connected" and body["llm"] == "configured"
    assert "X-Request-ID" in r.headers
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_search_returns_normalised_results_and_saves_session(client):
    r = client.post("/api/search", json={"query": "achhe headphones"}, headers=DEVICE_A)
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "wireless headphones"
    assert body["session_id"]
    assert body["source_status"] == {"amazon": "ok", "flipkart": "ok", "web": "ok"}
    # Accessory ("Carry Case") is filtered out because the query isn't for one.
    assert [p["title"] for p in body["results"]["amazon"]] == ["Sony WH-1000XM5 Wireless Headphones"]
    flip = body["results"]["flipkart"][0]
    assert flip["price"] == "₹1,799" and flip["price_value"] == 1799.0
    web = body["results"]["web"][0]
    assert web["source"] == "Croma" and web["price"] == "₹5,999"
    assert body["recommendation"]["product"]["title"].startswith("Sony")


def test_search_with_no_results(client, monkeypatch):
    for name in ("scrape_amazon", "scrape_flipkart", "scrape_ddg"):
        monkeypatch.setattr(pipeline, name, lambda q: [])
    body = client.post("/api/search", json={"query": "zzzz"}).json()
    assert body["session_id"] is None
    assert body["recommendation"] is None
    assert body["source_status"] == {"amazon": "empty", "flipkart": "empty", "web": "empty"}


def test_failing_and_slow_scrapers_do_not_block_the_response(client, monkeypatch):
    def broken(q):
        raise RuntimeError("blocked")

    def slow(q):
        time.sleep(2)
        return []

    monkeypatch.setattr(pipeline, "scrape_flipkart", broken)
    monkeypatch.setattr(pipeline, "scrape_ddg", slow)
    monkeypatch.setattr(settings, "scrape_timeout_seconds", 0.5)
    started = time.perf_counter()
    body = client.post("/api/search", json={"query": "headphones"}).json()
    assert time.perf_counter() - started < 1.8
    assert body["source_status"]["flipkart"] == "failed"
    assert body["source_status"]["web"] == "timeout"
    assert body["results"]["amazon"]


def test_translation_failure_falls_back_to_raw_query(client, monkeypatch):
    def flaky(q):
        raise TimeoutError("llm down")
    monkeypatch.setattr(pipeline, "translate_query", flaky)
    body = client.post("/api/search", json={"query": "headphones"}).json()
    assert body["query"] == "headphones"


def test_recommendation_failure_uses_highest_rated(client, monkeypatch):
    def broken(q, products):
        raise RuntimeError("llm down")
    monkeypatch.setattr(pipeline, "recommend", broken)
    body = client.post("/api/search", json={"query": "headphones"}).json()
    assert body["recommendation"]["product"]["title"].startswith("Sony")  # 4.4 is the top rating


def test_search_validation(client):
    assert client.post("/api/search", json={"query": "x"}).status_code == 422
    assert client.post("/api/search", json={"query": "y" * 201}).status_code == 422


def test_history_is_scoped_per_device(client):
    sid = client.post("/api/search", json={"query": "headphones"}, headers=DEVICE_A).json()["session_id"]

    mine = client.get("/api/sessions?summary=true", headers=DEVICE_A).json()
    assert sid in [s["session_id"] for s in mine]
    assert "results" not in mine[0] and mine[0]["result_counts"]["amazon"] == 1

    theirs = client.get("/api/sessions", headers=DEVICE_B).json()
    assert sid not in [s["session_id"] for s in theirs]
    assert client.get(f"/api/sessions/{sid}", headers=DEVICE_B).status_code == 404
    assert client.get(f"/api/sessions/{sid}", headers=DEVICE_A).json()["results"]["amazon"]


def test_delete_session_and_clear_history(client):
    sid = client.post("/api/search", json={"query": "headphones"}, headers=DEVICE_A).json()["session_id"]
    assert client.delete(f"/api/sessions/{sid}", headers=DEVICE_B).status_code == 404
    assert client.delete(f"/api/sessions/{sid}", headers=DEVICE_A).status_code == 204
    assert client.get(f"/api/sessions/{sid}", headers=DEVICE_A).status_code == 404

    client.post("/api/search", json={"query": "headphones"}, headers=DEVICE_A)
    assert client.delete("/api/sessions", headers=DEVICE_A).json()["deleted"] >= 1
    assert client.get("/api/sessions", headers=DEVICE_A).json() == []
    assert client.delete("/api/sessions").status_code == 400


def test_invalid_ids_are_rejected(client):
    assert client.get("/api/sessions/not-a-uuid").status_code == 404
    assert client.get(f"/api/sessions/{uuid.uuid4()}").status_code == 404
    assert client.get("/api/sessions", headers={"X-Client-ID": "bad id!"}).status_code == 400


def test_chat_masks_cards_and_validates_roles(client, monkeypatch):
    seen = {}

    def fake_process(history):
        seen["history"] = history
        return {"message": "Budget?", "is_ready_to_search": False, "search_query": ""}

    monkeypatch.setattr(api, "process_chat", fake_process)
    r = client.post("/api/chat", json={"history": [
        {"role": "agent", "content": "Hi!"},
        {"role": "user", "content": "pay with 4111 1111 1111 1234"},
    ]})
    assert r.status_code == 200 and r.json()["message"] == "Budget?"
    assert "1111 1111 1234" not in seen["history"][1]["content"]
    assert client.post("/api/chat", json={"history": [{"role": "system", "content": "x"}]}).status_code == 422
    assert client.post("/api/chat", json={"history": []}).status_code == 422


def test_rate_limit_returns_429_with_retry_after(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_search_per_min", 2)
    for _ in range(2):
        assert client.post("/api/search", json={"query": "headphones"}).status_code == 200
    r = client.post("/api/search", json={"query": "headphones"})
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1


def test_api_key_is_enforced_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "s3cret")
    assert client.get("/api/sessions").status_code == 401
    assert client.get("/api/sessions", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/api/sessions", headers={"X-API-Key": "s3cret"}).status_code == 200
    assert client.get("/health").status_code == 200  # probes stay open
