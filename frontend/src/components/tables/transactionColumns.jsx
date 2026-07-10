import { Badge } from "../common/ui.jsx";
import { formatINR, formatDateTime, truncate } from "../../utils/format.js";

/** Status pill for a transaction outcome. */
export function StatusPill({ status }) {
  const tone = status === "SUCCESS" ? "success" : status === "FAILURE" ? "danger" : "neutral";
  return <Badge tone={tone}>{status}</Badge>;
}

/** Shared column set for transaction-summary tables (dashboard, activity, history). */
export function transactionColumns() {
  return [
    {
      key: "transaction_id",
      header: "Transaction",
      value: (r) => r.transaction_id,
      render: (r) => <span className="font-mono text-xs text-ink-500">{truncate(r.transaction_id, 16)}</span>,
    },
    {
      key: "timestamp",
      header: "Time",
      sortable: true,
      value: (r) => r.timestamp,
      render: (r) => <span className="whitespace-nowrap text-xs">{formatDateTime(r.timestamp)}</span>,
    },
    { key: "type", header: "Type", value: (r) => r.type, render: (r) => <span className="text-xs">{r.type}</span> },
    {
      key: "payee_name",
      header: "Payer → Payee",
      value: (r) => r.payee_name,
      render: (r) => (
        <div className="min-w-0 text-xs">
          <span className="text-ink-400">{truncate(r.payer_vpa, 18)}</span>
          <span className="mx-1 text-ink-300">→</span>
          <span className="font-medium text-ink-700">{truncate(r.payee_name || r.payee_vpa, 18)}</span>
        </div>
      ),
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      sortable: true,
      value: (r) => Number(r.amount ?? 0),
      render: (r) => <span className="text-xs font-medium">{r.amount != null ? formatINR(r.amount) : "—"}</span>,
    },
    {
      key: "status",
      header: "Status",
      align: "right",
      value: (r) => r.status,
      render: (r) => <StatusPill status={r.status} />,
    },
  ];
}
