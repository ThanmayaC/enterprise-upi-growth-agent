import { useMemo } from "react";
import EChart from "./EChart.jsx";
import { baseGrid, baseTooltip, categoryAxis, valueAxis, palette } from "./chartBase.js";

/**
 * Reusable bar chart. Supports vertical/horizontal orientation, multiple or
 * stacked series, and a value formatter for axis + tooltip.
 */
export default function BarChart({
  categories,
  series,
  horizontal = false,
  stack = false,
  height = 320,
  valueFormatter,
  color,
}) {
  const option = useMemo(() => {
    const cat = categoryAxis(categories);
    const val = valueAxis(valueFormatter);
    return {
      color: color ? [color] : palette,
      grid: baseGrid,
      tooltip: baseTooltip(valueFormatter),
      legend: series.length > 1 ? { top: 0, textStyle: { color: "#64748b" }, icon: "roundRect" } : undefined,
      xAxis: horizontal ? val : cat,
      yAxis: horizontal ? { ...cat, inverse: true } : val,
      series: series.map((s) => ({
        name: s.name,
        type: "bar",
        stack: stack ? "total" : undefined,
        data: s.data,
        barMaxWidth: 26,
        itemStyle: { borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0], color: s.color },
        emphasis: { focus: "series" },
      })),
    };
  }, [categories, series, horizontal, stack, valueFormatter, color]);

  return <EChart option={option} height={height} />;
}
