"""Base comune per gli adapter + utilita' di parsing prezzi e JSON-LD."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from core.http import PoliteClient
from core.models import Offer, Query


def parse_price(text: Optional[str]) -> tuple[Optional[float], Optional[str]]:
    """Estrae importo e valuta da stringhe tipo '€1.234,56', '$1,234.56', '£2,500'."""
    if not text:
        return None, None
    low = text.lower()
    if "€" in text or "eur" in low:
        cur = "EUR"
    elif "$" in text or "usd" in low:
        cur = "USD"
    elif "£" in text or "gbp" in low:
        cur = "GBP"
    elif "¥" in text or "cny" in low or "rmb" in low:
        cur = "CNY"
    else:
        cur = None
    m = re.search(r"(\d[\d.,\s]*\d|\d)", text)
    if not m:
        return None, cur
    num = m.group(1).strip().replace(" ", "").replace("\u00a0", "")
    if "," in num and "." in num:
        if num.rfind(",") > num.rfind("."):
            num = num.replace(".", "").replace(",", ".")
        else:
            num = num.replace(",", "")
    elif "," in num:
        parts = num.split(",")
        if len(parts[-1]) == 3 and len(parts) > 1:
            num = num.replace(",", "")
        else:
            num = num.replace(",", ".")
    else:
        parts = num.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            num = num.replace(".", "")
    try:
        return float(num), cur
    except ValueError:
        return None, cur


def _walk_ld(data: Any):
    if isinstance(data, list):
        for d in data:
            yield from _walk_ld(d)
    elif isinstance(data, dict):
        if data.get("@type") in ("Product", "Offer", "AggregateOffer") or "offers" in data:
            yield data
        for v in data.values():
            yield from _walk_ld(v)


def iter_json_ld(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:  # noqa: BLE001
            continue
        out.extend(_walk_ld(data))
    return out


def extract_ld_offers(html: str, source: str, origin_eu: Optional[bool]) -> List[Offer]:
    offers: List[Offer] = []
    for block in iter_json_ld(html):
        name = block.get("name") or block.get("title")
        node = block.get("offers") if isinstance(block.get("offers"), dict) else block
        price = node.get("price") or node.get("lowPrice")
        cur = node.get("priceCurrency") or "EUR"
        url = node.get("url") or block.get("url")
        if name and price is not None and url:
            try:
                p = float(price)
            except (TypeError, ValueError):
                continue
            offers.append(
                Offer(
                    source=source, title=str(name), url=str(url),
                    price=p, currency=str(cur), origin_eu=origin_eu,
                    raw={"via": "json-ld"},
                )
            )
    return offers


class Source:
    adapter = "base"

    def __init__(self, cfg: Dict[str, Any], client: PoliteClient) -> None:
        self.cfg = cfg
        self.client = client
        self.name = cfg.get("name", self.adapter)
        self.origin_eu = cfg.get("origin_eu")

    def search(self, q: Query) -> List[Offer]:  # pragma: no cover - abstract
        raise NotImplementedError

    def _offer(self, **kw: Any) -> Offer:
        kw.setdefault("source", self.name)
        kw.setdefault("origin_eu", self.origin_eu)
        return Offer(**kw)


REGISTRY: Dict[str, type] = {}


def register(cls: type) -> type:
    REGISTRY[cls.adapter] = cls
    return cls


def build_source(cfg: Dict[str, Any], client: PoliteClient) -> Source:
    adapter = cfg.get("adapter", "base")
    if adapter not in REGISTRY:
        raise KeyError(f"adapter sconosciuto: {adapter}")
    return REGISTRY[adapter](cfg, client)
