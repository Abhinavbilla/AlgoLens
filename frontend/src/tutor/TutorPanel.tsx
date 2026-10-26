import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ApiError, api, type ChatMessage, type ChatMode, type CheckResult, type TutorStep } from "../api";
import type { PageInfo, StepReport } from "./TutorContext";
import { Markdown } from "./Markdown";
import { MIN_HEIGHT, MIN_WIDTH, useResizable } from "./resize";
import styles from "./TutorPanel.module.css";

export type Tab = "explain" | "hint" | "check";
export type Opening = { tab?: Tab; question?: string; withStep?: boolean; nonce?: number };

type Shown = ChatMessage & { mode: ChatMode; step?: string };

const MAX_MESSAGES = 20; // the server's limit for one conversation
const MAX_CHARS = 19000; // a little under the server's 20 000

type Props = {
  page: PageInfo;
  open: boolean;
  opening: Opening | null;
  hasStep: boolean;
  currentStep: () => StepReport | null;
  onOpen: () => void;
  onClose: () => void;
};

// Per tab, so a reload keeps the conversation but nothing leaves this browser.
function load<T>(key: string, fallback: T): T {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown) {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage full or blocked: the chat still works, it just won't survive a reload
  }
}

function stub(page: PageInfo) {
  return `def ${page.functionName}(${page.params.join(", ")}):\n    `;
}

export function TutorPanel({ page, open, opening, hasStep, currentStep, onOpen, onClose }: Props) {
  const key = `algolens:tutor:${page.target.kind}:${page.target.id}`;
  const [tab, setTab] = useState<Tab>("explain");
  const [messages, setMessages] = useState<Shown[]>(() => load(`${key}:chat`, []));
  const [draft, setDraft] = useState("");
  const [withStep, setWithStep] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [code, setCode] = useState<string>(() => load(`${key}:code`, stub(page)));
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [checkError, setCheckError] = useState("");
  const input = useRef<HTMLTextAreaElement>(null);
  const log = useRef<HTMLDivElement>(null);
  const resize = useResizable();

  useEffect(() => save(`${key}:chat`, messages), [key, messages]);
  useEffect(() => save(`${key}:code`, code), [key, code]);
  useEffect(() => {
    log.current?.scrollTo?.({ top: log.current.scrollHeight });
  }, [messages, busy]);

  // Opened from somewhere specific ("ask about this step"): go to that tab, prefill the question.
  // (Adjusted while rendering, keyed by the opening's nonce, rather than in an effect.)
  const [seen, setSeen] = useState<number | undefined>(undefined);
  if (opening && opening.nonce !== seen) {
    setSeen(opening.nonce);
    if (opening.tab) setTab(opening.tab);
    if (opening.question !== undefined) setDraft(opening.question);
    if (opening.withStep !== undefined) setWithStep(opening.withStep);
  }

  useEffect(() => {
    if (open && tab !== "check") input.current?.focus();
  }, [open, tab, opening]);

  const used = messages.length;
  const full = used >= MAX_MESSAGES - 1;

  async function send(text: string, mode: ChatMode) {
    const question = text.trim();
    if (!question || busy || full) return;
    const report = withStep && mode !== "review" ? currentStep() : null;
    const step: TutorStep | null = report
      ? { index: report.index, line: report.line, narration: report.narration, variables: report.variables }
      : null;
    const mine: Shown = {
      role: "user",
      content: question,
      mode,
      step: step ? `step ${step.index + 1}${step.line ? `, line ${step.line}` : ""}` : undefined,
    };
    const next = [...messages, mine];
    setMessages(next);
    setDraft("");
    setError("");
    setBusy(true);
    try {
      const { reply } = await api.chat({
        context: { ...page.target, approach_id: report?.approachId ?? page.target.approach_id, step },
        mode,
        messages: trimmed(next),
      });
      setMessages([...next, { role: "assistant", content: reply, mode }]);
    } catch (e) {
      // Keep the question so it can be sent again.
      setMessages(messages);
      setDraft(question);
      setError(e instanceof ApiError ? e.message : "Couldn't reach the server.");
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    void send(draft, tab === "hint" ? "hint" : "explain");
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) submit(e);
  }

  async function runCheck() {
    setChecking(true);
    setCheckError("");
    setResult(null);
    try {
      setResult(await api.checkCode(page.target, code));
    } catch (e) {
      setCheckError(e instanceof ApiError ? e.message : "Couldn't reach the server.");
    } finally {
      setChecking(false);
    }
  }

  function askAboutResult() {
    if (!result) return;
    const detail = result.failure?.detail ? `\n\nError output:\n\`\`\`\n${result.failure.detail}\n\`\`\`` : "";
    const ask =
      result.verdict === "passed"
        ? "It passed. How does it compare with the verified approaches, and can it be simpler or faster?"
        : "What's wrong, and how do I fix it?";
    setTab("explain");
    void send(
      `Here's my code:\n\`\`\`python\n${code.trim()}\n\`\`\`\n\nThe check said: ${result.message}${detail}\n\n${ask}`,
      "review",
    );
  }

  function newChat() {
    setMessages([]);
    setError("");
    setDraft("");
  }

  if (!open) {
    return (
      <button type="button" className={styles.launcher} onClick={onOpen}>
        <TutorMark />
        <span>Ask the tutor</span>
      </button>
    );
  }

  return (
    <aside
      className={resize.dragging ? `${styles.panel} ${styles.resizing}` : styles.panel}
      style={resize.style}
      role="dialog"
      aria-label="Tutor"
      onKeyDown={(e) => e.key === "Escape" && onClose()}
    >
      {/* Drag an edge to resize; arrow keys work too, and a double-click resets the size. */}
      <div
        className={styles.edgeLeft}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize the tutor's width"
        aria-valuemin={MIN_WIDTH}
        aria-valuenow={resize.size.width}
        tabIndex={0}
        title="Drag to resize · double-click to reset"
        onPointerDown={resize.onPointerDown("left")}
        onKeyDown={resize.onKeyDown("left")}
        onDoubleClick={resize.reset}
      />
      <div
        className={styles.edgeTop}
        role="separator"
        aria-orientation="horizontal"
        aria-label="Resize the tutor's height"
        aria-valuemin={MIN_HEIGHT}
        aria-valuenow={resize.size.height ?? undefined}
        tabIndex={0}
        title="Drag to resize · double-click to reset"
        onPointerDown={resize.onPointerDown("top")}
        onKeyDown={resize.onKeyDown("top")}
        onDoubleClick={resize.reset}
      />
      <div
        className={styles.edgeCorner}
        aria-hidden="true"
        title="Drag to resize · double-click to reset"
        onPointerDown={resize.onPointerDown("corner")}
        onDoubleClick={resize.reset}
      />
      <header className={styles.head}>
        <TutorMark />
        <div className={styles.headText}>
          <h2>Tutor</h2>
          <p>Knows this page&rsquo;s verified code and tests</p>
        </div>
        {messages.length > 0 && (
          <button type="button" className={styles.ghost} onClick={newChat}>
            New chat
          </button>
        )}
        <button type="button" className={styles.close} onClick={onClose} aria-label="Close the tutor">
          ×
        </button>
      </header>

      <div className={styles.tabs} role="tablist" aria-label="What kind of help">
        {(
          [
            ["explain", "Explain"],
            ["hint", "Just a hint"],
            ["check", "Check my code"],
          ] as const
        ).map(([t, label]) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={tab === t ? styles.tabOn : styles.tab}
            onClick={() => setTab(t)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "check" ? (
        <div className={styles.check}>
          <p className={styles.lead}>
            Write your own <code>{page.functionName}</code> in Python. It runs in our sandbox on the worked
            examples and {25} small random inputs, and is compared with the verified solution.
          </p>
          <textarea
            className={styles.code}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            spellCheck={false}
            aria-label="Your Python code"
            rows={12}
            onKeyDown={(e) => {
              if (e.key === "Tab" && !e.shiftKey) {
                e.preventDefault();
                const t = e.currentTarget;
                const { selectionStart: a, selectionEnd: b } = t;
                setCode(code.slice(0, a) + "    " + code.slice(b));
                requestAnimationFrame(() => t.setSelectionRange(a + 4, a + 4));
              }
            }}
          />
          <div className={styles.row}>
            <button type="button" className={styles.primary} onClick={runCheck} disabled={checking}>
              {checking ? "Running the tests…" : "Run the tests"}
            </button>
            <button type="button" className={styles.ghost} onClick={() => setCode(stub(page))}>
              Start over
            </button>
          </div>
          {checkError && <p role="alert">{checkError}</p>}
          {result && (
            <div className={result.verdict === "passed" ? styles.pass : styles.fail} role="status">
              <p className={styles.verdict}>
                {result.verdict === "passed" ? "✓ All tests pass" : "✗ Not yet"}
                {result.total > 0 && (
                  <span>
                    {" "}
                    · {result.passed} of {result.total}
                  </span>
                )}
              </p>
              <p>{result.message}</p>
              {result.failure?.detail && <pre className={styles.detail}>{result.failure.detail}</pre>}
              {result.verdict !== "missing_function" && (
                <button type="button" className={styles.primary} onClick={askAboutResult} disabled={busy || full}>
                  {result.verdict === "passed" ? "Ask how it compares" : "Ask the tutor why"}
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <>
          <div className={styles.log} ref={log} aria-live="polite">
            {messages.length === 0 && (
              <div className={styles.empty}>
                <p className={styles.lead}>
                  {tab === "hint"
                    ? "Stuck? Ask for a nudge. You'll get one hint at a time, never the answer."
                    : "Ask anything about this page: why a line is there, what a step does, or why it's fast."}
                </p>
                <div className={styles.chips}>
                  {(tab === "hint" ? HINT_CHIPS : page.suggestions).map((s) => (
                    <button key={s} type="button" onClick={() => void send(s, tab === "hint" ? "hint" : "explain")}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? styles.mine : styles.theirs}>
                {m.role === "user" && (m.mode !== "explain" || m.step) && (
                  <p className={styles.meta}>
                    {[m.mode === "hint" && "hint", m.mode === "review" && "code review", m.step && `about ${m.step}`]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                )}
                {m.role === "assistant" ? <Markdown text={m.content} /> : <UserText text={m.content} />}
              </div>
            ))}
            {busy && (
              <div className={styles.theirs} role="status">
                <span className={styles.dots} aria-label="The tutor is thinking">
                  <i />
                  <i />
                  <i />
                </span>
              </div>
            )}
          </div>
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
          <form className={styles.compose} onSubmit={submit}>
            {hasStep && (
              <label className={styles.stepToggle}>
                <input type="checkbox" checked={withStep} onChange={(e) => setWithStep(e.target.checked)} />
                Include the step I'm on in the player
              </label>
            )}
            {full ? (
              <p className={styles.lead}>
                This conversation is as long as it can get.{" "}
                <button type="button" className={styles.link} onClick={newChat}>
                  Start a new one
                </button>
              </p>
            ) : (
              <div className={styles.inputRow}>
                <textarea
                  ref={input}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={onKey}
                  rows={2}
                  maxLength={4000}
                  placeholder={tab === "hint" ? "What are you stuck on?" : "Ask a question…"}
                  aria-label="Your question"
                />
                <button type="submit" className={styles.send} disabled={busy || !draft.trim()} aria-label="Send">
                  <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
                    <path d="M3 10h11M10 5l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="2" />
                  </svg>
                </button>
              </div>
            )}
          </form>
        </>
      )}
      <p className={styles.note}>
        The code and test results on this page are checked. The tutor&rsquo;s words are AI-written and can be wrong.
      </p>
    </aside>
  );
}

const HINT_CHIPS = [
  "I don't know where to start",
  "What's the key observation?",
  "Which data structure would help?",
  "My idea is too slow. What's the bottleneck?",
];

// The newest messages that fit the server's limits, starting with one of the learner's.
function trimmed(all: Shown[]): ChatMessage[] {
  let msgs = all.map(({ role, content }) => ({ role, content }));
  while (
    msgs.length > MAX_MESSAGES ||
    msgs.reduce((n, m) => n + m.content.length, 0) > MAX_CHARS ||
    (msgs.length > 1 && msgs[0].role !== "user")
  ) {
    msgs = msgs.slice(1);
  }
  return msgs;
}

function UserText({ text }: { text: string }) {
  // The learner's own words, shown as typed; their code (in a review) gets a code block.
  const fence = text.indexOf("```");
  if (fence === -1) return <p className={styles.plain}>{text}</p>;
  return <Markdown text={text} />;
}

function TutorMark() {
  return (
    <svg className={styles.mark} viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
      <path
        d="M6 8.5C6 6.6 7.6 5 9.5 5h13C24.4 5 26 6.6 26 8.5v9c0 1.9-1.6 3.5-3.5 3.5H15l-5.5 5v-5h0C7.6 21 6 19.4 6 17.5z"
        fill="var(--brand)"
      />
      <circle cx="11.5" cy="13" r="1.6" fill="var(--surface)" />
      <circle cx="16" cy="13" r="1.6" fill="var(--surface)" />
      <circle cx="20.5" cy="13" r="1.6" fill="var(--surface)" />
    </svg>
  );
}
