"""Result filters applied before the AI picks a product."""

import pytest

from pipeline import drop_accessories, drop_over_budget
from products import query_keywords


def _p(title, price_value):
    return {"title": title, "price_value": price_value}


RESULTS = {
    "amazon": [_p("HP 15 Laptop", 74990), _p("Acer Aspire 3 Laptop", 42990), _p("Lenovo Laptop", None)],
    "flipkart": [_p("ASUS Vivobook", 98990)],
    "web": [_p("Dell Laptop", 47990)],
}


def test_over_budget_items_are_hidden():
    out = drop_over_budget(RESULTS, "college laptop under 50000")
    assert {site: [p["title"] for p in items] for site, items in out.items()} == {
        "amazon": ["Acer Aspire 3 Laptop", "Lenovo Laptop"],   # unknown price is kept
        "flipkart": [],
        "web": ["Dell Laptop"],
    }


def test_no_budget_keeps_everything():
    assert drop_over_budget(RESULTS, "laptop") is RESULTS


def test_budget_filter_never_empties_the_results():
    assert drop_over_budget(RESULTS, "laptop under 1000") is RESULTS


def test_accessories_are_hidden_unless_asked_for():
    results = {"amazon": [_p("Sony WH-1000XM5 Headphones", 26990), _p("Headphone Carry Case", 499)]}
    assert [p["title"] for p in drop_accessories(results, "headphones")["amazon"]] == ["Sony WH-1000XM5 Headphones"]
    assert len(drop_accessories(results, "headphone case")["amazon"]) == 2


@pytest.mark.parametrize("query, expected", [
    ("college laptop under 50000", ["laptop"]),
    ("gym earbuds with mic under 3000", ["earbud"]),
    ("gaming laptop", ["gaming", "laptop"]),
])
def test_use_case_words_do_not_block_store_results(query, expected):
    assert query_keywords(query) == expected
