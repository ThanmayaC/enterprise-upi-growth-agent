import { useMemo, useState } from "react";
import { PageHeader, Panel, DeltaBadge } from "../../components/common/ui.jsx";
import { LoadingBlock, ErrorState } from "../../components/common/states.jsx";
import KpiCard from "../../components/cards/KpiCard.jsx";
import StatCard from "../../components/cards/StatCard.jsx";
import LineChart from "../../components/charts/LineChart.jsx";
import AreaChart from "../../components/charts/AreaChart.jsx";
import DateRangeFilter from "../../components/filters/DateRangeFilter.jsx";
import { useApi } from "../../hooks/useApi.js";
import { portfolioApi } from "../../api/endpoints.js";
import { formatCompact, formatINR, formatPercent, formatPeriod, formatDelta } from "../../utils/format.js";

const PRESETS = [
  { label: "All time", range: { start_date: null, end_date: null } },
  { label: "Q1", range: { start_date: "2024-01-01", end_date: "2024-03-31" } },
  { label: "Q2", range: { start_date: "2024-04-01", end_date: "2024-06-30" } },
  { label: "Q3", range: { start_date: "2024-07-01", end_date: "2024-09-30" } },
  { label: "Q4", range: { start_date: "2024-10-01", end_date: "2024-12-31" } },
];

function MonthPoint({ label, point }) {
  return (
    <StatCard
      label={label}
      value={point ? formatPeriod(point.period, "monthly") : "—"}
      sub={point ? `${formatCompact(point.transaction_count)} txns · ${formatINR(point.total_amount)}` : undefined}
    />
  );
}

export default function PortfolioPage() {
  const [range, setRange] = useState({ start_date: null, end_date: null });
  const rangeKey = `${range.start_date || "all"}:${range.end_date || "all"}`;

  const kpis = useApi(() => portfolioApi.kpis(range), [rangeKey], { cacheKey: `pf:kpis:${rangeKey}` });
  const trends = useApi(() => portfolioApi.trends(range), [rangeKey], { cacheKey: `pf:trends:${rangeKey}` });
  const growth = useApi(() => portfolioApi.growth(), [], { cacheKey: "pf:growth" });
  const health = useApi(() => portfolioApi.health(), [], { cacheKey: "pf:health" });

  // Comparison
  const [cur, setCur] = useState({ start_date: "2024-04-01", end_date: "2024-06-30" });
  const [prev, setPrev] = useState({ start_date: "2024-01-01", end_date: "2024-03-31" });
  const [cmp, setCmp] = useState(null);
  const [cmpLoading, setCmpLoading] = useState(false);
  const [cmpError, setCmpError] = useState(null);
  const runCompare = async () => {
    setCmpLoading(true);
    setCmpError(null);
    try {
      const res = await portfolioApi.compare({
        current_start: cur.start_date,
        current_end: cur.end_date,
        previous_start: prev.start_date,
        previous_end: prev.end_date,
      });
      setCmp(res);
    } catch (e) {
      setCmpError(e);
    } finally {
      setCmpLoading(false);
    }
  };

  const k = kpis.data;
  const cards = useMemo(
    () =>
      k
        ? [
            { title: "Transactions", value: k.total_transactions, unit: "transactions", icon: "activity", accent: "brand" },
            { title: "Volume", value: k.total_volume, unit: "INR", icon: "trend", accent: "sky" },
            { title: "Avg Ticket", value: k.average_transaction_amount, unit: "INR", icon: "activity", accent: "brand" },
            { title: "Success Rate", value: k.success_rate, unit: "%", icon: "check", accent: "success" },
            { title: "Approval Rate", value: k.approval_rate, unit: "%", icon: "check", accent: "success" },
            { title: "Failed", value: k.failed_transactions, unit: "transactions", icon: "alert", accent: "danger" },
          ]
        : [],
    [k]
  );

  const series = trends.data?.series || [];
  const cats = series.map((r) => formatPeriod(r.period, "monthly"));
  const g = growth.data;
  const momentum = health.data?.momentum;

  return (
    <div>
      <PageHeader title="Portfolio Analytics" description="Growth, trends, and period-over-period movement across the portfolio.">
        <DateRangeFilter value={range} onChange={setRange} presets={PRESETS} />
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {kpis.loading
          ? Array.from({ length: 6 }).map((_, i) => <KpiCard key={i} title=" " loading />)
          : kpis.error
          ? <div className="col-span-full"><Panel><ErrorState error={kpis.error} onRetry={kpis.refetch} /></Panel></div>
          : cards.map((c) => <KpiCard key={c.title} {...c} />)}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Activity Trend" subtitle="Transactions vs successful (monthly)" bodyClassName="p-4">
          {trends.loading ? <LoadingBlock rows={6} /> : trends.error ? <ErrorState error={trends.error} onRetry={trends.refetch} compact /> : (
            <LineChart height={300} categories={cats} valueFormatter={formatCompact}
              series={[
                { name: "Transactions", data: series.map((r) => r.transaction_count), color: "#4f46e5" },
                { name: "Successful", data: series.map((r) => r.successful_count), color: "#059669" },
              ]} />
          )}
        </Panel>
        <Panel title="Success Rate Trend" subtitle="Monthly reliability" bodyClassName="p-4">
          {trends.loading ? <LoadingBlock rows={6} /> : trends.error ? <ErrorState error={trends.error} onRetry={trends.refetch} compact /> : (
            <AreaChart height={300} categories={cats} valueFormatter={(v) => formatPercent(v, 1)}
              series={[{ name: "Success Rate", data: series.map((r) => r.success_rate), color: "#059669" }]} />
          )}
        </Panel>
      </div>

      {/* Growth + health */}
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Growth Overview" subtitle="All-time trajectory">
          {growth.loading ? <LoadingBlock rows={4} /> : growth.error ? <ErrorState error={growth.error} onRetry={growth.refetch} compact /> : (
            <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3">
              <StatCard label="Overall Txn Growth" value={formatDelta(g?.overall_count_growth_pct)} />
              <StatCard label="Overall Volume Growth" value={formatDelta(g?.overall_amount_growth_pct)} />
              <StatCard label="Avg Monthly Growth" value={formatDelta(g?.average_monthly_count_growth_pct)} />
              <MonthPoint label="First Month" point={g?.first_month} />
              <MonthPoint label="Best Month" point={g?.best_growth_month} />
              <MonthPoint label="Latest Month" point={g?.latest_month} />
            </div>
          )}
        </Panel>
        <Panel title="Business Health" subtitle="Latest month momentum">
          {health.loading ? <LoadingBlock rows={4} /> : health.error ? <ErrorState error={health.error} onRetry={health.refetch} compact /> : (
            <div className="space-y-3 p-4">
              <div className="grid grid-cols-2 gap-3">
                <StatCard label="Current Txns" value={formatCompact(health.data?.current?.total_transactions)} />
                <StatCard label="Current Success" value={formatPercent(health.data?.current?.success_rate)} />
              </div>
              <div className="rounded-lg border border-ink-100 p-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-400">
                  {momentum?.latest_month ? `${formatPeriod(momentum.previous_month, "monthly")} → ${formatPeriod(momentum.latest_month, "monthly")}` : "Momentum"}
                </p>
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2 text-sm">Transactions <DeltaBadge value={momentum?.count_change_pct} /></div>
                  <div className="flex items-center gap-2 text-sm">Volume <DeltaBadge value={momentum?.amount_change_pct} /></div>
                  <div className="flex items-center gap-2 text-sm">Success pts
                    <span className="chip bg-ink-100 text-ink-600">{momentum?.success_rate_change_points != null ? `${momentum.success_rate_change_points > 0 ? "+" : ""}${momentum.success_rate_change_points}` : "—"}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </Panel>
      </div>

      {/* Comparison */}
      <div className="mt-6">
        <Panel title="Period Comparison" subtitle="Compare two periods side by side">
          <div className="flex flex-col gap-4 p-4">
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <p className="mb-1 text-xs font-medium text-ink-500">Current period</p>
                <DateRangeFilter value={cur} onChange={setCur} />
              </div>
              <div>
                <p className="mb-1 text-xs font-medium text-ink-500">Previous period</p>
                <DateRangeFilter value={prev} onChange={setPrev} />
              </div>
              <button className="btn-primary" onClick={runCompare} disabled={cmpLoading}>
                {cmpLoading ? "Comparing…" : "Compare"}
              </button>
            </div>
            {cmpError && <ErrorState error={cmpError} compact />}
            {cmp && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard label="Txn Change" value={<span className="flex items-center gap-2">{formatCompact(cmp.current.total_transactions)} <DeltaBadge value={cmp.changes.transaction_count_pct} /></span>} />
                <StatCard label="Volume Change" value={<span className="flex items-center gap-2">{formatINR(cmp.current.total_volume)} <DeltaBadge value={cmp.changes.volume_pct} /></span>} />
                <StatCard label="Avg Ticket Change" value={<span className="flex items-center gap-2">{formatINR(cmp.current.average_transaction_amount)} <DeltaBadge value={cmp.changes.average_amount_pct} /></span>} />
                <StatCard label="Success Rate Δ (pts)" value={`${cmp.changes.success_rate_points > 0 ? "+" : ""}${cmp.changes.success_rate_points}`} />
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
