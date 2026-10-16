import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import type { Frame, TutorStep, TutorTarget } from "../api";
import { TutorPanel, type Opening } from "./TutorPanel";

// One tutor per page. The player tells it which step is on screen, so a question can be about
// exactly what the learner is looking at.

export type PageInfo = {
  target: TutorTarget;
  title: string;
  functionName: string;
  params: string[];
  /** Ready-made questions shown before the first message. */
  suggestions: string[];
};

export type StepReport = TutorStep & { approachId?: string };

type Tutor = {
  open: (o?: Opening) => void;
  reportStep: (s: StepReport | null) => void;
};

const TutorCtx = createContext<Tutor | null>(null);

/** The tutor on this page, or null where there isn't one (the player then hides its button). */
export const useTutor = () => useContext(TutorCtx);

export function TutorProvider({ page, children }: { page: PageInfo; children: ReactNode }) {
  const [opening, setOpening] = useState<Opening | null>(null);
  const [isOpen, setOpen] = useState(false);
  // The latest step is read when a message is sent; keeping it in a ref means stepping
  // through the animation doesn't re-render the whole page.
  const step = useRef<StepReport | null>(null);
  const [hasStep, setHasStep] = useState(false);

  const open = useCallback((o?: Opening) => {
    setOpening(o ? { ...o, nonce: Date.now() } : null);
    setOpen(true);
  }, []);
  const reportStep = useCallback((s: StepReport | null) => {
    step.current = s;
    setHasStep(s !== null);
  }, []);
  const value = useMemo(() => ({ open, reportStep }), [open, reportStep]);

  return (
    <TutorCtx.Provider value={value}>
      {children}
      <TutorPanel
        page={page}
        open={isOpen}
        opening={opening}
        hasStep={hasStep}
        currentStep={() => step.current}
        onOpen={() => open()}
        onClose={() => setOpen(false)}
      />
    </TutorCtx.Provider>
  );
}

/** What the tutor is told about a step: the line, the sentence on screen and the values shown. */
export function stepFromFrame(frame: Frame): TutorStep {
  const variables: Record<string, unknown> = {};
  for (const p of frame.panels) {
    if (p.kind === "vars") {
      for (const v of p.items) if (v.defined) variables[v.name] = v.value;
    } else if (p.kind === "array" && p.defined) {
      variables[p.label] = p.items;
      for (const ptr of p.pointers ?? []) variables[ptr.label] = ptr.index;
    } else if (p.kind === "map" && p.defined) {
      variables[p.label] = Object.fromEntries((p.entries ?? []).map((e) => [e.key, e.value]));
    } else if (p.kind === "stack" || p.kind === "queue" || p.kind === "list") {
      if (p.defined) variables[p.label] = p.items;
    } else if (p.kind === "linked_list" && p.defined) {
      variables[p.label] = (p.nodes ?? []).map((n) => n.text).join(" -> ");
    } else if (p.kind === "grid" && p.defined) {
      variables[p.label] = (p.rows ?? []).map((r) => r.map((c) => c.text));
    } else if ((p.kind === "tree" || p.kind === "graph") && p.defined) {
      const marked = (p.nodes ?? []).filter((n) => n.marks.length > 0);
      variables[`${p.label} (marked nodes)`] = marked.map(
        (n) => `${"text" in n ? n.text : (n.label ?? n.id)}: ${n.marks.join(", ")}`,
      );
    }
    if ("pointers" in p && p.kind !== "array" && p.kind !== "grid") {
      for (const ptr of p.pointers ?? []) variables[ptr.label] = `node ${ptr.node ?? "None"}`;
    }
  }
  // Stay under the server's limit: drop the biggest values first.
  let entries = Object.entries(variables);
  while (entries.length > 0 && JSON.stringify(Object.fromEntries(entries)).length > 1800) {
    entries = entries
      .map(([k, v]) => [k, v, JSON.stringify(v)?.length ?? 0] as const)
      .sort((a, b) => a[2] - b[2])
      .slice(0, -1)
      .map(([k, v]) => [k, v]);
  }
  return {
    index: frame.i,
    line: frame.line || null,
    narration: frame.narration.text.slice(0, 600),
    variables: Object.fromEntries(entries),
  };
}
