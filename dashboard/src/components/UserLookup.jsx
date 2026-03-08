import { useState } from 'react';
import { api } from '../api';
import { Card, CardHeader, Badge, Divider, ErrorState } from './UI';
import { Search, User } from 'lucide-react';

const EVENT_COLORS = {
  view:        '#4d9fff',
  click:       '#f0a500',
  add_to_cart: '#a78bfa',
  purchase:    '#00d4aa',
};

export default function UserLookup() {
  const [input,   setInput]   = useState('');
  const [userId,  setUserId]  = useState(null);
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  async function lookup() {
    const uid = input.trim();
    if (!uid) return;
    setUserId(uid);
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const result = await api.userJourney(uid, '7d');
      setData(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader label="◈ User Journey Lookup" accent />

      {/* Search bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && lookup()}
            placeholder="e.g. u_42"
            style={{
              width: '100%', padding: '8px 12px 8px 30px',
              background: 'var(--bg-void)', border: '1px solid var(--border-mid)',
              borderRadius: 'var(--radius-md)', color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)', fontSize: 12, outline: 'none',
            }}
          />
        </div>
        <button onClick={lookup} style={{
          background: 'var(--amber-glow)', border: '1px solid var(--amber-dim)',
          color: 'var(--amber)', fontFamily: 'var(--font-mono)', fontSize: 10,
          padding: '8px 16px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
          letterSpacing: '0.1em',
        }}>LOOKUP</button>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
          QUERYING...
        </div>
      )}
      {error && <ErrorState message={error.includes('404') ? `No events found for "${userId}"` : error} />}

      {data && (
        <div>
          {/* User summary */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: 'var(--amber-glow)', border: '1px solid var(--amber-dim)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <User size={16} color="var(--amber)" />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                {data.user_id}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                {data.summary.first_seen?.slice(0,16)} → {data.summary.last_seen?.slice(0,16)}
              </div>
            </div>
          </div>

          {/* Stats grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 16 }}>
            {[
              { label: 'EVENTS', value: data.summary.total_events, color: 'var(--text-primary)' },
              { label: 'PURCHASES', value: data.summary.purchases, color: 'var(--green)' },
              { label: 'SPENT', value: `$${Number(data.summary.total_spent).toFixed(2)}`, color: 'var(--amber)' },
              { label: 'PRODUCTS', value: data.summary.unique_products_viewed, color: 'var(--blue)' },
            ].map(s => (
              <div key={s.label} style={{ background: 'var(--bg-raised)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '10px 12px' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 4 }}>{s.label}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 500, color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>

          <Divider />

          {/* Event timeline */}
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 10 }}>
            EVENT TIMELINE (last 200)
          </div>
          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
            {data.events.map((e, i) => (
              <div key={e.event_id} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '5px 0',
                borderBottom: i < data.events.length - 1 ? '1px solid var(--border)' : 'none',
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                  background: EVENT_COLORS[e.event_type] || 'var(--text-muted)',
                  boxShadow: `0 0 4px ${EVENT_COLORS[e.event_type] || 'transparent'}`,
                }} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', width: 90, flexShrink: 0 }}>
                  {e.timestamp?.slice(11, 19)}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: EVENT_COLORS[e.event_type], width: 80, flexShrink: 0 }}>
                  {e.event_type}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)' }}>
                  {e.product_id}
                </span>
                <Badge color={e.category === 'food' ? 'green' : e.category === 'electronics' ? 'blue' : 'amber'}>
                  {e.category}
                </Badge>
                {e.event_type === 'purchase' && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--green)', marginLeft: 'auto' }}>
                    ${e.price}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
