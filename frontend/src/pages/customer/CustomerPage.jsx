import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader, Panel, Badge } from "../../components/common/ui.jsx";
import { LoadingBlock, ErrorState } from "../../components/common/states.jsx";
import KpiCard from "../../components/cards/KpiCard.jsx";
import StatCard from "../../components/cards/StatCard.jsx";
import BarChart from "../../components/charts/BarChart.jsx";
import DonutChart from "../../components/charts/DonutChart.jsx";
import DataTable from "../../components/tables/DataTable.jsx";
import { transactionColumns } from "../../components/tables/transactionColumns.jsx";
import EntitySearchBox from "../../components/search/EntitySearchBox.jsx";
import Icon from "../../components/common/Icon.jsx";
import { useApi } from "../../hooks/useApi.js";
import { customerApi } from "../../api/endpoints.js";
import { formatCompact, formatINR, formatPercent, formatDate, truncate } from "../../utils/format.js";

export default function CustomerPage() {
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("id") || null;
  const setSelectedId = (id) => setParams(id ? { id } : {}, { replace: true });

  const profile = useApi(() => customerApi.profile(selectedId), [selectedId], { enabled: !!selectedId });
  const summary = useApi(() => customerApi.summary(selectedId), [selectedId], { enabled: !!selectedId });
  const history = useApi(() => customerApi.history(selectedId, 20), [selectedId], { enabled: !!selectedId });

  const active = useApi(() => customerApi.active(), [], { cacheKey: "c:active" });
  const frequency = useApi(() => customerApi.frequency(), [], { cacheKey: "c:freq" });
  const top = useApi(() => customerApi.top({ n: 15 }), [], { cacheKey: "c:top" });

  const a = active.data;
  const f = frequency.data;

  const freqBars = f?.frequency_histogram || [];
  const repeatDonut = useMemo(
    () =>
      f
        ? [
            { name: "Single transaction", value: f.single_transaction_customers },
            { name: "Repeat", value: f.repeat_customers },
          ]
        : [],
    [f]
  );

  const topColumns = [
    { key: "rank", header: "#", value: (r) => r.rank, render: (r) => <span className="text-ink-400">{r.rank}</span> },
    { key: "customer_vpa", header: "Customer VPA", sortable: true, value: (r) => r.customer_vpa,
      render: (r) => <span className="font-mono text-xs text-ink-600">{truncate(r.customer_vpa, 30)}</span> },
    { key: "transaction_count", header: "Transactions", align: "right", sortable: true, value: (r) => r.transaction_count, render: (r) => formatCompact(r.transaction_count) },
    { key: "total_amount", header: "Total Spent", align: "right", sortable: true, value: (r) => Number(r.total_amount), render: (r) => formatINR(r.total_amount) },
  ];

  const s = summary.data;

  return (
    <div>
      <PageHeader title="Customer Intelligence" description="Search a customer for their behaviour and history, or explore activation, frequency, and the most active customers.">
        <EntitySearchBox
          fetcher={(term) => customerApi.search({ q: term, limit: 8 }).then((p) => p.items)}
          idKey="customer_id" labelKey="customer_name" subKey="vpa"
          onSelect={(c) => setSelectedId(c.customer_id)}
          placeholder="Search customers by name…"
        />
      </PageHeader>

      {selectedId && (
        <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
          <Panel title="Customer Profile"
            actions={<button onClick={() => setSelectedId(null)} className="text-ink-400 hover:text-ink-700"><Icon name="close" size={16} /></button>}>
            {profile.loading ? <LoadingBlock rows={4} /> : profile.error ? <ErrorState error={profile.error} onRetry={profile.refetch} compact /> : (
              <div className="space-y-3 p-4">
                <div>
                  <p className="text-base font-semibold text-ink-900">{profile.data?.customer_name}</p>
                  <p className="text-xs text-ink-400">{profile.data?.vpa}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge tone="brand">{profile.data?.psp}</Badge>
                  <Badge tone="neutral">{profile.data?.bank}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><p className="text-xs text-ink-400">Mobile</p><p className="font-medium">{profile.data?.mobile}</p></div>
                  <div><p className="text-xs text-ink-400">Account</p><p className="font-medium">{profile.data?.account_type}</p></div>
                </div>
              </div>
            )}
          </Panel>
          <Panel title="Behaviour Summary" className="xl:col-span-2" bodyClassName="p-4">
            {summary.loading ? <LoadingBlock rows={3} /> : summary.error ? <ErrorState error={summary.error} onRetry={summary.refetch} compact /> : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard label="Transactions" value={formatCompact(s?.total_transactions)} />
                <StatCard label="Success Rate" value={formatPercent(s?.success_rate)} />
                <StatCard label="Total Spent" value={formatINR(s?.total_spent)} />
                <StatCard label="Active Since" value={formatDate(s?.first_transaction_date)} sub={`Last: ${formatDate(s?.last_transaction_date)}`} />
              </div>
            )}
          </Panel>
        </div>
      )}

      {selectedId && (
        <div className="mb-6">
          <Panel title="Transaction History" subtitle="Most recent transactions">
            <DataTable columns={transactionColumns()} rows={history.data} loading={history.loading} error={history.error} onRetry={history.refetch} pageSize={8} getRowKey={(r) => r.transaction_id} emptyText="No transaction history" />
          </Panel>
        </div>
      )}

      {/* Base analytics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {active.loading ? (
          Array.from({ length: 4 }).map((_, i) => <KpiCard key={i} title=" " loading />)
        ) : active.error ? (
          <div className="col-span-full"><Panel><ErrorState error={active.error} onRetry={active.refetch} /></Panel></div>
        ) : (
          <>
            <KpiCard title="Active Customers" value={a?.active_customers} unit="customers" icon="users" accent="brand" />
            <KpiCard title="Registered" value={a?.registered_customers} unit="customers" icon="users" accent="sky" />
            <KpiCard title="Activation Rate" value={a?.activation_rate_pct} unit="%" icon="check" accent="success" />
            <KpiCard title="Avg Txns / Active" display={formatCompact(a?.average_transactions_per_active_customer)} icon="activity" accent="brand" />
          </>
        )}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel title="Transaction Frequency" subtitle="Customers by transaction-count bucket" className="xl:col-span-2" bodyClassName="p-4">
          {frequency.loading ? <LoadingBlock rows={5} /> : frequency.error ? <ErrorState error={frequency.error} onRetry={frequency.refetch} compact /> : (
            <BarChart height={280} categories={freqBars.map((b) => b.bucket)} series={[{ name: "Customers", data: freqBars.map((b) => b.count) }]} valueFormatter={formatCompact} color="#4f46e5" />
          )}
        </Panel>
        <Panel title="Repeat vs Single" subtitle="Engagement split" bodyClassName="p-4">
          {frequency.loading ? <LoadingBlock rows={5} /> : frequency.error ? <ErrorState error={frequency.error} onRetry={frequency.refetch} compact /> : (
            <DonutChart height={280} data={repeatDonut} valueFormatter={formatCompact}
              centerLabel={f ? `Repeat\n${formatPercent(f.repeat_share_pct)}` : ""} />
          )}
        </Panel>
      </div>

      <div className="mt-6">
        <Panel title="Most Active Customers" subtitle="Top customers by transaction count">
          <DataTable columns={topColumns} rows={top.data} loading={top.loading} error={top.error} onRetry={top.refetch} pageSize={10} getRowKey={(r) => r.customer_vpa} />
        </Panel>
      </div>
    </div>
  );
}
