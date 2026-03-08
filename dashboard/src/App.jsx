import { useState, useEffect } from 'react';
import { api } from './api';

import Overview    from './components/Overview';
import Funnel      from './components/Funnel';
import Timeseries  from './components/Timeseries';
import Revenue     from './components/Revenue';
import TopProducts from './components/TopProducts';
import Categories  from './components/Categories';
import Realtime    from './components/Realtime';
import UserLookup  from './components/UserLookup';
import EventsLog   from './components/EventsLog';

const NAV = [
  { id: 'overview',  label: 'Overview'   },
  { id: 'realtime',  label: 'Live'       },
  { id: 'funnel',    label: 'Funnel'     },
  { id: 'revenue',   label: 'Revenue'    },
  { id: 'products',  label: 'Products'   },
  { id: 'events',    label: 'Events'     },
  { id: 'users',     label: 'Users'      },
];

export default function App() {
  const [page,   setPage]   = useState('overview');
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health()
      .then(d => setHealth({ ok: true, total: d.total_events }))
      .catch(() => setHealth({ ok: false }));
  }, []);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-void)' }}>

      {/* Top bar */}
      <header style={{
        height: 48,
        background: 'var(--bg-base)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center',
        padding: '0 24px',
        position: 'sticky', top: 0, zIndex: 100,
        gap: 20,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginRight: 12 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color: 'var(--amber)', letterSpacing: '0.04em' }}>
            ◈ STREAM
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.12em' }}>
            ANALYTICS
          </span>
        </div>

        {/* Nav */}
        <nav style={{ display: 'flex', gap: 2, flex: 1 }}>
          {NAV.map(n => (
            <button key={n.id} onClick={() => setPage(n.id)} style={{
              background: page === n.id ? 'var(--amber-glow)' : 'transparent',
              border: `1px solid ${page === n.id ? 'var(--amber-dim)' : 'transparent'}`,
              color: page === n.id ? 'var(--amber)' : 'var(--text-muted)',
              fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.1em',
              padding: '4px 12px', borderRadius: 'var(--radius)',
              cursor: 'pointer', transition: 'all 0.15s',
            }}>
              {n.label.toUpperCase()}
            </button>
          ))}
        </nav>

        {/* Status pill */}
        {health && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '4px 10px',
            background: health.ok ? 'var(--green-glow)' : 'rgba(255,77,106,0.08)',
            border: `1px solid ${health.ok ? 'var(--green-dim)' : 'var(--red-dim)'}`,
            borderRadius: 'var(--radius)',
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: health.ok ? 'var(--green)' : 'var(--red)',
              boxShadow: `0 0 6px ${health.ok ? 'var(--green)' : 'var(--red)'}`,
              animation: health.ok ? 'pulse-dot 2s infinite' : 'none',
            }} />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: health.ok ? 'var(--green)' : 'var(--red)', letterSpacing: '0.08em' }}>
              {health.ok ? `CH CONNECTED · ${health.total?.toLocaleString()} events` : 'CH OFFLINE'}
            </span>
          </div>
        )}
      </header>

      {/* Page content */}
      <main style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>

        {page === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <Overview />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <Timeseries />
              <Funnel />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <Revenue />
              <Realtime />
            </div>
          </div>
        )}

        {page === 'realtime' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <Realtime />
            <Timeseries />
          </div>
        )}

        {page === 'funnel' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <Funnel />
            <Categories />
          </div>
        )}

        {page === 'revenue' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <Revenue />
            <TopProducts />
          </div>
        )}

        {page === 'products' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <TopProducts />
            <Categories />
          </div>
        )}

        {page === 'events' && <EventsLog />}

        {page === 'users' && <UserLookup />}
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '12px 24px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginTop: 40,
      }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
          ◈ STREAM ANALYTICS · KAFKA → CLICKHOUSE PIPELINE
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>
          FastAPI · ClickHouse · React · Recharts
        </span>
      </footer>

    </div>
  );
}
