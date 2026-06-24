"use client";

import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

export function HeaderControls() {
  const { theme, toggle } = useTheme();

  return (
    <div className="flex items-center gap-2">
      {/* Theme toggle (Settings → Appearance offers the same control on every page) */}
      <button
        onClick={toggle}
        aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        className="glass w-9 h-9 flex items-center justify-center rounded-lg text-text-muted hover:text-text hover:border-primary/40 transition-all duration-150 active:scale-95"
      >
        {theme === "dark" ? (
          <Sun className="w-4 h-4" />
        ) : (
          <Moon className="w-4 h-4" />
        )}
      </button>
    </div>
  );
}
