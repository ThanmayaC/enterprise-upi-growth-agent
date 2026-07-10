import { lazy } from "react";
import { Routes, Route, Link } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout.jsx";
import { EmptyState } from "./components/common/states.jsx";

// Route-based code splitting: every page is a separate lazy chunk, so the
// initial load ships only the shell + dashboard.
const DashboardPage = lazy(() => import("./pages/dashboard/DashboardPage.jsx"));
const PortfolioPage = lazy(() => import("./pages/portfolio/PortfolioPage.jsx"));
const MerchantPage = lazy(() => import("./pages/merchant/MerchantPage.jsx"));
const CustomerPage = lazy(() => import("./pages/customer/CustomerPage.jsx"));
const BankPage = lazy(() => import("./pages/bank/BankPage.jsx"));
const PspPage = lazy(() => import("./pages/psp/PspPage.jsx"));
const AnalyticsPage = lazy(() => import("./pages/analytics/AnalyticsPage.jsx"));
const CopilotPage = lazy(() => import("./pages/copilot/CopilotPage.jsx"));
const ReportsPage = lazy(() => import("./pages/reports/ReportsPage.jsx"));
const AdminPage = lazy(() => import("./pages/admin/AdminPage.jsx"));

function NotFound() {
  return (
    <div className="panel">
      <EmptyState
        title="Page not found"
        hint="The page you are looking for does not exist in the workspace."
        icon="alert"
      />
      <div className="flex justify-center pb-6">
        <Link to="/" className="btn-primary">
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="merchants" element={<MerchantPage />} />
        <Route path="customers" element={<CustomerPage />} />
        <Route path="banks" element={<BankPage />} />
        <Route path="psps" element={<PspPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="copilot" element={<CopilotPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
