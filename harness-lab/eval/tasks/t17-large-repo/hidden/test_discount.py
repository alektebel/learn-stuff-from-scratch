import pytest
from bigapp.api import handle


@pytest.mark.parametrize("code", ["SPRING25", "spring25", " Spring25 "])
def test_promotion_applies(code):
    assert handle("discount", code=code, amount_cents=10000) == 7500


def test_other_codes_and_unknown():
    assert handle("discount", code="welcome10", amount_cents=999) == 900
    assert handle("discount", code="NOPE", amount_cents=500) == 500


def test_other_handler_untouched():
    assert handle("refund_window", tier="gold") == 30
