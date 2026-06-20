import { useState, useCallback } from "react";
import { Outlet } from "react-router-dom";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";
import { LiveAlertsProvider } from "@/context/LiveAlertsContext";

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const toggleSidebar = useCallback(() => setSidebarOpen((o) => !o), []);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  return (
    <LiveAlertsProvider>
      <div className="min-h-screen bg-background flex flex-col">
        <TopBar onMenuToggle={toggleSidebar} />
        <div className="flex flex-1 relative">
          <Sidebar open={sidebarOpen} onClose={closeSidebar} />
          <main className="flex-1 overflow-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </LiveAlertsProvider>
  );
}
