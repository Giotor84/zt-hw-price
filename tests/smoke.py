"""Fase 0 fail-fast: prova 1 query per fonte attiva e riporta esito/conteggio."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

from core.http import PoliteClient  # noqa: E402
from core.models import Query  # noqa: E402
from sources.loader import build_sources, load_yaml  # noqa: E402

PROBE = "Ryzen AI Max 395 128GB"


def main() -> int:
    cfg = load_yaml("sources.yaml")
    defaults = cfg.get("defaults", {})
    client = PoliteClient(
        timeout_s=defaults.get("timeout_s", 20),
        min_delay_s=defaults.get("min_delay_s", 1.2),
        max_delay_s=defaults.get("max_delay_s", 3.0),
        max_retries=1,
    )
    q = Query(text=PROBE)
    results = []
    try:
        for s in build_sources(cfg, client):
            try:
                res = s.search(q)
                sample = res[0].title[:50] if res else ""
                results.append((s.name, "OK", len(res), sample))
            except Exception as exc:  # noqa: BLE001
                results.append((s.name, "ERR", 0, str(exc)[:80]))
    finally:
        client.close()

    print(f"\n{'FONTE':<18} {'ESITO':<5} {'N':>3}  CAMPIONE/ERRORE")
    print("-" * 90)
    ok = 0
    for name, status, n, info in results:
        if status == "OK" and n > 0:
            ok += 1
        print(f"{name:<18} {status:<5} {n:>3}  {info}")
    print(f"\nFonti con risultati: {ok}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
