"""ai-trading-terminal build CLI: `python3 services/main.py build`.

Pipeline: fetch market data (Stooq first, Yahoo Finance fallback, cache
fallback) -> indicators -> audit trades -> analytics ->
write web/public/{market, trades, analytics}.json.
Exits non-zero on ANY failure (including all sources unreachable with no
cache — real prices only, never invented).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow `python3 services/main.py build` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import (
    ROOT,
    STARTING_CAPITAL,
    load_open_positions,
    load_trades,
)
from services import market_data
from services import indicators as ind
from services import auditor
from services import analytics

META = {
    "AAPL": ("Apple Inc.", "Technology"),
    "MSFT": ("Microsoft Corp.", "Technology"),
    "TSLA": ("Tesla Inc.", "Consumer Cyclical"),
    "NVDA": ("NVIDIA Corp.", "Technology"),
    "SPY": ("SPDR S&P 500 ETF", "Benchmark"),
}

HISTORY_DAYS = 120  # last ~120 trading days per symbol in market.json


def build_indicators(bars) -> dict | None:
    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    if len(closes) < 2:
        return None
    macd = ind.macd(closes)
    bb = ind.bollinger(closes)
    return {
        "sma20": ind.sma(closes, 20),
        "ema12": ind.ema(closes, 12),
        "rsi14": ind.rsi(closes),
        "macd": macd,  # None when history < 26
        "atr14": ind.atr(highs, lows, closes),
        "bollinger": bb,  # None when history < 20
    }


def round_indicators(payload: dict | None):
    if payload is None:
        return None
    out = {}
    for k, v in payload.items():
        if isinstance(v, dict):
            out[k] = {kk: (round(vv, 4) if vv is not None else None) for kk, vv in v.items()}
        else:
            out[k] = round(v, 4) if v is not None else None
    return out


def run_build() -> int:
    out_dir = ROOT / "web" / "public"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Market data — Stooq, then Yahoo Finance, then cache; fail loud otherwise.
    histories, stale, as_of, source = market_data.fetch()
    summary = market_data.summarize(histories)

    # 2. market.json
    symbols = {}
    for sym in market_data.SYMBOLS:
        bars = histories.get(sym, [])
        if not bars:
            raise market_data.MarketDataError(f"no history available for {sym}")
        name, sector = META[sym]
        recent = bars[-HISTORY_DAYS:]
        symbols[sym] = {
            "symbol": sym,
            "name": name,
            "sector": sector,
            "price": round(summary[sym]["price"], 4),
            "changePct": round(summary[sym]["changePct"], 4),
            "history": recent,
            "indicators": round_indicators(build_indicators(bars))
            if sym != "SPY"
            else None,
        }
    market_doc = {
        "asOf": as_of,
        "stale": stale,
        "source": source,
        "symbols": symbols,
    }
    (out_dir / "market.json").write_text(json.dumps(market_doc, indent=2), encoding="utf-8")

    # 3. Audit trades.
    trades = load_trades()
    audited = auditor.audit_all(trades, STARTING_CAPITAL)
    trades_doc = {
        "trades": [
            {
                "id": t.trade_id,
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "entryDate": t.entry_date.isoformat(),
                "entryPrice": t.entry_price,
                "exitDate": t.exit_date.isoformat() if t.exit_date else None,
                "exitPrice": t.exit_price,
                "stopLoss": t.stop_loss,
                "takeProfit": t.take_profit,
                "riskPctPlanned": t.risk_pct_planned,
                "notes": t.notes,
                "pnl": round(a["pnl"], 2) if a["pnl"] is not None else None,
                "pnlPct": round(a["pnlPct"], 4) if a["pnlPct"] is not None else None,
                "rMultiple": round(a["rMultiple"], 4) if a["rMultiple"] is not None else None,
                "disciplineScore": a["disciplineScore"],
                "violations": a["violations"],
            }
            for t, a in zip(trades, audited)
        ],
        "openPositions": load_open_positions(),
    }
    (out_dir / "trades.json").write_text(json.dumps(trades_doc, indent=2), encoding="utf-8")

    # 4. Analytics.
    analytics_doc = analytics.compute(trades, audited, histories.get("SPY", []))
    (out_dir / "analytics.json").write_text(
        json.dumps(analytics_doc, indent=2), encoding="utf-8"
    )
    print(
        f"[build] source={source} asOf={as_of} stale={stale} "
        f"trades={len(trades)} avgScore={analytics_doc['discipline']['avgScore']} "
        f"finalEquity={analytics_doc['equityCurve'][-1]['equity'] if analytics_doc['equityCurve'] else 'n/a'}"
    )
    return 0


def main(argv) -> int:
    if len(argv) != 2 or argv[1] != "build":
        print("usage: python3 services/main.py build", file=sys.stderr)
        return 2
    try:
        return run_build()
    except market_data.MarketDataError as exc:
        print(f"[build] FATAL market data: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"[build] FATAL missing input file: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # fail loudly on anything unexpected
        print(f"[build] FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
