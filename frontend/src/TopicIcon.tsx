import type { ReactNode } from "react";
import styles from "./TopicIcon.module.css";

// One small diagram per topic, drawn like a textbook sketch: round strokes, slightly uneven
// lines, ink plus one coral accent. Decorative only (the text next to it says what it is).

const ICONS: Record<string, ReactNode> = {
  sorting: (
    <>
      <path className={styles.ink} d="M7 33 L7 24 M14 33 L14 18 M21 33 L21 12.5 M28 33 L28 8" />
      <path className={styles.accent} d="M5.5 36.2 C13 35.4 23 36.6 33.5 35.6" />
    </>
  ),
  searching: (
    <>
      <circle className={styles.ink} cx="17" cy="17" r="9.5" />
      <path className={styles.ink} d="M24.2 24.4 L33.3 33.1" />
      <path className={styles.accent} d="M12.4 17.3 C14.2 13.8 18.9 13.1 21.6 15.6" />
    </>
  ),
  "strings-hashing": (
    <>
      <path className={styles.ink} d="M5 30 L10 11.5 L15 30 M7 23.5 L13.2 23.4" />
      <path
        className={styles.ink}
        d="M28.6 18.6 C24.6 15.7 19.4 17.4 19.6 22.8 C19.8 28.6 25.6 30.1 28.8 26.5"
      />
      <path className={styles.accent} d="M4.5 34.6 L35 34.2" />
    </>
  ),
  bits: (
    <>
      <rect className={styles.ink} x="4.5" y="13" width="9" height="14" rx="2.5" />
      <path className={styles.accent} d="M22 13.5 L22 27" />
      <rect className={styles.ink} x="27" y="13" width="9" height="14" rx="2.5" />
      <path className={styles.ink} d="M17 13.4 L19 12 L19 27" />
    </>
  ),
  "array-techniques": (
    <>
      <path
        className={styles.ink}
        d="M4 15 L36 15 L36 25 L4 25 Z M12 15 L12 25 M20 15 L20 25 M28 15 L28 25"
      />
      <path
        className={styles.accent}
        d="M8 31 L8 27.5 M5.8 29.6 L8 27.3 L10.2 29.6 M32 31 L32 27.5 M29.8 29.6 L32 27.3 L34.2 29.6"
      />
    </>
  ),
  heaps: (
    <>
      <circle className={styles.accent} cx="20" cy="9" r="4" />
      <circle className={styles.ink} cx="11" cy="21" r="4" />
      <circle className={styles.ink} cx="29" cy="21" r="4" />
      <circle className={styles.ink} cx="6" cy="33" r="3.4" />
      <circle className={styles.ink} cx="16" cy="33" r="3.4" />
      <path
        className={styles.ink}
        d="M17.4 12 L13.6 17.8 M22.6 12 L26.4 17.8 M9.4 24.6 L7.4 29.8 M12.6 24.6 L14.6 29.8"
      />
    </>
  ),
  "linked-lists": (
    <>
      <rect className={styles.ink} x="3" y="15" width="9" height="10" rx="2.5" />
      <rect className={styles.ink} x="16" y="15" width="9" height="10" rx="2.5" />
      <rect className={styles.accent} x="29" y="15" width="8" height="10" rx="2.5" />
      <path
        className={styles.ink}
        d="M12.4 20.2 L15.2 20 M13.8 18.4 L15.4 20 L13.8 21.7 M25.4 20 L28.2 20.1 M26.8 18.4 L28.4 20 L26.8 21.6"
      />
    </>
  ),
  graphs: (
    <>
      <path
        className={styles.ink}
        d="M9 10 L30 8 M9 10 L12 30 M30 8 L30.5 28.6 M12 30 L30.5 28.6 M9 10 L30.5 28.6"
      />
      <circle className={styles.accent} cx="9" cy="10" r="3.6" />
      <circle className={styles.ink} cx="30" cy="8" r="3.4" />
      <circle className={styles.ink} cx="12" cy="30" r="3.4" />
      <circle className={styles.ink} cx="30.5" cy="28.6" r="3.4" />
    </>
  ),
  trees: (
    <>
      <path className={styles.ink} d="M20 9 L11 21 M20 9 L29 21 M11 21 L6 32 M11 21 L16 32" />
      <circle className={styles.accent} cx="20" cy="8" r="3.8" />
      <circle className={styles.ink} cx="11" cy="21" r="3.4" />
      <circle className={styles.ink} cx="29" cy="21" r="3.4" />
      <circle className={styles.ink} cx="6" cy="32.5" r="3" />
      <circle className={styles.ink} cx="16" cy="32.5" r="3" />
    </>
  ),
  "dynamic-programming": (
    <>
      <path
        className={styles.ink}
        d="M5 6 L35 6 L35 34 L5 34 Z M15 6 L15 34 M25 6 L25 34 M5 15.3 L35 15.3 M5 24.6 L35 24.6"
      />
      <path className={styles.accent} d="M10 10.6 L19.6 20 L29.6 29.6" />
    </>
  ),
  greedy: (
    <>
      <path className={styles.ink} d="M4 30 C10 30 12 22 18 22 C24 22 26 12 34 11" />
      <path className={styles.accent} d="M29.4 8.6 L34.6 10.8 L31.2 15.4" />
      <circle className={styles.ink} cx="18" cy="22" r="2.4" />
    </>
  ),
  backtracking: (
    <>
      <path
        className={styles.ink}
        d="M20 5 L20 14 M20 14 L10 24 M20 14 L30 24 M10 24 L6 34 M10 24 L14.5 34"
      />
      <path
        className={styles.accent}
        d="M33 30.8 C35.4 25.4 33.2 19.6 28.8 17.6 M27.2 21.2 L28.6 17.4 L32.4 18.4"
      />
    </>
  ),
  "range-queries": (
    <>
      <path
        className={styles.ink}
        d="M4 28 L36 28 M8 28 L8 31.6 M16 28 L16 31.6 M24 28 L24 31.6 M32 28 L32 31.6"
      />
      <path className={styles.accent} d="M10 22 C10 15 12 14 20 14 C28 14 30 15 30 22" />
      <path className={styles.ink} d="M20 14 L20 8.5" />
    </>
  ),
  foundations: (
    <>
      <path className={styles.ink} d="M6 31 L34 31 M9 31 L9 21 L31 21 L31 31 M13 21 L13 13 L27 13 L27 21" />
      <path className={styles.accent} d="M17 13 L17 7 L23 7 L23 13" />
    </>
  ),
  recursion: (
    <>
      <rect className={styles.ink} x="5" y="5" width="30" height="30" rx="4" />
      <rect className={styles.ink} x="11" y="11" width="18" height="18" rx="3" />
      <rect className={styles.accent} x="16.5" y="16.5" width="7" height="7" rx="2" />
    </>
  ),
  stacks: (
    <>
      <rect className={styles.ink} x="9" y="26" width="22" height="7" rx="2" />
      <rect className={styles.ink} x="9" y="17" width="22" height="7" rx="2" />
      <rect className={styles.accent} x="9" y="8" width="22" height="7" rx="2" />
    </>
  ),
};

const ALIASES: Record<string, string> = {
  more: "foundations",
  "first-algorithms": "sorting",
  numbers: "bits",
  "stacks-queues": "stacks",
};

export function TopicIcon({ topic, size = 40 }: { topic: string; size?: number }) {
  const icon = ICONS[topic] ?? ICONS[ALIASES[topic] ?? ""] ?? ICONS.foundations;
  return (
    <svg className={styles.icon} width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      {icon}
    </svg>
  );
}
