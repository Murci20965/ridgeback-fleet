"use client";

import { useEffect } from "react";

export const INTRO_SEEN_KEY = "intro-seen";

const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)";
const EASE_MOVE = "cubic-bezier(0.77, 0, 0.175, 1)";

// Runs before first paint, so the card doesn't flash before the animation starts. Without
// JavaScript this never runs and the card simply shows, so nobody can lose the way in.
export const INTRO_SCRIPT = `try{if(!sessionStorage.getItem("${INTRO_SEEN_KEY}")&&!matchMedia("(prefers-reduced-motion: reduce)").matches)document.documentElement.dataset.intro="play"}catch(e){}`;

function finishIntro() {
  delete document.documentElement.dataset.intro;
  try {
    sessionStorage.setItem(INTRO_SEEN_KEY, "1");
  } catch {
    // Storage can be blocked. The intro would just play again on the next visit.
  }
}

/** Bars rise, then the logo glides into its place on the card. Any click or key skips it. */
export function LogoIntro() {
  useEffect(() => {
    const root = document.documentElement;
    if (root.dataset.intro !== "play") return;

    const logo = document.querySelector<SVGElement>(".intro-logo");
    const target = document.querySelector<SVGElement>(".intro-target");
    const card = document.querySelector<HTMLElement>(".intro-card");
    const photo = document.querySelector<HTMLElement>(".intro-photo");
    if (!logo || !target || !card || !photo) {
      finishIntro();
      return;
    }

    const from = logo.getBoundingClientRect();
    const to = target.getBoundingClientRect();
    const moved = `translate(${to.left + to.width / 2 - (from.left + from.width / 2)}px, ${
      to.top + to.height / 2 - (from.top + from.height / 2)
    }px) scale(${to.height / from.height})`;

    const animations = [
      photo.animate([{ opacity: 0 }, { opacity: 1 }], {
        duration: 700,
        easing: "ease-out",
        fill: "both",
      }),
      ...[...logo.querySelectorAll("rect")].map((bar, index) =>
        bar.animate([{ transform: "scaleY(0)" }, { transform: "scaleY(1)" }], {
          duration: 380,
          delay: index * 100,
          easing: EASE_OUT,
          fill: "both",
        }),
      ),
      logo.animate([{ transform: "none" }, { transform: moved }], {
        duration: 560,
        delay: 760,
        easing: EASE_MOVE,
        fill: "both",
      }),
      card.animate(
        [
          { opacity: 0, transform: "translateY(6px) scale(0.98)" },
          { opacity: 1, transform: "none" },
        ],
        // Lands with the logo, so the logo doesn't cross the card's text once it's readable.
        { duration: 340, delay: 980, easing: "ease-out", fill: "both" },
      ),
    ];

    const skip = () => animations.forEach((animation) => animation.finish());
    window.addEventListener("pointerdown", skip);
    window.addEventListener("keydown", skip);

    let cancelled = false;
    Promise.all(animations.map((animation) => animation.finished))
      .then(() => {
        if (cancelled) return;
        finishIntro();
        animations.forEach((animation) => animation.cancel());
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      window.removeEventListener("pointerdown", skip);
      window.removeEventListener("keydown", skip);
      animations.forEach((animation) => animation.cancel());
      // Leaving mid-animation must not leave the card hidden on the way back.
      finishIntro();
    };
  }, []);

  return null;
}
