import { NavLink } from "react-router-dom";
import Icon from "../common/Icon.jsx";
import { cn } from "../../utils/cn.js";

/** A single sidebar navigation link with active state and optional badge. */
export default function NavItem({ item, onNavigate }) {
  return (
    <NavLink
      to={item.path}
      end={item.end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-brand-600/15 text-white"
            : "text-ink-300 hover:bg-white/5 hover:text-white"
        )
      }
    >
      {({ isActive }) => (
        <>
          <span className={cn("transition-colors", isActive ? "text-brand-300" : "text-ink-400 group-hover:text-ink-200")}>
            <Icon name={item.icon} size={18} />
          </span>
          <span className="flex-1 truncate">{item.label}</span>
          {item.badge && (
            <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[10px] font-medium text-ink-300">
              {item.badge}
            </span>
          )}
        </>
      )}
    </NavLink>
  );
}
