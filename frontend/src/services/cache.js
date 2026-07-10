// A tiny in-memory TTL cache shared by the data hooks. Some platform calls
// (executive composition, KPI snapshots) are deliberately expensive on the
// backend; caching their results for a short window avoids re-hitting them
// on every navigation without introducing a heavyweight data library.

const store = new Map();
const DEFAULT_TTL_MS = 60_000;

export function cacheGet(key) {
  const entry = store.get(key);
  if (!entry) return undefined;
  if (Date.now() > entry.expires) {
    store.delete(key);
    return undefined;
  }
  return entry.value;
}

export function cacheSet(key, value, ttl = DEFAULT_TTL_MS) {
  store.set(key, { value, expires: Date.now() + ttl });
}

export function cacheClear() {
  store.clear();
}
