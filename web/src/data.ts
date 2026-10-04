import type { AnalyticsData, MarketData, TradesData } from './types';

const base = import.meta.env.BASE_URL || './';

async function get<T>(file: string): Promise<T> {
  const res = await fetch(`${base}${file}`);
  if (!res.ok) throw new Error(`failed to load ${file}: ${res.status}`);
  return (await res.json()) as T;
}

export interface AllData {
  market: MarketData;
  trades: TradesData;
  analytics: AnalyticsData;
}

export async function loadData(): Promise<AllData> {
  const [market, trades, analytics] = await Promise.all([
    get<MarketData>('market.json'),
    get<TradesData>('trades.json'),
    get<AnalyticsData>('analytics.json'),
  ]);
  return { market, trades, analytics };
}
