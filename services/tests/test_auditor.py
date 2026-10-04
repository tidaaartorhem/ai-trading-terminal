"""Auditor rule tests — each rule triggers in isolation and clears when fine.

Fixture trades are synthetic and use STARTING_CAPITAL = $50,000.
"""

from datetime import date

import pytest

from services import STARTING_CAPITAL, Trade
from services import auditor

ACCT = STARTING_CAPITAL


def mk(
    trade_id="T1",
    symbol="AAPL",
    qty=100.0,
    entry=100.0,
    exit_=110.0,
    entry_date=date(2026, 8, 5),
    exit_date=date(2026, 8, 10),
    stop=95.0,
):
    return Trade(
        trade_id=trade_id,
        symbol=symbol,
        side="long",
        quantity=qty,
        entry_date=entry_date,
        entry_price=entry,
        exit_date=exit_date,
        exit_price=exit_,
        stop_loss=stop,
        take_profit=None,
        risk_pct_planned=None,
    )


def rules(result):
    return {v["rule"] for v in result["violations"]}


def test_clean_trade_scores_100():
    r = auditor.audit_trade(mk(), ACCT, [])
    assert r["disciplineScore"] == 100
    assert r["violations"] == []
    assert r["pnl"] == pytest.approx(1000.0)
    assert r["pnlPct"] == pytest.approx(10.0)


def test_risk_per_trade_triggers():
    # risk = (100-88)*100 = $1200 > 2% of $50k; notional $10k <= 25% ok
    r = auditor.audit_trade(mk(stop=88.0), ACCT, [])
    assert "risk-per-trade" in rules(r)
    assert r["disciplineScore"] == 85  # 100 - 15


def test_risk_per_trade_clears_at_boundary():
    # risk exactly 2%: (100-90)*100 = $1000 -> no violation
    r = auditor.audit_trade(mk(stop=90.0), ACCT, [])
    assert "risk-per-trade" not in rules(r)
    assert r["disciplineScore"] == 100


def test_stop_loss_missing_triggers():
    r = auditor.audit_trade(mk(stop=None), ACCT, [])
    assert "stop-loss" in rules(r)
    assert r["disciplineScore"] == 85
    assert r["rMultiple"] is None  # no measurable planned risk


def test_stop_loss_wrong_side_triggers():
    # stop ABOVE entry for a long is not a real stop
    r = auditor.audit_trade(mk(stop=105.0), ACCT, [])
    assert "stop-loss" in rules(r)
    assert r["disciplineScore"] == 85


def test_position_size_triggers():
    # notional 200*100 = $20k > 25% of $50k; risk (100-99)*200=$200 ok
    r = auditor.audit_trade(mk(qty=200.0, stop=99.0), ACCT, [])
    assert "position-size" in rules(r)
    assert r["disciplineScore"] == 90  # 100 - 10


def test_reentry_triggers_after_next_day_loss():
    loser = mk("T1", entry_date=date(2026, 8, 3), exit_date=date(2026, 8, 5),
               exit_=90.0)  # -$1000 loss
    revenge = mk("T2", entry_date=date(2026, 8, 6), exit_date=date(2026, 8, 12),
                 stop=95.0)
    r = auditor.audit_trade(revenge, ACCT, [loser])
    assert "re-entry" in rules(r)
    assert r["disciplineScore"] == 90


def test_reentry_clears_when_gap_is_longer_or_prior_was_win():
    winner = mk("T1", entry_date=date(2026, 8, 3), exit_date=date(2026, 8, 5),
                exit_=110.0)  # +$1000
    later = mk("T2", entry_date=date(2026, 8, 6), exit_date=date(2026, 8, 12))
    assert "re-entry" not in rules(auditor.audit_trade(later, ACCT, [winner]))

    loser = mk("T1", entry_date=date(2026, 8, 3), exit_date=date(2026, 8, 5),
               exit_=90.0)
    coolheaded = mk("T2", entry_date=date(2026, 8, 10), exit_date=date(2026, 8, 12))
    assert "re-entry" not in rules(auditor.audit_trade(coolheaded, ACCT, [loser]))


def test_reentry_same_day_triggers():
    loser = mk("T1", entry_date=date(2026, 8, 3), exit_date=date(2026, 8, 5),
               exit_=90.0)
    same_day = mk("T2", entry_date=date(2026, 8, 5), exit_date=date(2026, 8, 12))
    assert "re-entry" in rules(auditor.audit_trade(same_day, ACCT, [loser]))


def test_penalties_stack_and_rmultiple():
    # no stop AND oversized notional -> 100 - 15 - 10 = 75
    r = auditor.audit_trade(mk(stop=None, qty=200.0), ACCT, [])
    assert rules(r) == {"stop-loss", "position-size"}
    assert r["disciplineScore"] == 75

    r2 = auditor.audit_trade(mk(), ACCT, [])  # pnl 1000, risk 500
    assert r2["rMultiple"] == pytest.approx(2.0)
