// Presentation-only formatting. All business math is done by the backend;
// these helpers only shape already-computed numbers for display.

const NUM = new Intl.NumberFormat("en-IN");

/** Group-separated integer/decimal, e.g. 1012591 -> "10,12,591". */
export function formatNumber(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

/** Compact Indian currency, e.g. 9561290293 -> "₹956.13 Cr". */
export function formatINR(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const n = Number(value);
  const abs = Math.abs(n);
  if (abs >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`;
  if (abs >= 1e3) return `₹${(n / 1e3).toFixed(2)} K`;
  return `₹${NUM.format(n)}`;
}

/** Full rupee amount with separators, e.g. "₹9,56,12,90,293.62". */
export function formatINRFull(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `₹${new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 2,
  }).format(value)}`;
}

/** Compact count, e.g. 1012591 -> "1.01M". */
export function formatCompact(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const n = Number(value);
  const abs = Math.abs(n);
  if (abs >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return NUM.format(n);
}

/** Percentage with a fixed precision, e.g. 93.63 -> "93.63%". */
export function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Number(value).toFixed(digits)}%`;
}

/** Signed percent change with a sign, e.g. 4.2 -> "+4.20%", null -> "—". */
export function formatDelta(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const n = Number(value);
  return `${n >= 0 ? "+" : ""}${n.toFixed(digits)}%`;
}

/** ISO date -> "12 Jan 2024". */
export function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/** ISO datetime -> "12 Jan 2024, 14:30". */
export function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a trend "period" for an axis label. The backend emits several
 * period shapes across grains: ISO date (daily/weekly/monthly), a quarter
 * label ("2024-Q2"), a year (int), or an hour (0-23). Handle each.
 */
export function formatPeriod(period, grain) {
  if (period === null || period === undefined) return "—";
  if (grain === "hourly" || (typeof period === "number" && period < 24 && grain !== "yearly")) {
    return `${String(period).padStart(2, "0")}:00`;
  }
  if (grain === "yearly" || typeof period === "number") return String(period);
  if (typeof period === "string" && period.includes("-Q")) return period;
  const d = new Date(period);
  if (Number.isNaN(d.getTime())) return String(period);
  if (grain === "monthly") {
    return d.toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
  }
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

/** Truncate a long string with an ellipsis. */
export function truncate(value, max = 28) {
  if (!value) return "—";
  const s = String(value);
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}
