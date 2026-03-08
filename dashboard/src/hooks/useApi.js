import { useState, useEffect, useCallback, useRef } from 'react';

export function useApi(fetcher, deps = [], interval = null) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const mountedRef = useRef(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetcher();
      if (mountedRef.current) setData(result);
    } catch (e) {
      if (mountedRef.current) setError(e.message);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    mountedRef.current = true;
    load();
    if (interval) {
      const id = setInterval(load, interval);
      return () => { clearInterval(id); mountedRef.current = false; };
    }
    return () => { mountedRef.current = false; };
  }, [load, interval]);

  return { data, loading, error, refetch: load };
}
