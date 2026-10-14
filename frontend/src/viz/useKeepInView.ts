import { useEffect, type RefObject } from "react";

/** When a panel's content is wider than the panel, scroll it sideways (inside the panel,
 *  never the page) so the elements marked `data-keep-in-view` stay visible. `key` changes
 *  whenever they may have moved, e.g. the current step. */
export function useKeepInView(container: RefObject<HTMLElement | null>, key: unknown) {
  useEffect(() => {
    const box = container.current;
    if (!box || box.scrollWidth <= box.clientWidth) return;
    const targets = [...box.querySelectorAll<HTMLElement>("[data-keep-in-view]")];
    if (!targets.length) return;
    const boxLeft = box.getBoundingClientRect().left;
    const lefts = targets.map((t) => t.getBoundingClientRect().left - boxLeft + box.scrollLeft);
    const rights = targets.map((t) => t.getBoundingClientRect().right - boxLeft + box.scrollLeft);
    const lo = Math.min(...lefts) - 8;
    const hi = Math.max(...rights) + 8;
    if (lo < box.scrollLeft) box.scrollTo({ left: Math.max(0, lo) });
    else if (hi > box.scrollLeft + box.clientWidth) box.scrollTo({ left: hi - box.clientWidth });
  }, [container, key]);
}
