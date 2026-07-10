import PieChart from "./PieChart.jsx";

/** Donut chart — a pie with a hollow center (thin convenience wrapper). */
export default function DonutChart(props) {
  return <PieChart {...props} donut />;
}
