import { useCallback, useEffect, useRef, useState } from "react";
import { cacheGet, cacheSet } from "../services/cache.js";

/**
 * Generic data-fetching hook: runs an async fetcher, tracks
 * loading/error/data, supports short-TTL caching, cancellation on unmount,
 * and manual refetch. The whole workspace reads data through this hook, so
 * every page gets consistent loading, error, and retry behaviour for free.
 *
 * @param {Function} fetcher  async () => data
 * @param {Array}    deps     re-run when these change
 * @param {Object}   options  { cacheKey, ttl, enabled }
 */
export function useApi(fetcher, deps = [], options = {}) {
  const { cacheKey, ttl, enabled = true } = options;
  const [data, setData] = useState(() => (cacheKey ? cacheGet(cacheKey) : undefined));
  const [loading, setLoading] = useState(enabled && data === undefined);
  const [error, setError] = useState(null);
  const mounted = useRef(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const run = useCallback(
    async ({ force = false } = {}) => {
      if (!enabled) return;
      if (!force && cacheKey) {
        const cached = cacheGet(cacheKey);
        if (cached !== undefined) {
          setData(cached);
          setLoading(false);
          return;
        }
      }
      setLoading(true);
      setError(null);
      try {
        const result = await fetcherRef.current();
        if (!mounted.current) return;
        setData(result);
        if (cacheKey) cacheSet(cacheKey, result, ttl);
      } catch (err) {
        if (!mounted.current) return;
        setError(err);
      } finally {
        if (mounted.current) setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cacheKey, ttl, enabled]
  );

  useEffect(() => {
    mounted.current = true;
    run();
    return () => {
      mounted.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled]);

  const refetch = useCallback(() => run({ force: true }), [run]);
  return { data, loading, error, refetch };
}
