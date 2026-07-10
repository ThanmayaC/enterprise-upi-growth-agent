import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader, Panel } from "../../components/common/ui.jsx";
import { LoadingBlock, ErrorState } from "../../components/common/states.jsx";
import KpiCard from "../../components/cards/KpiCard.jsx";
import StatCard from "../../components/cards/StatCard.jsx";
import BarChart from "../../components/charts/BarChart.jsx";
import DonutChart from "../../components/charts/DonutChart.jsx";
import LineChart from "../../components/charts/LineChart.jsx";
import DataTable from "../../components/tables/DataTable.jsx";
import Icon from "../../components/common/Icon.jsx";
import { useApi } from "../../hooks/useApi.js";
import { pspApi } from "../../api/endpoints.js";
import { formatCompact, formatINR, formatPercent, formatPeriod, truncate } from "../../utils/format.js";

const YEAR = { start_date: "2024-01-01", end_date: "2024-12-31" };

export default function PspPage() {
  const [params, setParams] = useSearchParams();
  const selected = params.get("name") || null;

  const overview = useApi(() => pspApi.overview(), [], { cacheKey: "p:overview" });
  const performance = useApi(() => pspApi.performance(), [], { cacheKey: "p:perf" });
  const contribution = useApi(() => pspApi.contribution({ top_n: 5 }), [], { cacheKey: "p:contrib" });

  const stats = useApi(() => pspApi.statistics(selected), [selected], { enabled: !!selected });
  const trend = useApi(() => pspApi.trend(selected, YEAR), [selected], { enabled: !!selected });

  const rows = overview.data || [];
  const byTxn = [...rows].sort((a, b) => b.total_transactions - a.total_transactions);

  const contribData = useMemo(() => {
    const c = contribution.data;
    if (!c) return [];
    const leaders = c.leaders || [];
    const sum = leaders.reduce((n, r) => n + r.total_transactions, 0);
    const rest = Math.max(0, c.total_transactions - sum);
    const slices = leaders.map((r) => ({ name: r.psp, value: r.total_transactions }));
    if (rest > 0) slices.push({ name: "Others", value: rest });
    return slices;
  }, [contribution.data]);

  const columns = [
    { key: "rank", header: "#", value: (r, i) => i, render: (_r, i) => null },
    { key: "psp", header: "PSP", sortable: true, value: (r) => r.psp,
      render: (r) => <button onClick={() => setParams({ name: r.psp })} className="font-medium text-brand-700 hover:underline">{r.psp}</button> },
    { key: "total_transactions", header: "Transactions", align: "right", sortable: true, value: (r) => r.total_transactions, render: (r) => formatCompact(r.total_transactions) },
    { key: "successful_transactions", header: "Successful", align: "right", sortable: true, value: (r) => r.successful_transactions, render: (r) => formatCompact(r.successful_transactions) },
    { key: "success_rate", header: "Success", align: "right", sortable: true, value: (r) => r.success_rate, render: (r) => formatPercent(r.success_rate) },
    { key: "total_amount", header: "Volume", align: "right", sortable: true, value: (r) => Number(r.total_amount), render: (r) => formatINR(r.total_amount) },
  ].filter((c) => c.key !== "rank");

  const tseries = trend.data?.series || [];
  const perf = performance.data;

  return (
    <div>
      <PageHeader title="PSP Intelligence" description="Payment service provider performance — rankings, concentration, reliability, and traffic." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {performance.loading ? (
          Array.from({ length: 4 }).map((_, i) => <KpiCard key={i} title=" " loading />)
        ) : performance.error ? (
          <div className="col-span-full"><Panel><ErrorState error={performance.error} onRetry={performance.refetch} /></Panel></div>
        ) : (
          <>
            <KpiCard title="Active PSPs" value={perf?.active_psps} unit="" display={formatCompact(perf?.active_psps)} icon="app" accent="brand" />
            <KpiCard title="Median Txns" display={formatCompact(perf?.transaction_count_stats?.median)} icon="activity" accent="sky" />
            <KpiCard title="Median Success" value={perf?.success_rate_stats?.median} unit="%" icon="check" accent="success" />
            <KpiCard title="Top Success" value={perf?.success_rate_stats?.maximum} unit="%" icon="check" accent="success" />
          </>
        )}
      </div>

      {selected && (
        <div className="mt-6">
          <Panel title={`${selected}`} subtitle="Selected PSP"
            actions={<button onClick={() => setParams({})} className="text-ink-400 hover:text-ink-700"><Icon name="close" size={16} /></button>}>
            {stats.loading ? <LoadingBlock rows={3} /> : stats.error ? <ErrorState error={stats.error} onRetry={stats.refetch} compact /> : (
              <div className="space-y-4 p-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <StatCard label="Transactions" value={formatCompact(stats.data?.total_transactions)} />
                  <StatCard label="Successful" value={formatCompact(stats.data?.successful_transactions)} />
                  <StatCard label="Success Rate" value={formatPercent(stats.data?.success_rate)} />
                  <StatCard label="Volume" value={formatINR(stats.data?.total_amount)} />
                </div>
                {tseries.length > 0 && (
                  <LineChart height={240} categories={tseries.map((r) => formatPeriod(r.period, "monthly"))} valueFormatter={formatCompact}
                    series={[{ name: "Transactions", data: tseries.map((r) => r.transaction_count), color: "#4f46e5" }]} />
                )}
              </div>
            )}
          </Panel>
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel title="PSP Rankings & Traffic" className="xl:col-span-2">
          <DataTable columns={columns} rows={rows} loading={overview.loading} error={overview.error} onRetry={overview.refetch} pageSize={10} getRowKey={(r) => r.psp} />
        </Panel>
        <Panel title="PSP Contribution" subtitle="Share of transactions" bodyClassName="p-4">
          {contribution.loading ? <LoadingBlock rows={6} /> : contribution.error ? <ErrorState error={contribution.error} onRetry={contribution.refetch} compact /> : (
            <DonutChart height={300} data={contribData} valueFormatter={formatCompact}
              centerLabel={contribution.data ? `Top ${contribution.data.top_n}\n${formatPercent(contribution.data.top_n_count_share_pct)}` : ""} />
          )}
        </Panel>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Traffic by PSP" subtitle="Transactions per provider" bodyClassName="p-4">
          {overview.loading ? <LoadingBlock rows={6} /> : (
            <BarChart height={300} categories={byTxn.map((r) => r.psp)} series={[{ name: "Transactions", data: byTxn.map((r) => r.total_transactions) }]} valueFormatter={formatCompact} color="#4f46e5" />
          )}
        </Panel>
        <Panel title="Reliability by PSP" subtitle="Success rate per provider" bodyClassName="p-4">
          {overview.loading ? <LoadingBlock rows={6} /> : (
            <BarChart height={300} categories={byTxn.map((r) => r.psp)} series={[{ name: "Success Rate", data: byTxn.map((r) => r.success_rate) }]} valueFormatter={(v) => formatPercent(v, 1)} color="#059669" />
          )}
        </Panel>
      </div>
    </div>
  );
}
