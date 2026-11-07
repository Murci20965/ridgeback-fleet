"use client";

import { Moon, Sun } from "lucide-react";

function currentTheme() {
  const chosen = document.documentElement.dataset.theme;
  if (chosen) return chosen;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeToggle() {
  function toggle() {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Storage can be blocked. The theme still applies for this visit.
    }
  }

  return (
    <button
      onClick={toggle}
      aria-label="Switch between light and dark theme"
      className="pressable grid size-9 shrink-0 place-items-center rounded-lg border border-white/15 text-[#d5dce6] hover:bg-white/10"
    >
      <Sun size={16} className="hidden dark-icon" aria-hidden />
      <Moon size={16} className="light-icon" aria-hidden />
    </button>
  );
}
