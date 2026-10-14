import { useEffect, useReducer } from "react";
import { initialState, playerReducer, stepDurationMs } from "./playerState";

/** `narrations[i]` is step i's sentence; it sets how long that step stays on screen. */
export function usePlayer(narrations: string[]) {
  const count = narrations.length;
  const [state, dispatch] = useReducer(playerReducer, count, initialState);

  useEffect(() => {
    if (!state.playing) return;
    const ms = stepDurationMs(narrations[state.index] ?? "", state.speed);
    const id = window.setTimeout(() => dispatch({ type: "tick" }), ms);
    return () => window.clearTimeout(id);
  }, [state.playing, state.speed, state.index, narrations]);

  // Keyboard: Space plays/pauses, arrows step, Home/End jump.
  //  - ignored while typing in a text field or choosing from a select
  //  - when the step slider has focus it handles arrows/Home/End itself; Space still toggles
  //  - a focused button keeps Space for itself (standard button behaviour)
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      const isSlider = tag === "INPUT" && (target as HTMLInputElement).type === "range";
      const typing =
        tag === "TEXTAREA" || tag === "SELECT" || target?.isContentEditable || (tag === "INPUT" && !isSlider);
      if (typing || (isSlider && e.key !== " ")) return;
      if (e.key === " ") {
        if (tag === "BUTTON") return;
        e.preventDefault();
        dispatch({ type: "toggle" });
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        dispatch({ type: "step", by: 1 });
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        dispatch({ type: "step", by: -1 });
      } else if (e.key === "Home") {
        e.preventDefault();
        dispatch({ type: "seek", to: 0 });
      } else if (e.key === "End") {
        e.preventDefault();
        dispatch({ type: "seek", to: count - 1 });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [count]);

  return { state, dispatch };
}
