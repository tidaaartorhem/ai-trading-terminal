"""End-to-end build tests.

- Loud failure: network down + no cache -> build exits non-zero, writes nothing.
- Stale cache: a SYNTHETIC fixture cache (clearly not market data) in a tmp
  dir -> build succeeds end-to-end with stale=true and the exact JSON shapes.

The network is monkeypatched down in these tests, so they never hit Stooq and
never depend on its reachability. The fixture cache is synthetic test data
written only to tmp_path; the real data/market_cache is never touched.
"""

import csv
import json
import urllib.error
from datetime import date

import pytest

from services import ROOT, Trade
from services import market_data
from services import main as build_main


def _raise_down(*a, **k):
    raise urllib.error.URLError("network down (test)")


def test_build_fails_loudly_with_no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(market_data, "_http_get", _raise_down)
    monkeypatch.setattr(market_data, "CACHE_DIR", tmp_path / "empty_cache")
    monkeypatch.setattr(build_main, "ROOT", tmp_path)  # keep real web/public clean
    rc = build_main.main(["prog", "build"])
    assert rc == 1  # non-zero: Stooq unreachable and no cache
    # Nothing written anywhere: the tmp out dir is never even created.
    assert not (tmp_path / "web" / "public" / "market.json").exists()


def test_build_usage_error():
    assert build_main.main(["prog"]) == 2


# ---------------- stale-cache end-to-end ----------------

def _write_fixture_cache(cache_dir):
    """SYNTHETIC 30-bar histories for the 5 symbols. Test fixture only."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "fetched_on.txt").write_text("2026-09-30")
    bases = {"AAPL": 200.0, "MSFT": 400.0, "TSLA": 250.0, "NVDA": 150.0, "SPY": 500.0}
    for sym, base in bases.items():
        with open(cache_dir / f"{sym}.csv", "w", newline="") as f:
            w = csv.DictWriter(
                f, fieldnames=["date", "open", "high", "low", "close", "volume"])
            w.writeheader()
            for i in range(30):
                d = date(2026, 9, 1).toordinal() + i
                close = base + i * 0.5 + (i % 3) * 0.2
                w.writerow({
                    "date": date.fromordinal(d).isoformat(),
                    "open": round(close - 0.3, 2),
                    "high": round(close + 0.4, 2),
                    "low": round(close - 0.6, 2),
                    "close": round(close, 2),
                    "volume": 1_000_000,
                })


def _fixture_trades():
    return [
        Trade("T1", "AAPL", "long", 50.0, date(2026, 9, 2), 100.0,
              date(2026, 9, 10), 110.0, 95.0, None, None),
        Trade("T2", "MSFT", "long", 50.0, date(2026, 9, 12), 200.0,
              date(2026, 9, 20), 190.0, 190.0, None, None),
    ]


def test_build_with_stale_cache(tmp_path, monkeypatch):
    cache = tmp_path / "fixture_cache"
    _write_fixture_cache(cache)
    monkeypatch.setattr(market_data, "_http_get", _raise_down)
    monkeypatch.setattr(market_data, "CACHE_DIR", cache)
    monkeypatch.setattr(
        build_main, "load_trades", lambda: _fixture_trades())
    monkeypatch.setattr(
        build_main, "load_open_positions",
        lambda: [{"symbol": "NVDA", "quantity": 25.0,
                  "entryDate": "2026-09-25", "entryPrice": 180.0}])
    monkeypatch.setattr(build_main, "ROOT", tmp_path)  # keep real web/public clean

    rc = build_main.run_build()
    assert rc == 0

    out = tmp_path / "web" / "public"
    market = json.loads((out / "market.json").read_text())
    assert market["stale"] is True
    assert market["asOf"] == "2026-09-30"
    assert market["source"] == "Stooq"
    assert set(market["symbols"]) == {"AAPL", "MSFT", "TSLA", "NVDA", "SPY"}
    aapl = market["symbols"]["AAPL"]
    assert aapl["name"] == "Apple Inc." and aapl["sector"] == "Technology"
    assert len(aapl["history"]) == 30
    assert set(aapl["indicators"]) == {
        "sma20", "ema12", "rsi14", "macd", "atr14", "bollinger"}
    assert set(aapl["indicators"]["macd"]) == {"line", "signal", "hist"}
    assert set(aapl["indicators"]["bollinger"]) == {"upper", "mid", "lower"}
    assert market["symbols"]["SPY"]["indicators"] is None

    trades = json.loads((out / "trades.json").read_text())
    assert len(trades["trades"]) == 2
    t1 = trades["trades"][0]
    for k in ("pnl", "pnlPct", "rMultiple", "disciplineScore", "violations"):
        assert k in t1
    assert t1["pnl"] == pytest.approx(500.0)
    assert t1["rMultiple"] == pytest.approx(2.0)  # 500 / (5*50)
    assert trades["openPositions"][0]["symbol"] == "NVDA"

    analytics_doc = json.loads((out / "analytics.json").read_text())
    assert analytics_doc["startingCapital"] == 50000
    assert len(analytics_doc["equityCurve"]) == 3  # baseline + 2 exits
    assert len(analytics_doc["benchmarkCurve"]) == 3
    assert set(analytics_doc["metrics"]) == {
        "cagr", "sharpe", "maxDrawdownPct", "winRate", "profitFactor",
        "expectancy", "totalTrades", "avgR"}
    assert "2026-09" in analytics_doc["monthlyReturns"]
    assert set(analytics_doc["discipline"]) == {
        "avgScore", "violationsByRule", "scoreTrend"}
