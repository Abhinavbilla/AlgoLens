import type { Frame } from "../api";

// The largest size each panel needs anywhere in the animation. Views size themselves to it,
// so a panel is the same height at every step and nothing below it moves.
export type Reserve = {
  pointerRows: number; // most pointer labels sharing one array cell
  hasRange: boolean; // an array shows a range at some step, so its legend line is reserved
  marks: string[]; // every mark name used, in first-seen order (legends always list them all)
  treeWidth: number;
  treeHeight: number;
  gridRows: number;
  gridCols: number;
  gridRowHeader: boolean;
  gridColHeader: boolean;
  mapRows: number;
};

export const NO_RESERVE: Reserve = {
  pointerRows: 1,
  hasRange: false,
  marks: [],
  treeWidth: 1,
  treeHeight: 1,
  gridRows: 0,
  gridCols: 0,
  gridRowHeader: false,
  gridColHeader: false,
  mapRows: 0,
};

export function computeReserves(frames: Frame[]): Reserve[] {
  const count = frames[0]?.panels.length ?? 0;
  const out: Reserve[] = Array.from({ length: count }, () => ({ ...NO_RESERVE, marks: [] }));
  for (const f of frames) {
    f.panels.forEach((panel, i) => {
      const r = out[i];
      if (!r) return;
      const addMarks = (lists: string[][]) => {
        for (const marks of lists) for (const m of marks) if (!r.marks.includes(m)) r.marks.push(m);
      };
      switch (panel.kind) {
        case "array": {
          const perIndex = new Map<number, number>();
          for (const p of panel.pointers ?? []) perIndex.set(p.index, (perIndex.get(p.index) ?? 0) + 1);
          r.pointerRows = Math.max(r.pointerRows, ...perIndex.values());
          r.hasRange ||= !!panel.range;
          break;
        }
        case "tree":
          r.treeWidth = Math.max(r.treeWidth, panel.width ?? 1);
          r.treeHeight = Math.max(r.treeHeight, panel.height ?? 1);
          addMarks((panel.nodes ?? []).map((n) => n.marks));
          break;
        case "graph":
          addMarks((panel.nodes ?? []).map((n) => n.marks));
          break;
        case "grid":
          r.gridRows = Math.max(r.gridRows, panel.rows?.length ?? 0);
          r.gridCols = Math.max(r.gridCols, ...(panel.rows ?? []).map((row) => row.length));
          r.gridRowHeader ||= !!panel.row_header;
          r.gridColHeader ||= !!panel.col_header;
          addMarks((panel.rows ?? []).flat().map((c) => c.marks));
          break;
        case "map":
          r.mapRows = Math.max(r.mapRows, panel.entries?.length ?? 0);
          break;
      }
    });
  }
  return out;
}
