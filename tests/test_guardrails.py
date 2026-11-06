from guardrails import mask_credit_card


def test_masks_card_number_keeping_last_four():
    assert mask_credit_card("my card is 4111 1111 1111 1234") == "my card is **** **** **** 1234"
    assert mask_credit_card("4111-1111-1111-1234") == "****-****-****-1234"


def test_leaves_normal_text_and_short_numbers_alone():
    text = "laptop under 80000 with 16 GB RAM"
    assert mask_credit_card(text) == text
    assert mask_credit_card("") == ""
