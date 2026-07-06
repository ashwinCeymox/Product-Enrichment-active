import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, 
  FilePlus2, 
  CheckSquare, 
  Image as ImageIcon, 
  PackageCheck, 
  AlertTriangle,
  Settings,
  ChevronLeft,
  ChevronRight,
  UserCircle,
  LogOut
} from 'lucide-react';
import clsx from 'clsx';

const ALL_NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', roles: ['SUPERADMIN', 'ADMIN', 'NORMALUSER'] },
  { to: '/jobs/create', icon: FilePlus2, label: 'Create Job', roles: ['SUPERADMIN', 'ADMIN', 'NORMALUSER'] },
  { to: '/approvals/json', icon: CheckSquare, label: 'JSON Review', roles: ['SUPERADMIN', 'ADMIN'] },
  { to: '/approvals/images', icon: ImageIcon, label: 'Image Review', roles: ['SUPERADMIN', 'ADMIN'] },
  { to: '/bundles', icon: PackageCheck, label: 'Bundle Review', roles: ['SUPERADMIN', 'ADMIN', 'NORMALUSER'] },
  { to: '/error-logs', icon: AlertTriangle, label: 'Error Logs', roles: ['SUPERADMIN', 'ADMIN', 'NORMALUSER'] },
  { to: '/settings', icon: Settings, label: 'Settings', roles: ['SUPERADMIN'] },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();

  const navItems = ALL_NAV_ITEMS.filter(item => item.roles.includes(user.role));

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-50">
      {/* Sidebar */}
      <aside 
        className={clsx(
          "bg-slate-900 text-slate-300 flex flex-col transition-all duration-300",
          collapsed ? "w-16" : "w-60"
        )}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800 shrink-0">
          {!collapsed && <span className="font-bold text-white text-sm tracking-tight">Active Fitness</span>}
          <button 
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-white"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        <nav className="flex-1 py-4 flex flex-col gap-1 px-2 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => clsx(
                "flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium",
                isActive 
                  ? "bg-primary text-white" 
                  : "hover:bg-slate-800 hover:text-white"
              )}
              title={collapsed ? item.label : undefined}
            >
              <item.icon size={18} className="shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-800 shrink-0">
          <div className="flex items-center gap-3 mb-4">
            <UserCircle size={24} className="text-slate-400 shrink-0" />
            {!collapsed && (
              <div className="flex flex-col overflow-hidden">
                <span className="text-xs font-semibold text-white truncate">{user.name}</span>
                <span className="text-[10px] text-slate-500">{user.role}</span>
              </div>
            )}
          </div>
          
          <button 
            onClick={logout}
            className={clsx(
              "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors",
              collapsed && "justify-center px-0"
            )}
            title={collapsed ? "Logout" : undefined}
          >
            <LogOut size={18} className="shrink-0" />
            {!collapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0 shadow-sm z-10">
          <h1 className="text-lg font-semibold text-slate-800">Product Enrichment Pipeline</h1>
          <div className="text-sm font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
            {user.role} Mode
          </div>
        </header>
        <div className="flex-1 overflow-auto p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
