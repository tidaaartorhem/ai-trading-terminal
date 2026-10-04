// Number, currency, percent and date formatting for terminal readouts.
// All numeric output uses tabular figures via the .num CSS class.

function group(v: number, dp: number): string {
  return Math.abs(v).toLocaleString('en-US', {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
}

/** $1,234.56 / -$1,234.56 */
export function fmtMoney(v: number, dp = 2): string {
  return `${v < 0 ? '-' : ''}$${group(v, dp)}`;
}

/** +$1,234.56 / -$1,234.56 / $0.00 */
export function fmtSignedMoney(v: number, dp = 2): string {
  if (v > 0) return `+$${group(v, dp)}`;
  if (v < 0) return `-$${group(v, dp)}`;
  return `$${group(0, dp)}`;
}

/** +1.23% / -1.23% / 0.00% */
export function fmtPct(v: number, dp = 2): string {
  if (v > 0) return `+${Math.abs(v).toFixed(dp)}%`;
  if (v < 0) return `-${Math.abs(v).toFixed(dp)}%`;
  return `${(0).toFixed(dp)}%`;
}

/** 1,234.56 with fixed decimals (no currency sign). */
export function fmtNum(v: number, dp = 2): string {
  return `${v < 0 ? '-' : ''}${group(v, dp)}`;
}

/** Directional arrow used alongside color so moves are never color-only. */
export function arrow(v: number): '▲' | '▼' | '—' {
  if (v > 0) return '▲';
  if (v < 0) return '▼';
  return '—';
}

/** "2026-08-11" -> "Aug 11, 2026". Falls back to the raw string when unparseable. */
export function fmtDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = months[Number(m[2]) - 1];
  if (!month) return iso;
  return `${month} ${Number(m[3])}, ${m[1]}`;
}

/** "2026-08" -> "Aug '26". */
export function fmtMonthKey(key: string): string {
  const m = /^(\d{4})-(\d{2})$/.exec(key);
  if (!m) return key;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = months[Number(m[2]) - 1];
  if (!month) return key;
  return `${month} '${m[1].slice(2)}`;
}
