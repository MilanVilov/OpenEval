import { NavLink } from 'react-router-dom';
import { BarChart3, Settings, Play, Database, FileText, Terminal } from 'lucide-react';
import type { ReactNode } from 'react';

interface NavItemProps {
  to: string;
  icon: ReactNode;
  label: string;
}

function NavItem({ to, icon, label }: NavItemProps) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-2 rounded px-3 py-2 text-sm transition-all duration-150
         ${isActive
           ? 'bg-accent-muted text-foreground border-l-2 border-accent'
           : 'text-foreground-secondary hover:text-foreground hover:bg-[rgba(255,255,255,0.04)]'
         }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}

export function Sidebar() {
  return (
    <aside className="flex w-[220px] flex-col bg-background-secondary border-r border-border p-4 gap-1">
      <div className="mb-4 px-3">
        <h1 className="text-lg font-semibold text-foreground">ai-eval</h1>
        <p className="text-xs text-foreground-secondary">Evaluation Framework</p>
      </div>
      <NavItem to="/" icon={<BarChart3 className="h-4 w-4" />} label="Dashboard" />
      <NavItem to="/configs" icon={<Settings className="h-4 w-4" />} label="Configs" />
      <NavItem to="/datasets" icon={<Database className="h-4 w-4" />} label="Datasets" />
      <NavItem to="/runs" icon={<Play className="h-4 w-4" />} label="Runs" />
      <NavItem to="/vector-stores" icon={<FileText className="h-4 w-4" />} label="Vector Stores" />
      <NavItem to="/containers" icon={<Terminal className="h-4 w-4" />} label="Containers" />
    </aside>
  );
}
