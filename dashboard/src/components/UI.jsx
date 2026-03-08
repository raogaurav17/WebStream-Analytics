import { Loader2, AlertTriangle } from 'lucide-react';

export function Card({ children, className = '', style = {} }) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      padding: '20px',
      ...style,
    }} className={className}>
      {children}
    </div>
  );
}

export function CardHeader({ label, accent = false, children }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        color: accent ? 'var(--text-amber)' : 'var(--text-secondary)',
      }}>
        {label}
      </span>
      {children}
    </div>
  );
}

export function Skeleton({ height = 20, width = '100%', style = {} }) {
  return (
    <div style={{
      height, width,
      background: 'linear-gradient(90deg, var(--bg-raised) 25%, var(--bg-hover) 50%, var(--bg-raised) 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.5s infinite',
      borderRadius: 'var(--radius)',
      ...style,
    }} />
  );
}

export function Loading({ rows = 3 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 4 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} height={16} width={`${80 - i * 10}%`} />
      ))}
    </div>
  );
}

export function ErrorState({ message }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 11,
      padding: '12px 0',
    }}>
      <AlertTriangle size={14} />
      <span>{message}</span>
    </div>
  );
}

export function StatBox({ label, value, sub, color = 'var(--text-primary)', className = '' }) {
  return (
    <div className={className} style={{
      background: 'var(--bg-raised)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      padding: '16px 20px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        color: 'var(--text-muted)',
        marginBottom: 8,
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 26,
        fontWeight: 500,
        color,
        lineHeight: 1,
        marginBottom: sub ? 6 : 0,
        animation: 'counter 0.5s ease both',
      }}>{value}</div>
      {sub && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  );
}

export function WindowPicker({ value, onChange }) {
  const opts = ['1h', '6h', '24h', '7d', '30d'];
  return (
    <div style={{ display: 'flex', gap: 2 }}>
      {opts.map(o => (
        <button key={o} onClick={() => onChange(o)} style={{
          background: value === o ? 'var(--amber-glow)' : 'transparent',
          border: `1px solid ${value === o ? 'var(--amber-dim)' : 'var(--border)'}`,
          borderRadius: 'var(--radius)',
          color: value === o ? 'var(--amber)' : 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          padding: '3px 8px',
          cursor: 'pointer',
          transition: 'all 0.15s',
        }}>{o}</button>
      ))}
    </div>
  );
}

export function Badge({ children, color = 'amber' }) {
  const colors = {
    amber: { bg: 'var(--amber-glow)', border: 'var(--amber-dim)', text: 'var(--amber)' },
    green: { bg: 'var(--green-glow)', border: 'var(--green-dim)', text: 'var(--green)' },
    red:   { bg: 'rgba(255,77,106,0.1)', border: 'var(--red-dim)', text: 'var(--red)' },
    blue:  { bg: 'rgba(77,159,255,0.1)', border: 'var(--blue-dim)', text: 'var(--blue)' },
  };
  const c = colors[color] || colors.amber;
  return (
    <span style={{
      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
      fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.1em',
      textTransform: 'uppercase', padding: '2px 7px', borderRadius: 'var(--radius)',
    }}>{children}</span>
  );
}

export function LiveDot() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: 'var(--green)',
        boxShadow: '0 0 6px var(--green)',
        display: 'inline-block',
        animation: 'pulse-dot 2s infinite',
      }} />
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-green)', letterSpacing: '0.1em' }}>LIVE</span>
    </span>
  );
}

export function Divider() {
  return <div style={{ height: 1, background: 'var(--border)', margin: '16px 0' }} />;
}
