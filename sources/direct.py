"""Adapter negozio diretto (frame.work, minisforum, gmktec, refurb...).

Strategia: pagina/search_url -> JSON-LD (schema.org Product/Offer); fallback meta og.
Copia la voce 'template_direct' in sources.yaml per aggiungere negozi.
"""
from __future__ import annotations

from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from core.models import Offer, Query
from .base import Source, extract_ld_offers, parse_price, register


@register
class DirectStore(Source):
    adapter = "direct_store"

    def search(self, q: Query) -> List[Offer]:
        tpl = self.cfg.get("search_url") or self.cfg.get("base", "")
        url = tpl.replace("{q}", quote_plus(q.text))
        html = self.client.get(url).text
        offers = extract_ld_offers(html, self.name, self.origin_eu)
        if not offers:
            offers = self._from_meta(html, url)
        return offers[:40]

    def _from_meta(self, html: str, url: str) -> List[Offer]:
        soup = BeautifulSoup(html, "lxml")
        price_meta = soup.find("meta", attrs={"property": "product:price:amount"}) or \
            soup.find("meta", attrs={"property": "og:price:amount"})
        title_meta = soup.find("meta", attrs={"property": "og:title"})
        if not price_meta:
            return []
        price, cur = parse_price(price_meta.get("content"))
        if price is None:
            return []
        title = title_meta.get("content") if title_meta else url
        cur_meta = soup.find("meta", attrs={"property": "product:price:currency"})
        return [
            self._offer(
                title=title, url=url, price=price,
                currency=(cur_meta.get("content") if cur_meta else cur) or "EUR",
                raw={"via": "og-meta"},
            )
        ]
