"""Technical indicators — pure stdlib functions on OHLC lists.

All functions accept sequences of floats (or None-graceful lists) and return
None when the history is too short to compute the value, so short histories
never raise. Conventions:
  - SMA/EMA seed: EMA uses the standard Wilder-style recursive EMA seeded with
    the first close in the window (documented choice, not a fitted series).
  - RSI(14): Wilder's smoothing; returns 100.0 if avg loss is 0 (all gains),
    0.0 if avg gain is 0, None on flat/empty data.
  - MACD(12,26,9): EMA12-EMA26 line, 9-period EMA of the line as signal,
    histogram = line - signal. Needs >= 26 closes; the signal needs a few
    extra points but we use what is available (>= 26 + 1 ideally).
  - ATR(14): Wilder-smoothed average true range.
  - Bollinger(20,2): SMA20 +/- 2 * population std of the last 20 closes.
"""

from __future__ import annotations

from typing import List, Optional, Sequence


def sma(values: Sequence[float], period: int) -> Optional[float]:
    if period <= 0 or len(values) < period:
        return None
    window = values[-period:]
    if any(v is None for v in window):
        return None
    return sum(window) / period


def ema(values: Sequence[float], period: int) -> Optional[float]:
    """Recursive EMA seeded with the first close in the available series."""
    if period <= 0 or len(values) < period:
        return None
    series = list(values)
    if any(v is None for v in series):
        return None
    k = 2.0 / (period + 1)
    e = series[0]
    for v in series[1:]:
        e = v * k + e * (1 - k)
    return e


def rsi(closes: Sequence[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, len(closes)):
        a, b = closes[i - 1], closes[i]
        if a is None or b is None:
            return None
        d = b - a
        gains.append(d if d > 0 else 0.0)
        losses.append(-d if d < 0 else 0.0)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else None  # flat series: undefined
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _ema_series(values: Sequence[float], period: int) -> List[float]:
    """Full recursive EMA series (needs at least `period` values)."""
    k = 2.0 / (period + 1)
    e = values[0]
    out = [e]
    for v in values[1:]:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def macd(
    closes: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Optional[dict]:
    if len(closes) < slow or any(v is None for v in closes):
        return None
    ema_fast = _ema_series(closes, fast)
    ema_slow = _ema_series(closes, slow)
    line_series = [f - s for f, s in zip(ema_fast, ema_slow)]
    # Signal is the EMA of the MACD line, seeded from the first line value.
    k = 2.0 / (signal + 1)
    sig = line_series[0]
    for v in line_series[1:]:
        sig = v * k + sig * (1 - k)
    line = line_series[-1]
    return {"line": line, "signal": sig, "hist": line - sig}


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> Optional[float]:
    n = len(closes)
    if n < period + 1 or len(highs) < n or len(lows) < n:
        return None
    trs: List[float] = []
    for i in range(1, n):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        if h is None or l is None or pc is None:
            return None
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    # Wilder smoothing over the first `period` TR values, then continue.
    atr_v = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr_v = (atr_v * (period - 1) + tr) / period
    return atr_v


def bollinger(
    closes: Sequence[float], period: int = 20, mult: float = 2.0
) -> Optional[dict]:
    if len(closes) < period:
        return None
    window = closes[-period:]
    if any(v is None for v in window):
        return None
    mid = sum(window) / period
    var = sum((v - mid) ** 2 for v in window) / period  # population std
    sd = var ** 0.5
    return {"upper": mid + mult * sd, "mid": mid, "lower": mid - mult * sd}
