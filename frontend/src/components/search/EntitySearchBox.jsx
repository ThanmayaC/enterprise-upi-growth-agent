import { useEffect, useRef, useState } from "react";
import Icon from "../common/Icon.jsx";
import { Spinner } from "../common/states.jsx";
import { useDebounce } from "../../hooks/useDebounce.js";

/**
 * Reusable inline entity search with a results dropdown. Used by the
 * intelligence pages to pick a merchant/customer to drill into.
 *
 * fetcher(term) -> Promise<items[]>; each item exposes idKey/labelKey/subKey.
 */
export default function EntitySearchBox({
  fetcher,
  idKey,
  labelKey,
  subKey,
  onSelect,
  placeholder = "Search…",
}) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const debounced = useDebounce(query, 300);
  const ref = useRef(null);

  useEffect(() => {
    const term = debounced.trim();
    if (term.length < 1) {
      setItems([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.resolve(fetcher(term))
      .then((res) => !cancelled && setItems(res || []))
      .catch(() => !cancelled && setItems([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  useEffect(() => {
    const onClick = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const pick = (item) => {
    setOpen(false);
    setQuery("");
    onSelect(item);
  };

  return (
    <div ref={ref} className="relative w-full max-w-md">
      <Icon name="search" size={16} className="absolute left-3 top-2.5 text-ink-400" />
      <input
        className="input pl-9"
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
      />
      {open && debounced.trim().length >= 1 && (
        <div className="absolute left-0 right-0 z-30 mt-2 max-h-80 overflow-y-auto rounded-xl border border-ink-200 bg-white p-1.5 shadow-panel">
          {loading ? (
            <div className="flex items-center gap-2 px-3 py-3 text-sm text-ink-400">
              <Spinner size={15} /> Searching…
            </div>
          ) : items.length === 0 ? (
            <div className="px-3 py-4 text-center text-sm text-ink-400">No matches</div>
          ) : (
            items.map((item) => (
              <button
                key={item[idKey]}
                onClick={() => pick(item)}
                className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm text-ink-700 hover:bg-brand-50"
              >
                <span className="min-w-0 flex-1 truncate font-medium">{item[labelKey]}</span>
                <span className="truncate text-xs text-ink-400">{subKey ? item[subKey] : item[idKey]}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
