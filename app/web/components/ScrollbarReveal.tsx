"use client";

import { useEffect } from "react";

const HIDE_AFTER_MS = 700;

/** Marks whichever element is scrolling, so the CSS can show its scrollbar only then. */
export function ScrollbarReveal() {
  useEffect(() => {
    const timers = new WeakMap<Element, number>();

    function onScroll(event: Event) {
      const element = event.target === document ? document.documentElement : event.target;
      if (!(element instanceof Element)) return;
      element.setAttribute("data-scrolling", "true");
      window.clearTimeout(timers.get(element));
      timers.set(
        element,
        window.setTimeout(() => element.removeAttribute("data-scrolling"), HIDE_AFTER_MS),
      );
    }

    // Scroll events don't bubble, so capturing is what catches every scrolling panel.
    window.addEventListener("scroll", onScroll, { capture: true, passive: true });
    return () => window.removeEventListener("scroll", onScroll, { capture: true });
  }, []);

  return null;
}
