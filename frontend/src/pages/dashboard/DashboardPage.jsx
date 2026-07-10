import { useMemo } from "react";
import { PageHeader, Panel } from "../../components/common/ui.jsx";
import { LoadingBlock, ErrorState, EmptyState } from "../../components/common/states.jsx";
import KpiCard from "../../components/cards/KpiCard.jsx";
import LineChart from "../../components/charts/LineChart.jsx";
import AreaChart from "../../components/charts/AreaChart.jsx";
import BarChart from "../../components/charts/BarChart.jsx";
import DataTable from "../../components/tables/DataTable.jsx";
import { transactionColumns } from "../../components/tables/transactionColumns.jsx";
import { useApi } from "../../hooks/useApi.js";
import { portfolioApi, dashboardApi } from "../../api/endpoints.js";
import { formatCompact, formatINR, formatPeriod, truncate } from "../../utils/format.js";

function LeaderBars({ title, rows, valueKey = "transaction_count" }) {
  const data = (rows || []).slice(0, 6);
  return (
    <Panel title={title} bodyClassName="p-4">
      {data.length === 0 ? (
        <EmptyState compact />
      ) : (
        <BarChart
          horizontal
          height={230}
          categories={data.map((r) => truncate(r.name, 18))}
          series={[{ name: title, data: data.map((r) => r[valueKey]) }]}
          valueFormatter={formatCompact}
          color="#4f46e5"
        />
      )}
    </Panel>
  );
}

export default function DashboardPage() {
  const overview = useApi(() => portfolioApi.overview(6), [], { cacheKey: "dash:overview" });
  const trends = useApi(() => portfolioApi.trends(), [], { cacheKey: "dash:trends" });
  const recent = useApi(() => dashboardApi.recentActivity(8), [], { cacheKey: "dash:recent", ttl: 20000 });

  const kpis = overview.data?.summary?.kpis;
  const leaders = overview.data?.leaders;

  const cards = useMemo(() => {
    if (!kpis) return [];
    return [
      { title: "Total Transactions", value: kpis.total_transactions, unit: "transactions", icon: "activity", accent: "brand" },
      { title: "Total Volume", value: kpis.total_volume, unit: "INR", icon: "trend", accent: "sky" },
      { title: "Success Rate", value: kpis.success_rate, unit: "%", icon: "check", accent: "success" },
      { title: "Failure Rate", value: kpis.failure_rate, unit: "%", icon: "alert", accent: "danger" },
      { title: "Active Merchants", value: kpis.unique_merchants, unit: "merchants", icon: "store", accent: "brand" },
      { title: "Active Customers", value: kpis.unique_customers, unit: "customers", icon: "users", accent: "sky" },
    ];
  }, [kpis]);

  const trendSeries = trends.data?.series || [];
  const trendCats = trendSeries.map((r) => formatPeriod(r.period, "monthly"));

  return (
    <div>
      <PageHeader
        title="Executive Dashboard"
        description="Portfolio-wide health of the UPI network — activity, reliability, and the participants driving growth."
      />

      {/* KPI row */}
      {overview.error ? (
        <Panel><ErrorState error={overview.error} onRetry={overview.refetch} /></Panel>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          {overview.loading
            ? Array.from({ length: 6 }).map((_, i) => <KpiCard key={i} title=" " loading />)
            : cards.map((c) => <KpiCard key={c.title} {...c} />)}
        </div>
      )}

      {/* Trends */}
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel title="Transaction Trend" subtitle="Monthly activity vs successful" className="xl:col-span-2" bodyClassName="p-4">
          {trends.loading ? (
            <LoadingBlock rows={6} />
          ) : trends.error ? (
            <ErrorState error={trends.error} onRetry={trends.refetch} compact />
          ) : (
            <LineChart
              height={300}
              categories={trendCats}
              valueFormatter={formatCompact}
              series={[
                { name: "Transactions", data: trendSeries.map((r) => r.transaction_count), color: "#4f46e5" },
                { name: "Successful", data: trendSeries.map((r) => r.successful_count), color: "#059669" },
              ]}
            />
          )}
        </Panel>
        <Panel title="Volume Trend" subtitle="Monthly settled volume" bodyClassName="p-4">
          {trends.loading ? (
            <LoadingBlock rows={6} />
          ) : trends.error ? (
            <ErrorState error={trends.error} onRetry={trends.refetch} compact />
          ) : (
            <AreaChart
              height={300}
              categories={trendCats}
              valueFormatter={formatINR}
              series={[{ name: "Volume", data: trendSeries.map((r) => Number(r.total_amount)), color: "#0ea5e9" }]}
            />
          )}
        </Panel>
      </div>

      {/* Leaders */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {overview.loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Panel key={i} title=" "><LoadingBlock rows={6} /></Panel>
          ))
        ) : (
          <>
            <LeaderBars title="Top Merchants" rows={leaders?.top_merchants} />
            <LeaderBars title="Top Banks" rows={leaders?.top_banks} />
            <LeaderBars title="Top PSPs" rows={leaders?.top_psps} />
          </>
        )}
      </div>

      {/* Recent activity */}
      <div className="mt-6">
        <Panel title="Recent Activity" subtitle="Latest transactions across the network" bodyClassName="">
          <DataTable
            columns={transactionColumns()}
            rows={recent.data}
            loading={recent.loading}
            error={recent.error}
            onRetry={recent.refetch}
            pageSize={8}
            getRowKey={(r) => r.transaction_id}
            emptyText="No recent transactions"
          />
        </Panel>
      </div>
    </div>
  );
}
