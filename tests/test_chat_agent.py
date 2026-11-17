import json

import pytest

import chat_agent
from llm import LLMConfigError


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch):
    # tenacity sleeps between retries; skip the waiting in tests.
    monkeypatch.setattr(chat_agent._get_chat_response.retry, "sleep", lambda _: None)


def _reply(monkeypatch, payload):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr(chat_agent, "_ask", lambda prompt: raw)


def test_string_false_is_not_treated_as_true(monkeypatch):
    _reply(monkeypatch, {"message": "Which budget?", "is_ready_to_search": "false", "search_query": ""})
    out = chat_agent.process_chat([{"role": "user", "content": "laptop"}])
    assert out["is_ready_to_search"] is False


def test_ready_without_query_uses_users_words(monkeypatch):
    _reply(monkeypatch, {"message": "On it!", "is_ready_to_search": True, "search_query": ""})
    out = chat_agent.process_chat([{"role": "user", "content": "i7 gaming laptop"}])
    assert out == {"message": "On it!", "is_ready_to_search": True, "search_query": "i7 gaming laptop"}


def test_json_wrapped_in_prose_and_fences_is_parsed(monkeypatch):
    _reply(monkeypatch, 'Sure!\n```json\n{"message": "Budget?", "is_ready_to_search": false}\n```')
    out = chat_agent.process_chat([{"role": "user", "content": "shoes"}])
    assert out["message"] == "Budget?"


def test_confirmation_forces_search_with_clean_query(monkeypatch):
    _reply(monkeypatch, {"message": "So, a camera bag?", "is_ready_to_search": False})
    history = [
        {"role": "user", "content": "camera bag for travel"},
        {"role": "agent", "content": "So, you're looking for a camera bag?"},
        {"role": "user", "content": "Yes!"},
    ]
    out = chat_agent.process_chat(history)
    assert out["is_ready_to_search"] is True
    assert out["search_query"] == "camera bag for travel"


def test_too_many_rounds_forces_search(monkeypatch):
    _reply(monkeypatch, {"message": "Any colour?", "is_ready_to_search": False})
    history = []
    for text in ["shoes", "running", "men", "size 9"]:
        history += [{"role": "user", "content": text}, {"role": "agent", "content": "ok?"}]
    out = chat_agent.process_chat(history[:-1])
    assert out["is_ready_to_search"] is True


def test_llm_failure_falls_back_to_search(monkeypatch):
    _reply(monkeypatch, "not json at all")
    out = chat_agent.process_chat([{"role": "user", "content": "bluetooth speaker"}])
    assert out["is_ready_to_search"] is True
    assert out["search_query"] == "bluetooth speaker"


def test_llm_failure_on_greeting_asks_instead_of_searching(monkeypatch):
    _reply(monkeypatch, "not json at all")
    out = chat_agent.process_chat([{"role": "user", "content": "hi"}])
    assert out["is_ready_to_search"] is False


def test_config_error_propagates(monkeypatch):
    def boom(prompt):
        raise LLMConfigError("no key")
    monkeypatch.setattr(chat_agent, "_ask", boom)
    with pytest.raises(LLMConfigError):
        chat_agent.process_chat([{"role": "user", "content": "hi"}])


# ── Follow-up questions about the shown results ─────────────────────────────

SHOWN = {
    "query_english": "gaming laptop under 60000",
    "recommendation": {
        "product": {"title": "Lenovo V15 G4 AMD Ryzen 5 7520U 15.6 inch FHD Laptop", "price": "₹59,490",
                    "source": "amazon", "url": "https://a/1", "rating_value": 4.0, "reviews_value": 538},
        "reason": "Closest option in the budget.",
    },
    "results": {
        "amazon": [{"title": "Lenovo V15 G4 AMD Ryzen 5 7520U 15.6 inch FHD Laptop", "price": "₹59,490",
                    "source": "amazon", "url": "https://a/1", "rating_value": 4.0, "reviews_value": 538}],
        "flipkart": [{"title": "HP Victus Ryzen 5 RTX 3050 Gaming Laptop", "price": "₹58,990",
                      "source": "flipkart", "url": "https://f/1", "rating_value": 4.3, "reviews_value": 2100}],
        "web": [{"title": "ASUS TUF A15 RTX 2050", "price": "₹55,990", "source": "Croma", "url": "https://c/1"}],
    },
}
SEARCHED_LINE = {"role": "agent", "content": 'Earlier in this chat I searched for "gaming laptop under 60000" and showed the results.'}


def _capture(monkeypatch, payload):
    seen = {}

    def fake(prompt):
        seen["prompt"] = prompt
        return json.dumps(payload)

    monkeypatch.setattr(chat_agent, "_ask", fake)
    return seen


def test_searched_query_reads_the_apps_line():
    assert chat_agent.searched_query([SEARCHED_LINE, {"role": "user", "content": "iski specs?"}]) == "gaming laptop under 60000"
    assert chat_agent.searched_query([{"role": "user", "content": 'Earlier in this chat I searched for "x" and showed the results.'}]) is None
    assert chat_agent.searched_query([{"role": "user", "content": "laptop"}]) is None


def test_shown_results_text_lists_pick_reason_and_other_options():
    text = chat_agent.shown_results_text(SHOWN)
    assert "Best pick: [Amazon] Lenovo V15 G4 AMD Ryzen 5 7520U 15.6 inch FHD Laptop - ₹59,490, rated 4.0/5 from 538 reviews" in text
    assert "Why it was picked: Closest option in the budget." in text
    assert "1. [Flipkart] HP Victus Ryzen 5 RTX 3050 Gaming Laptop - ₹58,990" in text
    assert "2. [Croma] ASUS TUF A15 RTX 2050 - ₹55,990" in text
    assert text.count("Lenovo V15") == 1            # the pick is not repeated in "Other options"


def test_follow_up_question_gets_the_real_products_in_the_prompt(monkeypatch):
    seen = _capture(monkeypatch, {"message": "Isme Ryzen 5 7520U hai, 15.6 inch FHD screen.", "is_ready_to_search": False})
    out = chat_agent.process_chat([SEARCHED_LINE, {"role": "user", "content": "Iski specification kya hai?"}], shown=SHOWN)
    prompt = seen["prompt"]
    assert "SEARCH RESULTS ALREADY SHOWN TO THE USER" in prompt
    assert "Best pick: [Amazon] Lenovo V15 G4" in prompt
    assert "Never invent specs" in prompt
    assert "same script" in prompt                       # Hinglish in, Hinglish out
    assert out["is_ready_to_search"] is False


def test_no_results_section_without_a_shown_search(monkeypatch):
    seen = _capture(monkeypatch, {"message": "Which budget?", "is_ready_to_search": False})
    chat_agent.process_chat([{"role": "user", "content": "laptop"}])
    assert "SEARCH RESULTS ALREADY SHOWN" not in seen["prompt"]


AFTER_ANSWER = [
    SEARCHED_LINE,
    {"role": "user", "content": "Yeh achi hai?"},
    {"role": "agent", "content": "Haan, yeh ek bahut achha option hai."},
]


@pytest.mark.parametrize("shown", [SHOWN, None])   # None: the saved results could not be loaded
def test_ok_after_an_answer_does_not_start_a_new_search(monkeypatch, shown):
    _capture(monkeypatch, {"message": "Great! Kuch aur chahiye toh batana.", "is_ready_to_search": False})
    out = chat_agent.process_chat(AFTER_ANSWER + [{"role": "user", "content": "ok"}], shown=shown)
    assert out == {"message": "Great! Kuch aur chahiye toh batana.", "is_ready_to_search": False, "search_query": ""}


def test_results_rules_cover_acknowledgements_and_buying(monkeypatch):
    seen = _capture(monkeypatch, {"message": "Great!", "is_ready_to_search": False})
    chat_agent.process_chat(AFTER_ANSWER + [{"role": "user", "content": "ok"}], shown=SHOWN)
    assert "only says ok, thanks" in seen["prompt"]
    assert "cannot place orders" in seen["prompt"]


def test_ai_failure_after_results_does_not_search(monkeypatch):
    _reply(monkeypatch, "not json at all")
    out = chat_agent.process_chat([SEARCHED_LINE, {"role": "user", "content": "Yeh achi hai?"}], shown=SHOWN)
    assert out["is_ready_to_search"] is False
    assert "View deal" in out["message"]


def test_new_search_without_a_query_builds_on_the_earlier_search(monkeypatch):
    _capture(monkeypatch, {"message": "Searching!", "is_ready_to_search": True, "search_query": ""})
    out = chat_agent.process_chat(AFTER_ANSWER + [{"role": "user", "content": "Intel wala dikhao"}], shown=SHOWN)
    assert out["search_query"] == "gaming laptop under 60000 Intel wala dikhao"   # not "Yeh achi hai?"


@pytest.mark.parametrize("text, language", [
    ("I need earbuds for gym, budget 3000", "English"),
    ("Is it good for running?", "English"),
    ("ok thanks", "English"),
    ("iphone 15", "English"),
    ("Yeh achi hai?", "Hinglish"),
    ("theek hai", "Hinglish"),
    ("mujhe 50000 ke andar laptop chahiye college ke liye", "Hinglish"),
    ("Menu ek water garam karn wali kettle leni 2k tak ki koi ?", "Hinglish"),
    ("मुझे लैपटॉप चाहिए", "Devanagari"),
    ("ਮੈਨੂੰ ਫ਼ੋਨ ਚਾਹੀਦਾ", "Gurmukhi"),
])
def test_reply_language_follows_the_latest_message(monkeypatch, text, language):
    assert language in chat_agent._language_of(text)
    seen = _capture(monkeypatch, {"message": "ok", "is_ready_to_search": False})
    chat_agent.process_chat([{"role": "user", "content": "laptop"}, {"role": "agent", "content": "Budget?"},
                             {"role": "user", "content": text}])
    assert f"The user's latest message is in {chat_agent._language_of(text)}." in seen["prompt"]


def test_questions_about_results_do_not_force_a_search(monkeypatch):
    _capture(monkeypatch, {"message": "Details store page par hain.", "is_ready_to_search": False})
    history = [SEARCHED_LINE] + [{"role": "user", "content": q} for q in
                                 ("iski specs?", "gaming ke liye theek hai?", "battery kaisi hai?", "aur warranty?")]
    out = chat_agent.process_chat(history, shown=SHOWN)
    assert out["is_ready_to_search"] is False           # 4 questions, still no forced search
