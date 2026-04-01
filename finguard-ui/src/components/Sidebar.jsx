import { NavLink } from 'react-router-dom';
import { Shield, Activity, Search, Brain, Share2, GitMerge, Database } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Command Center', icon: Shield },
  { path: '/live', label: 'Live Feed', icon: Activity },
  { path: '/score', label: 'Score Transaction', icon: Search },
  { path: '/intelligence', label: 'Model Intelligence', icon: Brain },
  { path: '/network', label: 'Network Graph', icon: Share2 },
  { path: '/probe', label: 'Adversarial Probe', icon: GitMerge },
  { path: '/federated', label: 'Federated Learning', icon: Database }
];

export default function Sidebar() {
  return (
    <div className="fixed left-0 top-0 h-full w-60 bg-background border-r border-border p-4 flex flex-col">
      <div className="mb-8 px-2 pt-4">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-decision-approve to-user-aman bg-clip-text text-transparent">FinGuard</h1>
        <p className="text-xs text-secondary mt-1 tracking-wider uppercase">SOC / Real-Time Auth</p>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive 
                  ? 'bg-surface text-primary border border-border block' 
                  : 'text-secondary hover:text-primary hover:bg-surface/50 border border-transparent'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto px-2 pb-2">
        <div className="text-xs text-muted flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-decision-approve animate-pulse"></div>
          API Connected
        </div>
      </div>
    </div>
  );
}
