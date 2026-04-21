import { NavLink } from 'react-router-dom';
import { BarChart3, Settings, Play, Database, FileText, Terminal, MessageSquareCode, Clock } from 'lucide-react';
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

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
        cn(
          'group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-all duration-200 ease-[var(--ease-smooth)]',
          isActive
            ? 'bg-accent-muted text-foreground border-l-2 border-accent shadow-subtle'
            : 'text-foreground-secondary hover:text-foreground hover:bg-[rgba(255,255,255,0.04)] hover:translate-x-0.5'
        )
      }
    >
      <span className="transition-transform duration-200 group-hover:scale-110">{icon}</span>
      {label}
    </NavLink>
  );
}

export function Sidebar() {
  return (
    <aside className="flex w-[240px] flex-col bg-background-secondary border-r border-border p-4 gap-0.5 animate-slide-in-left" style={{ animationDuration: '300ms' }}>
      <div className="mb-6 px-3 pt-2">
        <h1 className="text-lg font-semibold text-foreground tracking-tight">OpenEval</h1>
        <p className="text-xs text-foreground-secondary mt-0.5">Evaluation Framework</p>
      </div>

      <p className="text-[10px] font-medium text-foreground-disabled uppercase tracking-widest px-3 mb-1">Navigation</p>
      <NavItem to="/" icon={<BarChart3 className="h-4 w-4" />} label="Dashboard" />
      <NavItem to="/configs" icon={<Settings className="h-4 w-4" />} label="Configs" />
      <NavItem to="/datasets" icon={<Database className="h-4 w-4" />} label="Datasets" />
      <NavItem to="/runs" icon={<Play className="h-4 w-4" />} label="Runs" />
      <NavItem to="/schedules" icon={<Clock className="h-4 w-4" />} label="Schedules" />
      <NavItem to="/vector-stores" icon={<FileText className="h-4 w-4" />} label="Vector Stores" />
      <NavItem to="/containers" icon={<Terminal className="h-4 w-4" />} label="Containers" />

      <div className="my-3 mx-3 border-t border-border-muted" />

      <p className="text-[10px] font-medium text-foreground-disabled uppercase tracking-widest px-3 mb-1">Tools</p>
      <NavItem to="/playground" icon={<MessageSquareCode className="h-4 w-4" />} label="Playground" />
    </aside>
  );
}
