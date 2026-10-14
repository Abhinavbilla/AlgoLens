import { useState } from "react";
import styles from "./viz.module.css";

type Props = { python: string; cpp: string; pythonLine: number; cppLine: number | null };

export function CodeView({ python, cpp, pythonLine, cppLine }: Props) {
  const [lang, setLang] = useState<"python" | "cpp">("python");
  const source = lang === "python" ? python : cpp;
  const current = lang === "python" ? pythonLine : cppLine;
  return (
    <section className={styles.panel} aria-label="Code">
      <div className={styles.tabs} role="group" aria-label="Language">
        <button type="button" aria-pressed={lang === "python"} onClick={() => setLang("python")}>
          Python
        </button>
        <button type="button" aria-pressed={lang === "cpp"} onClick={() => setLang("cpp")}>
          C++
        </button>
      </div>
      {lang === "cpp" && <p className={styles.legend}>The highlighted C++ line is the closest match to the Python line.</p>}
      <pre className={styles.code}>
        {source.replace(/\n$/, "").split("\n").map((text, i) => {
          const n = i + 1;
          const isCurrent = n === current;
          return (
            <div key={n} className={isCurrent ? styles.currentLine : styles.line} aria-current={isCurrent ? "step" : undefined}>
              <span className={styles.gutter} aria-hidden="true">
                {isCurrent ? "▶" : ""}
              </span>
              <span className={styles.lineNo} aria-hidden="true">
                {n}
              </span>
              <code>{text || " "}</code>
            </div>
          );
        })}
      </pre>
    </section>
  );
}
