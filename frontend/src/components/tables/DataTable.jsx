import { useMemo, useState } from "react";
import Icon from "../common/Icon.jsx";
import { LoadingBlock, EmptyState, ErrorState } from "../common/states.jsx";
import { cn } from "../../utils/cn.js";

/**
 * Reusable, self-contained data table: client-side sorting, optional search,
 * pagination, a sticky header, and first-class loading / empty / error
 * states. Columns declare how to read and render each cell, so pages never
 * re-implement table plumbing.
 *
 * columns: [{ key, header, render?(row), sortable?, align?, value?(row) }]
 */
export default function DataTable({
  columns,
  rows,
  loading = false,
  error = null,
  onRetry,
  searchable = false,
  searchPlaceholder = "Filter…",
  pageSize = 10,
  initialSort,
  getRowKey = (_, i) => i,
  onRowClick,
  emptyText = "No records found",
  dense = false,
}) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState(initialSort || null);
  const [page, setPage] = useState(0);

  const readValue = (row, col) =>
    col.value ? col.value(row) : row[col.key];

  const filtered = useMemo(() => {
    if (!searchable || !query.trim()) return rows || [];
    const q = query.toLowerCase();
    return (rows || []).filter((row) =>
      columns.some((c) => String(readValue(row, c) ?? "").toLowerCase().includes(q))
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, query, columns, searchable]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return filtered;
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const va = readValue(a, col);
      const vb = readValue(b, col);
      if (va === vb) return 0;
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb)) * dir;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtered, sort, columns]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = sorted.slice(safePage * pageSize, safePage * pageSize + pageSize);

  const toggleSort = (col) => {
    if (!col.sortable) return;
    setSort((prev) =>
      prev?.key === col.key
        ? { key: col.key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key: col.key, dir: "desc" }
    );
    setPage(0);
  };

  if (error) return <ErrorState error={error} onRetry={onRetry} compact />;

  return (
    <div>
      {searchable && (
        <div className="border-b border-ink-100 p-3">
          <div className="relative max-w-xs">
            <Icon name="search" size={15} className="absolute left-3 top-2.5 text-ink-400" />
            <input
              className="input pl-9"
              placeholder={searchPlaceholder}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(0);
              }}
            />
          </div>
        </div>
      )}

      {loading ? (
        <LoadingBlock rows={6} />
      ) : pageRows.length === 0 ? (
        <EmptyState title={emptyText} compact />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead className="sticky top-0 z-10 bg-ink-50/90 backdrop-blur">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => toggleSort(col)}
                    className={cn(
                      "border-b border-ink-200 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-ink-500",
                      col.align === "right" ? "text-right" : "text-left",
                      col.sortable && "cursor-pointer select-none hover:text-ink-700"
                    )}
                  >
                    <span className={cn("inline-flex items-center gap-1", col.align === "right" && "flex-row-reverse")}>
                      {col.header}
                      {col.sortable && sort?.key === col.key && (
                        <Icon name={sort.dir === "asc" ? "arrowUp" : "arrowDown"} size={12} />
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row, i) => (
                <tr
                  key={getRowKey(row, i)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cn(
                    "border-b border-ink-100 transition-colors",
                    onRowClick && "cursor-pointer hover:bg-brand-50/40"
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        "px-4 text-ink-700",
                        dense ? "py-2" : "py-3",
                        col.align === "right" ? "text-right tabular-nums" : "text-left"
                      )}
                    >
                      {col.render ? col.render(row) : readValue(row, col) ?? "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && sorted.length > pageSize && (
        <div className="flex items-center justify-between border-t border-ink-100 px-4 py-2.5 text-xs text-ink-500">
          <span>
            {safePage * pageSize + 1}–{Math.min((safePage + 1) * pageSize, sorted.length)} of{" "}
            {sorted.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              className="btn-ghost px-2 py-1 disabled:opacity-40"
              disabled={safePage === 0}
              onClick={() => setPage(safePage - 1)}
            >
              <Icon name="chevronRight" size={14} className="rotate-180" />
            </button>
            <span className="px-1">
              {safePage + 1} / {pageCount}
            </span>
            <button
              className="btn-ghost px-2 py-1 disabled:opacity-40"
              disabled={safePage >= pageCount - 1}
              onClick={() => setPage(safePage + 1)}
            >
              <Icon name="chevronRight" size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
