"""Portfolio analytics — equity curve, risk/return metrics, discipline rollups.

Methods (documented for auditability):
  - equityCurve: starts at STARTING_CAPITAL on the first trade's ENTRY date
    (baseline point: {"date": first_entry, "equity": 50000}), then one point per
    closed trade ordered by exit_date; each point = equity after that exit.
    Trade PnL is (exit - entry) * qty, long only.
  - CAGR: (end/start) ** (365.25 / days) - 1 over the curve span (calendar days).
  - Sharpe: per-trade returns r_i = pnl_i / equity_before_i (risk-free 0);
    annualized Sharpe = mean(r)/stdev(r) * sqrt(252). This treats each trade
    as one return observation — with few trades the estimate is noisy.
  - maxDrawdownPct: max peak-to-trough % decline on the equity curve.
  - winRate: fraction of closed trades with pnl > 0. profitFactor:
    gross profit / |gross loss| (None if no losing trades). expectancy:
    mean pnl per closed trade. avgR: mean rMultiple over trades that have one.
  - monthlyReturns: for each "YYYY-MM", sum of exit PnL in the month divided
    by the equity at the start of that month (first month uses starting capital).
  - benchmarkCurve: SPY buy-and-hold normalized to STARTING_CAPITAL at the
    first curve date; one point per equity-curve date, using the SPY close on
    or before that date (last available).
  - discipline: avgScore over audited trades, violationsByRule counts keyed by
    rule name, scoreTrend = [{date, score}] of each trade's exit date in order.
"""

from __future__ import annotations

import math
from datetime import date
from statistics import mean, pstdev, stdev
from typing import Dict, List, Optional

from . import STARTING_CAPITAL, Trade


def closed_trades(trades: List[Trade]) -> List[Trade]:
    return sorted(
        (t for t in trades if t.exit_date is not None and t.pnl() is not None),
        key=lambda t: (t.exit_date, t.trade_id),
    )


def build_equity_curve(trades: List[Trade], start: float = STARTING_CAPITAL):
    ct = closed_trades(trades)
    if not ct:
        return [], []
    first_entry = min(t.entry_date for t in trades)
    curve = [{"date": first_entry.isoformat(), "equity": round(start, 2)}]
    equity = start
    per_trade_returns: List[float] = []
    for t in ct:
        pnl = t.pnl()
        per_trade_returns.append(pnl / equity)
        equity += pnl
        curve.append({"date": t.exit_date.isoformat(), "equity": round(equity, 2)})
    return curve, per_trade_returns


def cagr(curve) -> Optional[float]:
    if len(curve) < 2:
        return None
    start, end = curve[0]["equity"], curve[-1]["equity"]
    days = (date.fromisoformat(curve[-1]["date"]) - date.fromisoformat(curve[0]["date"])).days
    if days <= 0 or start <= 0:
        return None
    return (end / start) ** (365.25 / days) - 1


def sharpe(per_trade_returns: List[float]) -> Optional[float]:
    if len(per_trade_returns) < 2:
        return None
    sd = stdev(per_trade_returns)
    if sd == 0:
        return None
    return mean(per_trade_returns) / sd * math.sqrt(252)


def max_drawdown_pct(curve) -> float:
    peak = curve[0]["equity"]
    worst = 0.0
    for p in curve:
        e = p["equity"]
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100 if peak > 0 else 0.0
        worst = max(worst, dd)
    return worst


def monthly_returns(trades: List[Trade], start: float = STARTING_CAPITAL) -> Dict[str, float]:
    ct = closed_trades(trades)
    months: Dict[str, float] = {}
    for t in ct:
        key = t.exit_date.strftime("%Y-%m")
        months[key] = months.get(key, 0.0) + t.pnl()
    # equity at the start of each month
    equity = start
    by_month: Dict[str, float] = {}
    for t in ct:
        key = t.exit_date.strftime("%Y-%m")
        by_month.setdefault(key, equity)
        equity += t.pnl()
    return {k: round(months[k] / by_month[k], 6) for k in sorted(months)}


def benchmark_curve(curve, spy_history: List[dict]) -> List[dict]:
    """SPY buy-and-hold normalized to STARTING_CAPITAL at first curve date."""
    if not curve or not spy_history:
        return []
    spy_by_date = {h["date"]: h["close"] for h in spy_history}
    dates_sorted = sorted(spy_by_date)

    def close_on_or_before(d: str) -> Optional[float]:
        cands = [x for x in dates_sorted if x <= d]
        return spy_by_date[cands[-1]] if cands else None

    first = curve[0]["date"]
    base = close_on_or_before(first)
    if not base:
        return []
    out = []
    for p in curve:
        c = close_on_or_before(p["date"])
        out.append(
            {"date": p["date"], "equity": round(STARTING_CAPITAL * (c / base), 2)}
            if c
            else {"date": p["date"], "equity": None}
        )
    return out


def compute(trades: List[Trade], audited: List[dict], spy_history: List[dict]) -> dict:
    ct = closed_trades(trades)
    curve, per_trade_returns = build_equity_curve(trades)

    wins = [t for t in ct if t.pnl() > 0]
    losses = [t for t in ct if t.pnl() < 0]
    gross_profit = sum(t.pnl() for t in wins)
    gross_loss = sum(t.pnl() for t in losses)

    rs = [a["rMultiple"] for a in audited if a.get("rMultiple") is not None]

    violations_by_rule: Dict[str, int] = {}
    for a in audited:
        for v in a["violations"]:
            violations_by_rule[v["rule"]] = violations_by_rule.get(v["rule"], 0) + 1

    trend = sorted(
        (
            {"date": t.exit_date.isoformat(), "score": a["disciplineScore"]}
            for t, a in zip(trades, audited)
            if t.exit_date is not None
        ),
        key=lambda x: (x["date"], x["score"]),
    )

    metrics = {
        "cagr": round(cagr(curve), 6) if cagr(curve) is not None else None,
        "sharpe": round(sharpe(per_trade_returns), 4)
        if sharpe(per_trade_returns) is not None
        else None,
        "maxDrawdownPct": round(max_drawdown_pct(curve), 4) if curve else 0.0,
        "winRate": round(len(wins) / len(ct), 4) if ct else None,
        "profitFactor": round(gross_profit / abs(gross_loss), 4)
        if gross_loss
        else (None if not gross_profit else float("inf")),
        "expectancy": round(sum(t.pnl() for t in ct) / len(ct), 2) if ct else None,
        "totalTrades": len(ct),
        "avgR": round(mean(rs), 4) if rs else None,
    }

    return {
        "startingCapital": STARTING_CAPITAL,
        "equityCurve": curve,
        "benchmarkCurve": benchmark_curve(curve, spy_history),
        "metrics": metrics,
        "monthlyReturns": monthly_returns(trades),
        "discipline": {
            "avgScore": round(mean(a["disciplineScore"] for a in audited), 2)
            if audited
            else None,
            "violationsByRule": violations_by_rule,
            "scoreTrend": trend,
        },
    }
