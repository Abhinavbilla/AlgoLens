import styles from "./viz.module.css";

// A small per-line highlighter for Python and C++: keywords, strings, numbers, comments and
// a few builtins. Colour only reinforces what the text already says, so it can afford to be
// simple (no bundle download, no multi-line strings), and the line text is never changed.

export type Lang = "python" | "cpp";
type Kind = "kw" | "str" | "num" | "com" | "fn" | "plain";
export type Token = { kind: Kind; text: string };

const KEYWORDS: Record<Lang, Set<string>> = {
  python: new Set(
    (
      "and as assert break class continue def del elif else except False finally for from global if import in " +
      "is lambda None nonlocal not or pass raise return True try while with yield"
    ).split(" "),
  ),
  cpp: new Set(
    (
      "auto bool break case char class const constexpr continue default delete do double else enum explicit " +
      "false float for if inline int long namespace new nullptr private public return short signed size_t " +
      "sizeof static struct switch template this true typename unsigned using void while"
    ).split(" "),
  ),
};

const BUILTINS: Record<Lang, Set<string>> = {
  python: new Set(
    "len range min max sum sorted list dict set tuple abs enumerate zip print int str".split(" "),
  ),
  cpp: new Set("std vector string swap max min".split(" ")),
};

const PATTERNS: Record<Lang, RegExp> = {
  // comment | string | number | identifier | anything else
  python: /(#.*$)|("(?:[^"\\]|\\.)*"?|'(?:[^'\\]|\\.)*'?)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+|.)/g,
  cpp: /(\/\/.*$|^\s*#\s*include.*$)|("(?:[^"\\]|\\.)*"?|'(?:[^'\\]|\\.)*'?|<[\w./]+>(?=\s*$))|(\b\d+(?:\.\d+)?[LlUu]*\b)|([A-Za-z_]\w*)|(\s+|.)/g,
};

export function tokenize(line: string, lang: Lang): Token[] {
  const out: Token[] = [];
  const push = (kind: Kind, text: string) => {
    const last = out[out.length - 1];
    if (last && last.kind === kind) last.text += text;
    else out.push({ kind, text });
  };
  for (const m of line.matchAll(PATTERNS[lang])) {
    if (m[1]) push("com", m[1]);
    else if (m[2]) push("str", m[2]);
    else if (m[3]) push("num", m[3]);
    else if (m[4]) push(KEYWORDS[lang].has(m[4]) ? "kw" : BUILTINS[lang].has(m[4]) ? "fn" : "plain", m[4]);
    else push("plain", m[0]);
  }
  return out;
}

const CLASS: Record<Kind, string | undefined> = {
  kw: styles.synKw,
  str: styles.synStr,
  num: styles.synNum,
  com: styles.synCom,
  fn: styles.synFn,
  plain: undefined,
};

export function HighlightedLine({ text, lang }: { text: string; lang: Lang }) {
  return (
    <>
      {tokenize(text, lang).map((t, i) =>
        CLASS[t.kind] ? (
          <span key={i} className={CLASS[t.kind]}>
            {t.text}
          </span>
        ) : (
          t.text
        ),
      )}
    </>
  );
}
