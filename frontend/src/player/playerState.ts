// Player state as a pure reducer. The frame shown is always frames[index], and frames are
// immutable, so stepping back and forward again shows exactly the same state.

export const SPEEDS = [0.5, 1, 1.5, 2, 3, 4] as const;
export const BASE_STEP_MS = 900; // time per step at 1x

export type PlayerState = { index: number; playing: boolean; speed: number; count: number };

export type PlayerAction =
  | { type: "play" }
  | { type: "pause" }
  | { type: "toggle" }
  | { type: "step"; by: number }
  | { type: "seek"; to: number }
  | { type: "restart" }
  | { type: "speed"; speed: number }
  | { type: "tick" };

const clampIndex = (i: number, count: number) => Math.max(0, Math.min(count - 1, i));

export function initialState(count: number): PlayerState {
  return { index: 0, playing: false, speed: 1, count };
}

export function playerReducer(s: PlayerState, a: PlayerAction): PlayerState {
  const last = s.count - 1;
  switch (a.type) {
    case "play":
      // Playing from the end starts over, as a learner would expect.
      return { ...s, playing: s.count > 1, index: s.index >= last ? 0 : s.index };
    case "pause":
      return { ...s, playing: false };
    case "toggle":
      return playerReducer(s, { type: s.playing ? "pause" : "play" });
    case "step":
      return { ...s, playing: false, index: clampIndex(s.index + a.by, s.count) };
    case "seek":
      return { ...s, playing: false, index: clampIndex(a.to, s.count) };
    case "restart":
      return { ...s, playing: false, index: 0 };
    case "speed":
      return { ...s, speed: Math.max(0.5, Math.min(4, a.speed)) };
    case "tick":
      if (!s.playing) return s;
      if (s.index >= last) return { ...s, playing: false };
      return { ...s, index: s.index + 1, playing: s.index + 1 < last };
  }
}
