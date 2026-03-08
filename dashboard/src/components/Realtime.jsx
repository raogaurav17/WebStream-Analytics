import { useApi } from '../hooks/useApi';
import { api } from '../api';
import { Card, CardHeader, Loading, ErrorState, LiveDot } from './UI';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function Realtime() {
  // Poll every 5 seconds
  const { data, loading, error } = useApi(() => api.realtime(), [], 5000);

  const buckets = (data?.buckets || []).map(b => ({
    ...b,
    label: new Date(b.bucket).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' }),
  }));

  return (
    <Card>
      <CardHeader label="◈ Live Feed — 2min window" accent>
        <LiveDot />
      </CardHeader>

      {data && (
        <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em' }}>EVENTS/SEC</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 600, color: 'var(--green)',
              textShadow: '0 0 12px var(--green)' }}>
              {data.events_per_sec}
            </div>
          </div>
          {buckets.length > 0 && (
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em' }}>LAST MIN TOTAL</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 600, color: 'var(--amber)' }}>
                {buckets[buckets.length - 1]?.total?.toLocaleString() || 0}
              </div>
            </div>
          )}
        </div>
      )}

      {error   && <ErrorState message={error} />}
      {loading && !data && <Loading rows={3} />}

      {buckets.length > 0 && (
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={buckets} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              tickLine={false} axisLine={false} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-raised)', border: '1px solid var(--border-mid)', fontFamily: 'var(--font-mono)', fontSize: 11 }} />
            <Bar dataKey="views"     fill="#4d9fff" opacity={0.8} radius={[2,2,0,0]} stackId="a" />
            <Bar dataKey="clicks"    fill="#f0a500" opacity={0.8} radius={[0,0,0,0]} stackId="a" />
            <Bar dataKey="carts"     fill="#a78bfa" opacity={0.8} stackId="a" />
            <Bar dataKey="purchases" fill="#00d4aa" opacity={0.9} radius={[2,2,0,0]} stackId="a" />
          </BarChart>
        </ResponsiveContainer>
      )}

      {!loading && buckets.length === 0 && (
        <div style={{ textAlign: 'center', padding: 30, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
          WAITING FOR EVENTS...
        </div>
      )}
    </Card>
  );
}
