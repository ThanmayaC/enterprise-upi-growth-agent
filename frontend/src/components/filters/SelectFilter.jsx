import Icon from "../common/Icon.jsx";

/** A compact labelled select used across analytics toolbars. */
export default function SelectFilter({ label, value, onChange, options }) {
  return (
    <label className="flex items-center gap-2 rounded-lg border border-ink-200 bg-white px-2.5 py-1.5">
      {label && <span className="text-xs font-medium text-ink-400">{label}</span>}
      <div className="relative flex items-center">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="appearance-none bg-transparent pr-5 text-xs font-medium text-ink-700 outline-none"
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <Icon name="chevronDown" size={13} className="pointer-events-none absolute right-0 text-ink-400" />
      </div>
    </label>
  );
}
