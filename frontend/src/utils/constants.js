// Static workspace configuration: navigation model and the shared chart
// palette (kept in sync with the Tailwind brand colors).

export const NAV_SECTIONS = [
  {
    heading: "Overview",
    items: [
      { key: "dashboard", label: "Dashboard", path: "/", icon: "grid", end: true },
      { key: "portfolio", label: "Portfolio", path: "/portfolio", icon: "briefcase" },
    ],
  },
  {
    heading: "Intelligence",
    items: [
      { key: "merchant", label: "Merchant Intelligence", path: "/merchants", icon: "store" },
      { key: "customer", label: "Customer Intelligence", path: "/customers", icon: "users" },
      { key: "bank", label: "Bank Intelligence", path: "/banks", icon: "bank" },
      { key: "psp", label: "PSP Intelligence", path: "/psps", icon: "app" },
      { key: "analytics", label: "Analytics", path: "/analytics", icon: "chart" },
    ],
  },
  {
    heading: "Workspace",
    items: [
      { key: "copilot", label: "AI Copilot", path: "/copilot", icon: "sparkles", badge: "Phase 12" },
      { key: "reports", label: "Report Studio", path: "/reports", icon: "document", badge: "Phase 13" },
      { key: "admin", label: "Administration", path: "/admin", icon: "cog" },
    ],
  },
];

// Human labels for breadcrumbs, keyed by the first path segment.
export const ROUTE_TITLES = {
  "": "Executive Dashboard",
  portfolio: "Portfolio",
  merchants: "Merchant Intelligence",
  customers: "Customer Intelligence",
  banks: "Bank Intelligence",
  psps: "PSP Intelligence",
  analytics: "Portfolio Analytics",
  copilot: "AI Copilot",
  reports: "Report Studio",
  admin: "Administration",
};

// Categorical chart palette — indigo-led, colour-blind-considerate, and
// consistent across every visualization.
export const CHART_PALETTE = [
  "#4f46e5",
  "#0ea5e9",
  "#059669",
  "#d97706",
  "#db2777",
  "#7c3aed",
  "#0891b2",
  "#65a30d",
  "#e11d48",
  "#475569",
];

export const STATUS_COLORS = {
  success: "#059669",
  failure: "#dc2626",
  neutral: "#6366f1",
  amount: "#0ea5e9",
};

// Reusable time-grain and date presets for analytics filters.
export const TIME_GRAINS = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "yearly", label: "Yearly" },
];
