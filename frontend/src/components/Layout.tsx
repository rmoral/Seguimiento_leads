import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItem = (to: string, label: string) => {
    const active = location.pathname === to;
    return (
      <Link
        to={to}
        className={`px-3 py-2 rounded-md text-sm font-medium ${
          active ? "bg-slate-800 text-white" : "text-slate-300 hover:bg-slate-700"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="text-lg font-semibold">Seguimiento Leads</span>
            <nav className="flex gap-1">
              {navItem("/leads", "Leads")}
              {navItem("/settings", "Ajustes")}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-300">{user?.email}</span>
            <button
              onClick={logout}
              className="bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-md"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
