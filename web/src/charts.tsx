import { linePath, scaleLinear } from './svg-geometry';
import type { DrawdownPoint } from './drawdown';
import type { EquityPoint } from './types';
import { arrow, fmtDate, fmtPct } from './format';

const GREEN = '#1a7f37';
const RED = '#cf222e';
const INK = '#334155';
const GRID = '#e5e7eb';

function r(n: number): number {
  return Math.round(n * 100) / 100;
}

/** Compact price sparkline. Color follows the series direction; the arrow in the
 *  adjacent change cell carries the direction too, so color is never the only signal. */
export function Sparkline({
  values,
  width = 110,
  height = 30,
}: {
  values: number[];
  width?: number;
  height?: number;
}) {
  if (values.length === 0) return <span className="num muted">—</span>;
  const up = values[values.length - 1] >= values[0];
  const d = linePath(values, width, height);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="price sparkline">
      <path d={d} fill="none" stroke={up ? GREEN : RED} strokeWidth={1.5} strokeLinejoin="round" />
      <circle
        cx={r(scaleLinear([0, values.length - 1], [2, width - 2])(values.length - 1))}
        cy={r(scaleLinear([Math.min(...values), Math.max(...values)], [height - 2, 2])(values[values.length - 1]))}
        r={2.2}
        fill={up ? GREEN : RED}
      />
    </svg>
  );
}

/** Equity curve with benchmark overlay on a shared scale. */
export function EquityChart({
  equity,
  benchmark,
  width = 760,
  height = 240,
}: {
  equity: EquityPoint[];
  benchmark: EquityPoint[];
  width?: number;
  height?: number;
}) {
  if (equity.length === 0) return <div className="empty">No equity data.</div>;
  const padL = 64;
  const padT = 10;
  const padB = 22;
  const padR = 8;
  const all = [...equity.map((p) => p.equity), ...benchmark.map((p) => p.equity)];
  const domain: [number, number] = [Math.min(...all), Math.max(...all)];
  const w = width - padL - padR;
  const h = height - padT - padB;
  const x = scaleLinear([0, equity.length - 1], [padL, padL + w]);
  const y = scaleLinear(domain, [padT + h, padT]);

  const d = (pts: EquityPoint[]) =>
    pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${r(x(i))},${r(y(p.equity))}`).join(' ');

  const ticks = [domain[0], (domain[0] + domain[1]) / 2, domain[1]];

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="equity curve with benchmark">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={padL} x2={width - padR} y1={r(y(t))} y2={r(y(t))} stroke={GRID} strokeWidth={1} />
          <text x={padL - 6} y={r(y(t)) + 4} textAnchor="end" fontSize={10} fill={INK} className="chart-text">
            ${(t / 1000).toFixed(1)}k
          </text>
        </g>
      ))}
      {benchmark.length > 0 && (
        <path d={d(benchmark)} fill="none" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="5 3" />
      )}
      <path d={d(equity)} fill="none" stroke={INK} strokeWidth={2} strokeLinejoin="round" />
      <text x={padL} y={height - 6} fontSize={10} fill={INK} className="chart-text">
        {fmtDate(equity[0].date)}
      </text>
      <text x={width - padR} y={height - 6} fontSize={10} fill={INK} textAnchor="end" className="chart-text">
        {fmtDate(equity[equity.length - 1].date)}
      </text>
    </svg>
  );
}

/** Drawdown as a shaded red area hanging from the zero line. */
export function DrawdownChart({
  points,
  width = 760,
  height = 170,
}: {
  points: DrawdownPoint[];
  width?: number;
  height?: number;
}) {
  if (points.length === 0) return <div className="empty">No drawdown data.</div>;
  const values = points.map((p) => p.drawdownPct);
  const min = Math.min(0, ...values);
  const padL = 56;
  const padT = 8;
  const padB = 22;
  const padR = 8;
  const x = scaleLinear([0, values.length - 1], [padL, width - padR]);
  const y = scaleLinear([min, 0], [height - padB, padT]);
  const line = values.map((v, i) => `${i === 0 ? 'M' : 'L'}${r(x(i))},${r(y(v))}`).join(' ');
  const topY = r(y(0));
  const area = `${line} L${r(x(values.length - 1))},${topY} L${r(x(0))},${topY} Z`;
  const ticks = [0, min / 2, min];

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="drawdown chart">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={padL} x2={width - padR} y1={r(y(t))} y2={r(y(t))} stroke={GRID} strokeWidth={1} />
          <text x={padL - 6} y={r(y(t)) + 4} textAnchor="end" fontSize={10} fill={INK} className="chart-text">
            {t.toFixed(0)}%
          </text>
        </g>
      ))}
      <path d={area} fill={RED} opacity={0.14} />
      <path d={line} fill="none" stroke={RED} strokeWidth={1.5} />
      <text x={padL} y={height - 6} fontSize={10} fill={INK} className="chart-text">
        {fmtDate(points[0].date)}
      </text>
      <text x={width - padR} y={height - 6} fontSize={10} fill={INK} textAnchor="end" className="chart-text">
        {fmtDate(points[points.length - 1].date)}
      </text>
    </svg>
  );
}

/** Monthly returns as a heatmap row: green/red cell + signed % + arrow. */
export function MonthlyHeatmap({ monthlyReturns }: { monthlyReturns: Record<string, number> }) {
  const entries = Object.entries(monthlyReturns).sort(([a], [b]) => (a < b ? -1 : 1));
  if (entries.length === 0) return <div className="empty">No monthly returns.</div>;
  const maxAbs = Math.max(1, ...entries.map(([, v]) => Math.abs(v)));
  return (
    <div className="heatmap">
      {entries.map(([key, v]) => {
        const up = v > 0;
        const alpha = 0.12 + (0.5 * Math.abs(v)) / maxAbs;
        return (
          <div
            key={key}
            className="heat-cell"
            style={{ backgroundColor: up ? `rgba(26,127,55,${alpha.toFixed(2)})` : `rgba(207,34,46,${alpha.toFixed(2)})` }}
          >
            <div className="heat-month">{key}</div>
            <div className={`num heat-val ${up ? 'pos' : 'neg'}`}>
              {arrow(v)} {fmtPct(v, 1)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** 0-100 discipline score as a labeled bar. */
export function ScoreBar({ score, color }: { score: number; color: string }) {
  const clamped = Math.max(0, Math.min(100, score));
  return (
    <span className="scorebar" role="img" aria-label={`discipline score ${score} of 100`}>
      <span className="scorebar-track">
        <span className="scorebar-fill" style={{ width: `${clamped}%`, backgroundColor: color }} />
      </span>
      <span className="num scorebar-val">{score}</span>
    </span>
  );
}
