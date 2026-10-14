import type { Verification } from "./api";
import styles from "./pages/pages.module.css";

// Text carries the meaning; the icon and colour only reinforce it.
export function VerificationBadge({ verification: v }: { verification: Verification }) {
  if (v.status === "verified") {
    return (
      <p className={`${styles.badge} ${styles.verified}`}>
        <span aria-hidden="true">✓</span> Verified · passed {v.tests} tests
      </p>
    );
  }
  if (v.status === "failed") {
    return (
      <p className={`${styles.badge} ${styles.unverified}`}>
        <span aria-hidden="true">✗</span> Not verified: {v.failures?.[0] ?? "a check failed"}
      </p>
    );
  }
  return (
    <p className={`${styles.badge} ${styles.unverified}`}>
      <span aria-hidden="true">?</span> Not verified yet
    </p>
  );
}
