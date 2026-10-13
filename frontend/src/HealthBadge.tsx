import { useEffect, useState } from "react";
import styles from "./HealthBadge.module.css";

type Health = "checking" | "ok" | "degraded" | "offline";

const LABELS: Record<Health, string> = {
  checking: "Checking server…",
  ok: "Server OK",
  degraded: "Database down",
  offline: "Server unreachable",
};

export function HealthBadge() {
  const [health, setHealth] = useState<Health>("checking");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then((r) => r.json())
      .then((body: { status: string }) => {
        if (!cancelled) setHealth(body.status === "ok" ? "ok" : "degraded");
      })
      .catch(() => {
        if (!cancelled) setHealth("offline");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Text label carries the state; the dot is decoration only.
  return (
    <span className={styles.badge} data-state={health} role="status">
      <span className={styles.dot} aria-hidden="true" />
      {LABELS[health]}
    </span>
  );
}
