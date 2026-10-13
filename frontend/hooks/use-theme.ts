"use client";

import * as React from "react";

type Theme = "light" | "dark";

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => observer.disconnect();
}

export function useTheme() {
  const theme = React.useSyncExternalStore<Theme>(
    subscribe,
    () => (document.documentElement.classList.contains("dark") ? "dark" : "light"),
    () => "light",
  );
  const toggle = React.useCallback(() => {
    const next: Theme = document.documentElement.classList.contains("dark") ? "light" : "dark";
    document.documentElement.classList.toggle("dark", next === "dark");
    try {
      localStorage.setItem("tf-theme", next);
    } catch {
      /* storage unavailable */
    }
  }, []);
  return { theme, toggle };
}

/** Inline script for <head>: applies the stored theme before first paint (no flash). */
export const themeScript = `(function(){try{var t=localStorage.getItem('tf-theme');if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark')}catch(e){}})()`;
