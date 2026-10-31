"""Adapter generico Shopify: API JSON + prezzo e specifiche per-variante.

Legge product.options / variant.optionN per estrarre spec strutturate (RAM, SSD),
evitando i falsi positivi del matching testuale (es. '128GB SSD' scambiato per RAM).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from core.models import Offer, Query
from .base import Source, register

_RAM_HINTS = ("ram", "memory", "lpddr", "ddr", "unified")
_SSD_HINTS = ("ssd", "storage", "disk", "nvme", "emmc", "hdd")

# RAM da valore: '64GB LPDDR5x', '128GB RAM', '16G DDR5', '96G DDR5 ECC'
_RAM_RE = re.compile(r"(\d+)\s*g(?:b)?\s*(?:lp?ddr\w*|ddr\w*|ram|memory|unified)", re.I)
# Storage da valore: '128GB OS Storage', '2TB SSD'
_STO_RE = re.compile(r"(\d+)\s*(gb|g|tb)\s*(?:os\s*storage|ssd|nvme|hdd|emmc)", re.I)
_STO_TB = re.compile(r"(\d+)\s*tb", re.I)


def _gb(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:gb|g\b)", (text or "").lower())
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*tb", (text or "").lower())
    return int(m.group(1)) * 1024 if m else None


@register
class ShopifyStore(Source):
    adapter = "shopify"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._currency: Optional[str] = self.cfg.get("currency")
        self._product_cache: Dict[str, Optional[Dict[str, Any]]] = {}

    def search(self, q: Query) -> List[Offer]:
        base = (self.cfg.get("base") or "").rstrip("/")
        limit = str(self.cfg.get("limit", 10))
        products = self._suggest(base, q.text, limit)
        if products is None:
            products = self._products(base, limit)
        offers: List[Offer] = []
        for p in products:
            offers.extend(self._expand(base, p))
        return offers

    def _expand(self, base: str, p: Dict[str, Any]) -> List[Offer]:
        handle = p.get("handle") or ""
        title = p.get("title", "")
        link = urljoin(base + "/", (p.get("url") or f"/products/{handle}").split("?")[0])
        seller = p.get("vendor") or self.name
        currency = self._currency_value(base)

        prod = self._fetch_product(base, handle)
        options = (prod or {}).get("options") or []
        variants = (prod or {}).get("variants") or []

        if variants:
            offers: List[Offer] = []
            for v in variants:
                price = self._fnum(v.get("price"))
                if price is None or price <= 0:
                    continue
                vtitle = v.get("title") or ""
                specs = self._variant_specs(options, v)
                offers.append(
                    self._offer(
                        title=f"{title} - {vtitle}".strip(" -"),
                        url=link, price=price, currency=currency, condition="new",
                        in_stock=bool(v.get("available", True)), seller=seller,
                        raw={"via": "shopify-variant", "sku": v.get("sku"),
                             "specs": specs, "spec_text": f"{title} {vtitle}"},
                    )
                )
            if offers:
                return offers

        price = self._price(p)
        if price is None or price <= 0:
            return []
        return [
            self._offer(
                title=title, url=link, price=price, currency=currency,
                condition="new", in_stock=bool(p.get("available", True)), seller=seller,
                raw={"via": "shopify-product", "specs": {}, "spec_text": title},
            )
        ]

    @staticmethod
    def _variant_specs(options: List[Dict[str, Any]], variant: Dict[str, Any]) -> Dict[str, Any]:
        specs: Dict[str, Any] = {}
        for i, opt in enumerate(options, start=1):
            name = (opt.get("name") or "").lower()
            val = variant.get(f"option{i}")
            if not val:
                continue
            ram = _RAM_RE.search(val)
            if ram:
                specs.setdefault("ram_gb", int(ram.group(1)))
            elif any(h in name for h in _RAM_HINTS):
                gb = _gb(val)
                if gb:
                    specs.setdefault("ram_gb", gb)
            sto = _STO_RE.search(val)
            if sto:
                n, unit = int(sto.group(1)), sto.group(2).lower()
                specs.setdefault("ssd_gb", n * 1024 if unit == "tb" else n)
            else:
                tb = _STO_TB.search(val)
                if tb:
                    specs.setdefault("ssd_gb", int(tb.group(1)) * 1024)
                elif any(h in name for h in _SSD_HINTS):
                    gb = _gb(val)
                    if gb:
                        specs.setdefault("ssd_gb", gb)
        return specs

    def _fetch_product(self, base: str, handle: str) -> Optional[Dict[str, Any]]:
        if not handle:
            return None
        if handle in self._product_cache:
            return self._product_cache[handle]
        try:
            data = self.client.get(
                f"{base}/products/{handle}.json", headers={"Accept": "application/json"}
            ).json()
            prod = data.get("product")
        except Exception:  # noqa: BLE001
            prod = None
        self._product_cache[handle] = prod
        return prod

    def _currency_value(self, base: str) -> str:
        if not self._currency:
            self._currency = self._detect_currency(base) or "USD"
        return self._currency

    def _detect_currency(self, base: str) -> Optional[str]:
        try:
            return self.client.get(
                f"{base}/cart.js", headers={"Accept": "application/json"}
            ).json().get("currency")
        except Exception:  # noqa: BLE001
            return None

    def _suggest(self, base: str, query: str, limit: str) -> Optional[List[Dict[str, Any]]]:
        try:
            data = self.client.get(
                f"{base}/search/suggest.json",
                params={"q": query, "resources[type]": "product", "resources[limit]": limit},
                headers={"Accept": "application/json"},
            ).json()
            return (((data.get("resources") or {}).get("results") or {}).get("products")) or []
        except Exception:  # noqa: BLE001
            return None

    def _products(self, base: str, limit: str) -> List[Dict[str, Any]]:
        data = self.client.get(
            f"{base}/products.json", params={"limit": limit},
            headers={"Accept": "application/json"},
        ).json()
        return data.get("products", [])

    @staticmethod
    def _fnum(v: Any) -> Optional[float]:
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _price(cls, p: Dict[str, Any]) -> Optional[float]:
        v = p.get("price_min")
        if v is None:
            v = p.get("price")
        if v is None and p.get("variants"):
            v = p["variants"][0].get("price")
        return cls._fnum(v)
