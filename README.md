# AI Trading Terminal — the trade journal that audits your discipline

## The problem

Self-directed retail investors journal their trades in spreadsheets and never
review them. So they repeat the same discipline errors for years: oversized
positions, skipped stop-losses, re-entering a loser minutes after getting
stopped out. The P&L tells you *what* happened. Nothing tells you *why* it
keeps happening.

## What this does

This terminal pairs real market data with a rule-based trade audit. You get a
watchlist with live quotes and technicals, a positions and risk panel, a trade
journal where every trade is scored 0–100 against explicit discipline rules,
and an analytics view (equity curve vs SPY, drawdown, monthly returns
heatmap). The discipline summary shows exactly where the edge leaks:
risk-per-trade breaches, missing stop-losses, oversized positions, revenge
re-entries.

The audit is deterministic code, not vibes. Four rules, fixed penalties,
documented in `services/auditor.py`:

| Rule | Check | Penalty |
|---|---|---|
| risk-per-trade | planned risk per trade ≤ 2% of account | −15 |
| stop-loss | a stop exists, on the correct side | −15 |
| position-size | notional ≤ 25% of account | −10 |
| re-entry | no same/next-day re-entry after a losing exit | −10 |

Post-trade review is what separates systematic traders from hopeful ones.
This automates the review part: score every closed trade, aggregate the
violations, and make the pattern impossible to ignore.

## How it works

A Python service layer (`services/`, stdlib only) fetches real daily market
data, computes indicators (SMA, EMA, RSI-14, MACD, ATR-14, Bollinger), audits
`data/sample-trades.csv` against the discipline rules, and computes portfolio
analytics (equity curve, CAGR, Sharpe, max drawdown, win rate, profit factor,
expectancy). `python3 services/main.py build` writes
`web/public/{market,trades,analytics}.json`.

The React frontend (`web/`, Vite + React 18, light mode) reads those JSONs.
The build script runs the Python pipeline first, so every build ships freshly
computed data.

## Run it

```bash
# 1. Run the pipeline (fetches market data, audits trades, writes JSONs)
python3 services/main.py build

# 2. Dev the frontend
cd web && npm install && npm run dev

# 3. Production build (re-runs the pipeline, then vite build)
cd web && npm run build

# 4. Tests
python3 -m pytest services/tests/ -q   # 30 tests
cd web && npm test                     # 34 vitest tests
```

## Market data

Quotes and daily history come from free endpoints that need no API key:
Stooq first, Yahoo Finance chart API as fallback, then a local CSV cache in
`data/market_cache/` labeled with its real fetched-on date. The UI shows the
data source and as-of date; a stale cache is badged, never silently served.
If every source fails, the build exits non-zero instead of inventing prices.

## Honest limitations

- The 24 sample trades are a realistic journal, not anyone's real brokerage
  history. Bring your own `data/sample-trades.csv` (same columns) and the
  whole terminal recomputes.
- Indicators and analytics are computed on daily bars; there is no intraday
  data and no options Greeks.
- The discipline rules encode one specific risk philosophy (2% risk, 25%
  position cap). They are explicit and editable in `services/__init__.py`,
  not universal truths.
- Sharpe here uses per-trade returns, which flatters concentrated,
  short-horizon journals. Read it next to max drawdown, not instead of it.
- This is a journaling and review tool, not financial advice.
