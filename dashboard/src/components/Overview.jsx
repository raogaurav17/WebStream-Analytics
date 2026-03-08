import { useApi } from '../hooks/useApi';
import { api } from '../api';
import { StatBox, Loading, ErrorState, WindowPicker } from './UI';
import { useState } from 'react';

function fmt(n, decimals = 0) {
  if (n == null) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return Number(n).toFixed(decimals);
}

export default function Overview() {
  const [window, setWindow] = useState('24h');
  const { data, loading, error } = useApi(() => api.overview(window), [window]);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-amber)' }}>
          ◈ KPI Overview
        </span>
        <WindowPicker value={window} onChange={setWindow} />
      </div>

      {error   && <ErrorState message={error} />}
      {loading && <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
        {Array.from({length: 7}).map((_,i) => <Loading key={i} rows={2} />)}
      </div>}

      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
          <StatBox className="fade-up-1" label="Total Events"    value={fmt(data.total_events)}    sub="all event types" />
          <StatBox className="fade-up-2" label="Unique Users"    value={fmt(data.unique_users)}    sub="active sessions" color="var(--blue)" />
          <StatBox className="fade-up-3" label="Views"           value={fmt(data.views)}           sub="product views" />
          <StatBox className="fade-up-4" label="Purchases"       value={fmt(data.purchases)}       sub="completed orders" color="var(--green)" />
          <StatBox className="fade-up-5" label="Revenue"         value={`$${fmt(data.total_revenue, 0)}`} sub="from purchases" color="var(--amber)" />
          <StatBox className="fade-up-6" label="AOV"             value={`$${Number(data.aov).toFixed(2)}`} sub="avg order value" color="var(--amber)" />
          <StatBox className="fade-up-6" label="CVR"             value={`${Number(data.cvr_pct).toFixed(2)}%`} sub="view → purchase"
            color={data.cvr_pct >= 3 ? 'var(--green)' : data.cvr_pct >= 1 ? 'var(--amber)' : 'var(--red)'} />
        </div>
      )}
    </div>
  );
}
