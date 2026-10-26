import { useState, type CSSProperties, type KeyboardEvent, type PointerEvent } from "react";

// The tutor panel docks to the right edge. Dragging its left edge changes the width, its top
// edge the height (the bottom stays put). The size is remembered in this browser; phones get
// the full-screen panel regardless (TutorPanel.module.css).

export type Size = { width: number; height: number | null }; // height null: full height

export const DEFAULT_SIZE: Size = { width: 420, height: null };
export const MIN_WIDTH = 320;
export const MIN_HEIGHT = 360;
const MARGIN = 32; // 16px on each side, as in the CSS
const STEP = 24; // one arrow-key press
const KEY = "algolens:tutor-size";

function loadSize(): Size {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? "null");
    if (raw && typeof raw.width === "number") {
      return { width: raw.width, height: typeof raw.height === "number" ? raw.height : null };
    }
  } catch {
    // blocked or garbled: start from the default
  }
  return DEFAULT_SIZE;
}

function saveSize(size: Size) {
  try {
    localStorage.setItem(KEY, JSON.stringify(size));
  } catch {
    // the size just won't be remembered
  }
}

export function clampSize(size: Size, viewW = window.innerWidth, viewH = window.innerHeight): Size {
  const maxW = Math.max(MIN_WIDTH, viewW - MARGIN);
  const maxH = Math.max(MIN_HEIGHT, viewH - MARGIN);
  const width = Math.round(Math.min(maxW, Math.max(MIN_WIDTH, size.width)));
  if (size.height === null) return { width, height: null };
  const height = Math.round(Math.min(maxH, Math.max(MIN_HEIGHT, size.height)));
  // Dragged back up to (nearly) the full height: dock top to bottom again.
  return { width, height: height >= maxH - 4 ? null : height };
}

type Edge = "left" | "top" | "corner";

export function useResizable() {
  const [size, setSizeState] = useState<Size>(() => loadSize());
  const [dragging, setDragging] = useState(false);

  const setSize = (next: Size) => {
    const clamped = clampSize(next);
    setSizeState(clamped);
    saveSize(clamped);
  };

  // The CSS reads these and still caps them to the window, so a smaller window never cuts it off.
  const style = {
    "--tutor-width": `${size.width}px`,
    ...(size.height !== null ? { "--tutor-height": `${size.height}px` } : {}),
  } as CSSProperties;

  function onPointerDown(edge: Edge) {
    return (e: PointerEvent<HTMLElement>) => {
      if (e.button !== 0) return;
      e.preventDefault();
      const panel = e.currentTarget.parentElement;
      const rect = panel?.getBoundingClientRect();
      const start = { x: e.clientX, y: e.clientY, w: rect?.width ?? size.width, h: rect?.height ?? 0 };
      e.currentTarget.setPointerCapture?.(e.pointerId);
      setDragging(true);
      const move = (ev: globalThis.PointerEvent) => {
        // The panel grows leftward and upward, away from its docked corner.
        const width = edge === "top" ? size.width : start.w + (start.x - ev.clientX);
        const height = edge === "left" ? size.height : start.h + (start.y - ev.clientY);
        setSizeState(clampSize({ width, height }));
      };
      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        window.removeEventListener("pointercancel", up);
        setDragging(false);
        setSizeState((s) => {
          saveSize(s);
          return s;
        });
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
      window.addEventListener("pointercancel", up);
    };
  }

  function onKeyDown(edge: "left" | "top") {
    return (e: KeyboardEvent<HTMLElement>) => {
      const fullHeight = () => window.innerHeight - MARGIN;
      if (edge === "left" && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
        e.preventDefault();
        setSize({ ...size, width: size.width + (e.key === "ArrowLeft" ? STEP : -STEP) });
      } else if (edge === "top" && (e.key === "ArrowUp" || e.key === "ArrowDown")) {
        e.preventDefault();
        const h = size.height ?? fullHeight();
        setSize({ ...size, height: h + (e.key === "ArrowUp" ? STEP : -STEP) });
      } else if (e.key === "Home") {
        e.preventDefault();
        setSize(DEFAULT_SIZE);
      }
    };
  }

  return { size, style, dragging, onPointerDown, onKeyDown, reset: () => setSize(DEFAULT_SIZE) };
}
