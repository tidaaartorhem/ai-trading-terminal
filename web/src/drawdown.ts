// Drawdown computation from an equity curve: peak-to-trough declines.

export interface DrawdownPoint {
  date: string;
  equity: number;
  peak: number;
  /** <= 0, in percent of the running peak. */
  drawdownPct: number;
}

export interface DrawdownResult {
  points: DrawdownPoint[];
  maxDrawdownPct: number;
  maxEquity: number;
  minEquity: number;
}

export function computeDrawdown(curve: { date: string; equity: number }[]): DrawdownResult {
  const points: DrawdownPoint[] = [];
  let peak = -Infinity;
  let maxDrawdownPct = 0;
  let maxEquity = -Infinity;
  let minEquity = Infinity;

  for (const p of curve) {
    if (p.equity > peak) peak = p.equity;
    if (p.equity > maxEquity) maxEquity = p.equity;
    if (p.equity < minEquity) minEquity = p.equity;
    const drawdownPct = peak > 0 ? ((p.equity - peak) / peak) * 100 : 0;
    if (drawdownPct < maxDrawdownPct) maxDrawdownPct = drawdownPct;
    points.push({ date: p.date, equity: p.equity, peak, drawdownPct });
  }

  if (points.length === 0) {
    return { points, maxDrawdownPct: 0, maxEquity: 0, minEquity: 0 };
  }
  return { points, maxDrawdownPct, maxEquity, minEquity };
}
