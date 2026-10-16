import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { ApiError, accounts, type MyProblem } from "../api";
import { useProgress } from "../learn/progress";
import { Avatar, GoogleMark } from "./AccountButton";
import { useAuth } from "./AuthContext";
import styles from "./account.module.css";

/** Only a path on this site (the server checks the same for Google sign-ins). */
function safeNext(path: string | null) {
  return path && path.startsWith("/") && !path.startsWith("//") && !path.includes("\\") ? path : "/account";
}

type Mode = "login" | "signup";

export function AccountPage() {
  const { enabled, methods, user, loading, signIn } = useAuth();
  const [params, setParams] = useSearchParams();
  const error = params.get("error");
  const next = safeNext(params.get("next"));
  const mode: Mode = params.get("mode") === "signup" ? "signup" : "login";
  const setMode = (m: Mode) =>
    setParams(
      (p) => {
        p.set("mode", m);
        p.delete("error");
        return p;
      },
      { replace: true },
    );
  const verb = mode === "signup" ? "Sign up" : "Log in";

  if (loading) return <p role="status">Loading…</p>;
  if (user) {
    return (
      <section className={styles.page}>
        <h1>Your account</h1>
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        <SignedIn />
      </section>
    );
  }
  // Signed out: one small, centred box. Nothing on the site needs it.
  return (
    <section className={styles.stage}>
      <div className={styles.box}>
        <svg className={styles.boxMark} width="44" height="44" viewBox="0 0 32 32" aria-hidden="true">
          <rect x="5" y="17" width="4" height="9" rx="1.5" />
          <rect x="11" y="11" width="4" height="15" rx="1.5" />
          <rect x="17" y="14" width="4" height="12" rx="1.5" />
          <circle cx="21" cy="11" r="7.5" fill="none" strokeWidth="2.6" />
          <line x1="26.4" y1="16.4" x2="30" y2="20" strokeWidth="2.8" strokeLinecap="round" />
        </svg>
        <div className={styles.modes} role="group" aria-label="Log in or sign up">
          {(["login", "signup"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              className={mode === m ? styles.modeOn : styles.mode}
              onClick={() => setMode(m)}
            >
              {m === "signup" ? "Sign up" : "Log in"}
            </button>
          ))}
        </div>
        <h1 className={styles.boxTitle}>{mode === "signup" ? "Create your account" : "Welcome back"}</h1>
        <p className={styles.boxSub}>Optional · keeps your progress</p>
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        {enabled ? (
          <>
            {methods.google && (
              <button type="button" className={styles.google} onClick={() => signIn(next)}>
                <GoogleMark />
                {verb} with Google
              </button>
            )}
            {methods.google && methods.email && (
              <p className={styles.or}>
                <span>or</span>
              </p>
            )}
            {methods.email && <EmailSignIn key={mode} next={next} mode={mode} />}
          </>
        ) : (
          <p className={styles.boxSub}>Sign-in isn&rsquo;t set up yet.</p>
        )}
        <Link to={next === "/account" ? "/" : next} className={styles.skip}>
          Continue without an account →
        </Link>
      </div>
    </section>
  );
}

// Sign in with a 6-digit code sent to the address: no password to remember or leak.
function EmailSignIn({ next, mode }: { next: string; mode: Mode }) {
  const { signedIn } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [devMode, setDevMode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function send(e?: FormEvent) {
    e?.preventDefault();
    const to = sentTo ?? email.trim();
    setBusy(true);
    setMessage("");
    try {
      const { dev } = await accounts.emailStart(to);
      setDevMode(!!dev);
      setSentTo(to);
      setCode("");
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Couldn't reach the server.");
    } finally {
      setBusy(false);
    }
  }

  async function verify(e: FormEvent) {
    e.preventDefault();
    if (!sentTo) return;
    setBusy(true);
    setMessage("");
    try {
      const { user } = await accounts.emailVerify(sentTo, code, mode === "signup" ? name : "");
      signedIn(user);
      navigate(next, { replace: true });
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Couldn't reach the server.");
      setBusy(false);
    }
  }

  const error = message && (
    <p className={styles.error} role="alert">
      {message}
    </p>
  );

  if (sentTo) {
    return (
      <form className={styles.emailForm} onSubmit={verify}>
        {devMode ? (
          <p className={styles.devNote}>
            Test mode: email isn&rsquo;t set up, so the code for <strong>{sentTo}</strong> is in the server log
          </p>
        ) : (
          <p className={styles.sent}>
            Code sent to <strong>{sentTo}</strong>
          </p>
        )}
        <label htmlFor="signin-code" className={styles.hiddenLabel}>
          Code
        </label>
        <div className={styles.stack}>
          <input
            id="signin-code"
            className={styles.codeInput}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/[^\d ]/g, "").slice(0, 7))}
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="123456"
            autoFocus
            required
          />
          <button type="submit" className={styles.primary} disabled={busy || code.replace(/\D/g, "").length !== 6}>
            {busy ? "Checking…" : mode === "signup" ? "Create account" : "Verify & log in"}
          </button>
        </div>
        {error}
        <p className={styles.minor}>
          <button type="button" className={styles.link} onClick={() => void send()} disabled={busy}>
            Resend
          </button>
          <span aria-hidden="true">·</span>
          <button type="button" className={styles.link} onClick={() => setSentTo(null)}>
            Change email
          </button>
        </p>
      </form>
    );
  }
  return (
    <form className={styles.emailForm} onSubmit={send}>
      <div className={styles.stack}>
        {mode === "signup" && (
          <>
            <label htmlFor="signin-name" className={styles.hiddenLabel}>
              Your name
            </label>
            <input
              id="signin-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              placeholder="Your name"
              maxLength={80}
            />
          </>
        )}
        <label htmlFor="signin-email" className={styles.hiddenLabel}>
          Your email
        </label>
        <input
          id="signin-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          placeholder="you@example.com"
          required
        />
        <button type="submit" className={styles.primary} disabled={busy || !email.includes("@")}>
          {busy ? "Sending…" : `${mode === "signup" ? "Sign up" : "Log in"} with email`}
        </button>
      </div>
      {error}
    </form>
  );
}

type Load = { status: "loading" } | { status: "error"; message: string } | { status: "ok"; data: MyProblem[] };

function SignedIn() {
  const { user, signOut, deleteAccount } = useAuth();
  const { done } = useProgress();
  const [problems, setProblems] = useState<Load>({ status: "loading" });
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  useEffect(() => {
    let cancelled = false;
    accounts
      .problems()
      .then((data) => !cancelled && setProblems({ status: "ok", data }))
      .catch((e: Error) => !cancelled && setProblems({ status: "error", message: e.message }));
    return () => {
      cancelled = true;
    };
  }, []);

  if (!user) return null;

  async function act(fn: () => Promise<void>) {
    setBusy(true);
    setFailure("");
    try {
      await fn();
    } catch (e) {
      setFailure(e instanceof ApiError ? e.message : "Couldn't reach the server.");
    } finally {
      setBusy(false);
    }
  }

  async function forget(id: string) {
    await accounts.forgetProblem(id);
    setProblems((p) => (p.status === "ok" ? { status: "ok", data: p.data.filter((x) => x.id !== id) } : p));
  }

  return (
    <>
      <div className={`${styles.card} ${styles.profile}`}>
        <Avatar name={user.name} picture={user.picture} size={56} />
        <div>
          <p className={styles.name}>{user.name}</p>
          <p className={styles.small}>{user.email}</p>
          <p className={styles.small}>
            {done.size === 0
              ? "Nothing marked as done yet."
              : `${done.size} ${done.size === 1 ? "topic" : "topics"} marked as done, saved to your account.`}{" "}
            <Link to="/path">Learning path</Link>
          </p>
        </div>
        <button type="button" className={styles.secondary} disabled={busy} onClick={() => act(signOut)}>
          Sign out
        </button>
      </div>

      <h2 className={styles.heading}>Your problems</h2>
      {problems.status === "loading" && <p role="status">Loading…</p>}
      {problems.status === "error" && <p role="alert">{problems.message}</p>}
      {problems.status === "ok" &&
        (problems.data.length === 0 ? (
          <p className={styles.small}>
            Problems you open while signed in show up here. <Link to="/solve">Paste a problem</Link>
          </p>
        ) : (
          <ul className={styles.problems}>
            {problems.data.map((p) => (
              <li key={p.id}>
                <Link to={`/problems/${p.id}`}>{p.title}</Link>
                <span className={styles.small}>{new Date(p.added_at).toLocaleDateString()}</span>
                <button
                  type="button"
                  className={styles.remove}
                  onClick={() => void forget(p.id)}
                  aria-label={`Remove ${p.title} from your list`}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        ))}

      <h2 className={styles.heading}>Delete your account</h2>
      <p className={styles.small}>
        This deletes your account, your saved progress and your problem list from our server. Progress in this
        browser stays until you clear it. The problems themselves are shared results and aren&rsquo;t tied to
        you.
      </p>
      {confirming ? (
        <div className={styles.row}>
          <button type="button" className={styles.danger} disabled={busy} onClick={() => act(deleteAccount)}>
            Yes, delete everything
          </button>
          <button type="button" className={styles.secondary} onClick={() => setConfirming(false)}>
            Keep my account
          </button>
        </div>
      ) : (
        <button type="button" className={styles.secondary} onClick={() => setConfirming(true)}>
          Delete my account…
        </button>
      )}
      {failure && <p role="alert">{failure}</p>}
    </>
  );
}
