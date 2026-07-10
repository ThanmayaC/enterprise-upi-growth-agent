import { useMemo } from "react";
import EChart from "./EChart.jsx";
import { AXIS_LABEL, itemTooltip } from "./chartBase.js";

/**
 * Reusable heatmap. `data` is `[[xIndex, yIndex, value], ...]`. Used for
 * intensity views such as the hour-of-day activity profile.
 */
export default function HeatmapChart({
  xCategories,
  yCategories,
  data,
  height = 200,
  valueFormatter,
  max,
}) {
  const option = useMemo(() => {
    return {
      tooltip: itemTooltip(valueFormatter),
      grid: { left: 8, right: 8, top: 10, bottom: 24, containLabel: true },
      xAxis: {
        type: "category",
        data: xCategories,
        splitArea: { show: true },
        axisLabel: { ...AXIS_LABEL, interval: 1 },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#e2e8f0" } },
      },
      yAxis: {
        type: "category",
        data: yCategories,
        axisLabel: AXIS_LABEL,
        axisTick: { show: false },
        axisLine: { show: false },
      },
      visualMap: {
        min: 0,
        max: max || 100,
        calculable: false,
        show: false,
        inRange: { color: ["#eef2ff", "#818cf8", "#4338ca"] },
      },
      series: [
        {
          type: "heatmap",
          data,
          itemStyle: { borderColor: "#fff", borderWidth: 2, borderRadius: 3 },
          emphasis: { itemStyle: { shadowBlur: 6, shadowColor: "rgba(67,56,202,0.4)" } },
        },
      ],
    };
  }, [xCategories, yCategories, data, valueFormatter, max]);

  return <EChart option={option} height={height} />;
}
