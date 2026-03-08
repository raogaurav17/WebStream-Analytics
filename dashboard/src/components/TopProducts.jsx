import { useApi } from '../hooks/useApi';
import { api } from '../api';
import { Card, CardHeader, Loading, ErrorState, WindowPicker, Badge } from './UI';
import { useState } from 'react';

function Bar({ value, max, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 3, background: 'var(--bg-void)', borderRadius: 2 }}>
        <div style={{
          height: '100%', width: `${Math.min(100, (value / max) * 100)}%`,
          background: color, borderRadius: 2,
          transition: 'width 0.6s ease',
        }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)', minWidth: 40, textAlign: 'right' }}>
        {value.toLocaleString()}
      </span>
    </div>
  );
}

export default function TopProducts() {
  const [window, setWindow]   = useState('24h');
  const [by,     setBy]       = useState('revenue');
  const { data, loading, error } = useApi(() => api.topProducts(window, by, 8), [window, by]);

  const rows   = data?.data || [];
  const maxVal = rows.length ? Math.max(...rows.map(r => r[by] || 0)) : 1;

  const CATEGORY_COLORS = {
    electronics: 'var(--blue)',
    clothing:    'var(--amber)',
    furniture:   '#a78bfa',
    food:        'var(--green)',
    books:       '#fb923c',
    sports:      '#f472b6',
  };

  return (
    <Card>
      <CardHeader label="◈ Top Products" accent>
        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{ display: 'flex', gap: 2 }}>
            {['revenue','views','purchases'].map(b => (
              <button key={b} onClick={() => setBy(b)} style={{
                background: by === b ? 'rgba(240,165,0,0.1)' : 'transparent',
                border: `1px solid ${by === b ? 'var(--amber-dim)' : 'var(--border)'}`,
                color: by === b ? 'var(--amber)' : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)', fontSize: 10,
                padding: '3px 8px', borderRadius: 'var(--radius)', cursor: 'pointer',
              }}>{b}</button>
            ))}
          </div>
          <WindowPicker value={window} onChange={setWindow} />
        </div>
      </CardHeader>

      {error   && <ErrorState message={error} />}
      {loading && <Loading rows={8} />}

      {!loading && !error && (
        <div>
          {/* Column headers */}
          <div style={{
            display: 'grid', gridTemplateColumns: '80px 1fr 60px 60px 60px',
            gap: 8, marginBottom: 10, paddingBottom: 8,
            borderBottom: '1px solid var(--border)',
          }}>
            {['PRODUCT', 'METRIC', 'VIEWS', 'ORDERS', 'CVR'].map(h => (
              <span key={h} style={{ fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '0.12em', color: 'var(--text-muted)' }}>{h}</span>
            ))}
          </div>

          {rows.map((r, i) => (
            <div key={r.product_id} style={{
              display: 'grid', gridTemplateColumns: '80px 1fr 60px 60px 60px',
              gap: 8, alignItems: 'center', padding: '7px 0',
              borderBottom: i < rows.length - 1 ? '1px solid var(--border)' : 'none',
            }}>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-primary)' }}>{r.product_id}</div>
                <Badge color={r.category === 'food' ? 'green' : r.category === 'electronics' ? 'blue' : 'amber'}>
                  {r.category}
                </Badge>
              </div>

              <Bar
                value={by === 'revenue' ? Number(r.revenue) : r[by]}
                max={maxVal}
                color={CATEGORY_COLORS[r.category] || 'var(--amber)'}
              />

              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)', textAlign: 'right' }}>
                {r.views.toLocaleString()}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--green)', textAlign: 'right' }}>
                {r.purchases.toLocaleString()}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, textAlign: 'right',
                color: r.cvr_pct >= 3 ? 'var(--green)' : r.cvr_pct >= 1 ? 'var(--amber)' : 'var(--red)' }}>
                {Number(r.cvr_pct).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
