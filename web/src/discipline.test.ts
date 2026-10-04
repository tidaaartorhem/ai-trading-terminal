import { describe, expect, it } from 'vitest';
import { BUCKET_COLOR, BUCKET_LABEL, disciplineBucket } from './discipline';

describe('disciplineBucket', () => {
  it('buckets 85+ as excellent', () => {
    expect(disciplineBucket(85)).toBe('excellent');
    expect(disciplineBucket(100)).toBe('excellent');
  });
  it('buckets 70-84 as good', () => {
    expect(disciplineBucket(84.9)).toBe('good');
    expect(disciplineBucket(70)).toBe('good');
  });
  it('buckets 50-69 as fair', () => {
    expect(disciplineBucket(69.9)).toBe('fair');
    expect(disciplineBucket(50)).toBe('fair');
  });
  it('buckets below 50 as poor', () => {
    expect(disciplineBucket(49.9)).toBe('poor');
    expect(disciplineBucket(0)).toBe('poor');
  });
});

describe('bucket metadata', () => {
  it('has a label and an accessible color for every bucket', () => {
    for (const b of ['excellent', 'good', 'fair', 'poor'] as const) {
      expect(BUCKET_LABEL[b]).toBeTruthy();
      expect(BUCKET_COLOR[b]).toMatch(/^#[0-9a-f]{6}$/);
    }
  });
  it('uses the terminal green/red pair at the extremes', () => {
    expect(BUCKET_COLOR.excellent).toBe('#1a7f37');
    expect(BUCKET_COLOR.poor).toBe('#cf222e');
  });
});
