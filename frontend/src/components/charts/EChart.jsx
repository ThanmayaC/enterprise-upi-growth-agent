import { useEffect, useRef } from "react";
import * as echarts from "echarts";

/**
 * Base Apache ECharts wrapper. Owns the chart lifecycle for every
 * visualization in the workspace:
 *   - initializes once on mount, disposes on unmount (no leaks),
 *   - auto-resizes via a ResizeObserver (charts fill their container fluidly),
 *   - applies new options with `notMerge` so data updates never leave stale
 *     series behind.
 * Callers pass a memoized `option` object; all option-building lives in the
 * thin chart components that wrap this.
 */
export default function EChart({ option, height = 320, className = "" }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    const chart = echarts.init(containerRef.current, null, { renderer: "canvas" });
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(containerRef.current);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (chartRef.current && option) {
      chartRef.current.setOption(option, true);
    }
  }, [option]);

  return <div ref={containerRef} style={{ height }} className={className} />;
}
