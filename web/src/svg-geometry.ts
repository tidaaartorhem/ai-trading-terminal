// Pure SVG geometry helpers for the hand-rolled charts (no chart library).

/** Map a value from a numeric domain to a pixel range. Guards a zero-width domain. */
export function scaleLinear(domain: [number, number], range: [number, number]): (v: number) => number {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  if (d1 === d0) {
    const mid = (r0 + r1) / 2;
    return () => mid;
  }
  return (v: number) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);
}

/**
 * SVG path for a polyline through the values, left to right.
 * Returns '' for an empty series; a single-point series yields a lone "M".
 */
export function linePath(values: number[], width: number, height: number, pad = 2): string {
  if (values.length === 0) return '';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const x = scaleLinear([0, values.length - 1], [pad, width - pad]);
  const y = scaleLinear([min, max], [height - pad, pad]);
  return values.map((v, i) => `${i === 0 ? 'M' : 'L'}${round(x(i))},${round(y(v))}`).join(' ');
}

/**
 * SVG path for a filled area under the values (closed back to the baseline y0).
 */
export function areaPath(values: number[], width: number, height: number, y0: number, pad = 2): string {
  const line = linePath(values, width, height, pad);
  if (!line) return '';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const y = scaleLinear([min, max], [height - pad, pad]);
  const base = round(y(y0));
  const last = values.length - 1;
  const x = scaleLinear([0, last], [pad, width - pad]);
  return `${line} L${round(x(last))},${base} L${round(x(0))},${base} Z`;
}

/** Convert a list of {date, equity} points to an SVG path on an explicit domain. */
export function seriesPath(
  points: { date: string; equity: number }[],
  width: number,
  height: number,
  domain: [number, number],
  pad = 4,
): string {
  if (points.length === 0) return '';
  const x = scaleLinear([0, points.length - 1], [pad, width - pad]);
  const y = scaleLinear(domain, [height - pad, pad]);
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${round(x(i))},${round(y(p.equity))}`).join(' ');
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}
