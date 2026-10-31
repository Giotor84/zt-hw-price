"""Modelli dati del motore prezzi."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Query:
    text: str
    spec: Dict[str, Any] = field(default_factory=dict)
    max_price: Optional[float] = None
    condition_any: bool = False


@dataclass
class Offer:
    source: str
    title: str
    url: str
    price: float
    currency: str = "EUR"
    condition: str = "new"
    origin_eu: Optional[bool] = None
    in_stock: bool = True
    seller: str = ""
    seller_rating: Optional[float] = None
    warranty_months: Optional[int] = None
    vat_included: Optional[bool] = None
    ships_to: List[str] = field(default_factory=list)
    spec_match: float = 1.0
    raw: Dict[str, Any] = field(default_factory=dict)
    fetched_at: str = field(default_factory=_now)

    # campi calcolati
    landed_cost: Optional[float] = None
    quality_score: Optional[float] = None
    trust_score: Optional[float] = None
    total_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScoredOffer:
    offer: Offer
    reasons: List[str] = field(default_factory=list)
