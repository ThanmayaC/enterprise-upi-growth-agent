import { PageHeader, Panel, Badge } from "../../components/common/ui.jsx";
import { EmptyState } from "../../components/common/states.jsx";
import Icon from "../../components/common/Icon.jsx";

const FORMATS = [
  { key: "pdf", title: "Executive PDF", desc: "Board-ready portfolio report.", icon: "document", accent: "bg-danger/10 text-danger" },
  { key: "pptx", title: "PowerPoint Deck", desc: "Growth review presentation.", icon: "chart", accent: "bg-warning/10 text-warning" },
  { key: "xlsx", title: "Excel Workbook", desc: "Full data export with pivots.", icon: "grid", accent: "bg-success/10 text-success" },
];

export default function ReportsPage() {
  return (
    <div>
      <PageHeader title="Report Studio" description="Generate branded, shareable reports from live platform analytics.">
        <Badge tone="brand">Coming in Phase 13</Badge>
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {FORMATS.map((f) => (
          <Panel key={f.key}>
            <div className="flex flex-col gap-4 p-5">
              <span className={`flex h-11 w-11 items-center justify-center rounded-xl ${f.accent}`}>
                <Icon name={f.icon} size={22} />
              </span>
              <div>
                <p className="text-sm font-semibold text-ink-800">{f.title}</p>
                <p className="mt-1 text-xs text-ink-500">{f.desc}</p>
              </div>
              <button className="btn-ghost cursor-not-allowed opacity-60" disabled>
                <Icon name="document" size={15} />
                Generate
              </button>
            </div>
          </Panel>
        ))}
      </div>

      <div className="mt-6">
        <Panel title="Report History">
          <EmptyState title="No reports yet" hint="Generated reports will be listed here in Phase 13." icon="inbox" />
        </Panel>
      </div>
    </div>
  );
}
