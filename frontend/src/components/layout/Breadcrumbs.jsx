import { Link, useLocation } from "react-router-dom";
import Icon from "../common/Icon.jsx";
import { ROUTE_TITLES } from "../../utils/constants.js";

/** Contextual breadcrumb trail derived from the current route. */
export default function Breadcrumbs() {
  const { pathname } = useLocation();
  const segments = pathname.split("/").filter(Boolean);
  const first = segments[0] || "";
  const title = ROUTE_TITLES[first] ?? "Workspace";

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-ink-400">
      <Link to="/" className="hover:text-ink-600">
        Workspace
      </Link>
      <Icon name="chevronRight" size={12} />
      <span className="font-medium text-ink-600">{title}</span>
    </nav>
  );
}
