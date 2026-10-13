```sh
# AlgoLens spec

Draft v1. This covers what AlgoLens should do and how we'll know it works. How to build it is up to the implementation plan, apart from the few constraints near the end.

## Why I'm building this

When I'm learning an algorithm or stuck on a problem, the hard part is usually picturing what the code is actually doing at each step. There are visualizers out there, but they either only cover a fixed set of classic algorithms, or they have an AI draw the animation directly, which means the animation can show steps the real code would never take. You can't tell when it's wrong.

AlgoLens should do two things:

1. Show narrated, step-by-step animations of the core DSA algorithms.
2. Let you paste a problem and get a few approaches to it (brute force, then better, then optimal), each animated from a real run of code that has been checked and shown to be correct.

The rule the whole project rests on: we only animate what the code actually did when it ran, and we only call a solution "verified" if it passed the checks described below. If we can't verify something, we say so plainly.

## Who it's for

Students and interview candidates who can already program a bit and want to understand algorithms and problem-solving approaches, not just read the code.

## What a user should be able to do

**Learn a known algorithm.** I pick something from the library, say merge sort or BFS, and it plays on a default input with a short sentence explaining each step. If I step backward and then forward again, I see exactly the same state as before.

**Paste a problem and see how to solve it.** I paste a problem statement and, after a short wait, get two or three approaches. Each one has a name, the key idea in one line, its time and space complexity, and whether it's verified. Opening a verified approach lets me play it on a small example. While it's working, I can see what stage it's at and how many tests have passed so far.

**Know what to trust.** A verified approach shows how many tests it passed. One that failed is clearly marked as unverified, with a plain reason (for example, the input it got wrong), and it's never presented as a correct answer. If I paste something that isn't a DSA problem, or isn't one we support, I get a clear message instead of a guess.

**Try my own input.** I can change the example input and watch the animation again on my version. If my input breaks the problem's rules (say, a negative length), I'm told what's wrong and nothing reruns.

**See why one approach is faster.** I can compare how many operations each approach takes as the input grows.

**Read the code alongside the animation.** The code for the approach sits next to the animation with the current line highlighted, in both Python and C++.

**Come back without waiting again.** If I paste a problem that's already been processed, the stored result shows up right away. The library and previously processed problems still work with no internet.

## What's in scope

Arrays, strings, hashing, two pointers, sliding window, prefix sums, stacks, queues, monotonic stacks, heaps, linked lists, binary trees, graphs (BFS, DFS, shortest paths, topological sort, union-find), grids, recursion and backtracking, dynamic programming with 1D and 2D tables, and segment trees.

Not in this version:

- Problems that are mostly pure maths, proofs or computational geometry
- Interactive problems, or ones where the answer itself is random
- Accounts, social features, payments and native mobile apps
- Shipping other people's problem statements with the app (users paste their own)

## Detailed requirements

### Reading the problem

- Accept a pasted statement as plain text, up to 10,000 characters.
- Work out the input format (types and constraints), the output type, and the worked examples with their expected outputs.
- Identify the pattern or patterns involved, for example "sliding window".
- Turn away anything out of scope or not a DSA problem, with a short explanation of why.

### Approaches

- Give two or three approaches, ordered from simplest to most efficient. The first is always a plain brute-force solution.
- Each approach comes with a name, a one-line key idea, time and space complexity, and code in Python and C++.
- The Python and C++ versions must be the same algorithm, taking the same inputs and returning the same outputs.

### What "verified" means

This is the most important part of the spec. An approach counts as verified only if all of these are true:

1. It gives the expected output on every worked example in the statement.
2. It agrees with the brute-force solution on at least 300 random valid inputs, kept small enough for the brute force to run.
3. Its C++ version gives the same outputs as its Python version on those same inputs.

Some details:

- Random inputs must respect the problem's stated constraints.
- When a problem allows more than one correct answer ("return any valid path"), outputs are judged by a checker instead of exact matching. The checker has to accept the expected outputs from the examples before we rely on it.
- The brute force itself is verified by the examples and the Python/C++ match, since there's nothing simpler to compare it against.
- The system may try to fix a failing approach automatically, but the fixed version has to pass everything above from scratch.
- Anything that still fails is marked unverified with the reason, either the failing input with both outputs or a timeout, and never gets a verified badge.

### Animations

- Every frame must come from a recorded run of the approach's code. No frame may show a state the code didn't actually reach.
- Recording a run must not change what the code does. The recorded version has to give the same outputs as the verified version on all the test inputs.
- Data structures are drawn as: arrays and strings with labelled pointers and highlights, hash maps, stacks, queues, linked lists, binary trees, graphs (showing visited and frontier nodes), grids and 2D tables, and plain variables.
- Each frame knows which source line ran and the running operation count.
- Each step, or small group of steps, gets one sentence of narration. The narration can only mention values that actually appear in that step's state.
- An animation has at most 300 frames. If an input would need more, the system picks or asks for a smaller one.

### The player

- Play, pause, step forward and back, jump to any point, restart, and change speed between 0.5x and 4x.
- Keyboard: Space to play or pause, left and right arrows to step.
- Values that change between frames are visibly marked. Everything else stays where it is.

### Editing the input

- Check an edited input against the problem's format and constraints before rerunning.
- Rerunning on a new input doesn't need verification again; the approach is already verified.

### Comparing approaches

- For verified approaches, show operation counts at four or more input sizes covering at least two orders of magnitude. Leave out sizes where an approach would run past its time limit.

### Code view

- Show the Python and C++ code with the current line highlighted. Python highlighting must be exact. For C++, the closest matching line is fine.

### The algorithm library

The library includes:

- Bubble, insertion, merge and quick sort
- Binary search, including lower bound
- Two pointers, sliding window, prefix sums and monotonic stack
- BFS and DFS on grids and graphs, Dijkstra, topological sort and union-find
- Binary tree traversals: pre-order, in-order, post-order and level order
- DP: a 1D problem, a 2D problem (LCS or edit distance) and 0/1 knapsack
- Heap operations
- Backtracking: subsets and permutations
- Segment tree build and range query

Library entries have to be verified like everything else, play without any AI service, and use descriptions we write ourselves.

### Progress and storage

- Show the current stage while a problem is processing, and verification progress as a count (for example, "214 / 300 tests").
- Store results and reuse them when the exact same problem text comes in again on the same version of the system.
- Keep a record of every run: how long each stage took, the final status and any failure reasons. We need these for evaluation.

### Safety

All generated code is untrusted, so it must run isolated: no network, no access to the host's files, and hard limits on CPU time, memory, processes and output size. Code that hits a limit is stopped and reported as a timeout or resource failure. It must never take the rest of the system down with it.

### Evaluation

There's a command that runs every problem in a local evaluation set and writes a report with:

- the percentage of problems where every approach was verified
- the percentage with at least one verified approach
- the percentage unverified and the percentage that timed out
- median and 90th-percentile processing time
- the reason for each failure

## Quality targets

- **Speed:** a new in-scope problem takes 60 seconds or less (median). A stored result shows up within 1 second.
- **Smoothness:** animations run at 30 fps or better in a normal laptop browser.
- **Accessibility:** colour is never the only way something is shown, so pointers and states also have labels. The player works fully from the keyboard. There are light and dark themes.
- **Screen sizes:** usable from phone width (375 px) up to desktop.
- **Privacy:** pasted problem text is only used for that request and only sent to the AI service needed to process it.
- **Robustness:** if one approach fails, the others still show.

## Edge cases to handle

- **No worked examples:** verification relies on the random tests only, and the badge says there were no examples to check against.
- **Several valid answers:** use a checker, as described above.
- **Floating-point answers:** compare within a tolerance, 1e-6 by default.
- **Brute force too slow at every size:** use the smallest sizes allowed. If even those don't run in time, report the problem as one we couldn't verify.
- **Ambiguous or contradictory statement:** turn it away and say what's unclear.
- **Trace too long:** fall back to a smaller input (the 300-frame limit).
- **Edited input outside the constraints:** reject it with a message.
- **AI service down:** stored results and the library still work, and new problems get a clear error.

## How we'll know it works

We'll measure this on an evaluation set of at least 50 in-scope problems, roughly 10 on arrays and strings, 8 on hashing, two pointers and sliding window, 8 on trees, 8 on graphs and grids, 10 on DP and 6 others.

1. At least 70% of problems get at least one verified approach that isn't the brute force.
2. No approach marked verified turns out to be wrong when checked against an independent reference solution. Not one.
3. Every frame in the evaluation run matches the recorded execution, checked automatically.
4. The speed targets above hold across the evaluation set.

Any numbers we quote must be exactly what the evaluation report measured.

## Constraints

- Use PostgreSQL for everything stored: results, run records and the library.
- The whole system has to start locally with a single command.

## Assumptions

- Users only paste problem statements they're allowed to use. The evaluation set stays on my machine and isn't shared.
- Problems are written in English.
- An AI service is available for reading problems, writing code and writing narration for new problems.
```