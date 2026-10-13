import { useEffect, useState } from "react";

type Theme = "system" | "light" | "dark";
const KEY = "algolens.theme";
const NEXT: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };

function readTheme(): Theme {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try {
      if (theme === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, theme);
    } catch {
      // Storage unavailable (private window etc.): theme still applies for this visit.
    }
  }, [theme]);

  return (
    <button type="button" onClick={() => setTheme(NEXT[theme])}>
      Theme: {theme}
    </button>
  );
}
