"use client";

import { Sun, Moon, HelpCircle, ChevronDown } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

export function HeaderControls() {
  const { theme, toggle } = useTheme();

  return (
    <div className="flex items-center gap-2">
      {/* Theme toggle */}
      <button
        onClick={toggle}
        aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        className="w-9 h-9 flex items-center justify-center rounded-lg bg-surface border border-border text-text-muted hover:text-text hover:bg-surface-elevated transition-all duration-150"
      >
        {theme === "dark" ? (
          <Sun className="w-4 h-4" />
        ) : (
          <Moon className="w-4 h-4" />
        )}
      </button>

      {/* Help button */}
      <button
        aria-label="Help"
        className="w-9 h-9 flex items-center justify-center rounded-full bg-surface border border-border text-text-muted hover:text-text hover:bg-surface-elevated transition-all duration-150"
      >
        <HelpCircle className="w-4 h-4" />
      </button>

      {/* User avatar */}
      <button
        aria-label="User menu"
        className="flex items-center gap-1.5 pl-1 pr-2 py-1 rounded-lg bg-surface border border-border hover:bg-surface-elevated transition-all duration-150"
      >
        <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-white">
          AU
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
      </button>
    </div>
  );
}
