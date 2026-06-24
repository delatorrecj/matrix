"use client";

import { Moon, Sun, X } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";
import { useLanguage, type Language } from "@/components/LanguageProvider";

/**
 * Minimal Settings (CR-010) — replaces the old dead gear. Theme + language only;
 * no fake account/admin controls. Reachable from the nav rail on every page, so
 * the scenario view finally has a theme control too.
 */
export function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { theme, toggle } = useTheme();
  const { language, setLanguage } = useLanguage();

  if (!open) return null;

  const setTheme = (target: "light" | "dark") => {
    if (theme !== target) toggle();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Settings"
    >
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div className="glass relative w-full max-w-sm rounded-xl p-5">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-bold text-foreground">Settings</h2>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="p-1 rounded-lg text-text-muted hover:text-text hover:bg-surface-elevated transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="mb-5">
          <div className="text-sm font-medium mb-2 text-foreground">Appearance</div>
          <div className="grid grid-cols-2 gap-2">
            <SegButton active={theme === "light"} onClick={() => setTheme("light")} icon={Sun} label="Light" />
            <SegButton active={theme === "dark"} onClick={() => setTheme("dark")} icon={Moon} label="Dark" />
          </div>
        </div>

        <div>
          <div className="text-sm font-medium mb-2 text-foreground">Language</div>
          <div className="grid grid-cols-2 gap-2">
            <SegButton active={language === "en"} onClick={() => setLanguage("en" as Language)} label="English" />
            <SegButton active={language === "hil"} onClick={() => setLanguage("hil" as Language)} label="Hiligaynon" />
          </div>
          <p className="text-xs text-text-muted mt-2">Sets the language for the narrative and brief.</p>
        </div>
      </div>
    </div>
  );
}

function SegButton({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon?: React.ElementType;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
        active
          ? "border-primary bg-primary/10 text-primary"
          : "border-border text-text-muted hover:text-text hover:border-primary/40"
      }`}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {label}
    </button>
  );
}
