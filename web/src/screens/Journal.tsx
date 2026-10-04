import { Fragment, useMemo, useState } from 'react';
import { ScoreBar } from '../charts';
import { BUCKET_COLOR, BUCKET_LABEL, disciplineBucket } from '../discipline';
import { arrow, fmtDate, fmtMoney, fmtPct, fmtSignedMoney } from '../format';
import type { Trade, TradesData } from '../types';

type SortKey = 'disciplineScore' | 'pnl' | 'entryDate' | 'rMultiple';

const SORT_LABELS: Record<SortKey, string> = {
  disciplineScore: 'Discipline',
  pnl: 'P&L',
  entryDate: 'Entry date',
  rMultiple: 'R multiple',
};

function ExpandedRow({ trade }: { trade: Trade }) {
  return (
    <tr className="detail-row">
      <td colSpan={9}>
        <div className="detail-grid">
          <div>
            <div className="micro-label">Plan</div>
            <dl className="kv">
              <dt>Stop loss</dt>
              <dd className="num">{fmtMoney(trade.stopLoss)}</dd>
              <dt>Take profit</dt>
              <dd className="num">{fmtMoney(trade.takeProfit)}</dd>
              <dt>Planned risk</dt>
              <dd className="num">{fmtPct(trade.riskPctPlanned, 1)}</dd>
              <dt>Account size</dt>
              <dd className="num">{fmtMoney(trade.accountSize, 0)}</dd>
            </dl>
          </div>
          <div>
            <div className="micro-label">Rule violations ({trade.violations.length})</div>
            {trade.violations.length === 0 ? (
              <p className="pos">✓ No rule violations recorded on this trade.</p>
            ) : (
              <ul className="violations">
                {trade.violations.map((v, i) => (
                  <li key={i}>
                    <span className="badge badge-red">{v.rule}</span>
                    <span className="viol-detail">{v.detail}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </td>
    </tr>
  );
}

export function Journal({ trades }: { trades: TradesData }) {
  const [symbolFilter, setSymbolFilter] = useState<string>('ALL');
  const [sortKey, setSortKey] = useState<SortKey>('disciplineScore');
  const [sortDir, setSortDir] = useState<1 | -1>(1);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const symbols = useMemo(
    () => [...new Set((trades.trades ?? []).map((t) => t.symbol))].sort(),
    [trades],
  );

  const rows = useMemo(() => {
    const list = (trades.trades ?? []).filter((t) => symbolFilter === 'ALL' || t.symbol === symbolFilter);
    const dir = sortDir;
    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
      return String(av).localeCompare(String(bv)) * dir;
    });
  }, [trades, symbolFilter, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 1 ? -1 : 1));
    } else {
      setSortKey(key);
      setSortDir(key === 'disciplineScore' ? 1 : -1);
    }
  };

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const sortArrow = (key: SortKey) => (sortKey === key ? (sortDir === 1 ? ' ▲' : ' ▼') : '');

  return (
    <section>
      <div className="panel-head">
        <h2>Trade journal</h2>
        <div className="filter-row">
          <label htmlFor="sym-filter" className="micro-label">
            Symbol
          </label>
          <select
            id="sym-filter"
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            className="select"
          >
            <option value="ALL">All symbols</option>
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <span className="muted micro-label">
            {rows.length} trade{rows.length === 1 ? '' : 's'} · sorted by {SORT_LABELS[sortKey]}
            {sortDir === 1 ? ' ascending' : ' descending'}
          </span>
        </div>
      </div>

      <div className="table-wrap">
        <table className="t journal">
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Symbol</th>
              <th scope="col">Side</th>
              <th scope="col" className="cell-r">Qty</th>
              <th scope="col">Entry</th>
              <th scope="col">Exit</th>
              <th scope="col" className="cell-r">
                <button className="th-sort" onClick={() => toggleSort('pnl')}>
                  P&amp;L{sortArrow('pnl')}
                </button>
              </th>
              <th scope="col" className="cell-r">
                <button className="th-sort" onClick={() => toggleSort('rMultiple')}>
                  R{sortArrow('rMultiple')}
                </button>
              </th>
              <th scope="col">
                <button className="th-sort" onClick={() => toggleSort('disciplineScore')}>
                  Discipline{sortArrow('disciplineScore')}
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const bucket = disciplineBucket(t.disciplineScore);
              const isOpen = expanded.has(t.id);
              const pnlUp = t.pnl > 0;
              return (
                <Fragment key={t.id}>
                  <tr
                    className={`journal-row${isOpen ? ' open' : ''}`}
                    onClick={() => toggleExpand(t.id)}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggleExpand(t.id);
                      }
                    }}
                    aria-expanded={isOpen}
                  >
                    <td className="num muted">{t.id}</td>
                    <td className="sym">{t.symbol}</td>
                    <td>
                      <span className={`badge ${t.side === 'long' ? 'badge-green' : 'badge-red'}`}>
                        {t.side === 'long' ? '▲ LONG' : '▼ SHORT'}
                      </span>
                    </td>
                    <td className="num cell-r">{t.quantity}</td>
                    <td className="num">
                      {fmtMoney(t.entryPrice)} <span className="muted">{fmtDate(t.entryDate)}</span>
                    </td>
                    <td className="num">
                      {fmtMoney(t.exitPrice)} <span className="muted">{fmtDate(t.exitDate)}</span>
                    </td>
                    <td className={`num cell-r ${pnlUp ? 'pos' : t.pnl < 0 ? 'neg' : ''}`}>
                      {arrow(t.pnl)} {fmtSignedMoney(t.pnl)}{' '}
                      <span className="muted">({fmtPct(t.pnlPct, 1)})</span>
                    </td>
                    <td className="num cell-r">{t.rMultiple.toFixed(2)}R</td>
                    <td>
                      <ScoreBar score={t.disciplineScore} color={BUCKET_COLOR[bucket]} />
                      <span className="micro-label muted"> {BUCKET_LABEL[bucket]}</span>
                      {t.violations.length > 0 && (
                        <span className="badge badge-red viol-count">{t.violations.length} ✕</span>
                      )}
                    </td>
                  </tr>
                  {isOpen && <ExpandedRow trade={t} />}
                </Fragment>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && <div className="empty">No trades match the filter.</div>}
      </div>
      <p className="footnote">
        Click a row (or press Enter) to audit it: plan vs. execution and every rule violation.
        Worst discipline surfaces first by default.
      </p>
    </section>
  );
}
