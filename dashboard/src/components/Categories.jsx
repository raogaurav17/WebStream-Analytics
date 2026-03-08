import { useApi } from '../hooks/useApi';
import { api } from '../api';
import { Card, CardHeader, Loading, ErrorState, WindowPicker } from './UI';
import { useState } from 'react';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts';

const CAT_COLORS = {
  electronics: '#4d9fff',
  clothing:    '#f0a500',
  furniture:   '#a78bfa',
  food:        '#00d4aa',
  books:       '#fb923c',
  sports:      '#f472b6',
};

export default function Categories() {
  const [window, setWindow] = useState('24h');
  const [view,   setView]   = useState('table'); // 'table' | 'radar'
  const { data, loading, error } = useApi(() => api.topCategories(window), [window]);

  const rows = data?.data || [];
  const maxRev = rows.length ? Math.max(...rows.map(r => r.revenue)) : 1;

  // Normalise for radar
  const radarData = rows.map(r => ({
    category: r.category,
    views:     r.views,
    purchases: r.purchases,
    cvr:       Number(r.cvr_pct),
    revenue:   Number(r.revenue),
    aov:       Number(r.aov),
  }));

  return (
    <Card>
      <CardHeader label="◈ Categories" accent>
        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{ display: 'flex', gap: 2 }}>
            {['table','radar'].map(v => (
              <button key={v} onClick={() => setView(v)} style={{
                background: view === v ? 'rgba(240,165,0,0.1)' : 'transparent',
                border: `1px solid ${view === v ? 'var(--amber-dim)' : 'var(--border)'}`,
                color: view === v ? 'var(--amber)' : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)', fontSize: 10,
                padding: '3px 8px', borderRadius: 'var(--radius)', cursor: 'pointer',
              }}>{v}</button>
            ))}
          </div>
          <WindowPicker value={window} onChange={setWindow} />
        </div>
      </CardHeader>

      {error   && <ErrorState message={error} />}
      {loading && <Loading rows={6} />}

      {!loading && !error && view === 'table' && (
        <div>
          {rows.map((r, i) => {
            const color = CAT_COLORS[r.category] || 'var(--amber)';
            const barW  = (r.revenue / maxRev) * 100;
            return (
              <div key={r.category} style={{
                display: 'grid', gridTemplateColumns: '90px 1fr 50px 60px 60px',
                gap: 8, alignItems: 'center', padding: '8px 0',
                borderBottom: i < rows.length - 1 ? '1px solid var(--border)' : 'none',
              }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 500,
                  color, textTransform: 'uppercase', letterSpacing: '0.05em',
                }}>{r.category}</span>

                <div style={{ height: 4, background: 'var(--bg-void)', borderRadius: 2 }}>
                  <div style={{
                    height: '100%', width: `${barW}%`, background: color,
                    borderRadius: 2, boxShadow: `0 0 6px ${color}44`,
                    transition: 'width 0.7s ease',
                  }} />
                </div>

                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', textAlign: 'right' }}>
                  {r.views.toLocaleString()}v
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--green)', textAlign: 'right' }}>
                  ${Number(r.revenue).toFixed(0)}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, textAlign: 'right',
                  color: r.cvr_pct >= 3 ? 'var(--green)' : r.cvr_pct >= 1 ? 'var(--amber)' : 'var(--red)' }}>
                  {Number(r.cvr_pct).toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      )}

      {!loading && !error && view === 'radar' && radarData.length > 0 && (
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={radarData}>
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis dataKey="category"
              tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontFamily: 'var(--font-mono)' }} />
            <Radar name="CVR %" dataKey="cvr" stroke="var(--amber)" fill="var(--amber)" fillOpacity={0.15} strokeWidth={1.5} />
            <Radar name="Purchases" dataKey="purchases" stroke="var(--green)" fill="var(--green)" fillOpacity={0.10} strokeWidth={1.5} />
            <Tooltip contentStyle={{ background: 'var(--bg-raised)', border: '1px solid var(--border-mid)', fontFamily: 'var(--font-mono)', fontSize: 11 }} />
          </RadarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
