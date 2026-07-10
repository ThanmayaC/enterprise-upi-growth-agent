import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader, Panel, Badge } from "../../components/common/ui.jsx";
import { LoadingBlock, ErrorState, EmptyState } from "../../components/common/states.jsx";
import StatCard from "../../components/cards/StatCard.jsx";
import DonutChart from "../../components/charts/DonutChart.jsx";
import BarChart from "../../components/charts/BarChart.jsx";
import DataTable from "../../components/tables/DataTable.jsx";
import { transactionColumns } from "../../components/tables/transactionColumns.jsx";
import EntitySearchBox from "../../components/search/EntitySearchBox.jsx";
import SelectFilter from "../../components/filters/SelectFilter.jsx";
import Icon from "../../components/common/Icon.jsx";
import { useApi } from "../../hooks/useApi.js";
import { merchantApi } from "../../api/endpoints.js";
import { formatCompact, formatINR, formatPercent, truncate } from "../../utils/format.js";

const METRICS = [
  { value: "total_transactions", label: "Transactions" },
  { value: "total_amount", label: "Volume" },
  { value: "success_rate", label: "Success Rate" },
];

export default function MerchantPage() {
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("id") || null;
  const setSelectedId = (id) => setParams(id ? { id } : {}, { replace: true });

  const [metric, setMetric] = useState("total_transactions");
  const [compareIds, setCompareIds] = useState([]);
  const [compareRows, setCompareRows] = useState(null);

  const profile = useApi(() => merchantApi.profile(selectedId), [selectedId], { enabled: !!selectedId });
  const summary = useApi(() => merchantApi.summary(selectedId), [selectedId], { enabled: !!selectedId });
  const activity = useApi(() => merchantApi.activity(selectedId, 20), [selectedId], { enabled: !!selectedId });

  const rankings = useApi(() => merchantApi.top({ n: 15, by: metric }), [metric], { cacheKey: `m:top:${metric}` });
  const contribution = useApi(() => merchantApi.contribution({ top_n: 8 }), [], { cacheKey: "m:contrib" });
  const distribution = useApi(() => merchantApi.distribution(), [], { cacheKey: "m:dist" });

  const addCompare = (id) => setCompareIds((prev) => (prev.includes(id) ? prev : [...prev, id]).slice(-6));
  const removeCompare = (id) => setCompareIds((prev) => prev.filter((x) => x !== id));
  useEffect(() => {
    if (compareIds.length < 2) {
      setCompareRows(null);
      return;
    }
    let cancelled = false;
    merchantApi.compare({ merchant_ids: compareIds }).then((r) => !cancelled && setCompareRows(r)).catch(() => {});
    return () => { cancelled = true; };
  }, [compareIds]);

  const contribData = useMemo(() => {
    const c = contribution.data;
    if (!c) return [];
    const top = c.top_merchants || [];
    const sum = top.reduce((n, r) => n + r.total_transactions, 0);
    const rest = Math.max(0, c.total_transactions - sum);
    const slices = top.map((r) => ({ name: truncate(r.merchant_name, 16), value: r.total_transactions }));
    if (rest > 0) slices.push({ name: "Others", value: rest });
    return slices;
  }, [contribution.data]);

  const hist = distribution.data?.count_histogram || [];

  const rankColumns = [
    { key: "rank", header: "#", value: (r) => r.rank, render: (r) => <span className="text-ink-400">{r.rank}</span> },
    { key: "merchant_name", header: "Merchant", sortable: true, value: (r) => r.merchant_name,
      render: (r) => <button onClick={() => setSelectedId(r.merchant_id)} className="font-medium text-brand-700 hover:underline">{truncate(r.merchant_name, 26)}</button> },
    { key: "total_transactions", header: "Txns", align: "right", sortable: true, value: (r) => r.total_transactions, render: (r) => formatCompact(r.total_transactions) },
    { key: "success_rate", header: "Success", align: "right", sortable: true, value: (r) => r.success_rate, render: (r) => formatPercent(r.success_rate) },
    { key: "total_amount", header: "Volume", align: "right", sortable: true, value: (r) => Number(r.total_amount), render: (r) => formatINR(r.total_amount) },
    { key: "action", header: "", align: "right", render: (r) => (
      <button onClick={() => addCompare(r.merchant_id)} className="text-ink-400 hover:text-brand-600" title="Add to comparison"><Icon name="filter" size={14} /></button>
    ) },
  ];

  const s = summary.data;

  return (
    <div>
      <PageHeader title="Merchant Intelligence" description="Search a merchant to inspect its profile and activity, or explore rankings, concentration, and distribution across the base.">
        <EntitySearchBox
          fetcher={(term) => merchantApi.search({ q: term, limit: 8 }).then((p) => p.items)}
          idKey="merchant_id" labelKey="merchant_name" subKey="merchant_id"
          onSelect={(m) => setSelectedId(m.merchant_id)}
          placeholder="Search merchants by name…"
        />
      </PageHeader>

      {/* Selected merchant */}
      {selectedId && (
        <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
          <Panel title="Merchant Profile" className="xl:col-span-1"
            actions={<button onClick={() => setSelectedId(null)} className="text-ink-400 hover:text-ink-700"><Icon name="close" size={16} /></button>}>
            {profile.loading ? <LoadingBlock rows={5} /> : profile.error ? <ErrorState error={profile.error} onRetry={profile.refetch} compact /> : (
              <div className="space-y-3 p-4">
                <div>
                  <p className="text-base font-semibold text-ink-900">{profile.data?.merchant_name}</p>
                  <p className="text-xs text-ink-400">{profile.data?.vpa}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge tone="brand">{profile.data?.merchant_type || "—"}</Badge>
                  <Badge tone="neutral">MCC {profile.data?.mcc_code || "—"}</Badge>
                  <Badge tone="neutral">{profile.data?.merchant_genre || "—"}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-1 text-sm">
                  <div><p className="text-xs text-ink-400">PSP</p><p className="font-medium">{profile.data?.psp}</p></div>
                  <div><p className="text-xs text-ink-400">Bank</p><p className="font-medium">{profile.data?.bank}</p></div>
                </div>
              </div>
            )}
          </Panel>

          <Panel title="Performance Summary" className="xl:col-span-2" bodyClassName="p-4">
            {summary.loading ? <LoadingBlock rows={3} /> : summary.error ? <ErrorState error={summary.error} onRetry={summary.refetch} compact /> : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard label="Transactions" value={formatCompact(s?.total_transactions)} />
                <StatCard label="Successful" value={formatCompact(s?.successful_transactions)} />
                <StatCard label="Success Rate" value={formatPercent(s?.success_rate)} />
                <StatCard label="Received" value={formatINR(s?.total_received)} />
              </div>
            )}
          </Panel>
        </div>
      )}

      {selectedId && (
        <div className="mb-6">
          <Panel title="Recent Activity" subtitle="Latest payments received">
            <DataTable columns={transactionColumns()} rows={activity.data} loading={activity.loading} error={activity.error} onRetry={activity.refetch} pageSize={8} getRowKey={(r) => r.transaction_id} emptyText="No recent activity" />
          </Panel>
        </div>
      )}

      {/* Analytics */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel title="Merchant Rankings" className="xl:col-span-2"
          actions={<SelectFilter label="By" value={metric} onChange={setMetric} options={METRICS} />}>
          <DataTable columns={rankColumns} rows={rankings.data} loading={rankings.loading} error={rankings.error} onRetry={rankings.refetch} pageSize={10} getRowKey={(r) => r.merchant_id} />
        </Panel>
        <Panel title="Contribution" subtitle="Top merchants' share of transactions" bodyClassName="p-4">
          {contribution.loading ? <LoadingBlock rows={6} /> : contribution.error ? <ErrorState error={contribution.error} onRetry={contribution.refetch} compact /> : (
            <DonutChart height={300} data={contribData} valueFormatter={formatCompact}
              centerLabel={contribution.data ? `Top ${contribution.data.top_merchants?.length}\n${formatPercent(contribution.data[`top_${contribution.data.top_merchants?.length}_count_share_pct`])}` : ""} />
          )}
        </Panel>
      </div>

      <div className="mt-6">
        <Panel title="Activity Distribution" subtitle="How merchants distribute across transaction-count buckets" bodyClassName="p-4">
          {distribution.loading ? <LoadingBlock rows={5} /> : distribution.error ? <ErrorState error={distribution.error} onRetry={distribution.refetch} compact /> : (
            <BarChart height={280} categories={hist.map((b) => b.bucket)} series={[{ name: "Merchants", data: hist.map((b) => b.count) }]} valueFormatter={formatCompact} color="#4f46e5" />
          )}
        </Panel>
      </div>

      {/* Comparison */}
      <div className="mt-6">
        <Panel title="Merchant Comparison" subtitle="Add merchants from the rankings table to compare">
          <div className="p-4">
            {compareIds.length === 0 ? (
              <EmptyState compact title="No merchants selected" hint="Use the filter icon in the rankings table to add merchants (min. 2)." icon="filter" />
            ) : (
              <>
                <div className="mb-3 flex flex-wrap gap-2">
                  {compareIds.map((id) => (
                    <span key={id} className="chip bg-brand-50 text-brand-700">
                      {id}
                      <button onClick={() => removeCompare(id)} className="ml-1"><Icon name="close" size={12} /></button>
                    </span>
                  ))}
                </div>
                {compareIds.length < 2 ? (
                  <p className="text-sm text-ink-400">Add at least one more merchant to compare.</p>
                ) : compareRows ? (
                  <DataTable
                    columns={[
                      { key: "merchant_name", header: "Merchant", value: (r) => r.merchant_name, render: (r) => <span className="font-medium">{truncate(r.merchant_name, 24)}</span> },
                      { key: "total_transactions", header: "Txns", align: "right", value: (r) => r.total_transactions, render: (r) => formatCompact(r.total_transactions) },
                      { key: "success_rate", header: "Success", align: "right", value: (r) => r.success_rate, render: (r) => formatPercent(r.success_rate) },
                      { key: "total_amount", header: "Volume", align: "right", value: (r) => Number(r.total_amount), render: (r) => formatINR(r.total_amount) },
                    ]}
                    rows={compareRows}
                    pageSize={6}
                    getRowKey={(r) => r.merchant_id}
                  />
                ) : (
                  <LoadingBlock rows={3} />
                )}
              </>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
