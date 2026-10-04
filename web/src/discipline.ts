// Discipline-score bucketing. Buckets drive badge color in the journal,
// analytics and position views; the label text always accompanies the color.

export type ScoreBucket = 'excellent' | 'good' | 'fair' | 'poor';

export function disciplineBucket(score: number): ScoreBucket {
  if (score >= 85) return 'excellent';
  if (score >= 70) return 'good';
  if (score >= 50) return 'fair';
  return 'poor';
}

export const BUCKET_LABEL: Record<ScoreBucket, string> = {
  excellent: 'Excellent',
  good: 'Good',
  fair: 'Fair',
  poor: 'Poor',
};

export const BUCKET_COLOR: Record<ScoreBucket, string> = {
  excellent: '#1a7f37',
  good: '#2f9e44',
  fair: '#9a6700',
  poor: '#cf222e',
};
