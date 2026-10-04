import { Sparkline } from '../charts';
import { arrow, fmtDate, fmtMoney, fmtNum, fmtPct } from '../format';
import type { MarketData, SymbolQuote } from '../types';

const GREEN = '#1a7f37';
const RED = '#cf222e';

function RsiBadge({ rsi }: { rsi: number }) {
  const state = rsi >= 70 ? 'Overbought' : rsi <= 30 ? 'Oversold' : 'Neutral';
  const cls = rsi >= 70 ? 'badge-red' : rsi <= 30 ? 'badge-green' : 'badge-neutral';
  return (
    <span className={`badge ${cls}`}>
      <span className="num">RSI {fmtNum(rsi, 1)}</span> · {state}
    </span>
  );
}

function SmaReadout({ price, sma20 }: { price: number; sma20: number }) {
  const diffPct = sma20 !== 0 ? ((price - sma20) / sma20) * 100 : 0;
  if (Math.abs(diffPct) < 0.25)
    return (
      <span className="num muted">≈ SMA20 {fmtMoney(sma20)}</span>
    );
  const above = diffPct > 0;
  return (
    <span className={`num ${above ? 'pos' : 'neg'}`}>
      {above ? '▲' : '▼'} {above ? 'Above' : 'Below'} SMA20 <span className="muted">({fmtPct(diffPct, 1)})</span>
    </span>
  );
}

function MacdReadout({ hist }: { hist: number }) {
  if (hist > 0)
    return (
      <span className="num pos">
        ▲ +{fmtNum(hist, 2)}
      </span>
    );
  if (hist < 0)
    return (
      <span className="num neg">
        ▼ −{fmtNum(Math.abs(hist), 2)}
      </span>
    );
  return <span className="num muted">— 0.00</span>;
}

function QuoteRow({ q }: { q: SymbolQuote }) {
  const closes = q.history.slice(-30).map((b) => b.close);
  const dayUp = q.changePct > 0;
  return (
    <tr>
      <td>
        <div className="sym">{q.symbol}</div>
        <div className="sym-name">{q.name}</div>
      </td>
      <td className="muted">{q.sector}</td>
      <td className="num cell-r">{fmtMoney(q.price)}</td>
      <td className={`num cell-r ${dayUp ? 'pos' : q.changePct < 0 ? 'neg' : ''}`}>
        {arrow(q.changePct)} {fmtPct(q.changePct)}
      </td>
      <td>
        <Sparkline values={closes} />
      </td>
      <td>
        <RsiBadge rsi={q.indicators.rsi14} />
      </td>
      <td>
        <SmaReadout price={q.price} sma20={q.indicators.sma20} />
      </td>
      <td>
        <MacdReadout hist={q.indicators.macd.hist} />
      </td>
    </tr>
  );
}

export function Watchlist({ market }: { market: MarketData }) {
  const quotes = Object.values(market.symbols ?? {});
  const benchmark = quotes.find((q) => q.symbol === 'SPY');
  const rows = quotes.filter((q) => q.symbol !== 'SPY').sort((a, b) => a.symbol.localeCompare(b.symbol));

  return (
    <section>
      <div className="panel-head">
        <h2>Watchlist</h2>
        {market.stale ? (
          <span className="badge badge-amber">⚠ Market data as of {fmtDate(market.asOf)} — cached snapshot</span>
        ) : (
          <span className="badge badge-green">● Live data as of {fmtDate(market.asOf)} · {market.source}</span>
        )}
      </div>

      {benchmark && (
        <div className="bench-row">
          <span className="micro-label">Benchmark</span>
          <span className="sym">{benchmark.symbol}</span>
          <span className="muted">{benchmark.name}</span>
          <span className="num">{fmtMoney(benchmark.price)}</span>
          <span className={`num ${benchmark.changePct > 0 ? 'pos' : benchmark.changePct < 0 ? 'neg' : ''}`}>
            {arrow(benchmark.changePct)} {fmtPct(benchmark.changePct)}
          </span>
          <Sparkline values={benchmark.history.slice(-30).map((b) => b.close)} />
        </div>
      )}

      <div className="table-wrap">
        <table className="t">
          <thead>
            <tr>
              <th scope="col">Symbol</th>
              <th scope="col">Sector</th>
              <th scope="col" className="cell-r">Price</th>
              <th scope="col" className="cell-r">Day</th>
              <th scope="col">30d</th>
              <th scope="col">RSI 14</th>
              <th scope="col">Trend</th>
              <th scope="col">MACD hist</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((q) => (
              <QuoteRow key={q.symbol} q={q} />
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <div className="empty">No symbols in watchlist.</div>}
      </div>
      <p className="footnote">
        RSI ≥ 70 flags overbought, ≤ 30 oversold. MACD histogram sign shows momentum direction.
      </p>
    </section>
  );
}
