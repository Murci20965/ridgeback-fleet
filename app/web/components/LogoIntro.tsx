"use client";

import { useEffect } from "react";

const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)";
const EASE_MOVE = "cubic-bezier(0.77, 0, 0.175, 1)";
const MAX_PHOTO_WAIT_MS = 1500;

// Runs before first paint, so the card doesn't flash before the animation starts. It plays on
// every page load. Without JavaScript this never runs and the card simply shows.
export const INTRO_SCRIPT = `try{if(!matchMedia("(prefers-reduced-motion: reduce)").matches)document.documentElement.dataset.intro="play"}catch(e){}`;

function finishIntro() {
  delete document.documentElement.dataset.intro;
}

/** Browsers can load a page before anyone sees it: preloading a typed address, or a tab opened
    in the background. Starting then would spend the whole animation unseen. */
async function whenVisible() {
  if ((document as Document & { prerendering?: boolean }).prerendering) {
    await new Promise((resolve) =>
      document.addEventListener("prerenderingchange", resolve, { once: true }),
    );
  }
  if (document.visibilityState === "visible") return;
  await new Promise<void>((resolve) => {
    const onChange = () => {
      if (document.visibilityState !== "visible") return;
      document.removeEventListener("visibilitychange", onChange);
      resolve();
    };
    document.addEventListener("visibilitychange", onChange);
  });
}

/** Holds until the photo can be drawn and the browser has painted, so no frames are lost while
    the page is still busy loading. A slow photo can't hold up the page for long. */
async function whenReadyToDraw(photo: HTMLImageElement) {
  await Promise.race([
    photo.decode().catch(() => undefined),
    new Promise((resolve) => setTimeout(resolve, MAX_PHOTO_WAIT_MS)),
  ]);
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

function play(logo: SVGElement, target: SVGElement, card: HTMLElement, photo: HTMLElement) {
  const from = logo.getBoundingClientRect();
  const to = target.getBoundingClientRect();
  const moved = `translate(${to.left + to.width / 2 - (from.left + from.width / 2)}px, ${
    to.top + to.height / 2 - (from.top + from.height / 2)
  }px) scale(${to.height / from.height})`;

  return [
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
}

/** Bars rise, then the logo glides into its place on the card. Any click or key skips it. */
export function LogoIntro() {
  useEffect(() => {
    if (document.documentElement.dataset.intro !== "play") return;

    const logo = document.querySelector<SVGElement>(".intro-logo");
    const target = document.querySelector<SVGElement>(".intro-target");
    const card = document.querySelector<HTMLElement>(".intro-card");
    const photo = document.querySelector<HTMLImageElement>(".intro-photo");
    if (!logo || !target || !card || !photo) {
      finishIntro();
      return;
    }

    let animations: Animation[] = [];
    let stopped = false;

    const skip = () => {
      if (animations.length) {
        animations.forEach((animation) => animation.finish());
      } else {
        stopped = true;
        finishIntro();
      }
    };
    window.addEventListener("pointerdown", skip);
    window.addEventListener("keydown", skip);

    (async () => {
      await whenVisible();
      await whenReadyToDraw(photo);
      if (stopped) return;
      animations = play(logo, target, card, photo);
      await Promise.all(animations.map((animation) => animation.finished));
      if (stopped) return;
      finishIntro();
      animations.forEach((animation) => animation.cancel());
    })().catch(() => {
      // Cancelled when leaving the page. The cleanup below has already restored the card.
    });

    return () => {
      stopped = true;
      window.removeEventListener("pointerdown", skip);
      window.removeEventListener("keydown", skip);
      animations.forEach((animation) => animation.cancel());
      // Leaving mid-animation must not leave the card hidden on the way back.
      finishIntro();
    };
  }, []);

  return null;
}
