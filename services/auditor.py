"""Discipline auditor — rule-based scoring of closed trades.

Rules (deterministic, long-only assumption: stop-loss must sit below entry):
  - risk-per-trade: |entry - stopLoss| * qty / account <= 2% of account.
      Violated when planned risk dollars exceed 2% of starting capital.
      {"rule": "risk-per-trade"}
  - stop-loss: a stop-loss must be set (non-empty, numeric) and, for a long
      trade, must be strictly below the entry price (i.e. on the correct side).
      {"rule": "stop-loss"}
  - position-size: qty * entryPrice <= 25% of starting capital.
      {"rule": "position-size"}
  - re-entry: the trade's entry date is the same calendar day as, or the next
      calendar day after, a LOSING exit in the same symbol. Revenge-trading
      proxy. {"rule": "re-entry"}

Scoring: start at 100; risk-per-trade -15; stop-loss -15; position-size -10;
re-entry -10; clamped to [0, 100].

Also computed per trade:
  - pnl        = (exit - entry) * qty (long)
  - pnlPct     = pnl / (entry * qty) * 100
  - rMultiple  = pnl / planned risk dollars (None when no stop-loss, i.e. no
                 measurable planned risk)
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from . import (
    Trade,
    RISK_PCT_LIMIT,
    POSITION_PCT_LIMIT,
    PENALTY_RISK_PER_TRADE,
    PENALTY_STOP_LOSS,
    PENALTY_POSITION_SIZE,
    PENALTY_REENTRY,
)

RULE_RISK_PER_TRADE = "risk-per-trade"
RULE_STOP_LOSS = "stop-loss"
RULE_POSITION_SIZE = "position-size"
RULE_REENTRY = "re-entry"

PENALTIES = {
    RULE_RISK_PER_TRADE: PENALTY_RISK_PER_TRADE,
    RULE_STOP_LOSS: PENALTY_STOP_LOSS,
    RULE_POSITION_SIZE: PENALTY_POSITION_SIZE,
    RULE_REENTRY: PENALTY_REENTRY,
}


def planned_risk_dollars(trade: Trade, account: float) -> Optional[float]:
    """Risk dollars implied by the stop-loss. None when no usable stop."""
    if trade.stop_loss is None:
        return None
    return abs(trade.entry_price - trade.stop_loss) * trade.quantity


def audit_trade(
    trade: Trade, account: float, prior_trades: List[Trade]
) -> dict:
    """Audit one trade. prior_trades = earlier trades (any order) for re-entry."""
    violations: List[dict] = []

    risk_dollars = planned_risk_dollars(trade, account)
    if risk_dollars is not None and risk_dollars > RISK_PCT_LIMIT * account:
        violations.append(
            {
                "rule": RULE_RISK_PER_TRADE,
                "detail": (
                    f"planned risk ${risk_dollars:,.2f} exceeds "
                    f"{RISK_PCT_LIMIT * 100:.0f}% of account"
                ),
            }
        )

    if trade.stop_loss is None or not (trade.stop_loss < trade.entry_price):
        violations.append(
            {
                "rule": RULE_STOP_LOSS,
                "detail": (
                    "no stop-loss set" if trade.stop_loss is None
                    else "stop-loss not below entry (wrong side for a long)"
                ),
            }
        )

    notional = trade.quantity * trade.entry_price
    if notional > POSITION_PCT_LIMIT * account:
        violations.append(
            {
                "rule": RULE_POSITION_SIZE,
                "detail": (
                    f"position notional ${notional:,.2f} exceeds "
                    f"{POSITION_PCT_LIMIT * 100:.0f}% of account"
                ),
            }
        )

    # Re-entry: entry same day or next calendar day after a losing exit,
    # same symbol.
    for prev in prior_trades:
        if prev.symbol != trade.symbol or prev.trade_id == trade.trade_id:
            continue
        if prev.exit_date is None or prev.pnl() is None or prev.pnl() >= 0:
            continue
        delta = (trade.entry_date - prev.exit_date).days
        if 0 <= delta <= 1:
            violations.append(
                {
                    "rule": RULE_REENTRY,
                    "detail": (
                        f"re-entered {trade.symbol} {delta} day(s) after losing "
                        f"exit of {prev.trade_id} ({prev.exit_date.isoformat()})"
                    ),
                }
            )
            break

    score = 100
    for v in violations:
        score -= PENALTIES[v["rule"]]
    score = max(0, min(100, score))

    r_multiple = None
    if risk_dollars and risk_dollars > 0 and trade.pnl() is not None:
        r_multiple = trade.pnl() / risk_dollars

    return {
        "pnl": trade.pnl(),
        "pnlPct": trade.pnl_pct(),
        "rMultiple": r_multiple,
        "disciplineScore": score,
        "violations": violations,
    }


def audit_all(trades: List[Trade], account: float) -> List[dict]:
    """Audit all trades in chronological (entry, id) order for re-entry context."""
    ordered = sorted(trades, key=lambda t: (t.entry_date, t.trade_id))
    results: List[dict] = []
    for i, trade in enumerate(ordered):
        results.append(audit_trade(trade, account, ordered[:i]))
    # Return in the original input order alongside results.
    by_id = {t.trade_id: r for t, r in zip(ordered, results)}
    return [by_id[t.trade_id] for t in trades]
