import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { InputParam } from "../api";
import { InputEditor } from "./InputEditor";

const PARAMS: InputParam[] = [
  { name: "nums", kind: "array", hint: "a sorted list of 0 to 1000 values" },
  { name: "word", kind: "string", hint: "text of 0 to 20 characters" },
];

function setup(onRun = vi.fn().mockResolvedValue(null)) {
  render(
    <InputEditor
      params={PARAMS}
      initial={[[1, 2], "ab"]}
      defaults={[[9], "z"]}
      running={false}
      onRun={onRun}
    />,
  );
  return onRun;
}

const field = (name: string) => screen.getByRole("textbox", { name });

async function replace(name: string, text: string) {
  await userEvent.clear(field(name));
  // userEvent treats [ and { as key descriptors, so type them escaped.
  await userEvent.type(
    field(name),
    text.replace(/[[{]/g, (c) => c + c),
  );
}

test("fields start from the shown input; strings are plain text, the rest JSON", () => {
  setup();
  expect(field("nums")).toHaveValue("[1,2]");
  expect(field("word")).toHaveValue("ab");
  expect(screen.getByText(/a sorted list of 0 to 1000 values/)).toBeInTheDocument();
});

test("runs with the parsed arguments", async () => {
  const onRun = setup();
  await replace("nums", "[3, 5, 8]");
  await replace("word", "hi there");
  await userEvent.click(screen.getByRole("button", { name: "Run with this input" }));
  expect(onRun).toHaveBeenCalledWith([[3, 5, 8], "hi there"]);
});

test("invalid JSON is caught before anything is sent", async () => {
  const onRun = setup();
  await replace("nums", "[3, 5,");
  await userEvent.click(screen.getByRole("button", { name: "Run with this input" }));
  expect(onRun).not.toHaveBeenCalled();
  expect(field("nums")).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByText(/nums: isn't valid JSON/)).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("Fix the highlighted fields first.");
});

test("server issues appear next to the field they're about", async () => {
  setup(
    vi.fn().mockResolvedValue({
      message: "This input doesn't fit the problem.",
      issues: [
        { path: "nums", message: "must be sorted in ascending order (nums[1] = 1 comes after 5)" },
        { path: "", message: "more than one pair adds up to 5" },
      ],
    }),
  );
  await userEvent.click(screen.getByRole("button", { name: "Run with this input" }));
  expect(await screen.findByText(/nums: must be sorted in ascending order/)).toBeInTheDocument();
  expect(field("nums")).toHaveAttribute("aria-invalid", "true");
  const alert = screen.getByRole("alert");
  expect(alert).toHaveTextContent("This input doesn't fit the problem.");
  expect(alert).toHaveTextContent("more than one pair adds up to 5");
});

test("JSON mode takes the whole argument list", async () => {
  const onRun = setup();
  await userEvent.click(screen.getByRole("checkbox", { name: "Edit all as JSON" }));
  const box = screen.getByRole("textbox");
  expect(box).toHaveValue('[[1,2],"ab"]');
  await userEvent.clear(box);
  await userEvent.type(
    box,
    "[[7]]".replace(/[[{]/g, (c) => c + c),
  ); // only one argument
  await userEvent.click(screen.getByRole("button", { name: "Run with this input" }));
  expect(onRun).not.toHaveBeenCalled();
  expect(screen.getByRole("alert")).toHaveTextContent("Give a JSON list of 2 arguments.");
});

test("reset restores the example input", async () => {
  setup();
  await replace("nums", "[100]");
  await userEvent.click(screen.getByRole("button", { name: "Reset to the example" }));
  expect(field("nums")).toHaveValue("[9]");
  expect(field("word")).toHaveValue("z");
});
