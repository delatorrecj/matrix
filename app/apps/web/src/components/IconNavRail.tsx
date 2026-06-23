"use client";

import { Home, Network, BarChart3, Layers, Settings, Box } from "lucide-react";
import { useState, useRef } from "react";

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
  const topItems = NAV_ITEMS.filter((item) => item.position !== "bottom");
  const bottomItems = NAV_ITEMS.filter((item) => item.position === "bottom");

  const [hoveredItem, setHoveredItem] = useState<{ label: string; top: number } | null>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = (label: string, e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const top = rect.top + rect.height / 2;
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => {
      setHoveredItem({ label, top });
    }, 150);
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    setHoveredItem(null);
  };

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const isActive = activeId === item.id;

    return (
      <button
        key={item.id}
        onClick={() => {
          onNavigate?.(item.id);
          handleMouseLeave();
        }}
        onMouseEnter={(e) => handleMouseEnter(item.label, e)}
        onMouseLeave={handleMouseLeave}
        aria-label={item.label}
        aria-current={isActive ? "page" : undefined}
        className={`
          w-10 h-10 flex items-center justify-center rounded-lg transition-all duration-150 mx-auto
          ${isActive
            ? "bg-primary/15 text-primary"
            : "text-text-muted hover:text-text hover:bg-surface-elevated"
          }
        `}
      >
        <Icon className="w-5 h-5 shrink-0" />
      </button>
    );
  };

  return (
    <>
      <nav
        className="w-16 h-full bg-surface border-r border-border flex flex-col py-4 shrink-0 relative z-20"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <div className="flex items-center justify-center pb-6 mb-2 border-b border-border/50">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white shrink-0">
            <Box className="w-5 h-5" />
          </div>
        </div>

        {/* Top icons */}
        <div className="flex flex-col gap-2 flex-1 mt-2">
          {topItems.map(renderItem)}
        </div>

        {/* Bottom-pinned icons */}
        <div className="flex flex-col gap-2 pt-4 mt-auto border-t border-border/50">
          {bottomItems.map(renderItem)}

          {/* User avatar */}
          <button
            aria-label="User profile"
            onMouseEnter={(e) => handleMouseEnter("Admin User", e)}
            onMouseLeave={handleMouseLeave}
            className="w-10 h-10 flex items-center justify-center mx-auto rounded-full hover:bg-surface-elevated transition-all duration-150 mt-1"
          >
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-white shadow-sm shrink-0">
              AU
            </div>
          </button>
        </div>
      </nav>

      {/* Tooltip Overlay */}
      {hoveredItem && (
        <div
          className="glass fixed z-50 pointer-events-none px-3 py-1.5 rounded-md text-sm font-medium text-foreground whitespace-nowrap"
          style={{
            top: hoveredItem.top,
            left: 72,
            transform: "translateY(-50%)",
          }}
        >
          {hoveredItem.label}
        </div>
      )}
    </>
  );
}
