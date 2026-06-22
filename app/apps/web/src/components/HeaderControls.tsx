"use client";

import { Sun, Moon, HelpCircle } from "lucide-react";
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
    </div>
  );
}
