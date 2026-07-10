import { Skeleton } from "../common/states.jsx";
import { cn } from "../../utils/cn.js";

/** A compact label/value stat used inside panels (profiles, summaries). */
export default function StatCard({ label, value, sub, loading = false, className = "" }) {
  return (
    <div className={cn("rounded-lg border border-ink-100 bg-ink-50/50 p-4", className)}>
      <p className="text-xs font-medium uppercase tracking-wide text-ink-400">{label}</p>
      {loading ? (
        <Skeleton className="mt-2 h-6 w-20" />
      ) : (
        <p className="mt-1.5 text-lg font-semibold text-ink-900">{value}</p>
      )}
      {sub && <p className="mt-0.5 text-xs text-ink-400">{sub}</p>}
    </div>
  );
}
