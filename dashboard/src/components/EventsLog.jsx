import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { api } from '../api';
import { Card, CardHeader, Loading, ErrorState, WindowPicker, Badge } from './UI';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const EVENT_COLORS = {
  view:        '#4d9fff',
  click:       '#f0a500',
  add_to_cart: '#a78bfa',
  purchase:    '#00d4aa',
};

export default function EventsLog() {
  const [window,    setWindow]    = useState('1h');
  const [offset,    setOffset]    = useState(0);
  const [eventType, setEventType] = useState('');
  const limit = 20;

  const { data, loading, error } = useApi(
    () => api.events({ window, limit, offset, ...(eventType ? { event_type: eventType } : {}) }),
    [window, offset, eventType]
  );

  const rows = data?.data || [];

  return (
    <Card>
      <CardHeader label="◈ Raw Events Log" accent>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select value={eventType} onChange={e => { setEventType(e.target.value); setOffset(0); }} style={{
            background: 'var(--bg-void)', border: '1px solid var(--border)',
            color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: 10,
            padding: '3px 8px', borderRadius: 'var(--radius)', cursor: 'pointer',
          }}>
            <option value="">all types</option>
            <option value="view">view</option>
            <option value="click">click</option>
            <option value="add_to_cart">add_to_cart</option>
            <option value="purchase">purchase</option>
          </select>
          <WindowPicker value={window} onChange={w => { setWindow(w); setOffset(0); }} />
        </div>
      </CardHeader>

      {error   && <ErrorState message={error} />}
      {loading && <Loading rows={5} />}

      {!loading && !error && (
        <>
          {/* Table header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '140px 90px 60px 70px 70px 60px 1fr',
            gap: 8, paddingBottom: 8, marginBottom: 4,
            borderBottom: '1px solid var(--border)',
          }}>
            {['TIMESTAMP','USER','TYPE','PRODUCT','CATEGORY','PRICE','EVENT ID'].map(h => (
              <span key={h} style={{ fontFamily: 'var(--font-mono)', fontSize: 8, letterSpacing: '0.12em', color: 'var(--text-muted)' }}>{h}</span>
            ))}
          </div>

          <div style={{ minHeight: 340 }}>
            {rows.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                NO EVENTS IN WINDOW
              </div>
            )}
            {rows.map((r, i) => (
              <div key={r.event_id} style={{
                display: 'grid',
                gridTemplateColumns: '140px 90px 60px 70px 70px 60px 1fr',
                gap: 8, alignItems: 'center', padding: '6px 0',
                borderBottom: i < rows.length - 1 ? '1px solid var(--border)' : 'none',
              }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                  {r.timestamp?.slice(0, 19).replace('T', ' ')}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.user_id}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: EVENT_COLORS[r.event_type] || 'var(--text-muted)' }}>
                  {r.event_type}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)' }}>
                  {r.product_id}
                </span>
                <Badge color={r.category === 'food' ? 'green' : r.category === 'electronics' ? 'blue' : 'amber'}>
                  {r.category}
                </Badge>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: r.event_type === 'purchase' ? 'var(--green)' : 'var(--text-muted)' }}>
                  {r.event_type === 'purchase' ? `$${r.price}` : '—'}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.event_id}
                </span>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
              rows {offset + 1}–{offset + rows.length}
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0} style={{
                background: 'var(--bg-raised)', border: '1px solid var(--border)',
                color: offset === 0 ? 'var(--text-muted)' : 'var(--text-primary)',
                borderRadius: 'var(--radius)', padding: '4px 8px', cursor: offset === 0 ? 'not-allowed' : 'pointer',
              }}>
                <ChevronLeft size={13} />
              </button>
              <button onClick={() => setOffset(offset + limit)} disabled={rows.length < limit} style={{
                background: 'var(--bg-raised)', border: '1px solid var(--border)',
                color: rows.length < limit ? 'var(--text-muted)' : 'var(--text-primary)',
                borderRadius: 'var(--radius)', padding: '4px 8px', cursor: rows.length < limit ? 'not-allowed' : 'pointer',
              }}>
                <ChevronRight size={13} />
              </button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
