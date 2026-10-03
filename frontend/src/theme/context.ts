import { createContext, useContext } from "react";

export type Theme = "light" | "dark" | "system";

export interface ThemeContextValue {
  theme: Theme;
  /** What's actually on screen once "system" is resolved. */
  resolvedTheme: "light" | "dark";
  setTheme: (theme: Theme) => void;
}

export const THEME_STORAGE_KEY = "researchai_theme";

export const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
