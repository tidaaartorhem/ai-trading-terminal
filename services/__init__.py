"""ai-trading-terminal service layer — stdlib only."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional

STARTING_CAPITAL = 50_000.0

# Discipline thresholds (fractions of starting capital).
RISK_PCT_LIMIT = 0.02      # risk-per-trade: planned risk <= 2%
POSITION_PCT_LIMIT = 0.25  # position-size: notional <= 25%

# Score penalties per rule violation.
PENALTY_RISK_PER_TRADE = 15
PENALTY_STOP_LOSS = 15
PENALTY_POSITION_SIZE = 10
PENALTY_REENTRY = 10

ROOT = Path(__file__).resolve().parent.parent  # ai-trading-terminal/


@dataclass
class Trade:
    trade_id: str
    symbol: str
    side: str
    quantity: float
    entry_date: date
    entry_price: float
    exit_date: Optional[date]
    exit_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_pct_planned: Optional[float]
    notes: str = ""

    def pnl(self) -> Optional[float]:
        if self.exit_price is None:
            return None
        return (self.exit_price - self.entry_price) * self.quantity

    def pnl_pct(self) -> Optional[float]:
        if self.exit_price is None:
            return None
        notional = self.entry_price * self.quantity
        if notional == 0:
            return None
        return (self.exit_price - self.entry_price) / self.entry_price * 100.0


def _f(v: str) -> Optional[float]:
    v = (v or "").strip()
    return float(v) if v else None


def _d(v: str) -> Optional[date]:
    v = (v or "").strip()
    return date.fromisoformat(v) if v else None


def load_trades(path: Optional[Path] = None) -> List[Trade]:
    path = path or ROOT / "data" / "sample-trades.csv"
    trades: List[Trade] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            trades.append(
                Trade(
                    trade_id=row["id"].strip(),
                    symbol=row["symbol"].strip().upper(),
                    side=row["side"].strip().lower(),
                    quantity=float(row["quantity"]),
                    entry_date=_d(row["entry_date"]),
                    entry_price=float(row["entry_price"]),
                    exit_date=_d(row["exit_date"]),
                    exit_price=_f(row["exit_price"]),
                    stop_loss=_f(row["stop_loss"]),
                    take_profit=_f(row["take_profit"]),
                    risk_pct_planned=_f(row["risk_pct_planned"]),
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return trades


def load_open_positions(path: Optional[Path] = None) -> List[dict]:
    path = path or ROOT / "data" / "open-positions.csv"
    positions: List[dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            positions.append(
                {
                    "symbol": row["symbol"].strip().upper(),
                    "quantity": float(row["quantity"]),
                    "entryDate": row["entry_date"].strip(),
                    "entryPrice": float(row["entry_price"]),
                }
            )
    return positions
