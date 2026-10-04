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

## Current status (2026-10-04)

Stooq is unreachable from this build environment: every endpoint returns an empty
reply (TLS handshake completes, then the server closes the connection — no HTTP
status). This reproduces across `stooq.com` and `stooq.pl`, history and quote
endpoints, IPv4, curl, and Python urllib. General internet egress works fine
(google.com returns 200), so this is server-side blocking of this environment's
egress IP, not a network outage.

Because there is no cache yet, the build exits non-zero per the stale policy, and
`sample-trades.csv` / `open-positions.csv` are header-only placeholders: their rows
require real fetched closes and cannot be written without them.

### How to get unblocked

- Run `python3 services/main.py build` once from an environment Stooq accepts; it
  will populate `data/market_cache/` and every later run can fall back to cache.
- Or authorize an alternate real-data source. Noted during this build: Yahoo
  Finance's chart API (`query1.finance.yahoo.com/v8/finance/chart/<SYM>`) returned
  HTTP 200 with real data from this environment using a browser User-Agent. It was
  NOT used — the spec designates Stooq and mandates loud failure over a fallback
  source — but it is available if the project owner approves a source change.
