import Icon from "./Icon.jsx";
import { cn } from "../../utils/cn.js";
import { formatDelta } from "../../utils/format.js";

const TONES = {
  brand: "bg-brand-50 text-brand-700",
  success: "bg-success/10 text-success",
  danger: "bg-danger/10 text-danger",
  warning: "bg-warning/10 text-warning",
  neutral: "bg-ink-100 text-ink-600",
};

/** A small status chip. */
export function Badge({ children, tone = "neutral", className = "" }) {
  return <span className={cn("chip", TONES[tone], className)}>{children}</span>;
}

/**
 * A signed change badge with an up/down arrow. Positive is treated as good
 * (success) unless `invert` is set (e.g. for failure rate).
 */
export function DeltaBadge({ value, invert = false }) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="text-xs text-ink-400">—</span>;
  }
  const positive = Number(value) >= 0;
  const good = invert ? !positive : positive;
  return (
    <span
      className={cn(
        "chip",
        good ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
      )}
    >
      <Icon name={positive ? "arrowUp" : "arrowDown"} size={12} />
      {formatDelta(value)}
    </span>
  );
}

/** A titled content panel — the primary surface for every section. */
export function Panel({ title, subtitle, actions, children, className = "", bodyClassName = "" }) {
  return (
    <section className={cn("panel animate-fade-in", className)}>
      {(title || actions) && (
        <header className="panel-header">
          <div>
            {title && <h3 className="panel-title">{title}</h3>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-400">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

/** Page-level header with a title, optional description, and actions slot. */
export function PageHeader({ title, description, children }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink-900">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-ink-500">{description}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}

/** A lightweight, accessible tab switcher. */
export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-1 rounded-lg bg-ink-100 p-1" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.value}
          role="tab"
          aria-selected={value === t.value}
          onClick={() => onChange(t.value)}
          className={cn(
            "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            value === t.value
              ? "bg-white text-brand-700 shadow-sm"
              : "text-ink-500 hover:text-ink-700"
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
