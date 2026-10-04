import { describe, expect, it } from 'vitest';
import { arrow, fmtDate, fmtMoney, fmtMonthKey, fmtNum, fmtPct, fmtSignedMoney } from './format';

describe('fmtMoney', () => {
  it('formats positive values with grouping and 2dp', () => {
    expect(fmtMoney(1234.5)).toBe('$1,234.50');
  });
  it('formats negative values with a leading minus', () => {
    expect(fmtMoney(-1234.5)).toBe('-$1,234.50');
  });
  it('formats zero', () => {
    expect(fmtMoney(0)).toBe('$0.00');
  });
});

describe('fmtSignedMoney', () => {
  it('prefixes gains with +', () => {
    expect(fmtSignedMoney(338)).toBe('+$338.00');
  });
  it('prefixes losses with -', () => {
    expect(fmtSignedMoney(-12.5)).toBe('-$12.50');
  });
  it('shows zero without a sign', () => {
    expect(fmtSignedMoney(0)).toBe('$0.00');
  });
});

describe('fmtPct', () => {
  it('signs positive percentages', () => {
    expect(fmtPct(0.87)).toBe('+0.87%');
  });
  it('signs negative percentages', () => {
    expect(fmtPct(-1.4)).toBe('-1.40%');
  });
  it('renders zero plainly', () => {
    expect(fmtPct(0)).toBe('0.00%');
  });
});

describe('fmtNum', () => {
  it('formats with fixed decimals', () => {
    expect(fmtNum(54.246, 1)).toBe('54.2');
    expect(fmtNum(-3.456)).toBe('-3.46');
  });
});

describe('arrow', () => {
  it('returns directional arrows, never blank', () => {
    expect(arrow(1)).toBe('▲');
    expect(arrow(-0.01)).toBe('▼');
    expect(arrow(0)).toBe('—');
  });
});

describe('fmtDate', () => {
  it('renders ISO dates as Mon D, YYYY', () => {
    expect(fmtDate('2026-08-11')).toBe('Aug 11, 2026');
    expect(fmtDate('2026-10-04')).toBe('Oct 4, 2026');
  });
  it('falls back to the raw string when unparseable', () => {
    expect(fmtDate('not-a-date')).toBe('not-a-date');
  });
});

describe('fmtMonthKey', () => {
  it("renders YYYY-MM as Mon 'YY", () => {
    expect(fmtMonthKey('2026-08')).toBe("Aug '26");
  });
});
