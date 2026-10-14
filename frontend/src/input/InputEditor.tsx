import { useId, useState, type FormEvent } from "react";
import type { InputParam, Issue } from "../api";
import styles from "./InputEditor.module.css";

type Props = {
  params: InputParam[];
  initial: unknown[]; // the input currently shown
  defaults: unknown[]; // the entry's default input
  running: boolean;
  /** Runs the input; resolves to the problems found (empty = it ran). */
  onRun: (args: unknown[]) => Promise<{ message: string; issues: Issue[] } | null>;
};

// Text fields: strings are typed as-is, everything else as JSON. The server checks the
// input against the problem's rules; nothing reruns until it passes.
export function InputEditor({ params, initial, defaults, running, onRun }: Props) {
  const id = useId();
  const [asJson, setAsJson] = useState(false);
  const [fields, setFields] = useState(() => params.map((p, i) => toText(p, initial[i])));
  const [whole, setWhole] = useState(() => JSON.stringify(initial));
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [summary, setSummary] = useState<string[]>([]);

  function load(args: unknown[]) {
    setFields(params.map((p, i) => toText(p, args[i])));
    setWhole(JSON.stringify(args));
    setFieldErrors({});
    setSummary([]);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const parsed = asJson ? parseWhole(whole, params.length) : parseFields(params, fields);
    if ("errors" in parsed) {
      setFieldErrors(parsed.errors);
      setSummary(parsed.summary);
      return;
    }
    setFieldErrors({});
    setSummary([]);
    const problems = await onRun(parsed.args);
    if (!problems) return;
    const byField: Record<string, string[]> = {};
    const general: string[] = [];
    for (const issue of problems.issues) {
      const name = issue.path.split("[")[0];
      if (!asJson && params.some((p) => p.name === name)) {
        (byField[name] ??= []).push(`${issue.path}: ${issue.message}`);
      } else {
        general.push(issue.path ? `${issue.path}: ${issue.message}` : issue.message);
      }
    }
    setFieldErrors(byField);
    setSummary([problems.message, ...general]);
  }

  return (
    <form className={styles.editor} onSubmit={submit} aria-label="Try your own input">
      <div className={styles.header}>
        <h2 className={styles.title}>Try your own input</h2>
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={asJson}
            onChange={(e) => {
              const next = e.target.checked;
              if (next) {
                const parsed = parseFields(params, fields);
                if (!("errors" in parsed)) setWhole(JSON.stringify(parsed.args));
              } else {
                const parsed = parseWhole(whole, params.length);
                if (!("errors" in parsed)) setFields(params.map((p, i) => toText(p, parsed.args[i])));
              }
              setFieldErrors({});
              setSummary([]);
              setAsJson(next);
            }}
          />
          Edit all as JSON
        </label>
      </div>

      {summary.length > 0 && (
        <div className={styles.summary} role="alert">
          {summary.map((s, i) => (
            <p key={i}>{s}</p>
          ))}
        </div>
      )}

      {asJson ? (
        <div className={styles.field}>
          <label htmlFor={`${id}-json`}>
            All arguments, in order: <code>[{params.map((p) => p.name).join(", ")}]</code>
          </label>
          <textarea
            id={`${id}-json`}
            className={styles.input}
            value={whole}
            onChange={(e) => setWhole(e.target.value)}
            rows={3}
            spellCheck={false}
          />
        </div>
      ) : (
        params.map((p, i) => {
          const errors = fieldErrors[p.name] ?? [];
          return (
            <div key={p.name} className={styles.field}>
              <label htmlFor={`${id}-${p.name}`}>
                <code>{p.name}</code>
              </label>
              <p id={`${id}-${p.name}-hint`} className={styles.hint}>
                {p.hint}
                {p.kind !== "string" && " (JSON)"}
              </p>
              <input
                id={`${id}-${p.name}`}
                className={`${styles.input} ${errors.length ? styles.invalid : ""}`}
                value={fields[i]}
                onChange={(e) => setFields(fields.map((f, j) => (j === i ? e.target.value : f)))}
                aria-invalid={errors.length > 0}
                aria-describedby={`${id}-${p.name}-hint${errors.length ? ` ${id}-${p.name}-err` : ""}`}
                spellCheck={false}
                autoComplete="off"
              />
              {errors.length > 0 && (
                <ul id={`${id}-${p.name}-err`} className={styles.errors}>
                  {errors.map((m, j) => (
                    <li key={j}>{m}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })
      )}

      <div className={styles.actions}>
        <button type="submit" className={styles.run} disabled={running}>
          {running ? "Running…" : "Run with this input"}
        </button>
        <button type="button" onClick={() => load(defaults)} disabled={running}>
          Reset to the example
        </button>
      </div>
    </form>
  );
}

function toText(p: InputParam, value: unknown): string {
  if (p.kind === "string" && typeof value === "string") return value;
  return JSON.stringify(value ?? null);
}

type Parsed = { args: unknown[] } | { errors: Record<string, string[]>; summary: string[] };

export function parseFields(params: InputParam[], fields: string[]): Parsed {
  const args: unknown[] = [];
  const errors: Record<string, string[]> = {};
  params.forEach((p, i) => {
    if (p.kind === "string") {
      args.push(fields[i]);
      return;
    }
    try {
      args.push(JSON.parse(fields[i]));
    } catch {
      errors[p.name] = [`${p.name}: isn't valid JSON (for example ${example(p.kind)})`];
    }
  });
  return Object.keys(errors).length ? { errors, summary: ["Fix the highlighted fields first."] } : { args };
}

export function parseWhole(text: string, count: number): Parsed {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    return { errors: {}, summary: ["That isn't valid JSON."] };
  }
  if (!Array.isArray(value) || value.length !== count) {
    return { errors: {}, summary: [`Give a JSON list of ${count} argument${count === 1 ? "" : "s"}.`] };
  }
  return { args: value };
}

function example(kind: string): string {
  switch (kind) {
    case "int":
      return "42";
    case "float":
      return "3.5";
    case "bool":
      return "true";
    case "binary_tree":
      return "[1, null, 2]";
    case "edges":
      return "[[0, 1], [1, 2]]";
    case "matrix":
    case "grid":
      return "[[1, 0], [0, 1]]";
    default:
      return "[1, 2, 3]";
  }
}
