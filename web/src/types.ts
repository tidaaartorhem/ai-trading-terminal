// TypeScript shapes matching the data contract written by the Python pipeline
// (python3 ../services/main.py build -> web/public/{market,trades,analytics}.json).

export interface HistoryBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Macd {
  line: number;
  signal: number;
  hist: number;
}

export interface Bollinger {
  upper: number;
  mid: number;
  lower: number;
}

export interface Indicators {
  sma20: number;
  ema12: number;
  rsi14: number;
  macd: Macd;
  atr14: number;
  bollinger: Bollinger;
}

export interface SymbolQuote {
  symbol: string;
  name: string;
  sector: string;
  price: number;
  changePct: number;
  history: HistoryBar[];
  indicators: Indicators;
}

export interface MarketData {
  asOf: string;
  stale: boolean;
  source: string;
  symbols: Record<string, SymbolQuote>;
}

export interface Violation {
  rule: string;
  detail: string;
}

export interface Trade {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  quantity: number;
  entryDate: string;
  entryPrice: number;
  exitDate: string;
  exitPrice: number;
  stopLoss: number;
  takeProfit: number;
  riskPctPlanned: number;
  accountSize: number;
  pnl: number;
  pnlPct: number;
  rMultiple: number;
  disciplineScore: number;
  violations: Violation[];
}

export interface OpenPosition {
  symbol: string;
  quantity: number;
  entryDate: string;
  entryPrice: number;
}

export interface TradesData {
  trades: Trade[];
  openPositions: OpenPosition[];
}

export interface EquityPoint {
  date: string;
  equity: number;
}

export interface Metrics {
  cagr: number;
  sharpe: number;
  maxDrawdownPct: number;
  winRate: number;
  profitFactor: number;
  expectancy: number;
  totalTrades: number;
  avgR: number;
}

export interface DisciplineData {
  avgScore: number;
  violationsByRule: Record<string, number>;
  scoreTrend: { date: string; score: number }[];
}

export interface AnalyticsData {
  startingCapital: number;
  equityCurve: EquityPoint[];
  benchmarkCurve: EquityPoint[];
  metrics: Metrics;
  monthlyReturns: Record<string, number>;
  discipline: DisciplineData;
}
