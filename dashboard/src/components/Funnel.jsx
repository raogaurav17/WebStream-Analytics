import { useApi } from '../hooks/useApi';
import { api } from '../api';
import { Card, CardHeader, Loading, ErrorState, WindowPicker } from './UI';
import { useState } from 'react';

const STAGE_COLORS = {
  view:        'var(--blue)',
  click:       'var(--amber)',
  add_to_cart: '#a78bfa',
  purchase:    'var(--green)',
};

const STAGE_LABELS = {
  view:        'VIEW',
  click:       'CLICK',
  add_to_cart: 'ADD TO CART',
  purchase:    'PURCHASE',
};

export default function Funnel() {
  const [window, setWindow] = useState('24h');
  const { data, loading, error } = useApi(() => api.funnel(window), [window]);

  const stages = data?.stages || [];
  const maxCount = stages[0]?.count || 1;

  return (
    <Card>
      <CardHeader label="◈ Conversion Funnel" accent>
        <WindowPicker value={window} onChange={setWindow} />
      </CardHeader>

      {error   && <ErrorState message={error} />}
      {loading && <Loading rows={4} />}

      {data && (
        <div>
          {stages.map((s, i) => {
            const pct = (s.count / maxCount) * 100;
            const color = STAGE_COLORS[s.stage];
            return (
              <div key={s.stage} style={{ marginBottom: i < stages.length - 1 ? 20 : 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-secondary)' }}>
                    {STAGE_LABELS[s.stage]}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 500, color }}>
                      {s.count.toLocaleString()}
                    </span>
                    {s.drop_off_pct != null && (
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                        ↑ {s.drop_off_pct}% from prev
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ height: 6, background: 'var(--bg-void)', borderRadius: 2, overflow: 'hidden', position: 'relative' }}>
                  <div style={{
                    height: '100%',
                    width: `${pct}%`,
                    background: color,
                    boxShadow: `0 0 8px ${color}`,
                    borderRadius: 2,
                    transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
                  }} />
                </div>

                {/* Drop arrow between stages */}
                {i < stages.length - 1 && (
                  <div style={{ textAlign: 'center', padding: '4px 0 0', color: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>
                    ▼
                  </div>
                )}
              </div>
            );
          })}

          <div style={{
            marginTop: 20, paddingTop: 16,
            borderTop: '1px solid var(--border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
              OVERALL CVR
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 600,
              color: data.overall_cvr_pct >= 3 ? 'var(--green)' : data.overall_cvr_pct >= 1 ? 'var(--amber)' : 'var(--red)',
            }}>
              {Number(data.overall_cvr_pct).toFixed(2)}%
            </span>
          </div>
        </div>
      )}
    </Card>
  );
}
