"""Punteggio composito: miglior prezzo + miglior qualita'."""
from __future__ import annotations

import re
import statistics
from typing import Any, Dict, List

from .landed import LandedCost
from .models import Offer, Query
from .quality import Quality


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower())


_GPU_HINTS = ("gddr", "vram", "rtx", "gtx", "geforce", "radeon", "quadro", "gpu")


def spec_match(title: str, spec: Dict[str, Any], specs: Dict[str, Any] | None = None) -> float:
    """Quota di vincoli soddisfatti (0..1). Usa specs strutturate se disponibili, altrimenti il testo."""
    if not spec:
        return 1.0
    t = _norm(title)
    hit = 0
    for key, val in spec.items():
        if specs and key in specs:
            hit += 1 if str(specs[key]) == str(val) else 0
            continue
        token = _norm(str(val))
        if key == "ram_gb":
            ok = bool(re.search(rf"\b{re.escape(token)}\s*gb\b", t))
        elif key == "vram_gb":
            ok = bool(re.search(rf"\b{re.escape(token)}\s*gb\b", t)) and any(h in t for h in _GPU_HINTS)
        else:
            ok = token in t
        hit += 1 if ok else 0
    return round(hit / len(spec), 3)


class Ranker:
    def __init__(self, cfg: Dict[str, Any], landed: LandedCost, quality: Quality) -> None:
        self.cfg = cfg
        self.landed = landed
        self.quality = quality
        self.w = cfg.get("weights", {})
        self.filters = cfg.get("filters", {})
        dest = (cfg.get("destination") or "IT").upper()
        kws = [_norm(k) for k in self.filters.get("non_ai_keywords", [])]
        kws = [k for k in kws if k]
        self._non_ai_re = re.compile(r"\b(" + "|".join(re.escape(k) for k in kws) + r")\b") if kws else None

    def prepare(self, offers: List[Offer], q: Query) -> List[Offer]:
        dest = (self.cfg.get("destination") or "IT").upper()
        out: List[Offer] = []
        for o in offers:
            if self.filters.get("exclude_out_of_stock", True) and not o.in_stock:
                continue
            if self.quality.is_blocked(o):
                continue
            if self._is_non_ai(o.title):
                continue
            try:
                o.landed_cost = self.landed.compute(o)
            except ValueError:
                continue
            max_price = self.filters.get("reject_price_above")
            if max_price and (o.landed_cost or 0.0) >= float(max_price):
                continue
            if q.spec:
                text = o.raw.get("spec_text") or o.title
                o.spec_match = spec_match(text, q.spec, o.raw.get("specs"))
            if o.spec_match < float(self.filters.get("min_spec_match", 0.0)):
                continue
            if self.filters.get("require_ships_to") and o.ships_to and dest not in [s.upper() for s in o.ships_to]:
                continue
            o.quality_score = self.quality.quality_score(o)
            o.trust_score = self.quality.trust_score(o)
            out.append(o)
        out = self._drop_outliers(out)
        out = self._dedupe(out)
        self._score(out)
        out.sort(key=lambda x: (x.total_score or 0.0), reverse=True)
        return out

    def _is_non_ai(self, title: str) -> bool:
        """True se il titolo contiene parole di hardware non-AI (mini-PC da ufficio)."""
        return bool(self._non_ai_re and self._non_ai_re.search(_norm(title)))

    def _drop_outliers(self, offers: List[Offer]) -> List[Offer]:
        """Scarta offerte troppo sotto la mediana della fonte (annunci fuorvianti/placeholder)."""
        ratio = float(self.filters.get("outlier_min_ratio", 0.0))
        min_count = int(self.filters.get("outlier_min_count", 4))
        if ratio <= 0:
            return offers
        by_source: Dict[str, List[Offer]] = {}
        for o in offers:
            by_source.setdefault(o.source, []).append(o)
        kept: List[Offer] = []
        for group in by_source.values():
            if len(group) >= min_count:
                med = statistics.median([o.landed_cost or 0.0 for o in group])
                floor = med * ratio
                kept.extend(o for o in group if (o.landed_cost or 0.0) >= floor)
            else:
                kept.extend(group)
        return kept

    @staticmethod
    def _dedupe(offers: List[Offer]) -> List[Offer]:
        seen = set()
        unique: List[Offer] = []
        for o in offers:
            key = (o.source, o.url, round(o.landed_cost or 0.0, 2), o.condition)
            if key in seen:
                continue
            seen.add(key)
            unique.append(o)
        return unique

    def _score(self, offers: List[Offer]) -> None:
        if not offers:
            return
        costs = [o.landed_cost or 0.0 for o in offers]
        lo, hi = min(costs), max(costs)
        span = (hi - lo) or 1.0
        for o in offers:
            cost = o.landed_cost or 0.0
            price_norm = 1.0 - (cost - lo) / span  # piu' economico = piu' alto
            total = (
                self.w.get("price", 0.45) * price_norm
                + self.w.get("quality", 0.30) * (o.quality_score or 0.0)
                + self.w.get("trust", 0.15) * (o.trust_score or 0.0)
                + self.w.get("spec", 0.10) * o.spec_match
            )
            o.total_score = round(total, 4)
