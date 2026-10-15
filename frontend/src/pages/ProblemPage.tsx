import { Fragment, useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { api, type ApproachView, type ProblemView } from "../api";
import { HighlightedLine } from "../viz/highlight";
import { ApproachPlayer } from "./ApproachPlayer";
import { ThoughtProcess } from "./ThoughtProcess";
import { Compare } from "./CompareChart";
import pageStyles from "./pages.module.css";
import styles from "./solve.module.css";

type Load =
  { status: "loading" } | { status: "error"; message: string } | { status: "ok"; data: ProblemView };

export function ProblemPage() {
  const { problemId = "" } = useParams();
  return <ProblemContent key={problemId} problemId={problemId} />;
}

function ProblemContent({ problemId }: { problemId: string }) {
  const [state, setState] = useState<Load>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .problem(problemId)
      .then((data) => !cancelled && setState({ status: "ok", data }))
      .catch((e: Error) => !cancelled && setState({ status: "error", message: e.message }));
    return () => {
      cancelled = true;
    };
  }, [problemId]);

  if (state.status === "loading") return <p role="status">Loading…</p>;
  if (state.status === "error") {
    return (
      <section className={styles.solve}>
        <p role="alert">{state.message}</p>
        <Link to="/solve">Paste a problem</Link>
      </section>
    );
  }
  const p = state.data;
  if (p.status !== "done") {
    return (
      <section className={styles.solve}>
        <h1>
          {p.status === "rejected" ? "This problem isn't supported" : "This problem couldn't be finished"}
        </h1>
        <p role="alert">{p.reason}</p>
        <Link to="/solve">Paste another problem</Link>
      </section>
    );
  }
  return (
    <article className={styles.problem}>
      <header className={pageStyles.entryHeader}>
        <p className={pageStyles.crumbs}>
          <Link to="/solve">Paste a problem</Link> / result
        </p>
        <h1>{p.title || p.function_name}</h1>
        <p className={pageStyles.input}>
          Signature: <code>{`${p.function_name}(${p.params.map((x) => x.name).join(", ")})`}</code>
        </p>
      </header>
      {p.explanation && <ThoughtProcess explanation={p.explanation} />}
      {p.explanation && <h2 className={styles.codeHeading}>The verified code, step by step</h2>}
      <ol className={styles.approaches}>
        {p.approaches.map((a) => (
          <li key={a.id}>
            <ApproachCard approach={a} problem={p} />
          </li>
        ))}
      </ol>
      {p.approaches.filter((a) => a.status === "verified").length > 0 && <Compare problemId={p.id} />}
    </article>
  );
}

export function ApproachBadge({ approach: a }: { approach: ApproachView }) {
  if (a.status === "verified") {
    return (
      <p className={`${pageStyles.badge} ${pageStyles.verified}`}>
        <span aria-hidden="true">✓</span> Verified · {a.examples_checked} examples and{" "}
        {a.exhaustive ? `all ${a.tests_passed} possible inputs` : `${a.tests_passed} random tests`}, Python
        and C++ agree
      </p>
    );
  }
  if (a.status === "timeout") {
    return (
      <p className={`${pageStyles.badge} ${pageStyles.unverified}`}>
        <span aria-hidden="true">⧗</span> Not verified: too slow on a test
      </p>
    );
  }
  return (
    <p className={`${pageStyles.badge} ${pageStyles.unverified}`}>
      <span aria-hidden="true">?</span> Not verified
    </p>
  );
}

function ApproachCard({ approach: a, problem }: { approach: ApproachView; problem: ProblemView }) {
  const [lang, setLang] = useState<"python" | "cpp">("python");
  const [watching, setWatching] = useState(false);
  return (
    <section className={styles.approach} aria-labelledby={`h-${a.id}`}>
      <h2 id={`h-${a.id}`}>
        {a.name}
        {a.is_brute && <span className={styles.tag}>reference</span>}
      </h2>
      <ApproachBadge approach={a} />
      <p>{a.key_idea}</p>
      <p className={styles.complexity}>
        Time <code>{a.time}</code> · Space <code>{a.space}</code>
        {a.repairs > 0 && (
          <span className={styles.muted}>
            {" "}
            · fixed {a.repairs === 1 ? "once" : `${a.repairs} times`} after failing a check
          </span>
        )}
      </p>
      {a.status !== "verified" && a.reason && <p className={styles.reason}>{a.reason}</p>}
      <p className={styles.watch}>
        {a.animated ? (
          <button type="button" aria-expanded={watching} onClick={() => setWatching((w) => !w)}>
            {watching ? "Show the code only" : "Watch it run step by step"}
          </button>
        ) : (
          <span className={styles.muted}>{a.animation_note}</span>
        )}
        {a.animated && a.animation_note && <span className={styles.muted}> {a.animation_note}</span>}
      </p>
      {watching ? (
        <ApproachPlayer problemId={problem.id} approach={a} inputs={problem.inputs} />
      ) : (
        <CodeTabs approach={a} lang={lang} setLang={setLang} />
      )}
    </section>
  );
}

function CodeTabs({
  approach: a,
  lang,
  setLang,
}: {
  approach: ApproachView;
  lang: "python" | "cpp";
  setLang: (l: "python" | "cpp") => void;
}) {
  return (
    <>
      <div className={styles.tabs} role="tablist" aria-label={`${a.name} code`}>
        {(["python", "cpp"] as const).map((l) => (
          <button
            key={l}
            role="tab"
            type="button"
            aria-selected={lang === l}
            className={lang === l ? styles.tabOn : styles.tab}
            onClick={() => setLang(l)}
          >
            {l === "python" ? "Python" : "C++"}
          </button>
        ))}
      </div>
      <pre className={styles.code} role="tabpanel" tabIndex={0}>
        <code>
          {(lang === "python" ? a.python_code : a.cpp_code)
            .trim()
            .split("\n")
            .map((line, i) => (
              <Fragment key={i}>
                {i > 0 && "\n"}
                <HighlightedLine text={line} lang={lang} />
              </Fragment>
            ))}
        </code>
      </pre>
    </>
  );
}
