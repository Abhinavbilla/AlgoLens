import { NavLink, Route, Routes } from "react-router";
import styles from "./App.module.css";
import { HealthBadge } from "./HealthBadge";
import { ThemeToggle } from "./ThemeToggle";
import { EntryPage } from "./pages/EntryPage";
import { LibraryPage } from "./pages/LibraryPage";
import { SolvePage } from "./pages/SolvePage";

export function App() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <span className={styles.brand}>AlgoLens</span>
        <nav aria-label="Main" className={styles.nav}>
          <NavLink to="/" end className={({ isActive }) => (isActive ? styles.active : "")}>
            Library
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
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </div>
  );
}
