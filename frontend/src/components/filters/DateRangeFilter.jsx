import Icon from "../common/Icon.jsx";
import { cn } from "../../utils/cn.js";

/**
 * Inclusive start/end date filter with quick presets. Controlled:
 * value = { start_date, end_date }, onChange receives the next value.
 */
export default function DateRangeFilter({ value, onChange, presets = [] }) {
  const set = (patch) => onChange({ ...value, ...patch });
  return (
    <div className="flex flex-wrap items-center gap-2">
      {presets.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {presets.map((p) => {
            const active =
              value.start_date === p.range.start_date && value.end_date === p.range.end_date;
            return (
              <button
                key={p.label}
                onClick={() => onChange(p.range)}
                className={cn(
                  "rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors",
                  active
                    ? "border-brand-300 bg-brand-50 text-brand-700"
                    : "border-ink-200 bg-white text-ink-500 hover:bg-ink-50"
                )}
              >
                {p.label}
              </button>
            );
          })}
        </div>
      )}
      <div className="flex items-center gap-1.5 rounded-lg border border-ink-200 bg-white px-2.5 py-1.5">
        <Icon name="filter" size={14} className="text-ink-400" />
        <input
          type="date"
          value={value.start_date || ""}
          onChange={(e) => set({ start_date: e.target.value || null })}
          className="bg-transparent text-xs text-ink-700 outline-none"
          aria-label="Start date"
        />
        <span className="text-ink-300">→</span>
        <input
          type="date"
          value={value.end_date || ""}
          onChange={(e) => set({ end_date: e.target.value || null })}
          className="bg-transparent text-xs text-ink-700 outline-none"
          aria-label="End date"
        />
        {(value.start_date || value.end_date) && (
          <button
            onClick={() => onChange({ start_date: null, end_date: null })}
            className="text-ink-400 hover:text-ink-700"
            aria-label="Clear dates"
          >
            <Icon name="close" size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
