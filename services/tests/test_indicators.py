"""Indicator unit tests — known-answer checks on small fixture series.

All fixtures here are synthetic, hand-verifiable series used only to pin the
math; they are NOT market data.
"""

import math

import pytest

from services import indicators as ind


def test_sma_known_answer():
    assert ind.sma([1.0, 2.0, 3.0, 4.0, 5.0], 3) == pytest.approx(4.0)


def test_sma_short_history_returns_none():
    assert ind.sma([1.0, 2.0], 5) is None


def test_ema_known_answer():
    # k = 2/(3+1) = 0.5; seed 10 -> 10.5 -> 11.25
    assert ind.ema([10.0, 11.0, 12.0], 3) == pytest.approx(11.25)


def test_ema_short_history_returns_none():
    assert ind.ema([10.0, 11.0], 3) is None


def test_rsi_all_gains_is_100():
    closes = [100.0 + i for i in range(15)]  # 14 straight +1 moves
    assert ind.rsi(closes) == pytest.approx(100.0)


def test_rsi_short_history_returns_none():
    assert ind.rsi([100.0, 101.0, 102.0]) is None


def test_atr_known_answer():
    highs = [10.0, 11.0, 12.0]
    lows = [9.0, 9.5, 10.0]
    closes = [9.5, 10.5, 11.0]
    # TR1 = max(1.5, 1.5, 0) = 1.5 ; TR2 = max(2, 1.5, 0.5) = 2 ; ATR(2) = 1.75
    assert ind.atr(highs, lows, closes, period=2) == pytest.approx(1.75)


def test_atr_short_history_returns_none():
    assert ind.atr([10.0], [9.0], [9.5], period=14) is None


def test_bollinger_known_answer():
    closes = [float(i) for i in range(1, 21)]
    bb = ind.bollinger(closes, period=20, mult=2.0)
    assert bb["mid"] == pytest.approx(10.5)
    sd = math.sqrt((20 ** 2 - 1) / 12)  # population std of 1..20
    assert bb["upper"] == pytest.approx(10.5 + 2 * sd)
    assert bb["lower"] == pytest.approx(10.5 - 2 * sd)


def test_bollinger_short_history_returns_none():
    assert ind.bollinger([1.0, 2.0, 3.0], period=20) is None


def test_macd_shape_and_short_returns_none():
    closes = [100.0 + i * 0.5 for i in range(30)]
    m = ind.macd(closes)
    assert set(m.keys()) == {"line", "signal", "hist"}
    assert m["hist"] == pytest.approx(m["line"] - m["signal"])
    assert ind.macd(closes[:25]) is None  # needs >= 26 closes
