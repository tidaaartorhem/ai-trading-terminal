import { useEffect, useState } from 'react';
import { loadData, type AllData } from './data';
import { Analytics } from './screens/Analytics';
import { Journal } from './screens/Journal';
import { Positions } from './screens/Positions';
import { Watchlist } from './screens/Watchlist';

type Tab = 'watchlist' | 'positions' | 'journal' | 'analytics';

const TABS: { id: Tab; label: string }[] = [
  { id: 'watchlist', label: 'Watchlist' },
  { id: 'positions', label: 'Positions & Risk' },
  { id: 'journal', label: 'Journal' },
  { id: 'analytics', label: 'Analytics' },
];

export function App() {
  const [tab, setTab] = useState<Tab>('watchlist');
  const [data, setData] = useState<AllData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData()
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            ◈
          </span>
          <div>
            <h1>AI Trading Terminal</h1>
            <p className="tagline">the trade journal that audits your discipline</p>
          </div>
        </div>
        <nav className="tabs" aria-label="Sections">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`tab${tab === t.id ? ' active' : ''}`}
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? 'page' : undefined}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="main">
        {error && (
          <div className="alert alert-error" role="alert">
            <strong>⚠ Could not load data.</strong> {error}
            <div className="muted">
              Run the data pipeline from the repo root (<span className="mono">python3 services/main.py build</span>)
              or <span className="mono">npm run build</span> in web/ to regenerate web/public/*.json.
            </div>
          </div>
        )}
        {!error && !data && <div className="empty">Loading market, trade and analytics data…</div>}
        {data && tab === 'watchlist' && <Watchlist market={data.market} />}
        {data && tab === 'positions' && (
          <Positions market={data.market} trades={data.trades} analytics={data.analytics} />
        )}
        {data && tab === 'journal' && <Journal trades={data.trades} />}
        {data && tab === 'analytics' && <Analytics analytics={data.analytics} />}
      </main>

      <footer className="footer">
        <span className="muted micro-label">
          {data ? `Data as of ${data.market.asOf} · source ${data.market.source}` : 'AI Trading Terminal'}
        </span>
      </footer>
    </div>
  );
}
