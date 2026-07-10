import Icon from "../common/Icon.jsx";
import { DeltaBadge } from "../common/ui.jsx";
import { Skeleton } from "../common/states.jsx";
import { cn } from "../../utils/cn.js";
import { formatCompact, formatINR, formatPercent, formatNumber } from "../../utils/format.js";

/** Format a raw value according to its unit as returned by the backend cards. */
export function formatByUnit(value, unit) {
  if (value === null || value === undefined) return "—";
  if (unit === "INR") return formatINR(value);
  if (unit === "%") return formatPercent(value);
  if (unit === "transactions" || unit === "customers" || unit === "merchants") {
    return formatCompact(value);
  }
  return formatNumber(value);
}

const ACCENTS = {
  brand: "bg-brand-50 text-brand-600",
  success: "bg-success/10 text-success",
  danger: "bg-danger/10 text-danger",
  warning: "bg-warning/10 text-warning",
  sky: "bg-sky-50 text-sky-600",
};

/**
 * The headline KPI tile. Accepts either a pre-formatted `display` string or a
 * raw `value` + `unit` pair (matching the backend card DTO).
 */
export default function KpiCard({
  title,
  value,
  unit,
  display,
  icon = "activity",
  accent = "brand",
  delta,
  invertDelta = false,
  hint,
  loading = false,
}) {
  return (
    <div className="panel p-5">
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-ink-400">{title}</span>
        <span className={cn("flex h-8 w-8 items-center justify-center rounded-lg", ACCENTS[accent])}>
          <Icon name={icon} size={16} />
        </span>
      </div>
      {loading ? (
        <Skeleton className="mt-4 h-8 w-28" />
      ) : (
        <div className="mt-3 text-2xl font-semibold tracking-tight text-ink-900">
          {display ?? formatByUnit(value, unit)}
        </div>
      )}
      <div className="mt-2 flex items-center gap-2">
        {delta !== undefined && <DeltaBadge value={delta} invert={invertDelta} />}
        {hint && <span className="text-xs text-ink-400">{hint}</span>}
      </div>
    </div>
  );
}
