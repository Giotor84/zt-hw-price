"""Tassi di cambio live (frankfurter.app, gratis senza chiave) con fallback statico.

Nota: `self.rates[CUR]` memorizza sempre quante unita' di `self.base` (default EUR) valgono
1 unita' di `CUR` (es. 1 USD = 0.92 EUR, 1 CNY = 0.128 EUR), cosi' `to_base()` moltiplica `amount * rate`.
L'API `frankfurter.app/latest?from=EUR` restituisce invece quante unita' estere valgono 1 EUR
(es. CNY = 7.80): `_parse_frankfurter_rates()` inverte `1.0 / v`.
"""
from __future__ import annotations

from typing import Any, Dict

import httpx

FALLBACK = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17, "CNY": 0.128, "CHF": 1.05, "JPY": 0.0061, "CAD": 0.67, "AUD": 0.60}


def _parse_frankfurter_rates(base: str, payload: Dict[str, Any]) -> Dict[str, float]:
    raw_rates = payload.get("rates") or {}
    parsed: Dict[str, float] = {base.upper(): 1.0}
    for k, v in raw_rates.items():
        cur = str(k).upper()
        val = float(v)
        if cur == base.upper():
            parsed[cur] = 1.0
        elif val > 0.0:
            parsed[cur] = 1.0 / val
    return parsed


class Fx:
    def __init__(self, base: str = "EUR", timeout_s: float = 10.0) -> None:
        self.base = base.upper()
        self.rates: Dict[str, float] = dict(FALLBACK)
        self.live = False
        self._load(timeout_s)

    def _load(self, timeout_s: float) -> None:
        try:
            r = httpx.get(
                f"https://api.frankfurter.app/latest?from={self.base}",
                timeout=timeout_s,
            )
            r.raise_for_status()
            self.rates.update(_parse_frankfurter_rates(self.base, r.json()))
            self.live = True
        except Exception:  # noqa: BLE001 - offline -> fallback
            pass

    def to_base(self, amount: float, currency: str) -> float:
        currency = (currency or self.base).upper()
        if currency == self.base:
            return amount
        rate = self.rates.get(currency)
        if rate is None:
            raise ValueError(f"Valuta non supportata per conversione in {self.base}: {currency}")
        return amount * rate
