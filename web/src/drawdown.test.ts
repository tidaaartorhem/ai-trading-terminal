import { describe, expect, it } from 'vitest';
import { computeDrawdown } from './drawdown';

const curve = [
  { date: '2026-08-01', equity: 100 },
  { date: '2026-08-02', equity: 110 },
  { date: '2026-08-03', equity: 105 },
  { date: '2026-08-04', equity: 90 },
  { date: '2026-08-05', equity: 95 },
];

describe('computeDrawdown', () => {
  it('finds the max peak-to-trough decline', () => {
    const { maxDrawdownPct } = computeDrawdown(curve);
    // trough 90 vs peak 110
    expect(maxDrawdownPct).toBeCloseTo(-18.1818, 3);
  });
  it('tracks running peaks and per-point drawdown', () => {
    const { points } = computeDrawdown(curve);
    expect(points.map((p) => p.peak)).toEqual([100, 110, 110, 110, 110]);
    expect(points[2].drawdownPct).toBeCloseTo(-4.5455, 3);
    expect(points[1].drawdownPct).toBe(0);
  });
  it('reports extremes of the curve', () => {
    const { maxEquity, minEquity } = computeDrawdown(curve);
    expect(maxEquity).toBe(110);
    expect(minEquity).toBe(90);
  });
  it('handles an empty curve', () => {
    const r = computeDrawdown([]);
    expect(r.points).toEqual([]);
    expect(r.maxDrawdownPct).toBe(0);
    expect(r.maxEquity).toBe(0);
    expect(r.minEquity).toBe(0);
  });
  it('reports zero drawdown for a monotonically rising curve', () => {
    const r = computeDrawdown([
      { date: '2026-08-01', equity: 100 },
      { date: '2026-08-02', equity: 120 },
    ]);
    expect(r.maxDrawdownPct).toBe(0);
  });
});
