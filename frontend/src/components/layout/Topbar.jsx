import Icon from "../common/Icon.jsx";
import Breadcrumbs from "./Breadcrumbs.jsx";
import GlobalSearch from "../search/GlobalSearch.jsx";

/** Sticky workspace header: menu toggle, breadcrumbs, global search, actions. */
export default function Topbar({ onMenu }) {
  return (
    <header className="sticky top-0 z-20 border-b border-ink-200 bg-white/80 backdrop-blur">
      <div className="flex h-16 items-center gap-3 px-4 lg:px-6">
        <button
          className="btn-ghost px-2 py-2 lg:hidden"
          onClick={onMenu}
          aria-label="Open navigation"
        >
          <Icon name="menu" size={18} />
        </button>

        <div className="hidden lg:block">
          <Breadcrumbs />
        </div>

        <div className="flex flex-1 justify-center px-2 lg:justify-end">
          <GlobalSearch />
        </div>

        <div className="hidden items-center gap-2 sm:flex">
          <span className="chip bg-success/10 text-success">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            Live
          </span>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
            PM
          </div>
        </div>
      </div>
    </header>
  );
}
