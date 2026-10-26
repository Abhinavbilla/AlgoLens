import { QUOTES, pickQuote } from "./quotes";

afterEach(() => localStorage.clear());

test("there are ten quotes, each with an author and a source", () => {
  expect(QUOTES).toHaveLength(10);
  for (const q of QUOTES) expect(q.text && q.author && q.source).toBeTruthy();
});

test("the same quote never shows twice in a row", () => {
  const first = pickQuote(() => 0.05);
  const second = pickQuote(() => 0.05); // would land on the same one
  expect(second).not.toBe(first);
});
