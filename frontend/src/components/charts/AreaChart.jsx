import LineChart from "./LineChart.jsx";

/** Area chart — a line chart with gradient fill (thin convenience wrapper). */
export default function AreaChart(props) {
  return <LineChart {...props} area />;
}
