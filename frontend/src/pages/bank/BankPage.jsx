import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader, Panel, Tabs } from "../../components/common/ui.jsx";
import { LoadingBlock, ErrorState } from "../../components/common/states.jsx";
import StatCard from "../../components/cards/StatCard.jsx";
import BarChart from "../../components/charts/BarChart.jsx";
import DonutChart from "../../components/charts/DonutChart.jsx";
import LineChart from "../../components/charts/LineChart.jsx";
import DataTable from "../../components/tables/DataTable.jsx";
import Icon from "../../components/common/Icon.jsx";
import { useApi } from "../../hooks/useApi.js";
import { bankApi } from "../../api/endpoints.js";
import { formatCompact, formatINR, formatPercent, formatPeriod, truncate } from "../../utils/format.js";

const SIDES = [
  { value: "issuer", label: "Issuer (Debit)" },
  { value: "acquirer", label: "Acquirer (Credit)" },
];

const YEAR = { start_date: "2024-01-01", end_date: "2024-12-31" };

export default function BankPage() {
  const [params, setParams] = useSearchParams();
  const side = params.get("side") === "acquirer" ? "acquirer" : "issuer";
  const selected = params.get("name") || null;
  const setSide = (s) => setParams(selected ? { side: s, name: selected } : { side: s }, { replace: true });
  const clearSelected = () => setParams({ side }, { replace: true });

  const rankings = useApi(() => bankApi.rankings({ side, by: "total_transactions", top_n: 15 }), [side], { cacheKey: `b:rank:${side}` });
  const contribution = useApi(() => bankApi.contribution({ side, top_n: 8 }), [side], { cacheKey: `b:contrib:${side}` });
  const success = useApi(() => bankApi.successComparison({ side, minimum_transactions: 100 }), [side], { cacheKey: `b:success:${side}` });

  const stats = useApi(() => bankApi.statistics(selected, side), [selected, side], { enabled: !!selected });
  const trend = useApi(() => bankApi.trend(selected, { ...YEAR, side }), [selected, side], { enabled: !!selected });

  const ranked = rankings.data || [];
  const contribData = useMemo(() => {
    const c = contribution.data;
    if (!c) return [];
    const leaders = c.leaders || [];
    const sum = leaders.reduce((n, r) => n + r.total_transactions, 0);
    const rest = Math.max(0, c.total_transactions - sum);
    const slices = leaders.map((r) => ({ name: truncate(r.bank, 16), value: r.total_transactions }));
    if (rest > 0) slices.push({ name: "Others", value: rest });
    return slices;
  }, [contribution.data]);

  const rankColumns = [
    { key: "rank", header: "#", value: (r) => r.rank, render: (r) => <span className="text-ink-400">{r.rank}</span> },
    { key: "bank", header: "Bank", sortable: true, value: (r) => r.bank,
      render: (r) => <button onClick={() => setParams({ side, name: r.bank })} className="font-medium text-brand-700 hover:underline">{r.bank}</button> },
    { key: "total_transactions", header: "Txns", align: "right", sortable: true, value: (r) => r.total_transactions, render: (r) => formatCompact(r.total_transactions) },
    { key: "success_rate", header: "Success", align: "right", sortable: true, value: (r) => r.success_rate, render: (r) => formatPercent(r.success_rate) },
    { key: "total_amount", header: "Volume", align: "right", sortable: true, value: (r) => Number(r.total_amount), render: (r) => formatINR(r.total_amount) },
  ];

  const successColumns = [
    { key: "rank", header: "#", value: (r) => r.rank, render: (r) => <span className="text-ink-400">{r.rank}</span> },
    { key: "bank", header: "Bank", value: (r) => r.bank, render: (r) => <span className="font-medium">{truncate(r.bank, 24)}</span> },
    { key: "success_rate", header: "Success", align: "right", value: (r) => r.success_rate, render: (r) => formatPercent(r.success_rate) },
    { key: "total_transactions", header: "Txns", align: "right", value: (r) => r.total_transactions, render: (r) => formatCompact(r.total_transactions) },
  ];

  const tseries = trend.data?.series || [];

  return (
    <div>
      <PageHeader title="Bank Intelligence" description="Issuer and acquirer performance — rankings, concentration, and payment-success comparison.">
        <Tabs tabs={SIDES} value={side} onChange={setSide} />
      </PageHeader>

      {selected && (
        <div className="mb-6">
          <Panel title={`${selected} · ${side}`} subtitle="Selected bank"
            actions={<button onClick={clearSelected} className="text-ink-400 hover:text-ink-700"><Icon name="close" size={16} /></button>}>
            {stats.loading ? <LoadingBlock rows={3} /> : stats.error ? <ErrorState error={stats.error} onRetry={stats.refetch} compact /> : (
              <div className="space-y-4 p-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <StatCard label="Transactions" value={formatCompact(stats.data?.total_transactions)} />
                  <StatCard label="Successful" value={formatCompact(stats.data?.successful_transactions)} />
                  <StatCard label="Success Rate" value={formatPercent(stats.data?.success_rate)} />
                  <StatCard label="Volume" value={formatINR(stats.data?.total_amount)} />
                </div>
                {trend.data && tseries.length > 0 && (
                  <LineChart height={240} categories={tseries.map((r) => formatPeriod(r.period, "monthly"))} valueFormatter={formatCompact}
                    series={[{ name: "Transactions", data: tseries.map((r) => r.transaction_count), color: "#4f46e5" }]} />
                )}
              </div>
            )}
          </Panel>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel title={`${side === "issuer" ? "Issuer" : "Acquirer"} Rankings`} className="xl:col-span-2">
          <DataTable columns={rankColumns} rows={ranked} loading={rankings.loading} error={rankings.error} onRetry={rankings.refetch} pageSize={10} getRowKey={(r) => r.bank} />
        </Panel>
        <Panel title="Bank Contribution" subtitle="Share of transactions" bodyClassName="p-4">
          {contribution.loading ? <LoadingBlock rows={6} /> : contribution.error ? <ErrorState error={contribution.error} onRetry={contribution.refetch} compact /> : (
            <DonutChart height={300} data={contribData} valueFormatter={formatCompact}
              centerLabel={contribution.data ? `Top ${contribution.data.top_n}\n${formatPercent(contribution.data.top_n_count_share_pct)}` : ""} />
          )}
        </Panel>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Volume by Bank" subtitle="Top banks by settled volume" bodyClassName="p-4">
          {rankings.loading ? <LoadingBlock rows={6} /> : (
            <BarChart horizontal height={320}
              categories={[...ranked].sort((a, b) => Number(b.total_amount) - Number(a.total_amount)).slice(0, 8).map((r) => truncate(r.bank, 18))}
              series={[{ name: "Volume", data: [...ranked].sort((a, b) => Number(b.total_amount) - Number(a.total_amount)).slice(0, 8).map((r) => Number(r.total_amount)) }]}
              valueFormatter={formatINR} color="#0ea5e9" />
          )}
        </Panel>
        <Panel title="Success Analysis" subtitle={`Lowest success rate (min ${success.data?.minimum_transactions ?? 100} txns)`}>
          <DataTable columns={successColumns} rows={success.data?.worst} loading={success.loading} error={success.error} onRetry={success.refetch} pageSize={5} getRowKey={(r) => r.bank} emptyText="No qualifying banks" />
        </Panel>
      </div>
    </div>
  );
}
