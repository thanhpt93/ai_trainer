import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { Navbar } from '../components/Navbar';
import { useAppStore } from '../stores/appStore';

export const AppLayout: React.FC = () => {
  const { checkBackendStatus, fetchSystemInfo } = useAppStore();

  useEffect(() => {
    // Initial health & system info check
    checkBackendStatus();
    fetchSystemInfo();

    // Periodic heartbeat check every 10 seconds
    const interval = setInterval(() => {
      checkBackendStatus();
    }, 10000);

    return () => clearInterval(interval);
  }, [checkBackendStatus, fetchSystemInfo]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-6 bg-slate-950">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
