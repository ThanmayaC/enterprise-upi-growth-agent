import { Suspense, useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "../navigation/Sidebar.jsx";
import Topbar from "./Topbar.jsx";
import Footer from "./Footer.jsx";
import { Spinner } from "../common/states.jsx";

/** The persistent workspace chrome: sidebar + topbar + routed content + footer. */
export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-ink-100">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="lg:pl-64">
        <Topbar onMenu={() => setSidebarOpen(true)} />
        <main className="mx-auto min-h-[calc(100vh-8rem)] max-w-[1600px] px-4 py-6 lg:px-6">
          <Suspense
            fallback={
              <div className="flex h-64 items-center justify-center">
                <Spinner size={26} />
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </main>
        <Footer />
      </div>
    </div>
  );
}
