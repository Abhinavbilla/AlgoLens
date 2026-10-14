import { render, screen, within } from "@testing-library/react";
import { GraphView } from "./GraphView";
import { GridView } from "./GridView";
import { LinkedListView } from "./LinkedListView";
import { SequenceView } from "./SequenceView";
import { TreeView } from "./TreeView";

test("a stack names its bottom and top, a queue its front and back", () => {
  const { unmount } = render(
    <SequenceView panel={{ kind: "stack", label: "Stack", defined: true, items: ["4", "7", "9"], changed: [2] }} />,
  );
  expect(screen.getByText("bottom")).toBeInTheDocument();
  expect(screen.getByText("top")).toBeInTheDocument();
  expect(screen.getByText("(changed)")).toBeInTheDocument();
  unmount();
  render(<SequenceView panel={{ kind: "queue", label: "Queue", defined: true, items: ["(0, 1)"], changed: [] }} />);
  expect(screen.getByText("front · back")).toBeInTheDocument();
});

test("an empty stack says so", () => {
  render(<SequenceView panel={{ kind: "stack", label: "Stack", defined: true, items: [], changed: [] }} />);
  expect(screen.getByText("Empty.")).toBeInTheDocument();
});

test("a linked list ends in null, with pointers under their nodes", () => {
  render(
    <LinkedListView
      panel={{
        kind: "linked_list", label: "List", defined: true, cycle_to: null,
        nodes: [{ id: 3, text: "1" }, { id: 4, text: "2" }],
        pointers: [{ label: "prev", node: 3 }, { label: "cur", node: null }],
      }}
    />,
  );
  const items = screen.getAllByRole("listitem");
  expect(within(items[0]).getByText("prev")).toBeInTheDocument();
  expect(within(items[2]).getByText("null")).toBeInTheDocument();
  expect(within(items[2]).getByText("cur")).toBeInTheDocument();
});

test("a cyclic linked list says where it loops back to", () => {
  render(
    <LinkedListView
      panel={{ kind: "linked_list", label: "List", defined: true, cycle_to: 0, pointers: [],
               nodes: [{ id: 1, text: "5" }, { id: 2, text: "6" }] }}
    />,
  );
  expect(screen.getByText("↺ back to 5")).toBeInTheDocument();
});

test("a tree lists its nodes in order with marks, in text", () => {
  render(
    <TreeView
      panel={{
        kind: "tree", label: "Tree", defined: true, width: 3, height: 2,
        nodes: [
          { id: 1, text: "9", x: 0, y: 1, marks: [] },
          { id: 0, text: "3", x: 1, y: 0, marks: [] },
          { id: 2, text: "20", x: 2, y: 1, marks: ["in queue"] },
        ],
        edges: [{ from: 0, to: 1 }, { from: 0, to: 2 }],
        pointers: [{ label: "node", node: 0 }],
      }}
    />,
  );
  expect(screen.getByText("In order: 9, 3 [node], 20 (in queue)")).toBeInTheDocument();
  expect(screen.getByText("in queue:").parentElement).toHaveTextContent("in queue: 20");
  expect(screen.getByRole("img", { name: "Tree: 3 nodes" })).toBeInTheDocument();
});

test("a graph shows weights, node labels and a legend of marks", () => {
  render(
    <GraphView
      panel={{
        kind: "graph", label: "Graph", defined: true, directed: false,
        nodes: [
          { id: 0, x: 0.5, y: 0.08, label: "0", marks: ["reached"] },
          { id: 1, x: 0.9, y: 0.6, label: "4", marks: ["in heap", "reached"] },
        ],
        edges: [{ u: 0, v: 1, w: "4" }],
        pointers: [{ label: "u", node: 0 }],
      }}
    />,
  );
  const legend = screen.getByText("reached:").parentElement!;
  expect(legend).toHaveTextContent("reached: 0, 1");
  expect(screen.getByText("in heap:").parentElement).toHaveTextContent("in heap: 1");
  expect(screen.getByText(/node 1 label 4 \(in heap, reached\)/)).toBeInTheDocument();
  expect(screen.getByText("u ▼")).toHaveAttribute("data-pointer", "u");
});

test("a grid shows headers, marks in text, and pointers in their cell", () => {
  render(
    <GridView
      panel={{
        kind: "grid", label: "dp", defined: true,
        col_header: ["", "B"], row_header: ["", "A"],
        rows: [
          [{ text: "0", marks: [], changed: false }, { text: "0", marks: [], changed: false }],
          [{ text: "0", marks: [], changed: false }, { text: "1", marks: ["match"], changed: true }],
        ],
        pointers: [{ label: "i, j", row: 1, col: 1 }],
      }}
    />,
  );
  expect(screen.getByRole("columnheader", { name: "B" })).toBeInTheDocument();
  expect(screen.getByRole("rowheader", { name: "A" })).toBeInTheDocument();
  const cell = screen.getByText("i, j").closest("td")!;
  expect(cell).toHaveTextContent("1");
  expect(cell).toHaveTextContent("(match)");
  expect(cell).toHaveTextContent("(changed)");
  expect(screen.getByText("match:").parentElement).toHaveTextContent("match: (1, 1)");
});

describe("syntax highlighting", () => {
  test("python tokens keep the text and mark keywords, strings, numbers and comments", async () => {
    const { tokenize } = await import("./highlight");
    const line = '    if nums[i] > 10:  # too big "x"';
    const tokens = tokenize(line, "python");
    expect(tokens.map((t) => t.text).join("")).toBe(line);
    expect(tokens.find((t) => t.text === "if")?.kind).toBe("kw");
    expect(tokens.find((t) => t.text === "10")?.kind).toBe("num");
    expect(tokens.find((t) => t.kind === "com")?.text).toBe('# too big "x"');
  });

  test("c++ tokens", async () => {
    const { tokenize } = await import("./highlight");
    const line = 'for (int i = 0; i < n; ++i) { s += "a"; } // loop';
    const tokens = tokenize(line, "cpp");
    expect(tokens.map((t) => t.text).join("")).toBe(line);
    expect(tokens.filter((t) => t.kind === "kw").map((t) => t.text)).toEqual(["for", "int"]);
    expect(tokens.find((t) => t.kind === "str")?.text).toBe('"a"');
    expect(tokens.find((t) => t.kind === "com")?.text).toBe("// loop");
    expect(tokenize("#include <algolens.h>", "cpp")[0].kind).toBe("com");
  });
});
