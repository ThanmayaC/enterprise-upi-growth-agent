import { CHART_PALETTE } from "../../utils/constants.js";

// Shared visual language for every chart: typography, muted gridlines, and a
// consistent tooltip. Keeping this in one place makes all charts look like
// one system.

export const AXIS_LABEL = { color: "#94a3b8", fontSize: 11 };
const SPLIT_LINE = { lineStyle: { color: "#eef2f6" } };
const AXIS_LINE = { lineStyle: { color: "#e2e8f0" } };

export const baseTooltip = (valueFormatter) => ({
  trigger: "axis",
  backgroundColor: "#0f172a",
  borderWidth: 0,
  padding: [8, 12],
  textStyle: { color: "#e2e8f0", fontSize: 12 },
  axisPointer: { type: "shadow", shadowStyle: { color: "rgba(99,102,241,0.06)" } },
  valueFormatter: valueFormatter ? (v) => valueFormatter(v) : undefined,
});

export const itemTooltip = (valueFormatter) => ({
  trigger: "item",
  backgroundColor: "#0f172a",
  borderWidth: 0,
  padding: [8, 12],
  textStyle: { color: "#e2e8f0", fontSize: 12 },
  valueFormatter: valueFormatter ? (v) => valueFormatter(v) : undefined,
});

export const baseGrid = { left: 8, right: 16, top: 24, bottom: 8, containLabel: true };

export const categoryAxis = (data) => ({
  type: "category",
  data,
  axisLabel: { ...AXIS_LABEL, hideOverlap: true },
  axisLine: AXIS_LINE,
  axisTick: { show: false },
});

export const valueAxis = (valueFormatter) => ({
  type: "value",
  axisLabel: {
    ...AXIS_LABEL,
    formatter: valueFormatter ? (v) => valueFormatter(v) : undefined,
  },
  splitLine: SPLIT_LINE,
});

export const palette = CHART_PALETTE;
