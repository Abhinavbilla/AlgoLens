import { initialState, playerReducer, type PlayerAction, type PlayerState } from "./playerState";

const run = (s: PlayerState, ...actions: PlayerAction[]) => actions.reduce(playerReducer, s);

test("steps stay within the animation", () => {
  const s = initialState(3);
  expect(run(s, { type: "step", by: -1 }).index).toBe(0);
  expect(run(s, { type: "step", by: 1 }, { type: "step", by: 1 }, { type: "step", by: 1 }).index).toBe(2);
  expect(run(s, { type: "seek", to: 99 }).index).toBe(2);
  expect(run(s, { type: "seek", to: -5 }).index).toBe(0);
});

test("back then forward returns to exactly the same step", () => {
  const s = run(initialState(10), { type: "seek", to: 6 });
  const again = run(s, { type: "step", by: -1 }, { type: "step", by: -1 }, { type: "step", by: 2 });
  expect(again).toEqual(s);
});

test("playing advances on each tick and stops at the end", () => {
  let s = run(initialState(3), { type: "play" });
  expect(s.playing).toBe(true);
  s = run(s, { type: "tick" });
  expect(s.index).toBe(1);
  s = run(s, { type: "tick" });
  expect(s).toMatchObject({ index: 2, playing: false });
  expect(run(s, { type: "tick" }).index).toBe(2);
});

test("play at the end starts over", () => {
  const s = run(initialState(3), { type: "seek", to: 2 }, { type: "play" });
  expect(s).toMatchObject({ index: 0, playing: true });
});

test("stepping or seeking pauses playback", () => {
  const playing = run(initialState(5), { type: "play" });
  expect(run(playing, { type: "step", by: 1 }).playing).toBe(false);
  expect(run(playing, { type: "seek", to: 3 }).playing).toBe(false);
  expect(run(playing, { type: "restart" })).toMatchObject({ index: 0, playing: false });
});

test("speed is limited to 0.5x to 4x", () => {
  const s = initialState(3);
  expect(run(s, { type: "speed", speed: 0.1 }).speed).toBe(0.5);
  expect(run(s, { type: "speed", speed: 10 }).speed).toBe(4);
  expect(run(s, { type: "speed", speed: 2 }).speed).toBe(2);
});

test("a single-frame animation can't play", () => {
  expect(run(initialState(1), { type: "play" }).playing).toBe(false);
});
