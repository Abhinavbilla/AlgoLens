import { Link, NavLink, Route, Routes, useLocation } from "react-router";
import styles from "./App.module.css";
import { HealthBadge } from "./HealthBadge";
import { ThemeToggle } from "./ThemeToggle";
import { PathPage } from "./learn/PathPage";
import { PrimerPage } from "./learn/PrimerPage";
import { EntryPage } from "./pages/EntryPage";
import { JobPage } from "./pages/JobPage";
import { LibraryPage } from "./pages/LibraryPage";
import { ProblemPage } from "./pages/ProblemPage";
import { SolvePage } from "./pages/SolvePage";

export function App() {
  const location = useLocation();
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link to="/" className={styles.brand} aria-label="AlgoLens home">
          <Logo />
          <span>AlgoLens</span>
        </Link>
        <nav aria-label="Main" className={styles.nav}>
          <NavLink
            to="/"
            className={({ isActive }) =>
              isActive && !/^\/(solve|jobs|problems|path|learn)/.test(location.pathname) ? styles.active : ""
            }
          >
            Library
          </NavLink>
          <NavLink to="/path" className={({ isActive }) => (isActive ? styles.active : "")}>
            Learning path
          </NavLink>
          <NavLink to="/solve" className={({ isActive }) => (isActive ? styles.active : "")}>
            Paste a problem
          </NavLink>
        </nav>
        <div className={styles.tools}>
          <HealthBadge />
          <ThemeToggle />
        </div>
      </header>
      <main className={styles.main}>
        <Routes>
          <Route path="/" element={<LibraryPage />} />
          <Route path="/library/:slug" element={<EntryPage />} />
          <Route path="/solve" element={<SolvePage />} />
          <Route path="/path" element={<PathPage />} />
          <Route path="/learn/:topic" element={<PrimerPage />} />
          <Route path="/jobs/:jobId" element={<JobPage />} />
          <Route path="/problems/:problemId" element={<ProblemPage />} />
          <Route
            path="*"
            element={
              <section className={styles.notFound}>
                <h1>Nothing here</h1>
                <p>
                  That page doesn't exist. <Link to="/">Back to the library</Link>
                </p>
              </section>
            }
          />
        </Routes>
      </main>
      <footer className={styles.footer}>
        <span>
          <strong>AlgoLens</strong> · every step is a real run of real code.
        </span>
        <span>
          <Link to="/">Library</Link> · <Link to="/solve">Paste a problem</Link>
        </span>
      </footer>
    </div>
  );
}

// A lens over three bars: the product in one picture.
function Logo() {
  return (
    <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true" className={styles.logo}>
      <rect x="5" y="17" width="4" height="9" rx="1.5" />
      <rect x="11" y="11" width="4" height="15" rx="1.5" />
      <rect x="17" y="14" width="4" height="12" rx="1.5" />
      <circle cx="21" cy="11" r="7.5" fill="none" strokeWidth="2.6" />
      <line x1="26.4" y1="16.4" x2="30" y2="20" strokeWidth="2.8" strokeLinecap="round" />
    </svg>
  );
}
