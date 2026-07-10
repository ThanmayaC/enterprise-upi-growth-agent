import { useMemo } from "react";
import EChart from "./EChart.jsx";
import { itemTooltip, palette } from "./chartBase.js";

/**
 * Reusable pie/donut chart. Set `donut` for a ring with a centered total.
 * Data is `[{ name, value }]`.
 */
export default function PieChart({
  data,
  donut = false,
  height = 320,
  valueFormatter,
  centerLabel,
}) {
  const option = useMemo(() => {
    return {
      color: palette,
      tooltip: itemTooltip(valueFormatter),
      legend: {
        type: "scroll",
        orient: "vertical",
        right: 0,
        top: "center",
        textStyle: { color: "#64748b", fontSize: 12 },
        icon: "circle",
      },
      series: [
        {
          type: "pie",
          radius: donut ? ["52%", "78%"] : ["0%", "72%"],
          center: ["38%", "50%"],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: "#fff", borderWidth: 2 },
          label: donut
            ? {
                show: true,
                position: "center",
                formatter: () => centerLabel || "",
                fontSize: 13,
                color: "#334155",
                lineHeight: 18,
              }
            : { color: "#64748b", fontSize: 11 },
          labelLine: { show: !donut },
          data,
        },
      ],
    };
  }, [data, donut, valueFormatter, centerLabel]);

  return <EChart option={option} height={height} />;
}
