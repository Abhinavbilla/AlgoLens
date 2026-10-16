import { Fragment, type ReactNode } from "react";
import { InlineMarkdown } from "../InlineMarkdown";
import { HighlightedLine } from "../viz/highlight";
import styles from "./TutorPanel.module.css";

// The Markdown the tutor writes: paragraphs, bullet and numbered lists, small headings and
// fenced code blocks, plus InlineMarkdown inside them. Builds React elements directly
// (never HTML strings), so a reply can't inject markup.
export function Markdown({ text }: { text: string }) {
  const out: ReactNode[] = [];
  const parts = text.split(/^```([\w+-]*)[^\n]*\n([\s\S]*?)^```[^\n]*$/m);
  // split() with two groups yields [text, lang, code, text, lang, code, ..., text]
  for (let i = 0; i < parts.length; i += 3) {
    out.push(...blocks(parts[i], i));
    if (i + 2 < parts.length) out.push(<CodeBlock key={`c${i}`} lang={parts[i + 1]} code={parts[i + 2]} />);
  }
  return <>{out}</>;
}

function CodeBlock({ lang, code }: { lang: string; code: string }) {
  const language = /^(c\+\+|cpp|c)$/i.test(lang) ? "cpp" : "python";
  const lines = code.replace(/\n$/, "").split("\n");
  return (
    <pre className={styles.codeBlock} tabIndex={0}>
      <code>
        {lines.map((line, i) => (
          <Fragment key={i}>
            {i > 0 && "\n"}
            <HighlightedLine text={line} lang={language} />
          </Fragment>
        ))}
      </code>
    </pre>
  );
}

const BULLET = /^\s*[-*]\s+/;
const NUMBER = /^\s*\d+[.)]\s+/;
type Run = { kind: "ul" | "ol" | "p"; lines: string[] };

function blocks(text: string, base: number): ReactNode[] {
  const out: ReactNode[] = [];
  const paragraphs = text
    .split(/\n\s*\n/)
    .map((b) => b.replace(/^\n+|\s+$/g, ""))
    .filter(Boolean);
  paragraphs.forEach((block, j) => {
    // A paragraph can mix a lead-in sentence and a list: split it into runs of one kind.
    const runs: Run[] = [];
    for (const line of block.split("\n")) {
      const kind = BULLET.test(line) ? "ul" : NUMBER.test(line) ? "ol" : "p";
      const last = runs[runs.length - 1];
      if (last && last.kind === kind) last.lines.push(line);
      else runs.push({ kind, lines: [line] });
    }
    runs.forEach((run, r) => out.push(renderRun(run, `${base}-${j}-${r}`)));
  });
  return out;
}

function renderRun({ kind, lines }: Run, key: string): ReactNode {
  if (kind !== "p") {
    const List = kind;
    const marker = kind === "ul" ? BULLET : NUMBER;
    return (
      <List key={key}>
        {lines.map((l, k) => (
          <li key={k}>
            <InlineMarkdown text={l.replace(marker, "")} />
          </li>
        ))}
      </List>
    );
  }
  const heading = /^#{1,4}\s+(.*)$/.exec(lines[0]);
  if (heading && lines.length === 1) {
    return (
      <p key={key} className={styles.mdHeading}>
        <InlineMarkdown text={heading[1]} />
      </p>
    );
  }
  return (
    <p key={key}>
      {lines.map((l, k) => (
        <Fragment key={k}>
          {k > 0 && <br />}
          <InlineMarkdown text={l.replace(/^#{1,4}\s+/, "")} />
        </Fragment>
      ))}
    </p>
  );
}
