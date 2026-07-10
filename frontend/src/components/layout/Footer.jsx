/** Workspace footer with attribution and version. */
export default function Footer() {
  return (
    <footer className="border-t border-ink-200 px-6 py-4">
      <div className="flex flex-col items-center justify-between gap-2 text-xs text-ink-400 sm:flex-row">
        <p>Enterprise UPI Growth Intelligence Platform — Product Analytics Workspace</p>
        <p>© {new Date().getFullYear()} · API v1.0.0 · Phase 10</p>
      </div>
    </footer>
  );
}
