"""Client HTTP educato: pacing per dominio, retry, timeout esplicito.

Non aggira mai protezioni anti-bot e applica pacing conservativo per dominio.
"""
from __future__ import annotations

import os
import random
import time
from typing import Dict, Optional
from urllib.parse import urlparse

import httpx

# User-Agent dichiarato: il motore si presenta per quello che e', con un link al progetto.
# Si puo' cambiare con la variabile d'ambiente PRICE_ENGINE_USER_AGENT (es. per aggiungere un contatto).
USER_AGENT = os.environ.get(
    "PRICE_ENGINE_USER_AGENT",
    "zt-hw-price/0.1 (+https://github.com/Giotor84/zt-hw-price)",
)


class HttpError(RuntimeError):
    pass


class PoliteClient:
    """Un client condiviso con pacing per dominio e retry con backoff."""

    def __init__(
        self,
        timeout_s: float = 20.0,
        min_delay_s: float = 1.2,
        max_delay_s: float = 3.0,
        max_retries: int = 3,
    ) -> None:
        self.timeout_s = timeout_s
        self.min_delay_s = min_delay_s
        self.max_delay_s = max_delay_s
        self.max_retries = max_retries
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=timeout_s,
            headers={"Accept-Language": "it-IT,it;q=0.9,en;q=0.8"},
        )
        self._last_hit: Dict[str, float] = {}

    def _pace(self, domain: str) -> None:
        dt = random.uniform(self.min_delay_s, self.max_delay_s)
        elapsed = time.monotonic() - self._last_hit.get(domain, 0.0)
        wait = dt - elapsed
        if wait > 0:
            time.sleep(wait)

    def get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        domain = urlparse(url).netloc
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            self._pace(domain)
            h = {"User-Agent": USER_AGENT}
            if headers:
                h.update(headers)
            try:
                # timeout esplicito: httpx non lo eredita sempre dal client
                resp = self._client.get(url, params=params, headers=h, timeout=self.timeout_s)
                self._last_hit[domain] = time.monotonic()
                if resp.status_code >= 500:
                    raise HttpError(f"HTTP {resp.status_code} su {url}")
                resp.raise_for_status()
                return resp
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._last_hit[domain] = time.monotonic()
                time.sleep(min(2 ** attempt, 15))
        raise HttpError(f"GET fallita dopo {self.max_retries} tentativi: {url} :: {last_exc}")

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PoliteClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
