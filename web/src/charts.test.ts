import { describe, expect, it } from 'vitest';
import { areaPath, linePath, scaleLinear, seriesPath } from './svg-geometry';

describe('scaleLinear', () => {
  it('maps domain endpoints to range endpoints', () => {
    const f = scaleLinear([0, 10], [2, 102]);
    expect(f(0)).toBe(2);
    expect(f(10)).toBe(102);
    expect(f(5)).toBe(52);
  });
  it('guards a zero-width domain by returning the range midpoint', () => {
    const f = scaleLinear([7, 7], [0, 100]);
    expect(f(7)).toBe(50);
    expect(f(999)).toBe(50);
  });
});

describe('linePath', () => {
  it('builds an M/L path across the box for a known series', () => {
    // values [0, 10] in a 100x50 box with pad 2:
    // x: 0->2, 1->98 ; y: 0->48, 10->2
    expect(linePath([0, 10], 100, 50)).toBe('M2,48 L98,2');
  });
  it('draws a flat series through the vertical middle', () => {
    // y for a flat domain is the midpoint of [48, 2] => 25
    expect(linePath([5, 5, 5], 100, 50)).toBe('M2,25 L50,25 L98,25');
  });
  it('returns empty string for an empty series', () => {
    expect(linePath([], 100, 50)).toBe('');
  });
});

describe('areaPath', () => {
  it('closes the line back to the zero baseline', () => {
    const d = areaPath([0, -10], 100, 50, 0);
    // line M2,2 L98,48 then back along y(0)=2
    expect(d).toBe('M2,2 L98,48 L98,2 L2,2 Z');
  });
  it('returns empty string for an empty series', () => {
    expect(areaPath([], 100, 50, 0)).toBe('');
  });
});

describe('seriesPath', () => {
  it('plots equity points on an explicit domain', () => {
    const pts = [
      { date: '2026-08-01', equity: 50000 },
      { date: '2026-08-02', equity: 51000 },
    ];
    // domain [50000, 51000], box 100x50 pad 4: x 4->96, y 46->4
    expect(seriesPath(pts, 100, 50, [50000, 51000])).toBe('M4,46 L96,4');
  });
  it('returns empty string for no points', () => {
    expect(seriesPath([], 100, 50, [0, 1])).toBe('');
  });
});
