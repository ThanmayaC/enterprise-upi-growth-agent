import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Icon from "../common/Icon.jsx";
import { Spinner } from "../common/states.jsx";
import { useDebounce } from "../../hooks/useDebounce.js";
import { searchApi } from "../../api/endpoints.js";
import { cn } from "../../utils/cn.js";

// Unified enterprise search across the four Phase 9 search endpoints. Results
// are grouped by entity; selecting one deep-links to its intelligence page.
const GROUPS = [
  { key: "merchants", label: "Merchants", icon: "store", fetch: searchApi.merchants,
    idKey: "merchant_id", labelKey: "merchant_name", to: (r) => `/merchants?id=${encodeURIComponent(r.merchant_id)}` },
  { key: "customers", label: "Customers", icon: "users", fetch: searchApi.customers,
    idKey: "customer_id", labelKey: "customer_name", to: (r) => `/customers?id=${encodeURIComponent(r.customer_id)}` },
  { key: "banks", label: "Banks", icon: "bank", fetch: searchApi.banks,
    idKey: "bank_id", labelKey: "bank_name", to: (r) => `/banks?name=${encodeURIComponent(r.bank_name)}` },
  { key: "psps", label: "PSPs", icon: "app", fetch: searchApi.psps,
    idKey: "psp_id", labelKey: "psp_name", to: (r) => `/psps?name=${encodeURIComponent(r.psp_name)}` },
];

export default function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(false);
  const debounced = useDebounce(query, 300);
  const containerRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const term = debounced.trim();
    if (term.length < 1) {
      setResults({});
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all(
      GROUPS.map((g) =>
        g.fetch({ q: term, limit: 5 }).then((page) => page.items).catch(() => [])
      )
    ).then((lists) => {
      if (cancelled) return;
      const next = {};
      GROUPS.forEach((g, i) => (next[g.key] = lists[i]));
      setResults(next);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [debounced]);

  useEffect(() => {
    const onClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        containerRef.current?.querySelector("input")?.focus();
        setOpen(true);
      }
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const select = (group, row) => {
    setOpen(false);
    setQuery("");
    navigate(group.to(row));
  };

  const totalResults = GROUPS.reduce((n, g) => n + (results[g.key]?.length || 0), 0);
  const showPanel = open && debounced.trim().length >= 1;

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <Icon name="search" size={16} className="absolute left-3 top-2.5 text-ink-400" />
      <input
        className="input pl-9 pr-16"
        placeholder="Search merchants, customers, banks, PSPs…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        aria-label="Global search"
      />
      <kbd className="absolute right-3 top-2 hidden rounded border border-ink-200 bg-ink-50 px-1.5 py-0.5 text-[10px] font-medium text-ink-400 sm:block">
        ⌘K
      </kbd>

      {showPanel && (
        <div className="absolute left-0 right-0 z-40 mt-2 max-h-[26rem] overflow-y-auto rounded-xl border border-ink-200 bg-white p-2 shadow-panel">
          {loading && (
            <div className="flex items-center gap-2 px-3 py-4 text-sm text-ink-400">
              <Spinner size={16} /> Searching…
            </div>
          )}
          {!loading && totalResults === 0 && (
            <div className="px-3 py-6 text-center text-sm text-ink-400">
              No matches for “{debounced}”.
            </div>
          )}
          {!loading &&
            GROUPS.map((g) => {
              const items = results[g.key] || [];
              if (items.length === 0) return null;
              return (
                <div key={g.key} className="mb-1">
                  <p className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                    {g.label}
                  </p>
                  {items.map((row) => (
                    <button
                      key={row[g.idKey]}
                      onClick={() => select(g, row)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm",
                        "text-ink-700 hover:bg-brand-50"
                      )}
                    >
                      <span className="flex h-7 w-7 items-center justify-center rounded-md bg-ink-100 text-ink-500">
                        <Icon name={g.icon} size={14} />
                      </span>
                      <span className="min-w-0 flex-1 truncate font-medium">{row[g.labelKey]}</span>
                      <span className="truncate text-xs text-ink-400">{row[g.idKey]}</span>
                    </button>
                  ))}
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
