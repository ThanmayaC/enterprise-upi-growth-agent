import Icon from "./Icon.jsx";
import { cn } from "../../utils/cn.js";

/** Indeterminate spinner. */
export function Spinner({ size = 20, className = "" }) {
  return (
    <svg
      className={cn("animate-spin text-brand-600", className)}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-label="Loading"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-20" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

/** A shimmering skeleton block for loading placeholders. */
export function Skeleton({ className = "" }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md bg-ink-200/70",
        "after:absolute after:inset-0 after:-translate-x-full",
        "after:animate-[shimmer_1.4s_infinite] after:bg-gradient-to-r",
        "after:from-transparent after:via-white/50 after:to-transparent",
        className
      )}
    />
  );
}

/** Full-panel loading skeleton with a configurable number of rows. */
export function LoadingBlock({ rows = 4, className = "" }) {
  return (
    <div className={cn("space-y-3 p-5", className)} role="status" aria-busy="true">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  );
}

/** Error panel with a retry affordance. */
export function ErrorState({ error, onRetry, compact = false }) {
  const message = error?.message || "Something went wrong.";
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 text-center",
        compact ? "p-6" : "p-10"
      )}
      role="alert"
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-danger/10 text-danger">
        <Icon name="alert" size={22} />
      </div>
      <div>
        <p className="text-sm font-semibold text-ink-800">Unable to load data</p>
        <p className="mt-1 max-w-md text-xs text-ink-500">{message}</p>
      </div>
      {onRetry && (
        <button className="btn-ghost" onClick={onRetry}>
          <Icon name="refresh" size={15} />
          Retry
        </button>
      )}
    </div>
  );
}

/** Empty-state placeholder. */
export function EmptyState({ title = "No data", hint, icon = "inbox", compact = false }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 text-center",
        compact ? "p-6" : "p-10"
      )}
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-ink-100 text-ink-400">
        <Icon name={icon} size={22} />
      </div>
      <p className="text-sm font-medium text-ink-700">{title}</p>
      {hint && <p className="max-w-sm text-xs text-ink-400">{hint}</p>}
    </div>
  );
}
