# zt-hw-price

[![tests](https://github.com/Giotor84/zt-hw-price/actions/workflows/tests.yml/badge.svg)](https://github.com/Giotor84/zt-hw-price/actions/workflows/tests.yml) [![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE) ![python](https://img.shields.io/badge/python-3.12-blue)

**In italiano:** trova il prezzo reale dell'hardware per l'AI locale: costo sbarcato in euro (spedizione, dazi, IVA, cambio), punteggio delle offerte e stima dei token al secondo.

**Find the real price of local-AI hardware.** Searches stores for unified-memory mini-PCs (Ryzen AI Max / Strix
Halo) and GPUs, converts every offer to its **landed cost in EUR** (price + shipping + import duty + VAT + FX),
scores price, quality, reliability and spec match, and estimates **tokens/second** from memory bandwidth.

- **JSON first, no HTML scraping**: Shopify storefront endpoints (`search/suggest.json`, `products/{handle}.json`,
  `cart.js` for currency detection), schema.org JSON-LD as fallback. Polite client with random delays, retries and
  a circuit breaker.
- **Landed cost** for buyers in the EU: extra-EU offers get duty, import VAT and handling; FX from
  [frankfurter.app](https://www.frankfurter.app) with a static fallback.
- **Watchlist** with price targets and alerts, **HTML report**, and one **interactive dashboard** that puts prices,
  estimated LLM performance (tok/s ≈ bandwidth ÷ bytes per token) and thermals side by side.

## Quickstart

```bash
pip install -r requirements.txt
python cli.py search "Ryzen AI Max+ 395 128GB" --spec ram_gb=128
python cli.py watch      # config/watchlist.yaml -> alerts + report + snapshot
python cli.py dash       # unified dashboard -> output/dashboard.html
```

Other commands: `python cli.py sources` (list sources), `python cli.py perf` (performance page),
`python cli.py purge` (drop non-AI offers and placeholder prices). On Windows, `MOTORE_PREZZI_AI.bat`,
`DASHBOARD.bat` and `PRESTAZIONI.bat` run the same commands and open the result.

## Add a store

Most hardware vendors run on Shopify. Copy the `template_shopify` entry in `config/sources.yaml`, set `base` to
the store URL and `enabled: true`. Currency is detected from `/cart.js` when not set.

## Configuration

| file | what |
|---|---|
| `config/sources.yaml` | sources, delays, EU origin, reliability notes |
| `config/watchlist.yaml` | products to watch, spec constraints, target landed price |
| `config/scoring.yaml` | weights for price / quality / trust / spec match, import rates |
| `config/hardware.yaml`, `config/performance.yaml` | hardware catalogue (memory, bandwidth, TDP) and model sizes for tok/s estimates |

Hardware figures are reference values from public spec sheets and benchmarks, declared as estimates.

## Tests

```bash
python -m pytest tests/test_offline.py   # offline
python tests/smoke.py                    # live: one query per enabled source
```

## Responsible use

The engine reads public storefront data at a low rate for personal price comparison. Respect each store's terms
of use and robots rules, keep the delays, and do not use it to republish catalogues.
Requests carry a declared User-Agent with a link to this repository; set `PRICE_ENGINE_USER_AGENT` to add
your own contact.

Comments and config notes are in Italian; PRs translating them are welcome.

## Known limits

- Shopify and schema.org stores only: other storefronts need a source adapter.
- Duty and VAT are simplified for buyers in the EU (rates in `config/scoring.yaml`).
- Tokens/second are estimates from memory bandwidth, not benchmarks.

## Related projects

- [zt-memory](https://github.com/Giotor84/zt-memory) — local code-context engine for LLMs, with an MCP server
- [zt-local-llm-kit](https://github.com/Giotor84/zt-local-llm-kit) — local coding agent on Windows with safety guards
- All projects: [github.com/Giotor84](https://github.com/Giotor84)

## License

MIT — see [LICENSE](LICENSE).
