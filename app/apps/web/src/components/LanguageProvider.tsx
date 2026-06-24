"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Language = "en" | "hil";

interface LanguageContextValue {
  language: Language;
  setLanguage: (l: Language) => void;
}

const LanguageContext = createContext<LanguageContextValue>({
  language: "en",
  setLanguage: () => {},
});

export function useLanguage() {
  return useContext(LanguageContext);
}

/**
 * App language preference (CR-010). English / Hiligaynon. The preference is
 * persisted now; the synthesis narrative + brief begin consuming it in Phase 2
 * (kernel emits delimited bilingual output instead of inline interleaving).
 */
export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    const stored = localStorage.getItem("matrix-language") as Language | null;
    if (stored === "en" || stored === "hil") setLanguageState(stored);
  }, []);

  const setLanguage = useCallback((l: Language) => {
    setLanguageState(l);
    try {
      localStorage.setItem("matrix-language", l);
    } catch {
      /* private mode — preference is in-memory only */
    }
  }, []);

  return (
    <LanguageContext.Provider value={{ language, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}
