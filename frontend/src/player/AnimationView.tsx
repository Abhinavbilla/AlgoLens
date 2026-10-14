import { useMemo } from "react";
import type { Animation, Panel } from "../api";
import { ArrayView } from "../viz/ArrayView";
import { CallStack } from "../viz/CallStack";
import { CodeView } from "../viz/CodeView";
import { GraphView } from "../viz/GraphView";
import { GridView } from "../viz/GridView";
import { LinkedListView } from "../viz/LinkedListView";
import { MapView } from "../viz/MapView";
import { SequenceView } from "../viz/SequenceView";
import { TreeView } from "../viz/TreeView";
import { VarsView } from "../viz/VarsView";
import styles from "./AnimationView.module.css";
import { Controls } from "./Controls";
import { computeReserves, NO_RESERVE, type Reserve } from "./reserve";
import { usePlayer } from "./usePlayer";

type Props = { animation: Animation; python: string; cpp: string };

export function AnimationView({ animation, python, cpp }: Props) {
  const { frames } = animation;
  const narrations = useMemo(() => frames.map((f) => f.narration.text), [frames]);
  const { state, dispatch } = usePlayer(narrations);
  const frame = frames[state.index];
  // The largest size each panel needs anywhere in this run, so panels never change height.
  const reserves = useMemo(() => computeReserves(frames), [frames]);

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
          <PanelView key={i} panel={p} reserve={reserves[i] ?? NO_RESERVE} />
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

function PanelView({ panel, reserve }: { panel: Panel; reserve: Reserve }) {
  switch (panel.kind) {
    case "array":
      return <ArrayView panel={panel} pointerRows={reserve.pointerRows} reserveRange={reserve.hasRange} />;
    case "vars":
      return <VarsView panel={panel} />;
    case "map":
      return <MapView panel={panel} minRows={reserve.mapRows} />;
    case "stack":
    case "queue":
    case "list":
      return <SequenceView panel={panel} />;
    case "linked_list":
      return <LinkedListView panel={panel} />;
    case "tree":
      return <TreeView panel={panel} reserve={reserve} />;
    case "graph":
      return <GraphView panel={panel} markNames={reserve.marks} />;
    case "grid":
      return <GridView panel={panel} reserve={reserve} />;
  }
}
