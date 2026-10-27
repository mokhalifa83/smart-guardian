"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import enTranslations from "@/locales/en.json";
import arTranslations from "@/locales/ar.json";

export type Language = "en" | "ar";
export type Direction = "ltr" | "rtl";

interface LanguageContextType {
  language: Language;
  direction: Direction;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
  t: (keyPath: string) => string;
}

const translations: Record<Language, any> = {
  en: enTranslations,
  ar: arTranslations,
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");
  const direction: Direction = language === "ar" ? "rtl" : "ltr";

  useEffect(() => {
    // Sync document HTML direction and lang
    document.documentElement.dir = direction;
    document.documentElement.lang = language;
  }, [direction, language]);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
  };

  const toggleLanguage = () => {
    setLanguageState((prev) => (prev === "en" ? "ar" : "en"));
  };

  const t = (keyPath: string): string => {
    const keys = keyPath.split(".");
    let current: any = translations[language];
    for (const key of keys) {
      if (current && typeof current === "object" && key in current) {
        current = current[key];
      } else {
        // Fallback to English if missing in target
        let fallback: any = translations["en"];
        for (const fKey of keys) {
          if (fallback && typeof fallback === "object" && fKey in fallback) {
            fallback = fallback[fKey];
          } else {
            return keyPath;
          }
        }
        return typeof fallback === "string" ? fallback : keyPath;
      }
    }
    return typeof current === "string" ? current : keyPath;
  };

  return (
    <LanguageContext.Provider value={{ language, direction, setLanguage, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
