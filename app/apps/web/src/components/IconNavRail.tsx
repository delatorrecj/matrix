"use client";

import { Home, Network, BarChart3, Layers, Settings } from "lucide-react";
import { useState } from "react";

interface NavItem {
  id: string;
  icon: React.ElementType;
  label: string;
  position?: "bottom";
}

const NAV_ITEMS: NavItem[] = [
  { id: "home", icon: Home, label: "Home" },
  { id: "trajectories", icon: Network, label: "Trajectories" },
  { id: "analytics", icon: BarChart3, label: "Analytics" },
  { id: "layers", icon: Layers, label: "Layers" },
  { id: "settings", icon: Settings, label: "Settings", position: "bottom" },
];

interface IconNavRailProps {
  activeId?: string;
  onNavigate?: (id: string) => void;
}

export function IconNavRail({ activeId = "home", onNavigate }: IconNavRailProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const topItems = NAV_ITEMS.filter((item) => item.position !== "bottom");
  const bottomItems = NAV_ITEMS.filter((item) => item.position === "bottom");

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const isActive = activeId === item.id;

    return (
      <div key={item.id} className="relative group">
        <button
          onClick={() => onNavigate?.(item.id)}
          onMouseEnter={() => setHoveredId(item.id)}
          onMouseLeave={() => setHoveredId(null)}
          aria-label={item.label}
          aria-current={isActive ? "page" : undefined}
          className={`
            w-10 h-10 flex items-center justify-center rounded-lg transition-all duration-150
            ${isActive
              ? "bg-primary/15 text-primary"
              : "text-text-muted hover:text-text hover:bg-surface-elevated"
            }
          `}
        >
          <Icon className="w-5 h-5" />
        </button>

        {/* Tooltip */}
        {hoveredId === item.id && (
          <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50 pointer-events-none">
            <div className="bg-surface-elevated text-text text-xs font-medium px-2.5 py-1.5 rounded-md shadow-md border border-border whitespace-nowrap">
              {item.label}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <nav
      className="w-[52px] h-full bg-surface border-r border-border flex flex-col items-center py-3 shrink-0"
      aria-label="Main navigation"
    >
      {/* Top icons */}
      <div className="flex flex-col items-center gap-1.5 flex-1">
        {topItems.map(renderItem)}
      </div>

      {/* Bottom-pinned icons */}
      <div className="flex flex-col items-center gap-1.5">
        {bottomItems.map(renderItem)}
      </div>
    </nav>
  );
}
