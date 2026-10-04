"""Market data — daily history + latest quotes with a local CSV cache.

Connectivity is tested FIRST. Source priority:
  1. Stooq daily history (free CSV, no key). Unreachable from some networks.
  2. Yahoo Finance chart API (free JSON, no key) — fallback when Stooq fails.
  3. Local cache data/market_cache/<SYM>.csv — stale=true with the cache's
     real fetched-on date.

Policy: real prices only, never invented. Stooq unreachable + Yahoo
unreachable + no cache => FAIL LOUDLY (exit non-zero).

Latest price = last close of the symbol's history; day change % = last close
vs previous close. The separate live-quote endpoint is attempted as a
supplement but history's last close is authoritative when they disagree or the
quote endpoint fails — a quote without a history to anchor it is not trusted.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from . import ROOT

CACHE_DIR = ROOT / "data" / "market_cache"

SYMBOLS = ["AAPL", "MSFT", "TSLA", "NVDA", "SPY"]

HISTORY_URL = (
    "https://stooq.com/q/d/l/?s=aapl.us,msft.us,tsla.us,nvda.us,spy.us&i=d"
)
QUOTE_URL = (
    "https://stooq.com/q/l/?s=aapl.us,msft.us,tsla.us,nvda.us&f=sd2t2ohlcv&h&e=csv"
)

YAHOO_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1y"

TIMEOUT = 25


class MarketDataError(RuntimeError):
    """Raised when market data cannot be obtained from any source."""


def _http_get(url: str, user_agent: str = "ai-trading-terminal/1.0") -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_history(text: str) -> Dict[str, List[dict]]:
    """Parse Stooq daily CSV (Symbol,Date,Open,High,Low,Close,Volume)."""
    out: Dict[str, List[dict]] = {}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        sym = (row.get("Symbol") or "").strip().upper().replace(".US", "")
        d = (row.get("Date") or "").strip()
        try:
            bar = {
                "date": d,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(float(row["Volume"] or 0)),
            }
        except (ValueError, KeyError):
            continue
        if not sym or not d:
            continue
        out.setdefault(sym, []).append(bar)
    for bars in out.values():
        bars.sort(key=lambda b: b["date"])
    return out


def _cache_path(sym: str) -> Path:
    return CACHE_DIR / f"{sym}.csv"


def write_cache(histories: Dict[str, List[dict]], as_of: str, source: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "fetched_on.txt").write_text(as_of, encoding="utf-8")
    (CACHE_DIR / "source.txt").write_text(source, encoding="utf-8")
    for sym, bars in histories.items():
        with open(_cache_path(sym), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume"])
            w.writeheader()
            w.writerows(bars)


def cache_date() -> str:
    meta = CACHE_DIR / "fetched_on.txt"
    if meta.exists():
        return meta.read_text(encoding="utf-8").strip()
    return "unknown"


def cache_source() -> str:
    meta = CACHE_DIR / "source.txt"
    if meta.exists():
        return meta.read_text(encoding="utf-8").strip()
    return "Stooq"  # legacy caches were written by the Stooq path


def read_cache() -> Dict[str, List[dict]]:
    histories: Dict[str, List[dict]] = {}
    for sym in SYMBOLS:
        p = _cache_path(sym)
        if not p.exists():
            raise MarketDataError(
                f"no cached history for {sym}; Stooq unreachable and no cache — "
                "cannot proceed without real prices"
            )
        with open(p, newline="", encoding="utf-8") as f:
            bars = []
            for row in csv.DictReader(f):
                bars.append(
                    {
                        "date": row["date"],
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": int(row["volume"]),
                    }
                )
        bars.sort(key=lambda b: b["date"])
        histories[sym] = bars
    return histories


def _fetch_yahoo() -> Dict[str, List[dict]]:
    """Fetch daily history from Yahoo Finance chart API (free, no key)."""
    histories: Dict[str, List[dict]] = {}
    for sym in SYMBOLS:
        text = _http_get(YAHOO_URL.format(sym=sym), user_agent=YAHOO_UA)
        payload = json.loads(text)
        results = (payload.get("chart") or {}).get("result") or []
        if not results:
            raise MarketDataError(f"Yahoo Finance returned no data for {sym}")
        r = results[0]
        gmtoffset = ((r.get("meta") or {}).get("gmtoffset")) or 0
        stamps = r.get("timestamp") or []
        quote = ((r.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        bars: List[dict] = []
        for i, ts in enumerate(stamps):
            try:
                c = closes[i]
                if c is None:
                    continue
                d = datetime.fromtimestamp(ts + gmtoffset, tz=timezone.utc).date().isoformat()
                bars.append({
                    "date": d,
                    "open": float(opens[i] if opens[i] is not None else c),
                    "high": float(highs[i] if highs[i] is not None else c),
                    "low": float(lows[i] if lows[i] is not None else c),
                    "close": float(c),
                    "volume": int(volumes[i] or 0),
                })
            except (IndexError, TypeError, ValueError):
                continue
        if not bars:
            raise MarketDataError(f"Yahoo Finance returned no usable bars for {sym}")
        bars.sort(key=lambda b: b["date"])
        histories[sym] = bars
    return histories


def _last_bar_date(histories: Dict[str, List[dict]]) -> str:
    """Most recent trading date across symbols — the honest 'as of' date."""
    return max(bars[-1]["date"] for bars in histories.values() if bars)


def fetch() -> Tuple[Dict[str, List[dict]], bool, str, str]:
    """Return (histories, stale, as_of, source). Raises MarketDataError if none."""
    # 1. Stooq first.
    try:
        text = _http_get(HISTORY_URL)
        histories = _parse_history(text)
        if not all(sym in histories and histories[sym] for sym in SYMBOLS):
            raise MarketDataError("Stooq response missing symbols")
        as_of = _last_bar_date(histories)
        write_cache(histories, as_of, "Stooq")
        return histories, False, as_of, "Stooq"
    except MarketDataError:
        raise
    except Exception as exc:  # network or parse failure -> Yahoo fallback
        print(f"[market_data] Stooq unreachable ({exc}); trying Yahoo Finance…",
              file=sys.stderr)
    # 2. Yahoo Finance fallback.
    try:
        histories = _fetch_yahoo()
        as_of = _last_bar_date(histories)
        write_cache(histories, as_of, "Yahoo Finance")
        print("[market_data] using Yahoo Finance (Stooq unreachable from here)",
              file=sys.stderr)
        return histories, False, as_of, "Yahoo Finance"
    except MarketDataError:
        raise
    except Exception as exc:
        print(f"[market_data] Yahoo Finance failed ({exc}); trying local cache…",
              file=sys.stderr)
    # 3. Local cache, honestly labeled stale.
    histories = read_cache()
    return histories, True, cache_date(), cache_source()


def latest_quote_prices() -> Dict[str, float]:
    """Best-effort live quotes; empty dict on any failure (history is primary)."""
    try:
        text = _http_get(QUOTE_URL)
    except Exception:
        return {}
    out: Dict[str, float] = {}
    for row in csv.DictReader(io.StringIO(text)):
        sym = (row.get("Symbol") or "").strip().upper().replace(".US", "")
        try:
            out[sym] = float(row.get("Close") or row.get("close") or 0) or out.get(sym)
        except ValueError:
            pass
    return {k: v for k, v in out.items() if v}


def summarize(histories: Dict[str, List[dict]]) -> Dict[str, dict]:
    """Per-symbol latest price + day change % from history."""
    out: Dict[str, dict] = {}
    for sym, bars in histories.items():
        if not bars:
            continue
        last, prev = bars[-1], bars[-2] if len(bars) > 1 else bars[-1]
        change = (last["close"] - prev["close"]) / prev["close"] * 100 if prev["close"] else 0.0
        out[sym] = {"price": last["close"], "changePct": change, "lastDate": last["date"]}
    return out
