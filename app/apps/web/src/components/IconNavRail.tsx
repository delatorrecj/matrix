"use client";

import { Home, Network, BarChart3, Layers, Settings } from "lucide-react";
import { useState, useRef } from "react";
import { SettingsPanel } from "@/components/SettingsPanel";
import { LogoMark } from "@/components/Logo";

interface NavItem {
  id: string;
  icon: React.ElementType;
  label: string;
  position?: "bottom";
}

const NAV_ITEMS: NavItem[] = [
  { id: "home", icon: Home, label: "Home" },
  { id: "trajectories", icon: Network, label: "Summary" },
  { id: "analytics", icon: BarChart3, label: "Analytics" },
  { id: "layers", icon: Layers, label: "Layers" },
  { id: "settings", icon: Settings, label: "Settings", position: "bottom" },
];

interface IconNavRailProps {
  activeId?: string;
  onNavigate?: (id: string) => void;
  /** Items that aren't actionable in this context (rendered disabled, not silent no-ops). */
  disabledIds?: string[];
  /** Tooltip shown for a disabled item. */
  disabledReason?: string;
}

export function IconNavRail({
  activeId = "home",
  onNavigate,
  disabledIds = [],
  disabledReason = "Not available here",
}: IconNavRailProps) {
  const topItems = NAV_ITEMS.filter((item) => item.position !== "bottom");
  const bottomItems = NAV_ITEMS.filter((item) => item.position === "bottom");
  const disabled = new Set(disabledIds);

  const [hoveredItem, setHoveredItem] = useState<{ label: string; top: number } | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
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

  // Settings is handled in-rail (its own panel); everything else is routed by the parent.
  const activate = (id: string) => {
    handleMouseLeave();
    if (id === "settings") {
      setSettingsOpen(true);
      return;
    }
    onNavigate?.(id);
  };

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const isActive = activeId === item.id;
    const isDisabled = disabled.has(item.id);

    return (
      <button
        key={item.id}
        onClick={() => {
          if (!isDisabled) activate(item.id);
        }}
        onMouseEnter={(e) => handleMouseEnter(isDisabled ? `${item.label} — ${disabledReason}` : item.label, e)}
        onMouseLeave={handleMouseLeave}
        aria-label={item.label}
        aria-current={isActive ? "page" : undefined}
        aria-disabled={isDisabled || undefined}
        disabled={isDisabled}
        className={`
          w-10 h-10 flex items-center justify-center rounded-lg transition-all duration-150 mx-auto
          ${isActive
            ? "bg-primary/15 text-primary"
            : isDisabled
              ? "text-text-muted/40 cursor-not-allowed"
              : "text-text-muted hover:text-text hover:bg-surface-elevated"
          }
        `}
      >
        <Icon className="w-5 h-5 shrink-0" />
      </button>
    );
  };

  return (
    <div className="h-full shrink-0 relative z-20">
      <nav
        className="w-16 h-full bg-surface border-r border-border flex flex-col py-4"
        aria-label="Main navigation"
      >
        {/* Logo → Home */}
        <div className="flex items-center justify-center pb-6 mb-2 border-b border-border/50">
          <button
            onClick={() => activate("home")}
            aria-label="MATRIX home"
            className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white shrink-0 hover:bg-primary-hover transition-colors active:scale-95"
          >
            <LogoMark className="w-5 h-5" />
          </button>
        </div>

        {/* Top icons */}
        <div className="flex flex-col gap-2 flex-1 mt-2">
          {topItems.map(renderItem)}
        </div>

        {/* Bottom-pinned icons */}
        <div className="flex flex-col gap-2 pt-4 mt-auto border-t border-border/50">
          {bottomItems.map(renderItem)}
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

      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
