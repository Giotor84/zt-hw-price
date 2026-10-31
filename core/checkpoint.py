"""Checkpoint/resume e storico prezzi su SQLite (pattern AS400 checkpoint.py / PATTERN §3)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List

from .models import Offer

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    source      TEXT NOT NULL,
    url         TEXT NOT NULL,
    title       TEXT,
    price       REAL,
    currency    TEXT,
    condition   TEXT,
    seller      TEXT,
    landed_cost REAL,
    total_score REAL,
    fetched_at  TEXT,
    PRIMARY KEY (source, url)
);
CREATE TABLE IF NOT EXISTS price_history (
    source      TEXT NOT NULL,
    url         TEXT NOT NULL,
    price       REAL,
    landed_cost REAL,
    currency    TEXT,
    seen_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_hist_url ON price_history(source, url);
"""


class Store:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert_offer(self, o: Offer) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO offers
                   (source,url,title,price,currency,condition,seller,landed_cost,total_score,fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(source,url) DO UPDATE SET
                     price=excluded.price, currency=excluded.currency,
                     condition=excluded.condition, seller=excluded.seller,
                     landed_cost=excluded.landed_cost,
                     total_score=excluded.total_score, fetched_at=excluded.fetched_at""",
                (
                    o.source, o.url, o.title, o.price, o.currency, o.condition,
                    o.seller, o.landed_cost, o.total_score, o.fetched_at,
                ),
            )
            c.execute(
                "INSERT INTO price_history(source,url,price,landed_cost,currency,seen_at) VALUES (?,?,?,?,?,?)",
                (o.source, o.url, o.price, o.landed_cost, o.currency, o.fetched_at),
            )

    def previous_price(self, source: str, url: str) -> float | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT price FROM price_history WHERE source=? AND url=? ORDER BY seen_at DESC LIMIT 1 OFFSET 1",
                (source, url),
            ).fetchone()
        return float(row[0]) if row else None

    def delete_where(self, predicate) -> int:
        """Elimina offerte (e storico) che soddisfano `predicate(dict)`. Ritorna quante rimosse."""
        victims = [
            (r["source"], r["url"])
            for r in self.all_offers_full()
            if predicate(r)
        ]
        with self._conn() as c:
            for source, url in victims:
                c.execute("DELETE FROM offers WHERE source=? AND url=?", (source, url))
                c.execute("DELETE FROM price_history WHERE source=? AND url=?", (source, url))
        return len(victims)

    def all_offers(self) -> List[tuple]:
        with self._conn() as c:
            cur = c.execute("SELECT source,url,title,price,currency,landed_cost,total_score FROM offers")
            return cur.fetchall()

    def all_offers_full(self) -> List[dict]:
        with self._conn() as c:
            cur = c.execute(
                "SELECT source,url,title,price,currency,condition,seller,"
                "landed_cost,total_score,fetched_at FROM offers"
            )
            cols = ["source", "url", "title", "price", "currency", "condition",
                    "seller", "landed_cost", "total_score", "fetched_at"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
