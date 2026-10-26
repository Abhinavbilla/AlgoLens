// Shown while a problem is being solved, one per run. Every quote here is checked against its
// source: no "attributed to Einstein" lines.

export type Quote = { text: string; author: string; source: string };

export const QUOTES: Quote[] = [
  {
    text: "An algorithm must be seen to be believed.",
    author: "Donald Knuth",
    source: "The Art of Computer Programming, 1968",
  },
  {
    text: "We can only see a short distance ahead, but we can see plenty there that needs to be done.",
    author: "Alan Turing",
    source: "Computing Machinery and Intelligence, 1950",
  },
  {
    text: "Program testing can be used to show the presence of bugs, but never to show their absence!",
    author: "Edsger W. Dijkstra",
    source: "Notes on Structured Programming, 1970",
  },
  {
    text: "If I have seen further, it is by standing on the shoulders of giants.",
    author: "Isaac Newton",
    source: "letter to Robert Hooke, 1675",
  },
  {
    text: "Programs must be written for people to read, and only incidentally for machines to execute.",
    author: "Harold Abelson and Gerald Jay Sussman",
    source: "Structure and Interpretation of Computer Programs, 1985",
  },
  {
    text: "Simplicity is prerequisite for reliability.",
    author: "Edsger W. Dijkstra",
    source: "EWD498, 1975",
  },
  {
    text: "Mathematics is not about numbers, equations, computations, or algorithms: it is about understanding.",
    author: "William Thurston",
    source: "On Proof and Progress in Mathematics, 1994",
  },
  {
    text: "Bad programmers worry about the code. Good programmers worry about data structures and their relationships.",
    author: "Linus Torvalds",
    source: "Git mailing list, 2006",
  },
  {
    text: "Premature optimization is the root of all evil.",
    author: "Donald Knuth",
    source: "Structured Programming with go to Statements, 1974",
  },
  {
    text: "The best way to predict the future is to invent it.",
    author: "Alan Kay",
    source: "Xerox PARC, 1971",
  },
];

const LAST = "algolens:last-quote";

/** A random quote, never the one shown last time (remembered in this browser if allowed). */
export function pickQuote(random: () => number = Math.random): Quote {
  let last = -1;
  try {
    last = Number(localStorage.getItem(LAST) ?? -1);
  } catch {
    // storage blocked: a repeat now and then is fine
  }
  let i = Math.floor(random() * QUOTES.length);
  if (i === last) i = (i + 1) % QUOTES.length;
  try {
    localStorage.setItem(LAST, String(i));
  } catch {
    // as above
  }
  return QUOTES[i];
}
