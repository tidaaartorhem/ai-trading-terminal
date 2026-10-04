import { arrow, fmtDate, fmtMoney, fmtPct, fmtSignedMoney } from '../format';
import type { AnalyticsData, MarketData, OpenPosition, TradesData } from '../types';

interface EnrichedPosition extends OpenPosition {
  live: number | null;
  changePct: number;
  marketValue: number | null;
  unrealized: number | null;
  sector: string;
}

function enrich(p: OpenPosition, market: MarketData): EnrichedPosition {
  const q = market.symbols?.[p.symbol];
  const live = q ? q.price : null;
  const changePct = q ? q.changePct : 0;
  return {
    ...p,
    live,
    changePct,
    marketValue: live != null ? p.quantity * live : null,
    unrealized: live != null ? p.quantity * (live - p.entryPrice) : null,
    sector: q ? q.sector : 'Unknown',
  };
}

export function Positions({
  market,
  trades,
  analytics,
}: {
  market: MarketData;
  trades: TradesData;
  analytics: AnalyticsData;
}) {
  const positions = (trades.openPositions ?? []).map((p) => enrich(p, market));
  const curve = analytics.equityCurve ?? [];
  const lastEquity = curve.length > 0 ? curve[curve.length - 1].equity : analytics.startingCapital;

  const totalUnrealized = positions.reduce((s, p) => s + (p.unrealized ?? 0), 0);
  const accountValue = lastEquity + totalUnrealized;
  const dayPnl = positions.reduce(
    (s, p) => s + (p.live != null ? p.quantity * p.live * (p.changePct / 100) : 0),
    0,
  );

  const sectorTotals = new Map<string, number>();
  for (const p of positions) {
    const v = p.marketValue ?? p.quantity * p.entryPrice;
    sectorTotals.set(p.sector, (sectorTotals.get(p.sector) ?? 0) + v);
  }
  const sectors = [...sectorTotals.entries()].sort((a, b) => b[1] - a[1]);
  const maxSector = sectors.length > 0 ? sectors[0][1] : 0;

  const largest = positions.reduce<EnrichedPosition | null>((best, p) => {
    const v = p.marketValue ?? p.quantity * p.entryPrice;
    const bv = best ? best.marketValue ?? best.quantity * best.entryPrice : -1;
    return v > bv ? p : best;
  }, null);
  const largestPct = largest && accountValue > 0 ? ((largest.marketValue ?? largest.quantity * largest.entryPrice) / accountValue) * 100 : 0;

  return (
    <section>
      <div className="panel-head">
        <h2>Positions &amp; Risk</h2>
        <span className="muted micro-label">as of {fmtDate(market.asOf)}</span>
      </div>

      <div className="stat-grid">
        <div className="stat">
          <div className="micro-label">Account value</div>
          <div className="num stat-val">{fmtMoney(accountValue)}</div>
          <div className="micro-label muted">cash + open positions at live price</div>
        </div>
        <div className="stat">
          <div className="micro-label">Day P&amp;L (open)</div>
          <div className={`num stat-val ${dayPnl > 0 ? 'pos' : dayPnl < 0 ? 'neg' : ''}`}>
            {arrow(dayPnl)} {fmtSignedMoney(dayPnl)}
          </div>
          <div className="micro-label muted">estimate from day change %</div>
        </div>
        <div className="stat">
          <div className="micro-label">Open positions</div>
          <div className="num stat-val">{positions.length}</div>
          <div className="micro-label muted">unrealized {fmtSignedMoney(totalUnrealized)}</div>
        </div>
      </div>

      <h3>Open positions</h3>
      <div className="table-wrap">
        <table className="t">
          <thead>
            <tr>
              <th scope="col">Symbol</th>
              <th scope="col" className="cell-r">Qty</th>
              <th scope="col">Entry</th>
              <th scope="col" className="cell-r">Current</th>
              <th scope="col" className="cell-r">Unrealized</th>
              <th scope="col" className="cell-r">Day</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => {
              const unr = p.unrealized;
              return (
                <tr key={p.symbol}>
                  <td>
                    <span className="sym">{p.symbol}</span>
                    <span className="muted"> · {p.sector}</span>
                  </td>
                  <td className="num cell-r">{p.quantity}</td>
                  <td className="num">
                    {fmtMoney(p.entryPrice)} <span className="muted">{fmtDate(p.entryDate)}</span>
                  </td>
                  <td className="num cell-r">{p.live != null ? fmtMoney(p.live) : <span className="muted">— no quote</span>}</td>
                  <td className={`num cell-r ${unr != null && unr > 0 ? 'pos' : unr != null && unr < 0 ? 'neg' : ''}`}>
                    {unr != null ? (
                      <>
                        {arrow(unr)} {fmtSignedMoney(unr)}{' '}
                        <span className="muted">({fmtPct(((p.live ?? p.entryPrice) - p.entryPrice) / p.entryPrice * 100)})</span>
                      </>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td className={`num cell-r ${p.live != null && p.changePct > 0 ? 'pos' : p.live != null && p.changePct < 0 ? 'neg' : ''}`}>
                    {p.live != null ? (
                      <>
                        {arrow(p.changePct)} {fmtSignedMoney(p.quantity * p.live * (p.changePct / 100))}
                      </>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {positions.length === 0 && <div className="empty">No open positions.</div>}
      </div>

      <div className="two-col">
        <div>
          <h3>Exposure by sector</h3>
          <div className="bar-list">
            {sectors.map(([sector, value]) => (
              <div className="bar-row" key={sector}>
                <span className="bar-label">{sector}</span>
                <span className="bar-track">
                  <span
                    className="bar-fill"
                    style={{ width: `${maxSector > 0 ? (value / maxSector) * 100 : 0}%` }}
                  />
                </span>
                <span className="num bar-val">
                  {fmtMoney(value, 0)} <span className="muted">({accountValue > 0 ? ((value / accountValue) * 100).toFixed(1) : '0.0'}%)</span>
                </span>
              </div>
            ))}
            {sectors.length === 0 && <div className="empty">No exposure.</div>}
          </div>
        </div>
        <div>
          <h3>Risk note</h3>
          <div className="note-box">
            {largest ? (
              <p>
                Largest position: <strong className="sym">{largest.symbol}</strong> —{' '}
                <span className="num">{largestPct.toFixed(1)}%</span> of account value
                ({fmtMoney(largest.marketValue ?? largest.quantity * largest.entryPrice, 0)}).
                {largestPct > 25 && (
                  <span className="neg"> ⚠ Concentration above 25% — a single-name drawdown moves the account.</span>
                )}
              </p>
            ) : (
              <p className="muted">No open positions to assess.</p>
            )}
            <p className="muted">
              {positions.length > 0 &&
                `${positions.length} open position${positions.length === 1 ? '' : 's'}; unrealized P&L ${fmtSignedMoney(totalUnrealized)} on ${fmtMoney(accountValue)} account value.`}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
