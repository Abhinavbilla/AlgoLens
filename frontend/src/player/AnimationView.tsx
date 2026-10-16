import { useEffect, useMemo, useState } from "react";
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
import { decisionTargets, questionAt, type Question, type Target } from "./predict";
import { computeReserves, NO_RESERVE, type Reserve } from "./reserve";
import { usePlayer } from "./usePlayer";
import { stepFromFrame, useTutor } from "../tutor/TutorContext";

type Props = { animation: Animation; python: string; cpp: string; approachId?: string };

export function AnimationView({ animation, python, cpp, approachId }: Props) {
  const { frames } = animation;
  const narrations = useMemo(() => frames.map((f) => f.narration.text), [frames]);
  const { state, dispatch } = usePlayer(narrations);
  const frame = frames[state.index];
  // The largest size each panel needs anywhere in this run, so panels never change height.
  const reserves = useMemo(() => computeReserves(frames), [frames]);

  // Predict mode: at steps where the code could have gone more than one way, ask where it
  // goes next before showing the sentence (which would give the answer away).
  const [predict, setPredict] = useState(false);
  const [answers, setAnswers] = useState<Record<number, Target>>({});
  const targets = useMemo(() => decisionTargets(frames), [frames]);
  const question = predict ? questionAt(frames, targets, state.index) : null;
  const pending = question !== null && answers[question.index] === undefined;
  const answered = Object.entries(answers);
  const right = answered.filter(([i, t]) => frames[Number(i)].next === t).length;
  const sourceLines = useMemo(() => python.split("\n"), [python]);

  useEffect(() => {
    if (pending && state.playing) dispatch({ type: "pause" });
  }, [pending, state.playing, dispatch]);

  // Tell the page's tutor (if there is one) which step is on screen.
  const tutor = useTutor();
  useEffect(() => {
    tutor?.reportStep({ ...stepFromFrame(frame), approachId });
  }, [tutor, frame, approachId]);
  useEffect(() => () => tutor?.reportStep(null), [tutor]);

  return (
    <div className={styles.layout}>
      <div className={styles.main}>
        <div className={styles.modeBar}>
          <button
            type="button"
            aria-pressed={predict}
            className={predict ? styles.modeOn : styles.modeOff}
            onClick={() => setPredict((p) => !p)}
          >
            {predict ? "Predict mode: on" : "Predict the next step"}
          </button>
          {tutor && (
            <button
              type="button"
              className={styles.modeOff}
              onClick={() => {
                if (state.playing) dispatch({ type: "pause" });
                tutor.open({ tab: "explain", question: "What's happening at this step, and why?", withStep: true });
              }}
            >
              Ask about this step
            </button>
          )}
          {predict && (
            <span className={styles.score} role="status">
              {answered.length === 0
                ? "At each decision, guess where the code goes next."
                : `${right} of ${answered.length} predicted right`}
            </span>
          )}
        </div>
        {pending && question && (
          <QuestionCard
            question={question}
            code={frame.code}
            lineText={(n) => sourceLines[n - 1]?.trim() ?? ""}
            onAnswer={(t) => setAnswers((a) => ({ ...a, [question.index]: t }))}
          />
        )}
        {predict && question && !pending && (
          <p
            className={answers[question.index] === question.answer ? styles.right : styles.wrong}
            role="status"
          >
            {answers[question.index] === question.answer
              ? "✓ Right."
              : `✗ Not quite: it went to ${describe(question.answer)}.`}
          </p>
        )}
        {/* Every step's sentence is laid out in the same cell, so the box is always as tall
            as the longest one and nothing below it moves. Only the current one is visible. */}
        <div
          className={styles.narration}
          aria-live={state.playing ? "off" : "polite"}
          hidden={pending || undefined}
        >
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

const describe = (t: Target) => (t === "return" ? "the end of the function (return)" : `line ${t}`);

function QuestionCard({
  question,
  code,
  lineText,
  onAnswer,
}: {
  question: Question;
  code: string;
  lineText: (n: number) => string;
  onAnswer: (t: Target) => void;
}) {
  return (
    <fieldset className={styles.question}>
      <legend>
        Line {question.line} just ran: <code>{code}</code>. Where does the code go next?
      </legend>
      <p className={styles.questionHint}>Look at the values on screen, then choose.</p>
      <div className={styles.choices}>
        {question.choices.map((t) => (
          <button key={String(t)} type="button" onClick={() => onAnswer(t)}>
            {t === "return" ? (
              "Leave the function (return)"
            ) : (
              <>
                Line {t}: <code>{lineText(t)}</code>
              </>
            )}
          </button>
        ))}
      </div>
    </fieldset>
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
