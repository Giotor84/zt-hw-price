"""zt-hw-price - ricerca worldwide del miglior prezzo + miglior qualita'.

Esempi:
  python cli.py search "Framework Desktop Ryzen AI Max+ 395 128GB" --spec ram_gb=128 --spec cpu=395
  python cli.py search "RTX 3090 24GB" --spec vram_gb=24 --condition-any
  python cli.py watch
  python cli.py sources
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.checkpoint import Store
from core.circuit_breaker import CircuitBreaker
from core.fx import Fx
from core.http import PoliteClient
from core.landed import LandedCost
from core.models import Offer, Query
from core.quality import Quality
from core.scoring import Ranker
from sources.loader import ROOT, build_sources, load_yaml

OUT = ROOT / "output"


def _cast(v: str) -> Any:
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def _parse_spec(pairs: Optional[List[str]]) -> Dict[str, Any]:
    spec: Dict[str, Any] = {}
    for p in pairs or []:
        if "=" in p:
            k, val = p.split("=", 1)
            spec[k.strip()] = _cast(val.strip())
    return spec


def run_search(q: Query, quiet: bool = False) -> List[Offer]:
    src_cfg = load_yaml("sources.yaml")
    score_cfg = load_yaml("scoring.yaml")
    defaults = src_cfg.get("defaults", {})
    client = PoliteClient(
        timeout_s=defaults.get("timeout_s", 20),
        min_delay_s=defaults.get("min_delay_s", 1.2),
        max_delay_s=defaults.get("max_delay_s", 3.0),
    )
    fx = Fx(base=score_cfg.get("base_currency", "EUR"))
    ranker = Ranker(score_cfg, LandedCost(score_cfg, fx), Quality(score_cfg))
    store = Store(OUT / "prezzi.db")

    sources = build_sources(src_cfg, client)
    breakers = {s.name: CircuitBreaker() for s in sources}
    offers: List[Offer] = []
    try:
        for s in sources:
            cb = breakers[s.name]
            if not cb.allow():
                print(f"[skip] {s.name}: circuito aperto", file=sys.stderr)
                continue
            try:
                res = s.search(q)
                cb.record_success()
                offers.extend(res)
                if not quiet:
                    print(f"[ok]   {s.name}: {len(res)} offerte", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001
                cb.record_failure()
                print(f"[fail] {s.name}: {exc}", file=sys.stderr)
    finally:
        client.close()

    ranked = ranker.prepare(offers, q)
    for o in ranked:
        store.upsert_offer(o)
    return ranked


def _print_table(offers: List[Offer]) -> None:
    if not offers:
        print("Nessuna offerta.")
        return
    hdr = f"{'#':>2}  {'LANDED€':>8}  {'PREZZO':>10}  {'SPEC':>4} {'QUAL':>4} {'SCORE':>6}  COND   FONTE / TITOLO"
    print(hdr)
    print("-" * len(hdr))
    for i, o in enumerate(offers[:25], 1):
        print(
            f"{i:>2}  {o.landed_cost or 0:>8.0f}  {o.price:>7.0f} {o.currency:<3} "
            f"{o.spec_match:>4.2f} {o.quality_score or 0:>4.2f} {o.total_score or 0:>6.3f}  "
            f"{o.condition:<6} {o.source}: {o.title[:60]}"
        )


def cmd_search(args: argparse.Namespace) -> int:
    q = Query(text=args.query, spec=_parse_spec(args.spec),
              max_price=args.max_price, condition_any=args.condition_any)
    offers = run_search(q)
    if q.max_price:
        offers = [o for o in offers if (o.landed_cost or o.price) <= q.max_price]
    _print_table(offers)
    from report import render
    path = render(offers, f"Ricerca: {q.text}", OUT / "report.html")
    print(f"\nReport HTML: {path}")
    return 0


def cmd_watch(_: argparse.Namespace) -> int:
    from datetime import datetime

    from report import render_watch

    wl = load_yaml("watchlist.yaml")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows: List[tuple] = []
    alerts: List[tuple] = []
    for p in wl.get("products", []):
        q = Query(text=p["query"], spec=p.get("spec", {}), condition_any=p.get("condition_any", False))
        offers = run_search(q, quiet=True)
        target = p.get("target_price")
        if not offers:
            rows.append((p["id"], "-", target, "NESSUNA", ""))
            print(f"[{p['id']}] nessuna offerta")
            continue
        best = offers[0]
        cost = best.landed_cost or best.price
        hit = target is not None and cost <= target
        status = "ALERT" if hit else "ok"
        if hit:
            alerts.append((p["id"], cost, target, best.title, best.url))
        rows.append((p["id"], cost, target, status, best.title))
        print(f"[{p['id']}] best {cost:.0f}€ (target {target}) -> {status}: {best.title[:60]}")

    path = render_watch(rows, alerts, ts, OUT / "watch_report.html")
    with open(OUT / "watch_snapshot.json", "w", encoding="utf-8") as fh:
        json.dump({"ts": ts, "rows": rows, "alerts": alerts}, fh, ensure_ascii=False)
    if alerts:
        with open(OUT / "alerts.log", "a", encoding="utf-8") as fh:
            for pid, cost, target, title, url in alerts:
                fh.write(f"{ts}\t{pid}\t{cost:.0f}\t{target}\t{url}\n")
        print(f"\n*** {len(alerts)} prodotti sotto target: {', '.join(a[0] for a in alerts)} ***")
    print(f"Report watchlist: {path}")
    return 0


def cmd_perf(_: argparse.Namespace) -> int:
    from report import render_performance

    perf = load_yaml("performance.yaml")
    chip = perf.get("chip", {})
    print(
        f"{chip.get('name','')} | {chip.get('memory','')} | "
        f"banda {chip.get('bandwidth_theoretical_gbs','?')} GB/s teorici "
        f"(~{chip.get('bandwidth_real_gbs','?')} reali) | VRAM ~{chip.get('vram_addressable_gb','?')} GB"
    )
    print()
    hdr = f"{'MODELLO':<26}{'P(att)B':>12}{'quant':>8}{'GB':>7}{'tok/s':>10}  note"
    print(hdr)
    print("-" * len(hdr))
    for m in perf.get("models", []):
        lo, hi = m.get("tok_s_low"), m.get("tok_s_high")
        spd = f"{lo:g}" if lo == hi else f"{lo:g}-{hi:g}"
        pa = f"{m.get('params_b','')} ({m.get('active_b','')})"
        note = str(m.get("note", ""))[:46]
        print(f"{m.get('label',''):<26}{pa:>12}{str(m.get('quant','')):>8}"
              f"{str(m.get('size_gb','')):>7}{spd:>10}  {note}")
    print()
    print("DEVICE (sost./picco W, rumore, espansione):")
    for d in perf.get("devices", []):
        sw = f"{d.get('sustained_w','')}/{d.get('peak_w','')}W"
        print(f"  {d.get('name',''):<26}{sw:>10}  {d.get('noise','')}")
    path = render_performance(perf, OUT / "performance.html")
    print(f"\nReport prestazioni: {path}")
    return 0


def cmd_dash(_: argparse.Namespace) -> int:
    from report import render_dashboard

    perf = load_yaml("performance.yaml")
    hw = load_yaml("hardware.yaml")
    models = perf.get("models", [])
    hardware = hw.get("hardware", [])
    ref_bw = hw.get("reference_bandwidth_gbs", 220)

    store = Store(OUT / "prezzi.db")
    offers = store.all_offers_full()
    watch = None
    snap = OUT / "watch_snapshot.json"
    if snap.exists():
        with open(snap, encoding="utf-8") as fh:
            watch = json.load(fh)

    path = render_dashboard(models, hardware, ref_bw, offers, watch, OUT / "dashboard.html")
    print(f"Dashboard unificata: {path}")
    extra = f"watch: {len(watch.get('alerts', []))} alert" if watch else "watch: nessuno snapshot (esegui `cli.py watch`)"
    print(f"{len(offers)} offerte · {len(hardware)} hardware · {len(models)} modelli · {extra}")
    return 0


def cmd_purge(_: argparse.Namespace) -> int:
    score_cfg = load_yaml("scoring.yaml")
    fx = Fx(base=score_cfg.get("base_currency", "EUR"))
    ranker = Ranker(score_cfg, LandedCost(score_cfg, fx), Quality(score_cfg))
    filters = score_cfg.get("filters", {})
    max_price = filters.get("reject_price_above")

    def bad(r: dict) -> bool:
        if ranker._is_non_ai(r.get("title") or ""):
            return True
        return bool(max_price and (r.get("price") or 0.0) >= float(max_price))

    store = Store(OUT / "prezzi.db")
    before = len(store.all_offers_full())
    removed = store.delete_where(bad)
    print(f"Rimosse {removed} offerte non-AI/placeholder (prima {before}, ora {before - removed}).")
    return 0


def cmd_sources(_: argparse.Namespace) -> int:
    cfg = load_yaml("sources.yaml")
    for s in cfg.get("sources", []):
        state = "ON " if s.get("enabled", True) else "off"
        print(f"[{state}] {s['name']:<18} {s['adapter']:<14} rel={s.get('reliability','?'):<5} {s.get('note','')}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="motore-prezzi", description="Miglior prezzo + miglior qualita' (worldwide)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="cerca un prodotto su tutte le fonti attive")
    s.add_argument("query")
    s.add_argument("--spec", action="append", help="vincolo, es. ram_gb=128 (ripetibile)")
    s.add_argument("--max-price", type=float, default=None)
    s.add_argument("--condition-any", action="store_true", help="ammetti anche usato/refurb")
    s.set_defaults(func=cmd_search)
    w = sub.add_parser("watch", help="controlla la watchlist e segnala i sotto-target")
    w.set_defaults(func=cmd_watch)
    sr = sub.add_parser("sources", help="elenca le fonti")
    sr.set_defaults(func=cmd_sources)
    pu = sub.add_parser("purge", help="rimuove dal DB offerte non-AI e prezzi placeholder")
    pu.set_defaults(func=cmd_purge)
    pf = sub.add_parser("perf", help="prestazioni LLM di riferimento e termica per device")
    pf.set_defaults(func=cmd_perf)
    dc = sub.add_parser("dash", help="genera la dashboard interattiva prestazioni (A/B)")
    dc.set_defaults(func=cmd_dash)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
