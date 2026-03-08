const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  health:        ()              => get('/health'),
  overview:      (w = '24h')    => get(`/metrics/overview?window=${w}`),
  funnel:        (w = '24h', c) => get(`/metrics/funnel?window=${w}${c ? `&category=${c}` : ''}`),
  timeseries:    (w = '24h', b = 'hour') => get(`/metrics/timeseries?window=${w}&bucket=${b}`),
  topProducts:   (w = '24h', by = 'revenue', n = 10) => get(`/metrics/top-products?window=${w}&by=${by}&limit=${n}`),
  topCategories: (w = '24h')    => get(`/metrics/top-categories?window=${w}`),
  revenue:       (w = '24h', b = 'hour') => get(`/metrics/revenue?window=${w}&bucket=${b}`),
  realtime:      ()              => get('/metrics/realtime'),
  userJourney:   (uid, w = '7d') => get(`/metrics/users/${uid}?window=${w}`),
  events:        (params = {})  => {
    const q = new URLSearchParams(params).toString();
    return get(`/events${q ? `?${q}` : ''}`);
  },
};
