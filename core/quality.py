"""Punteggi di qualita' e fiducia dell'offerta."""
from __future__ import annotations

from typing import Any, Dict

from .models import Offer


class Quality:
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        self.cond = cfg.get("condition_factor", {})
        trust = cfg.get("trusted_retailers", {})
        self.whitelist = [w.lower() for w in trust.get("whitelist", [])]
        self.blacklist = [b.lower() for b in trust.get("blacklist", [])]

    def quality_score(self, o: Offer) -> float:
        """0..1: condizione + garanzia + segnali venditore."""
        c = float(self.cond.get(o.condition, self.cond.get("unknown", 0.4)))
        # garanzia: fino a +0.15
        w = min((o.warranty_months or 0) / 24.0, 1.0) * 0.15
        # rating venditore: fino a +0.10
        r = ((o.seller_rating or 0) / 5.0) * 0.10 if o.seller_rating else 0.0
        return round(min(c + w + r, 1.0), 3)

    def trust_score(self, o: Offer) -> float:
        """0..1: whitelist/blacklist + rating venditore."""
        key = (o.seller or o.source).lower()
        if any(b in key for b in self.blacklist):
            return 0.0
        if any(w in key for w in self.whitelist):
            base = 0.9
        else:
            base = 0.5
        if o.seller_rating:
            base = min(base + 0.1, 1.0) if o.seller_rating >= 4.0 else base - 0.1
        return round(max(base, 0.0), 3)

    def is_blocked(self, o: Offer) -> bool:
        key = (o.seller or o.source).lower()
        return any(b in key for b in self.blacklist)
