import { useMemo } from "react";
import * as echarts from "echarts";
import EChart from "./EChart.jsx";
import { baseGrid, baseTooltip, categoryAxis, valueAxis, palette } from "./chartBase.js";

/**
 * Reusable line/area chart. One or more series over a shared category axis;
 * set `area` for a gradient-filled area chart.
 */
export default function LineChart({
  categories,
  series,
  area = false,
  smooth = true,
  height = 320,
  valueFormatter,
}) {
  const option = useMemo(() => {
    return {
      color: palette,
      grid: baseGrid,
      tooltip: baseTooltip(valueFormatter),
      legend: series.length > 1 ? { top: 0, textStyle: { color: "#64748b" }, icon: "roundRect" } : undefined,
      xAxis: { ...categoryAxis(categories), boundaryGap: false },
      yAxis: valueAxis(valueFormatter),
      series: series.map((s, i) => {
        const base = s.color || palette[i % palette.length];
        return {
          name: s.name,
          type: "line",
          smooth,
          showSymbol: false,
          lineStyle: { width: 2.5, color: base },
          itemStyle: { color: base },
          areaStyle: area
            ? {
                opacity: 0.18,
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: base },
                  { offset: 1, color: "rgba(255,255,255,0)" },
                ]),
              }
            : undefined,
          data: s.data,
        };
      }),
    };
  }, [categories, series, area, smooth, valueFormatter]);

  return <EChart option={option} height={height} />;
}
