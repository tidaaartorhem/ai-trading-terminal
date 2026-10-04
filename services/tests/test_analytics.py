"""Analytics tests — drawdown, win rate, profit factor, curve, benchmark.

Fixture trades are synthetic, hand-verifiable; NOT market data.
"""

from datetime import date

import pytest

from services import Trade, auditor
from services import analytics

ACCT = 50_000.0


def mk(trade_id, entry_date, exit_date, entry, exit_, qty=100.0):
    return Trade(
        trade_id=trade_id,
        symbol="AAPL",
        side="long",
        quantity=qty,
        entry_date=entry_date,
        entry_price=entry,
        exit_date=exit_date,
        exit_price=exit_,
        stop_loss=entry * 0.95,
        take_profit=None,
        risk_pct_planned=None,
    )


# pnl: +1000, -2000, +1000  -> equity: 50000 -> 51000 -> 49000 -> 50000
TRADES = [
    mk("T1", date(2026, 8, 3), date(2026, 8, 5), 100.0, 110.0),
    mk("T2", date(2026, 8, 6), date(2026, 8, 10), 200.0, 180.0),
    mk("T3", date(2026, 8, 20), date(2026, 9, 2), 50.0, 60.0),
]


def test_equity_curve_steps():
    curve, _ = analytics.build_equity_curve(TRADES)
    assert [p["equity"] for p in curve] == [50000, 51000, 49000, 50000]
    assert curve[0]["date"] == "2026-08-03"  # baseline at first entry
    assert [p["date"] for p in curve[1:]] == ["2026-08-05", "2026-08-10", "2026-09-02"]


def test_max_drawdown_pct():
    curve, _ = analytics.build_equity_curve(TRADES)
    # peak 51000 -> trough 49000 = 3.9216%
    assert analytics.max_drawdown_pct(curve) == pytest.approx(3.9216, abs=1e-3)


def test_metrics_win_rate_profit_factor_expectancy():
    audited = auditor.audit_all(TRADES, ACCT)
    spy = [
        {"date": "2026-08-03", "close": 400.0},
        {"date": "2026-08-05", "close": 404.0},
        {"date": "2026-08-10", "close": 408.0},
        {"date": "2026-09-02", "close": 412.0},
    ]
    doc = analytics.compute(TRADES, audited, spy)
    m = doc["metrics"]
    assert m["winRate"] == pytest.approx(round(2 / 3, 4))
    assert m["profitFactor"] == pytest.approx(1.0)  # 2000 / 2000
    assert m["expectancy"] == pytest.approx(0.0)
    assert m["totalTrades"] == 3
    assert m["maxDrawdownPct"] == pytest.approx(3.9216, abs=1e-3)


def test_monthly_returns_keyed():
    mr = analytics.monthly_returns(TRADES)
    assert mr["2026-08"] == pytest.approx(round((1000 - 2000) / 50000, 6))
    assert mr["2026-09"] == pytest.approx(round(1000 / 49000, 6))


def test_benchmark_normalized_to_starting_capital():
    spy = [
        {"date": "2026-08-03", "close": 400.0},
        {"date": "2026-08-05", "close": 404.0},
        {"date": "2026-08-10", "close": 408.0},
        {"date": "2026-09-02", "close": 412.0},
    ]
    curve, _ = analytics.build_equity_curve(TRADES)
    bench = analytics.benchmark_curve(curve, spy)
    assert bench[0]["equity"] == pytest.approx(50000.0)
    assert bench[-1]["equity"] == pytest.approx(50000 * 412 / 400)


def test_discipline_rollup():
    audited = auditor.audit_all(TRADES, ACCT)
    doc = analytics.compute(TRADES, audited, [])
    d = doc["discipline"]
    expected = round(sum(a["disciplineScore"] for a in audited) / 3, 2)
    assert d["avgScore"] == pytest.approx(expected)
    assert set(d["violationsByRule"].keys()) <= {
        "risk-per-trade", "stop-loss", "position-size", "re-entry"}
    assert [p["date"] for p in d["scoreTrend"]] == [
        "2026-08-05", "2026-08-10", "2026-09-02"]
