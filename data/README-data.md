# Data — sources, as-of semantics, and stale policy

## Sources

- **Market data:** Stooq daily history, `https://stooq.com/q/d/l/?s=aapl.us,msft.us,tsla.us,nvda.us,spy.us&i=d`
  (columns: Symbol, Date, Open, High, Low, Close, Volume). Fetched fresh on every
  `python3 services/main.py build` run and cached raw to `data/market_cache/<SYM>.csv`
  with the fetch date recorded in `data/market_cache/fetched_on.txt`.
- **Trades:** `data/sample-trades.csv` — hand-maintained journal entries. Entry prices
  must be actual closes from the fetched history for that symbol/date.
- **Open positions:** `data/open-positions.csv` — hand-maintained.

## As-of semantics

`market.json` carries `asOf` (the date the history behind it was fetched) and `stale`
(false = fetched live this run, true = served from local cache).

## Stale policy

1. Stooq reachable -> refresh cache, `stale: false`.
2. Stooq unreachable, cache present -> use cache, `stale: true`, `asOf` = the cache's
   real fetch date. Prices are real, just possibly old.
3. Stooq unreachable, no cache -> **fail loudly** (build exits non-zero). Prices are
   never invented, interpolated, or carried over from memory.

## Current status (2026-10-25)

Stooq no longer serves its CSV to this build environment at all: since
2026-10-25 it answers every history request with HTTP 200 carrying a
JavaScript browser-verification page instead of CSV (previously, 2026-10-04,
it returned an empty reply after the TLS handshake). The pipeline treats any
degraded Stooq answer — network error or non-CSV 200 — as a Stooq failure
and falls through to Yahoo Finance, then to cache; loud failure happens only
when all three are exhausted (see `services/market_data.py:fetch` and the
regression tests in `services/tests/test_market_data_fallback.py`).

Latest successful refresh: 2026-10-25 build, Yahoo Finance source, history
through Friday 2026-10-23 (the latest trading day before that Sunday run),
`stale: false`. Yahoo's chart API (`query1.finance.yahoo.com/v8/finance/chart/<SYM>`)
returns real data from this environment with a browser User-Agent; it is the
standing fallback, not a one-off workaround.

### How to get unblocked if Yahoo also fails

- Run `python3 services/main.py build` once from an environment Stooq accepts; it
  will populate `data/market_cache/` and every later run can fall back to cache
  (labeled `stale: true` with the cache's real fetch date).
- With no live source and no cache, the build exits non-zero per the stale
  policy — prices are never invented, interpolated, or carried over.
