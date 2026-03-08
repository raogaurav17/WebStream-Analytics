import { useApi } from '../hooks/useApi';
import { api } from '../api';
import { Card, CardHeader, Loading, ErrorState, WindowPicker } from './UI';
import { useState, useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';

const EVENT_COLORS = {
  view:        '#4d9fff',
  click:       '#f0a500',
  add_to_cart: '#a78bfa',
  purchase:    '#00d4aa',
};

function formatBucket(ts, bucket) {
  const d = new Date(ts);
  if (bucket === 'day')    return d.toLocaleDateString('en', { month: 'short', day: 'numeric' });
  if (bucket === 'minute') return d.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' });
  return d.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' });
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bg-raised)', border: '1px solid var(--border-mid)',
      borderRadius: 4, padding: '10px 14px',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 8 }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: p.color, marginBottom: 2 }}>
          {p.dataKey.toUpperCase()}: {p.value.toLocaleString()}
        </div>
      ))}
    </div>
  );
};

export default function Timeseries() {
  const [window, setWindow] = useState('24h');
  const [bucket, setBucket] = useState('hour');

  const { data, loading, error } = useApi(() => api.timeseries(window, bucket), [window, bucket]);

  // Pivot: [{bucket, view, click, add_to_cart, purchase}]
  const chartData = useMemo(() => {
    if (!data?.data) return [];
    const map = {};
    for (const row of data.data) {
      const b = formatBucket(row.bucket, bucket);
      if (!map[b]) map[b] = { bucket: b, view: 0, click: 0, add_to_cart: 0, purchase: 0 };
      map[b][row.event_type] = (map[b][row.event_type] || 0) + row.cnt;
    }
    return Object.values(map);
  }, [data, bucket]);

  return (
    <Card>
      <CardHeader label="◈ Event Volume Over Time" accent>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 2 }}>
            {['minute', 'hour', 'day'].map(b => (
              <button key={b} onClick={() => setBucket(b)} style={{
                background: bucket === b ? 'rgba(240,165,0,0.1)' : 'transparent',
                border: `1px solid ${bucket === b ? 'var(--amber-dim)' : 'var(--border)'}`,
                color: bucket === b ? 'var(--amber)' : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)', fontSize: 10,
                padding: '3px 8px', borderRadius: 'var(--radius)', cursor: 'pointer',
              }}>{b}</button>
            ))}
          </div>
          <WindowPicker value={window} onChange={setWindow} />
        </div>
      </CardHeader>

      {error   && <ErrorState message={error} />}
      {loading && <Loading rows={5} />}

      {!loading && !error && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
            <defs>
              {Object.entries(EVENT_COLORS).map(([k, c]) => (
                <linearGradient key={k} id={`grad-${k}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={c} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={c} stopOpacity={0.0}  />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="bucket" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.08em' }} />
            {Object.entries(EVENT_COLORS).map(([k, c]) => (
              <Area key={k} type="monotone" dataKey={k} stroke={c} strokeWidth={1.5}
                fill={`url(#grad-${k})`} dot={false} activeDot={{ r: 3, fill: c }} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      )}
      {!loading && !error && chartData.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
          NO DATA FOR SELECTED WINDOW
        </div>
      )}
    </Card>
  );
}
