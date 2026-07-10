import { PageHeader, Panel, Badge } from "../../components/common/ui.jsx";
import { LoadingBlock, ErrorState } from "../../components/common/states.jsx";
import StatCard from "../../components/cards/StatCard.jsx";
import Icon from "../../components/common/Icon.jsx";
import { useApi } from "../../hooks/useApi.js";
import { healthApi, dashboardApi } from "../../api/endpoints.js";
import { formatCompact } from "../../utils/format.js";
import { cn } from "../../utils/cn.js";

function StatusRow({ label, detail, icon, state = "up" }) {
  // state: "up" (operational), "down" (failure), "planned" (roadmap).
  const styles = {
    up: { box: "bg-success/10 text-success", tone: "success", dot: "bg-success", text: "Operational" },
    down: { box: "bg-danger/10 text-danger", tone: "danger", dot: "bg-danger", text: "Down" },
    planned: { box: "bg-ink-100 text-ink-400", tone: "neutral", dot: "bg-ink-300", text: "Planned" },
  }[state];
  return (
    <div className="flex items-center gap-3 rounded-lg border border-ink-100 p-4">
      <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", styles.box)}>
        <Icon name={icon} size={17} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink-800">{label}</p>
        <p className="truncate text-xs text-ink-400">{detail}</p>
      </div>
      <Badge tone={styles.tone}>
        <span className={cn("h-1.5 w-1.5 rounded-full", styles.dot)} />
        {styles.text}
      </Badge>
    </div>
  );
}

export default function AdminPage() {
  const live = useApi(() => healthApi.live(), [], { ttl: 15000 });
  const db = useApi(() => healthApi.db(), [], { ttl: 15000 });
  const overview = useApi(() => dashboardApi.systemOverview(), [], { cacheKey: "admin:overview" });

  const anyLoading = live.loading || db.loading;

  return (
    <div>
      <PageHeader title="Administration" description="Platform status, connectivity, and system inventory." >
        <button className="btn-ghost" onClick={() => { live.refetch(); db.refetch(); overview.refetch(); }}>
          <Icon name="refresh" size={15} /> Refresh
        </button>
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="System Health" subtitle="Live service and database status">
          {anyLoading ? <LoadingBlock rows={3} /> : (
            <div className="space-y-3 p-4">
              <StatusRow label="API Service" icon="server"
                state={live.data?.status === "ok" ? "up" : "down"}
                detail={live.data ? `${live.data.service} · v${live.data.version}` : (live.error?.message || "Unreachable")} />
              <StatusRow label="Database (PostgreSQL)" icon="database"
                state={db.data?.healthy === true ? "up" : "down"}
                detail={db.data?.detail || db.error?.message || "Unreachable"} />
              <StatusRow label="REST API v1" icon="activity"
                state={live.error ? "down" : "up"}
                detail={live.error ? "Endpoint errors detected" : "All endpoints reachable"} />
            </div>
          )}
        </Panel>

        <Panel title="Application" subtitle="Version and environment">
          <div className="grid grid-cols-2 gap-3 p-4">
            <StatCard label="API Version" value={live.data?.version || "—"} loading={live.loading} />
            <StatCard label="Service" value="UPI Growth API" />
            <StatCard label="Environment" value="Development" />
            <StatCard label="Workspace" value="Phase 10" />
          </div>
        </Panel>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="System Inventory" subtitle="Registered participants">
          {overview.loading ? <LoadingBlock rows={3} /> : overview.error ? <ErrorState error={overview.error} onRetry={overview.refetch} compact /> : (
            <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3">
              <StatCard label="Customers" value={formatCompact(overview.data?.customers)} />
              <StatCard label="Merchants" value={formatCompact(overview.data?.merchants)} />
              <StatCard label="Banks" value={overview.data?.banks} sub={`${overview.data?.active_banks} active`} />
              <StatCard label="PSPs" value={overview.data?.psps} sub={`${overview.data?.active_psps} active`} />
            </div>
          )}
        </Panel>

        <Panel title="Future Capabilities" subtitle="Roadmap status">
          <div className="space-y-3 p-4">
            <StatusRow label="ML Model Status" icon="sparkles" state="planned" detail="Recommendation & forecasting models — Phase 11" />
            <StatusRow label="Knowledge Base" icon="document" state="planned" detail="RAG knowledge store for the copilot — Phase 12" />
          </div>
        </Panel>
      </div>
    </div>
  );
}
