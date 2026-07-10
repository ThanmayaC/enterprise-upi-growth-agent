import NavItem from "./NavItem.jsx";
import Icon from "../common/Icon.jsx";
import { NAV_SECTIONS } from "../../utils/constants.js";
import { cn } from "../../utils/cn.js";

/** Persistent enterprise sidebar. Off-canvas on mobile, fixed on desktop. */
export default function Sidebar({ open, onClose }) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-ink-900/40 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-ink-900 transition-transform duration-200 lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center gap-2.5 px-5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
            <Icon name="trend" size={20} />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-white">UPI Growth</p>
            <p className="text-[11px] text-ink-400">Intelligence Workspace</p>
          </div>
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
          {NAV_SECTIONS.map((section) => (
            <div key={section.heading}>
              <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-ink-500">
                {section.heading}
              </p>
              <div className="space-y-1">
                {section.items.map((item) => (
                  <NavItem key={item.key} item={item} onNavigate={onClose} />
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-white/5 px-5 py-4">
          <div className="flex items-center gap-2 text-xs text-ink-400">
            <span className="h-2 w-2 rounded-full bg-success" />
            Platform v1.0.0
          </div>
        </div>
      </aside>
    </>
  );
}
