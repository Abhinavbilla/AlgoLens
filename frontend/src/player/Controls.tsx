import type { Dispatch } from "react";
import styles from "./Controls.module.css";
import { SPEEDS, type PlayerAction, type PlayerState } from "./playerState";

type Props = { state: PlayerState; dispatch: Dispatch<PlayerAction>; ops: number };

// On narrow screens Restart/Back/Forward show only their icon; the word stays available to
// screen readers (it's visually hidden, not removed), so every button keeps its name.
export function Controls({ state, dispatch, ops }: Props) {
  const last = state.count - 1;
  return (
    <div className={styles.controls}>
      <div className={styles.buttons} role="group" aria-label="Playback">
        <button type="button" onClick={() => dispatch({ type: "restart" })} disabled={state.index === 0}>
          <span aria-hidden="true">⏮</span> <span className={styles.word}>Restart</span>
        </button>
        <button type="button" onClick={() => dispatch({ type: "step", by: -1 })} disabled={state.index === 0}>
          <span aria-hidden="true">◀</span> <span className={styles.word}>Back</span>
        </button>
        <button
          type="button"
          className={styles.primary}
          onClick={() => dispatch({ type: "toggle" })}
          disabled={state.count < 2}
          aria-keyshortcuts="Space"
        >
          {state.playing ? (
            <>
              <span aria-hidden="true">⏸</span> Pause
            </>
          ) : (
            <>
              <span aria-hidden="true">▶</span> Play
            </>
          )}
        </button>
        <button
          type="button"
          onClick={() => dispatch({ type: "step", by: 1 })}
          disabled={state.index >= last}
          aria-keyshortcuts="ArrowRight"
        >
          <span className={styles.word}>Forward</span> <span aria-hidden="true">▶</span>
        </button>
        <label className={styles.speed}>
          Speed
          <select
            value={state.speed}
            onChange={(e) => dispatch({ type: "speed", speed: Number(e.target.value) })}
          >
            {SPEEDS.map((s) => (
              <option key={s} value={s}>
                {s}×
              </option>
            ))}
          </select>
        </label>
      </div>
      <input
        className={styles.scrubber}
        type="range"
        min={0}
        max={last}
        value={state.index}
        onChange={(e) => dispatch({ type: "seek", to: Number(e.target.value) })}
        aria-label="Step"
        aria-valuetext={`Step ${state.index + 1} of ${state.count}`}
      />
      <p className={styles.position} aria-live="polite">
        Step {state.index + 1} of {state.count} · {ops} {ops === 1 ? "operation" : "operations"} so far
      </p>
    </div>
  );
}
