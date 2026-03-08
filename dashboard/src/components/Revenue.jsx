import { useApi } from '../hooks/useApi';
import { api } from '../api';
import { Card, CardHeader, Loading, ErrorState, WindowPicker } from './UI';
import { useState } from 'react';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts';

function formatBucket(ts) {
  const d = new Date(ts);
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
          {p.dataKey === 'revenue' ? `$${Number(p.value).toFixed(2)}` : p.value}
          <span style={{ color: 'var(--text-muted)', marginLeft: 4 }}>{p.dataKey.toUpperCase()}</span>
        </div>
      ))}
    </div>
  );
};

export default function Revenue() {
  const [window, setWindow] = useState('24h');
  const [bucket, setBucket] = useState('hour');
  const { data, loading, error } = useApi(() => api.revenue(window, bucket), [window, bucket]);

  const chartData = (data?.timeseries || []).map(r => ({
    ...r,
    bucket: formatBucket(r.bucket),
    revenue: Number(r.revenue),
    aov:     Number(r.aov),
  }));

  return (
    <Card>
      <CardHeader label="◈ Revenue & Orders" accent>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 2 }}>
            {['minute','hour','day'].map(b => (
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

      {/* Summary row */}
      {data && (
        <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 2 }}>TOTAL REVENUE</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 500, color: 'var(--amber)' }}>
              ${Number(data.total_revenue).toLocaleString('en', { minimumFractionDigits: 2 })}
            </div>
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 2 }}>ORDERS</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 500, color: 'var(--blue)' }}>
              {data.total_orders.toLocaleString()}
            </div>
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 2 }}>AOV</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 500, color: 'var(--green)' }}>
              ${Number(data.overall_aov).toFixed(2)}
            </div>
          </div>
        </div>
      )}

      {error   && <ErrorState message={error} />}
      {loading && <Loading rows={4} />}

      {!loading && !error && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="bucket" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              tickLine={false} axisLine={false} interval="preserveStartEnd" />
            <YAxis yAxisId="rev" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
            <YAxis yAxisId="ord" orientation="right" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Bar yAxisId="rev" dataKey="revenue" fill="var(--amber)" opacity={0.7} radius={[2,2,0,0]} />
            <Line yAxisId="ord" type="monotone" dataKey="orders" stroke="var(--blue)"
              strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
