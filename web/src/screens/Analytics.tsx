import { DrawdownChart, EquityChart, MonthlyHeatmap, ScoreBar, Sparkline } from '../charts';
import { BUCKET_COLOR, disciplineBucket } from '../discipline';
import { computeDrawdown } from '../drawdown';
import { fmtDate, fmtMoney, fmtNum, fmtPct } from '../format';
import type { AnalyticsData } from '../types';

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="stat">
      <div className="micro-label">{label}</div>
      <div className="num stat-val">{value}</div>
      {sub && <div className="micro-label muted">{sub}</div>}
    </div>
  );
}

export function Analytics({ analytics }: { analytics: AnalyticsData }) {
  const m = analytics.metrics;
  const curve = analytics.equityCurve ?? [];
  const bench = analytics.benchmarkCurve ?? [];
  const dd = computeDrawdown(curve);
  const d = analytics.discipline;
  const ruleEntries = Object.entries(d.violationsByRule ?? {}).sort((a, b) => b[1] - a[1]);
  const maxViol = ruleEntries.length > 0 ? ruleEntries[0][1] : 0;
  const trend = (d.scoreTrend ?? []).map((p) => p.score);
  const bucket = disciplineBucket(d.avgScore);

  return (
    <section>
      <div className="panel-head">
        <h2>Analytics</h2>
        <span className="muted micro-label">
          starting capital {fmtMoney(analytics.startingCapital, 0)} · {m.totalTrades} closed trades
        </span>
      </div>

      <h3>Equity curve</h3>
      <div className="chart-panel">
        <div className="legend">
          <span className="legend-item">
            <span className="legend-swatch" style={{ backgroundColor: '#334155' }} /> Portfolio
          </span>
          <span className="legend-item">
            <span className="legend-swatch legend-dash" /> Benchmark (SPY)
          </span>
        </div>
        <EquityChart equity={curve} benchmark={bench} />
      </div>

      <h3>Drawdown</h3>
      <div className="chart-panel">
        <DrawdownChart points={dd.points} />
        <p className="footnote">
          Max drawdown <span className="num neg">▼ {fmtPct(dd.maxDrawdownPct, 1)}</span> · trough{' '}
          <span className="num">{fmtMoney(dd.minEquity, 0)}</span> vs peak{' '}
          <span className="num">{fmtMoney(dd.maxEquity, 0)}</span>
        </p>
      </div>

      <h3>Monthly returns</h3>
      <MonthlyHeatmap monthlyReturns={analytics.monthlyReturns ?? {}} />

      <h3>Performance metrics</h3>
      <div className="stat-grid">
        <Metric label="CAGR" value={fmtPct(m.cagr, 1)} />
        <Metric label="Sharpe" value={fmtNum(m.sharpe, 2)} />
        <Metric label="Win rate" value={fmtPct(m.winRate, 1)} />
        <Metric label="Profit factor" value={fmtNum(m.profitFactor, 2)} />
        <Metric label="Expectancy" value={fmtMoney(m.expectancy)} sub="per trade" />
        <Metric label="Max drawdown" value={fmtPct(m.maxDrawdownPct, 1)} />
        <Metric label="Total trades" value={String(m.totalTrades)} />
        <Metric label="Avg R" value={`${fmtNum(m.avgR, 2)}R`} />
      </div>

      <h3>Discipline audit</h3>
      <div className="two-col">
        <div>
          <div className="stat">
            <div className="micro-label">Average discipline score</div>
            <div className="num stat-val">{d.avgScore}</div>
            <ScoreBar score={d.avgScore} color={BUCKET_COLOR[bucket]} />
          </div>
          <h4>Violations by rule</h4>
          <div className="bar-list">
            {ruleEntries.map(([rule, count]) => (
              <div className="bar-row" key={rule}>
                <span className="bar-label mono">{rule}</span>
                <span className="bar-track">
                  <span
                    className="bar-fill bar-fill-red"
                    style={{ width: `${maxViol > 0 ? (count / maxViol) * 100 : 0}%` }}
                  />
                </span>
                <span className="num bar-val">{count}×</span>
              </div>
            ))}
            {ruleEntries.length === 0 && <div className="empty">No violations recorded.</div>}
          </div>
        </div>
        <div>
          <h4>Score trend</h4>
          <Sparkline values={trend} width={280} height={56} />
          <p className="footnote">
            {trend.length > 0 && (
              <>
                First <span className="num">{trend[0]}</span> → latest{' '}
                <span className="num">{trend[trend.length - 1]}</span>
                {d.scoreTrend.length > 0 && (
                  <span className="muted"> · {fmtDate(d.scoreTrend[0].date)} → {fmtDate(d.scoreTrend[d.scoreTrend.length - 1].date)}</span>
                )}
              </>
            )}
          </p>
        </div>
      </div>
    </section>
  );
}
