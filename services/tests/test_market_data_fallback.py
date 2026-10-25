"""Market-data source-fallback regression tests.

Regression (found 2026-10-25): Stooq stopped serving its CSV to this
environment and instead returns a JavaScript browser-verification page
(HTTP 200, HTML). ``_parse_history`` turns that into zero symbols, and the
old ``fetch()`` re-raised that ``MarketDataError`` instead of falling
through — so the build died even though Yahoo Finance and the local cache
could both serve real prices. A Stooq failure of any kind must now fall
through to Yahoo, then cache; loud failure happens only when all three
are exhausted.

All HTTP is monkeypatched; no test touches the real network or the real
``data/market_cache``.
"""

import json

import pytest

from services import market_data

# The shape of Stooq's answer since 2026-10-25: HTTP 200, HTML, no CSV rows.
STOOQ_CHALLENGE_PAGE = (
    "<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head>"
    "<body><noscript>This site requires JavaScript to verify your browser."
    "</noscript><script>/* browser verification challenge */</script>"
    "</body></html>"
)

# A Stooq CSV that covers only one symbol — also a "missing symbols" case.
STOOQ_PARTIAL_CSV = (
    "Symbol,Date,Open,High,Low,Close,Volume\n"
    "AAPL.US,2026-10-23,270.0,272.0,269.0,271.0,1000000\n"
)


def _yahoo_payload(symbol, base):
    """Minimal Yahoo chart-API payload: 5 daily bars, gmtoffset 0."""
    # 2026-10-19 .. 2026-10-23 as UTC epoch seconds (midnight UTC).
    stamps = [1792368000 + 86400 * i for i in range(5)]
    closes = [base + i for i in range(5)]
    return json.dumps({
        "chart": {
            "result": [{
                "meta": {"gmtoffset": 0},
                "timestamp": stamps,
                "indicators": {"quote": [{
                    "open": [c - 0.5 for c in closes],
                    "high": [c + 0.5 for c in closes],
                    "low": [c - 1.0 for c in closes],
                    "close": closes,
                    "volume": [1_000_000] * 5,
                }]},
            }],
        },
    })


def _http_get_factory(stooq_body):
    """_http_get stub: Stooq URLs get the given body, Yahoo URLs get data."""
    bases = {"AAPL": 270.0, "MSFT": 500.0, "TSLA": 440.0,
             "NVDA": 180.0, "SPY": 660.0}

    def fake(url, user_agent="ai-trading-terminal/1.0"):
        if "stooq.com" in url:
            return stooq_body
        if "yahoo.com" in url:
            sym = url.split("/chart/")[1].split("?")[0]
            return _yahoo_payload(sym, bases[sym])
        raise AssertionError(f"unexpected URL in test: {url}")

    return fake


@pytest.mark.parametrize("stooq_body", [STOOQ_CHALLENGE_PAGE, STOOQ_PARTIAL_CSV])
def test_stooq_degraded_response_falls_through_to_yahoo(
        tmp_path, monkeypatch, stooq_body):
    monkeypatch.setattr(
        market_data, "_http_get", _http_get_factory(stooq_body))
    monkeypatch.setattr(market_data, "CACHE_DIR", tmp_path / "cache")

    histories, stale, as_of, source = market_data.fetch()

    assert stale is False
    assert source == "Yahoo Finance"
    assert as_of == "2026-10-23"
    assert set(histories) == {"AAPL", "MSFT", "TSLA", "NVDA", "SPY"}
    assert histories["AAPL"][-1]["close"] == pytest.approx(274.0)
    assert len(histories["AAPL"]) == 5
    # The Yahoo refresh is cached, so the next degraded run can use it.
    assert (tmp_path / "cache" / "fetched_on.txt").read_text() == "2026-10-23"
    assert (tmp_path / "cache" / "source.txt").read_text() == "Yahoo Finance"
    assert (tmp_path / "cache" / "AAPL.csv").exists()


def test_stooq_and_yahoo_down_still_fails_loudly_with_no_cache(
        tmp_path, monkeypatch):
    """Fallthrough must not mask a total outage: no source + no cache = error."""
    def _raise_down(*a, **k):
        import urllib.error
        raise urllib.error.URLError("network down (test)")

    monkeypatch.setattr(market_data, "_http_get", _raise_down)
    monkeypatch.setattr(market_data, "CACHE_DIR", tmp_path / "empty_cache")
    with pytest.raises(market_data.MarketDataError):
        market_data.fetch()
