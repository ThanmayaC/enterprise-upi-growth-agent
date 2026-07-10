import { useMemo, useState } from "react";
import { PageHeader, Panel } from "../../components/common/ui.jsx";
import { LoadingBlock, ErrorState } from "../../components/common/states.jsx";
import StatCard from "../../components/cards/StatCard.jsx";
import LineChart from "../../components/charts/LineChart.jsx";
import AreaChart from "../../components/charts/AreaChart.jsx";
import BarChart from "../../components/charts/BarChart.jsx";
import HeatmapChart from "../../components/charts/HeatmapChart.jsx";
import SelectFilter from "../../components/filters/SelectFilter.jsx";
import DateRangeFilter from "../../components/filters/DateRangeFilter.jsx";
import { useApi } from "../../hooks/useApi.js";
import { analyticsApi } from "../../api/endpoints.js";
import { TIME_GRAINS } from "../../utils/constants.js";
import { formatCompact, formatINR, formatPeriod } from "../../utils/format.js";

const STATUS_OPTIONS = [
  { value: "", label: "All outcomes" },
  { value: "SUCCESS", label: "Successful" },
  { value: "FAILURE", label: "Failed" },
];

const HOURS = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}`);

export default function AnalyticsPage() {
  const [grain, setGrain] = useState("monthly");
  const [status, setStatus] = useState("");
  const [range, setRange] = useState({ start_date: null, end_date: null });
  const [hourWindow, setHourWindow] = useState({ start_date: "2024-06-03", end_date: "2024-06-09" });

  const key = `${grain}:${status}:${range.start_date || "all"}:${range.end_date || "all"}`;
  const trend = useApi(
    () => analyticsApi.time(grain, { ...range, status: status || undefined }),
    [key],
    { cacheKey: `an:${key}` }
  );
  const hourly = useApi(
    () => analyticsApi.hourly(hourWindow),
    [hourWindow.start_date, hourWindow.end_date],
    { cacheKey: `an:hourly:${hourWindow.start_date}:${hourWindow.end_date}` }
  );

  const series = trend.data?.series || [];
  const cats = series.map((r) => formatPeriod(r.period, grain));
  const summary = trend.data?.summary;

  const hourSeries = hourly.data?.series || [];
  const heatData = useMemo(() => hourSeries.map((r, i) => [i, 0, r.transaction_count]), [hourSeries]);
  const heatMax = useMemo(() => Math.max(1, ...hourSeries.map((r) => r.transaction_count)), [hourSeries]);

  return (
    <div>
      <PageHeader title="Portfolio Analytics" description="Time-series intelligence across every grain — activity, volume, and intraday rhythm.">
        <div className="flex flex-wrap items-center gap-2">
          <SelectFilter label="Grain" value={grain} onChange={setGrain} options={TIME_GRAINS} />
          <SelectFilter label="Outcome" value={status} onChange={setStatus} options={STATUS_OPTIONS} />
          <DateRangeFilter value={range} onChange={setRange} />
        </div>
      </PageHeader>

      {/* Summary tiles */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
        <StatCard label="Total Transactions" value={formatCompact(summary?.total_transactions)} loading={trend.loading} />
        <StatCard label="Total Volume" value={formatINR(summary?.total_amount)} loading={trend.loading} />
        <StatCard label="Avg / Period" value={formatCompact(summary?.average_transactions_per_period)} loading={trend.loading} />
        <StatCard label="Peak Period" value={summary?.peak_period ? formatPeriod(summary.peak_period.period, grain) : "—"} sub={summary?.peak_period ? formatCompact(summary.peak_period.transaction_count) : undefined} loading={trend.loading} />
        <StatCard label="Trough Period" value={summary?.trough_period ? formatPeriod(summary.trough_period.period, grain) : "—"} sub={summary?.trough_period ? formatCompact(summary.trough_period.transaction_count) : undefined} loading={trend.loading} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Activity Trend" subtitle={`Transactions per ${grain} period`} bodyClassName="p-4">
          {trend.loading ? <LoadingBlock rows={6} /> : trend.error ? <ErrorState error={trend.error} onRetry={trend.refetch} compact /> : (
            <LineChart height={320} categories={cats} valueFormatter={formatCompact}
              series={[{ name: "Transactions", data: series.map((r) => r.transaction_count), color: "#4f46e5" }]} />
          )}
        </Panel>
        <Panel title="Volume Trend" subtitle={`Amount per ${grain} period`} bodyClassName="p-4">
          {trend.loading ? <LoadingBlock rows={6} /> : trend.error ? <ErrorState error={trend.error} onRetry={trend.refetch} compact /> : (
            <AreaChart height={320} categories={cats} valueFormatter={formatINR}
              series={[{ name: "Volume", data: series.map((r) => Number(r.total_amount)), color: "#0ea5e9" }]} />
          )}
        </Panel>
      </div>

      {/* Hourly profile */}
      <div className="mt-6">
        <Panel title="Hour-of-Day Profile" subtitle="Intraday activity rhythm (max 7-day window)"
          actions={<DateRangeFilter value={hourWindow} onChange={setHourWindow} />}>
          {hourly.loading ? <LoadingBlock rows={4} /> : hourly.error ? <ErrorState error={hourly.error} onRetry={hourly.refetch} compact /> : (
            <div className="space-y-4 p-4">
              <HeatmapChart xCategories={HOURS} yCategories={["Activity"]} data={heatData} max={heatMax} height={120} valueFormatter={formatCompact} />
              <BarChart height={240} categories={HOURS} series={[{ name: "Transactions", data: hourSeries.map((r) => r.transaction_count) }]} valueFormatter={formatCompact} color="#818cf8" />
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
