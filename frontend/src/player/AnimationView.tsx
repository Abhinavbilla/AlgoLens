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
  const { state, dispatch } = usePlayer(animation.frames.length);
  const frame = animation.frames[state.index];
  return (
    <div className={styles.layout}>
      <div className={styles.main}>
        <div className={styles.narration} aria-live="polite">
          <p className={styles.sentence}>{frame.narration.text}</p>
          <p className={styles.ran}>
            <span className={styles.ranLabel}>Line {frame.line}:</span> <code>{frame.code}</code>
            {frame.raised && <span> · raised {frame.raised}</span>}
          </p>
        </div>
        {frame.panels.map((p, i) => (
          <PanelView key={i} panel={p} />
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

function PanelView({ panel }: { panel: Panel }) {
  switch (panel.kind) {
    case "array":
      return <ArrayView panel={panel} />;
    case "vars":
      return <VarsView panel={panel} />;
    case "map":
      return <MapView panel={panel} />;
  }
}
