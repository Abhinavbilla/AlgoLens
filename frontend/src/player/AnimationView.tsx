import { useMemo } from "react";
import type { Animation, Panel } from "../api";
import { ArrayView } from "../viz/ArrayView";
import { CallStack } from "../viz/CallStack";
import { CodeView } from "../viz/CodeView";
import { MapView } from "../viz/MapView";
import { VarsView } from "../viz/VarsView";
import styles from "./AnimationView.module.css";
import { Controls } from "./Controls";
import { usePlayer } from "./usePlayer";

type Props = { animation: Animation; python: string; cpp: string };

export function AnimationView({ animation, python, cpp }: Props) {
  const { frames } = animation;
  const narrations = useMemo(() => frames.map((f) => f.narration.text), [frames]);
  const { state, dispatch } = usePlayer(narrations);
  const frame = frames[state.index];
  // Space reserved for stacked pointer labels, per panel, so panels never grow mid-run.
  const pointerRows = useMemo(
    () =>
      frames[0].panels.map((_, p) =>
        Math.max(
          1,
          ...frames.map((f) => {
            const panel = f.panels[p];
            if (panel?.kind !== "array" || !panel.pointers) return 0;
            const perIndex = new Map<number, number>();
            for (const ptr of panel.pointers) perIndex.set(ptr.index, (perIndex.get(ptr.index) ?? 0) + 1);
            return Math.max(0, ...perIndex.values());
          }),
        ),
      ),
    [frames],
  );

  return (
    <div className={styles.layout}>
      <div className={styles.main}>
        {/* Every step's sentence is laid out in the same cell, so the box is always as tall
            as the longest one and nothing below it moves. Only the current one is visible. */}
        <div className={styles.narration} aria-live={state.playing ? "off" : "polite"}>
          <div className={styles.stackCell}>
            {frames.map((f, i) => (
              <div
                key={i}
                className={i === state.index ? styles.shown : styles.hidden}
                aria-hidden={i !== state.index}
                data-current-narration={i === state.index ? "" : undefined}
              >
                <p className={styles.sentence}>{f.narration.text}</p>
                <p className={styles.ran}>
                  <span className={styles.ranLabel}>Line {f.line}:</span> <code>{f.code}</code>
                  {f.raised && <span> · raised {f.raised}</span>}
                </p>
              </div>
            ))}
          </div>
        </div>
        {frame.panels.map((p, i) => (
          <PanelView key={i} panel={p} pointerRows={pointerRows[i] ?? 1} />
        ))}
        <Controls state={state} dispatch={dispatch} ops={frame.ops} />
      </div>
      <div className={styles.side}>
        <CodeView python={python} cpp={cpp} pythonLine={frame.line} cppLine={frame.cpp_line} />
        <CallStack stack={frame.stack} />
      </div>
    </div>
  );
}

function PanelView({ panel, pointerRows }: { panel: Panel; pointerRows: number }) {
  switch (panel.kind) {
    case "array":
      return <ArrayView panel={panel} pointerRows={pointerRows} />;
    case "vars":
      return <VarsView panel={panel} />;
    case "map":
      return <MapView panel={panel} />;
  }
}
