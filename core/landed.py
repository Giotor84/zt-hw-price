"""Costo finale 'landed': prodotto + spedizione + IVA/dazi import (worldwide)."""
from __future__ import annotations

from typing import Any, Dict

from .fx import Fx
from .models import Offer


class LandedCost:
    def __init__(self, cfg: Dict[str, Any], fx: Fx) -> None:
        imp = cfg.get("import", {})
        self.vat = float(imp.get("vat_rate", 0.22))
        self.duty_el = float(imp.get("duty_rate_electronics", 0.0))
        self.duty_def = float(imp.get("duty_rate_default", 0.04))
        self.handling = float(imp.get("handling_fee", 0.0))
        self.base = cfg.get("base_currency", "EUR")
        self.fx = fx

    def compute(self, o: Offer, shipping_estimate: float = 0.0) -> float:
        # 1) prezzo merce convertito in valuta base
        goods = self.fx.to_base(o.price, o.currency)
        extra_eu = (o.origin_eu is False) or (o.origin_eu is None and o.currency.upper() != "EUR")
        total = goods + shipping_estimate
        if extra_eu:
            duty_rate = self.duty_el if "gpu" in (o.raw.get("category", "") or "").lower() else self.duty_def
            duty = goods * duty_rate
            total += duty
            if o.vat_included is not True:
                # Art. 69 DPR 633/1972: base imponibile IVA doganale = valore merce + spedizione + dazio
                total += (goods + shipping_estimate + duty) * self.vat
            total += self.handling
        elif o.vat_included is False:
            # Offerta intra-UE esplicitamente imponibile / IVA esclusa (listini B2B)
            total += (goods + shipping_estimate) * self.vat
        return round(total, 2)
