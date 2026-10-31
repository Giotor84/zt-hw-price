"""Offline tests (no network): price parsing, FX inversion and landed cost."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.fx import Fx, _parse_frankfurter_rates  # noqa: E402
from core.landed import LandedCost  # noqa: E402
from core.models import Offer  # noqa: E402
from sources.base import parse_price  # noqa: E402


class _FixedFx:
    base = "EUR"

    def to_base(self, amount: float, currency: str) -> float:
        return amount * {"EUR": 1.0, "USD": 0.9}[currency.upper()]


def test_parse_price_formats():
    assert parse_price("€1.234,56") == (1234.56, "EUR")
    assert parse_price("$1,234.56") == (1234.56, "USD")
    assert parse_price("£2,500") == (2500.0, "GBP")
    assert parse_price("") == (None, None)


def test_frankfurter_rates_are_inverted_to_eur_per_unit():
    rates = _parse_frankfurter_rates("EUR", {"base": "EUR", "rates": {"USD": 1.08, "GBP": 0.85, "CNY": 7.80}})
    fx = Fx.__new__(Fx)
    fx.base = "EUR"
    fx.rates = rates
    assert round(fx.to_base(1000.0, "CNY"), 2) == 128.21
    assert round(fx.to_base(1000.0, "GBP"), 2) == 1176.47
    with pytest.raises(ValueError):
        fx.to_base(50000.0, "KRW")


def test_landed_cost_eu_offer_is_price_plus_shipping_and_b2b_net_adds_vat():
    lc = LandedCost({"import": {"vat_rate": 0.22}}, _FixedFx())
    retail = Offer(source="s", title="t", url="u", price=1000.0, currency="EUR", origin_eu=True)
    assert lc.compute(retail, shipping_estimate=20.0) == 1020.0
    b2b_net = Offer(source="s", title="t", url="u", price=1000.0, currency="EUR", origin_eu=True, vat_included=False)
    assert lc.compute(b2b_net, shipping_estimate=0.0) == 1220.0


def test_landed_cost_extra_eu_adds_duty_and_customs_vat():
    cfg = {"import": {"vat_rate": 0.22, "duty_rate_default": 0.04, "handling_fee": 10.0}}
    lc = LandedCost(cfg, _FixedFx())
    o = Offer(source="s", title="t", url="u", price=1000.0, currency="USD", origin_eu=False)
    goods = 900.0
    duty = goods * 0.04
    assert lc.compute(o, shipping_estimate=100.0) == round(goods + 100.0 + duty + (goods + 100.0 + duty) * 0.22 + 10.0, 2)
