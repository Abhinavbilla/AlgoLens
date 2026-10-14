# AlgoLens implementation plan

Draft v3, written against `spec.md` draft v1 (plus the call-stack, computed-narration-values and design-problem changes you're making). This is the "how"; the spec stays the source of truth for the "what". **[Decision]** marks a call I've made that you can overturn; **[Question]** marks something I need from you.

**Changes in v3**
- Narration may show engine-computed values, always with their operands; the grounding check tracks where each number came from (§7.4).
- A brute force that fails the worked examples is regenerated once instead of failing the problem (§6.2).
- Operations-list input type, shaped so class-style design problems can reuse it later (§5).

**Changes in v2**
- Narration templates have conditions and are chosen by which branch ran; there's a neutral fallback (§7.4).
- Template expressions use our own restricted parser, never `eval`/`exec`. Hostile templates are added to the M1 security tests (§7.5).
- What a frame shows is pinned down: the line that just ran, with values after it ran. A golden test guards it in M2 (§7.2).
- Every active solution frame is snapshotted, and there's a call-stack panel (§7.1, §9).
- M1 starts with an nsjail spike and stops for a fallback decision if it fails (§11).
- Milestones are reordered so the AI pipeline comes earlier (§13).
- The compare view counts with `sys.monitoring` (§7.6).
- A second, independent brute force always runs (§6).
- There's a configurable per-problem token budget (§6.4).
- Hash-only caching, with no raw text stored (§4, §12).
- Appendix A has a draft of the 50-problem eval set.

---

## 1. Summary

Core idea: **the AI writes code and descriptions, never frames.** Every frame is derived mechanically from a recorded Python execution. Every "verified" badge comes from a deterministic test pipeline that the AI can't influence beyond submitting code.

```
paste text ──► Parse (AI) ──► ProblemSpec (input schema, examples, comparator)
                                   │
         ┌──────────────┬──────────┼──────────────┬─────────────────────┐
         ▼              ▼          ▼              ▼                     ▼
   Brute A (AI)   Brute B (AI,   Approaches   Checker (AI,      Input generator
   shown to user  other model,   2–3 (AI)     if needed)        (ours, from schema)
                  hidden ref)
         └──────────────┴──────────┴──────────────┴─────────────────────┘
                                   │
         Sandbox: examples + 300 random tests + A==B + Py/C++ match
                       (repair loop on failure, token-budgeted)
                                   │
                     Verified / Unverified(reason)
                                   │
           Visual spec + conditional narration templates (AI, per approach)
                                   │
            Traced Python run in sandbox ──► Frames (≤300) ──► Player
```

## 2. Tech stack

| Concern | Choice | Why |
|---|---|---|
| Backend API | **Python 3.12 + FastAPI** | Tracing is Python-native; one language for pipeline, tracer and harness. |
| Worker | Same codebase, separate process | Long-running pipeline jobs off the request path. |
| Job queue | **Postgres table + `SELECT … FOR UPDATE SKIP LOCKED`**, progress via `LISTEN/NOTIFY` | Spec says Postgres for everything; no Redis. |
| DB | PostgreSQL 16, SQLAlchemy 2 + Alembic | Constraint. |
| Frontend | **React + TypeScript + Vite, CSS modules**, SVG rendering, no external CDNs | Confirmed. Local assets so it works offline. |
| Sandbox | **nsjail** in a dedicated `sandbox` container, *pending the M1 spike* (§11) | Isolation without mounting the Docker socket. |
| Languages | **Python 3.12** (`sys.settrace` + `sys.monitoring`), **C++17** with g++ 13 `-O2` | Confirmed. |
| AI service | **Provider-neutral client** (`backend/algolens/ai/client.py`): Gemini and Groq (free tiers) by default, Anthropic or any OpenAI-compatible endpoint by setting `ALGOLENS_MODEL_<ROLE>=provider:model`; JSON-object replies validated against strict models | Changed after M4 (no paid key to start). Brute B defaults to a different company's model from Brute A (§6.2); startup fails if they're equal. |
| Startup | **`docker compose up`** (db, api, worker, sandbox, web) | Single command. Migrations + library seeding run on api start. |

## 3. Repository layout

```
algolens/
  docker-compose.yml
  .env.example            # API key, models per role, token budget, limits
  backend/
    algolens/
      api/            # FastAPI routes, SSE progress
      pipeline/       # stages: parse, brute A/B, approaches, checker, verify, repair, visualize, narrate
      budget/         # per-problem token budget + reservations
      schema/         # input-type DSL, random generator, validator
      sandbox/        # client for the sandbox service, harness templates (py/cpp)
      tracer/         # settrace recorder, frame builder; sys.monitoring op counter
      narration/      # expression parser/evaluator, template selection, lint
      library/        # loader that seeds DB from library/
      eval/           # eval command + report writer
      db/             # models, migrations
    tests/
  sandbox/            # Dockerfile, nsjail configs, tiny HTTP runner
  frontend/src/
    player/  viz/  pages/
  library/            # hand-written entries, one folder each (§8)
  eval/               # gitignored; your local eval set lives here
```

## 4. Core data model

**ProblemSpec** (produced by Parse): `function_signature`, `input_schema` (§5), `output_type`, `comparator` (`exact` | `float(tol=1e-6)` | `unordered` | `checker`), `examples[]`, `patterns[]`, `in_scope`, `rejection_reason`.

**Approach**: `name`, `key_idea`, `time`, `space`, `python_code`, `cpp_code`, `py_to_cpp_lines`, `visual_spec`, `narration_templates`, `status` (`verified` / `unverified` / `timeout`), `verification` (counts, failing case with both outputs, "no examples" flag, reason).

**Frame** (sent to the client; semantics in §7.2):
```json
{ "i": 42, "event": 117, "py_line": 9, "cpp_line": 12, "next_line": 10, "ops": 117,
  "stack": [
    { "fn": "solve", "line": 14, "locals": { "grid": "#ref3", "res": "#ref7" } },
    { "fn": "dfs",   "line": 9,  "locals": { "r": 2, "c": 3, "path": "#ref9" } }
  ],
  "heap": { "#ref3": [[1,0],[1,1]], "#ref7": [], "#ref9": [[0,0],[1,0]] },
  "changed": ["dfs.c"],
  "narration": "Cell (2, 3) is water, so dfs returns without exploring it." }
```
`stack` lists the active activations of solution code, outermost first. Mutable objects are stored once in `heap` by identity, so aliasing (two names pointing at one list) is drawn correctly, and unchanged objects are shared between frames instead of copied. That keeps deep recursion traces small.

**Postgres tables**
- `problems`: `text_hash` (sha256 of the exact text), `system_version`, `spec`, `status`, `created_at`. Unique on (`text_hash`, `system_version`). **No raw text is stored.**
- `approaches`: FK problem, all approach fields.
- `runs`: one per pipeline execution, with per-stage timings, final status, failure reasons, and tokens used per stage and in total.
- `jobs`: queue + progress (`stage`, `tests_passed`, `tests_total`).
- `library_entries`: seeded from `library/`.

`system_version` = app version + prompt-set hash + model IDs per role. Changing any of these causes a cache miss.

## 5. Input schema DSL, generator and validator

The AI describes the input in a small typed DSL; **we** generate and validate inputs from it.

- **Types**: `int[lo,hi]`, `float[lo,hi]`, `bool`, `string(charset, len)`, `array<T>(len)`, `matrix<T>(rows, cols)`, `grid(chars, rows, cols)`, `linked_list<T>(len)`, `binary_tree<T>(nodes)`, `graph(n, m, directed, weighted, w_range)`.
- **Operations list**: `ops(init: {params…}, ops: [{name, args: {params…}, returns: T|null}…], len)`. An input is an initial state plus a sequence like `[["update", 2, 5], ["query", 0, 3]]`; the output is the list of non-null results, one per returning op. This covers "apply these queries" problems now (e.g. eval #50). It's deliberately shaped like a class-style design problem (`init` = constructor args, each op = a method call), so those can reuse it later without a new type. Nothing class-specific is built in v1.
- **Modifiers**: `sorted`, `distinct`, `permutation`, `connected`, `dag`, `tree`, `no_self_loops`, `valid_parentheses`, plus cross-parameter references (`k <= len(nums)`).
- **Generator**: seeded. It has a "small" profile for verification and a scaling profile for the compare chart, and is biased toward edge cases.
- **Validator**: built from the same schema, with plain-language error messages. It's used for both random inputs and edited inputs.
- **Escape hatch**: constraints the DSL can't express get an AI-written `validate(input)`. It runs **in the sandbox**, must accept every example, and we generate inputs by rejection sampling against it. If too few samples are accepted, the problem is reported as unverifiable.
- Every example input must pass the validator; if one doesn't, the parse is wrong.

**As built in M3:**
- The schema format is documented in `backend/algolens/schema/model.py`.
- Bounds and cross-parameter rules use the narration expression language (already hardened against hostile input).
- The escape hatch is a `validate(*args) -> str | None` function. For library entries it lives in `validator.py`, and it always runs in the sandbox.
- Random tests are filtered through the validator in one batch; if fewer than 5% pass, the rules count as too strict to sample from.
- Each parameter gets a plain-language hint for the input editor, from `schema/describe.py`.
- A property test checks that thousands of generated inputs always pass validation.
- Library entries are now verified with their hand-written tests plus 300 random tests, with recording integrity checked on every test input.

## 6. Verification pipeline

### 6.1 Stages
1. **Parse**: ProblemSpec or rejection (out of scope / not DSA / ambiguous), with the reason.
2. **Brute A**, **Brute B**, **Approaches**, **Checker**: run in parallel (§6.2).
3. **Test set**: examples + 300 random small inputs (fixed seed per problem, stored).
4. **Run in sandbox**: each approach × {Python, C++}, all tests batched in one process with a per-test timeout plus an overall budget. Brute B runs in Python only.
5. **Judge** (using the comparator):
   - **Brute A** must pass the examples, match C++ to Python on every test, and **agree with Brute B on every test**.
   - **Other approaches** must pass the examples, match Brute A on ≥300 random inputs, and match C++ to Python.
6. **Repair** (§6.3).
7. Approaches fail independently: one failing never hides the others.
8. **[Learned in M3] Time-dependent results are retried, never taken as wrong answers.** A test that times out, a batch that runs out of time, or a compile that times out (`compile_timeout`) can be caused by a busy machine rather than by the code. These are rerun once on their own before they count. A repeat is reported as a *timeout*, never as a wrong output or a compile error. In M3, before this rule existed, a correct library entry was briefly marked "failed" because a loaded machine made its C++ compile time out.

### 6.2 Two independent brute forces (always)
The goal is that both are unlikely to misread the problem in the same way:
- **Different model**: by default Brute A uses Sonnet 5.5 and Brute B uses Opus 5.5 (configurable, but the config loader refuses identical models for A and B).
- **Different inputs and instructions**:
  - Brute A gets the statement + ProblemSpec and is asked for the most direct simulation or enumeration.
  - Brute B gets **only the raw statement and the function signature**, not the parsed spec. It is told to first restate the problem and work each example by hand, then write the simplest possible exhaustive solution, in a different style from A (e.g. recursion/enumeration of all candidates rather than iteration).
  - Neither sees the other's code or the optimised approaches.
  - Because B ignores the parsed spec, a misreading in the Parse step also tends to show up as a disagreement.
- **If one brute force fails the worked examples**, it's simply wrong: drop it and regenerate it **once**, with the same independent inputs and instructions as before. The regenerated version is told only which example it failed, never the other brute's code or output. If the regenerated one still fails its examples, the problem is unverified ("reference solution A/B failed example N").
- **If both pass the examples (or there are none) and still disagree** on any random test, no approach for the problem can be verified. All are marked unverified with "the two reference solutions disagree on input X (A: …, B: …)". There's no reconciliation step, because asking either model to settle it would undo the independence. The eval reports how often this happens.
- Brute A is the one shown to users. B is an internal reference, Python only.

### 6.3 Repair
At most `MAX_REPAIR_ROUNDS` (default 2) rounds per approach. Each round sends the failing input and both outputs, and the new code is **re-run through every check from scratch**. If it still fails, the approach is `unverified` with the failing case, or `timeout`. Brute B is never repaired (see §6.2).

### 6.4 Token budget
- `MAX_TOKENS_PER_PROBLEM` (input + output, all calls) is set in `.env`. Default 200k until we have M5 numbers.
- Before every AI call, its `max_tokens` plus the prompt size is **reserved** against the budget. Parallel calls can't overshoot together, and a call that wouldn't fit isn't made. Unused reservation is released when the call returns.
- When the budget runs out, remaining AI stages stop. Approaches already verified keep their badge; anything unfinished becomes unverified with "token budget exhausted at stage X".
- Usage per stage is recorded in `runs` and shown in the eval report so you can pick the real limit.

### 6.5 Checker safeguards
The checker must:
- accept every example's expected output
- accept every output from Brute A and Brute B
- **reject** automatically mutated wrong outputs (off-by-one values, swapped or dropped elements) on a sample of tests

A checker that accepts everything is rejected. It runs in the sandbox.

### 6.6 Spec edge cases
- **No examples**: the badge says "no examples to check against". The A/B agreement still applies.
- **Brute force too slow**: shrink to the minimum allowed sizes; if that still fails, the problem is unverifiable.
- **Multiple valid answers**: use the checker.
- **Floating-point answers**: compare within a tolerance, 1e-6 by default.

## 7. Tracing, frames and narration

### 7.1 Recorder (settrace, runs in the sandbox)
- `sys.settrace` is enabled only for code objects belonging to the solution: its functions, nested helpers and recursive calls. Library and builtin frames are skipped.
- On each emitted frame it snapshots **every active solution activation** (walking `frame.f_back` and keeping solution frames only), each with its function name, current line and locals.
- Objects are serialized by identity into the shared `heap`, with structural sharing across frames. This covers lists, dicts, sets, deques, heaps, tuples, `ListNode`/`TreeNode`.
- There's a snapshot size cap. If it's exceeded, we fall back to a smaller input.

### 7.2 What a frame shows (pinned)
`settrace` fires `line` *before* the line runs, so a line's effects are only visible at the **next** event in the same activation. Definition:

> **A frame = one line that just finished running in some activation, plus the values after it ran.** `py_line` is that line; `stack`/`heap` are the state at the moment it finished; `next_line` is the line that activation runs next (or `return`).

How it's implemented:
- Each activation keeps a `pending_line`.
- When a `line` or `return` event arrives **for the same activation**, the pending line has finished. We emit a frame (`py_line` = pending, `next_line` = the new line, or `return`) and snapshot the stack.
- A `call` into a callee does **not** finish the caller's line. The callee's frames come first, and the caller's line (e.g. `res = dfs(x)`) finishes only when control comes back to it. While the callee runs, the call-stack panel shows the caller still sitting on that line.
- `return` events also record the return value in the frame.
- `exception` events produce a frame marked `raised`; a later `line` in a handler continues as normal.

**Golden-trace tests (M2)** cover:
- straight-line assignments
- `if`/`else` with both branches (checks that `next_line` identifies the branch)
- `for` and `while` loops, including the final failed loop check
- a line that calls a helper
- recursion three levels deep
- a `return` inside a loop
- a caught exception

Each test pins the exact `(py_line, next_line, values)` sequence. Any change to this definition has to update these tests on purpose.

**Op count** = number of finished line executions in solution code, i.e. number of frames before grouping. **[Decision]**

**No behaviour change**: traced output must equal untraced output on every test input. If it doesn't, the approach is still verified but marked not animatable.

### 7.3 Frame builder
- Consecutive frames that change nothing visible may be grouped. A group displays the exact state of its last frame; there is never an interpolated state.
- `changed[]` comes from diffing consecutive snapshots.
- More than 300 frames → shrink the input through the generator. For a custom input, tell the user and suggest a smaller one.
- Stepping back just means a lower index into an immutable array, so states are identical by construction.

### 7.4 Narration templates (conditional, branch-aware)
A template is chosen by the line that just ran, the branch taken, and a condition checked against that step's values:
```json
{ "line": 9, "next_line": 10,
  "when": "nums[l] + nums[r] > target",
  "text": "{nums[l]} plus {nums[r]} is more than {target}, so r moves left." }
```
- **Selection**:
  1. Take the templates for `py_line`.
  2. Keep those whose `next_line` matches the frame's `next_line`, or that don't specify one.
  3. Of those, keep the ones whose `when` evaluates to true.
  4. The first match in declared order wins.
- **Fallback when nothing matches** (or the expression errors): a neutral, auto-generated sentence built only from the diff, e.g. "Line 9 ran; `r` changed from 3 to 2." or "Line 9 ran; nothing changed." It's true by construction.
- **Scope**: names resolve in the innermost activation, then in the activation of the function that encloses it (closure variables like `res`). `old(path)` reads the value from before the line ran, e.g. "r moves left from {old(r)} to {r}".
- **What can go in `{…}` in text**:
  - **State paths**: names, indexing, node fields, `old(path)`. These render as the stored value.
  - **Computed values**: arithmetic or `len()` over state paths. The engine computes the value and **always renders it with its operands**, e.g. `{nums[l] + nums[r]}` renders as "2 + 15 = 17" and `{len(stack)}` as "len(stack) = 3". The template can't supply or format the result itself; it only names the expression. Nested expressions show their leaf operands: `{a + b * c}` renders as "2 + 3 × 4 = 14".
  - Comparisons and `and`/`or`/`not` are allowed only in `when`, not in text.
  - **[Decision, M2]** A placeholder that is only `len(x)` shows just the count ("3"), since its operand is a container already on screen; arithmetic always shows operands ("2 + 15 = 17").
  - **[Decided after M2]** Small constants from -2 to 2 may be operands inside `{…}` and are shown with the working (`{j + 1}` renders as "2 + 1 = 3"). A computed placeholder must still use at least one value from the state. Any number written into the plain sentence is still rejected. Literals of any size remain fine as indices (`{nums[0]}`) and anywhere in `when`.
- **Lint at generation time**, run over the traces of all test inputs:
  - every expression must parse and evaluate on the steps where its line runs
  - no literal numbers in text, except fixed phrases
  - templates for the same `(line, next_line)` whose conditions are true together but whose text differs are flagged
  - coverage (% of steps that get a non-neutral sentence) is reported

  Failures go back to the AI once. After that, the bad templates are dropped and the fallback is used.
- **Final guard**: the renderer records where every number it emits came from: a state value, or a result it computed from state values in that frame. After rendering, every number in the sentence must be one of those. Any other number (e.g. a literal the template slipped into the text) fails the guard, and the neutral fallback is used instead.
- Re-running on an edited input needs **no AI call**.

### 7.5 Restricted expression language (no `eval`/`exec`)
Narration runs in the worker, outside the sandbox, so it can't go anywhere near Python's evaluator.
- Our own tokenizer + Pratt parser → a small AST → an evaluator over the **JSON snapshot only**. It holds plain data, not live Python objects, so there's no object to reach `__class__` and friends from.
- **Grammar**:
  - literals: int, float, string, `True`/`False`/`None`
  - names, `x[i]`, `node.val`/`.next`/`.left`/`.right`. Field access is a key lookup in the serialized node and only these fields are allowed.
  - `+ - * // %`, unary `-`
  - comparisons (chainable)
  - `and`/`or`/`not`
  - `len(path)`, `old(path)`

  There is no `**`, no calls other than those two, no attribute access beyond the four node fields, no comprehensions and no lambdas.
- **Limits**: expression ≤ 200 chars, AST depth ≤ 32, `*` only on numbers, integer results capped at 10^18, evaluation errors → "no match". Template text is parsed by our own `{…}` scanner, **not** `str.format`, because `str.format` allows attribute and index access.
- **Hostile-template tests (M1)**:
  - `__import__('os')`
  - `().__class__.__mro__`
  - `x.__dict__`
  - `{nums.__class__}` in text
  - a lambda
  - a comprehension
  - `"a" * 10**9`
  - `9999…` (huge literal)
  - 10,000-deep parentheses
  - unbalanced and nested braces
  - unicode lookalike identifiers

  Every one must be rejected or evaluate to "no match", without crashing or slowing the worker.

### 7.6 Op counting for the compare view (`sys.monitoring`)
- A separate counting harness in the sandbox uses `sys.monitoring` (PEP 669) with only the `LINE` event, set as **local events on the solution's code objects** (walked recursively through `co_consts` for nested functions). The callback is a single counter increment, and there's no per-frame trace function.
- Sizes: e.g. 10, 30, 100, 300, 1000, 3000, each with a time limit. An approach is dropped at sizes it can't finish, and the chart labels it.
- **Consistency test (M7)**: on all library entries and test inputs, the `sys.monitoring` count must equal the settrace op count. If 3.12's two event semantics differ on some construct, we fix the definition or adjust before shipping. I'll report what we find.

### 7.7 C++ line highlighting
The AI supplies `py_to_cpp_lines`. It's validated to be in range and roughly monotone, and the nearest mapped line is used as a fallback.

## 8. Algorithm library
- Each entry is a folder in `library/` containing `solution.py`, `solution.cpp`, `reference.py`, `description.md` (written by us), and one `entry.json` holding the title, tests, default input, visual spec, C++ line map and narration templates. (M2: one file instead of six small ones; the input schema joins it in M3.)
- **As built in M4:** nine entries are verified. Panel kinds are array, stack, queue, list, map, variables, linked list, tree, graph and grid/2D table, documented in `backend/algolens/animation/panels.py`. Visual specs can use per-item expressions (`item`, `node`, `row`/`col`) and *marks* (e.g. "in heap", "wall"). Marks are drawn with a distinct pattern and always named in a text legend. Tree and linked-list inputs are built into `TreeNode`/`ListNode` by the sandbox driver (`convert` in sandbox requests). Every panel reserves the largest size it needs anywhere in the run, so nothing moves between steps; `frontend/scripts/ui-check.mjs` checks this at every step.
- `algolens library verify` checks Python against the reference and C++ against Python on every test, checks that recording never changes a result, and lints the narration on every recorded frame. The result is stored and shown as the entry's badge; changing an entry resets it to unverified.
- Entries are seeded into Postgres on startup and verified through the same pipeline with no AI involved. Sorts are checked against `sorted`; the rest against hand-written references.
- Built in three batches:
  - **M2 (3)**: bubble sort, binary search, two pointers.
  - **M4 (6)**, one per new renderer: BFS on a grid (grid + queue), level-order traversal (tree + queue), monotonic stack (stack), LCS (2D table), subsets via backtracking (call stack), Dijkstra (graph + heap).
  - **M8**: the rest of the spec's list (~21).

## 9. Frontend
Pages:
- **Library**
- **Paste a problem**: live stage plus "214 / 300 tests" over SSE
- **Approach view**: player + code + narration + call stack
- **Compare**

Details:
- **Player**: play/pause, step, scrub, restart, 0.5×–4×. Space, ←/→, Home/End. Every control is a labelled button.
- **Renderers**: array/string with pointer tags, hashmap, stack, queue, linked list, binary tree, graph (layout computed once, visited/frontier shown with fill **and** a text badge), grid/2D table, variables panel.
- **Call-stack panel**: active activations, innermost on top, each with the function name, arguments and current line. The innermost is expanded and the others can be expanded. Frames pushed or popped since the last step are marked with text, not just colour. For backtracking it shows the recursion path, e.g. `subsets(i=2, path=[1,3])`.
- **Layout stability**: positions are computed across the whole frame array up front. Changed values get an outline + "changed" marker.
- **Code view**: Python/C++ tabs, local Shiki bundle, current line highlighted. Python highlighting is exact; for C++ the closest matching line is used.
- **Input editor**: form generated from the schema plus a raw JSON mode. Errors are shown inline and nothing reruns until the input is valid.
- **Compare chart**: log-x line chart of ops vs n.
- Light/dark themes, 375 px and up.

## 10. Evaluation command
`docker compose run --rm api algolens eval [--set eval/]`
- **Eval set format**: one folder per problem with `statement.txt`, `reference.py` (your accepted submission or hand-written), and `meta.json` (category, function signature to adapt the reference to).
- **For each problem**, run the full pipeline (bypassing the cache), then:
  - **Criterion 2**: every verified approach vs `reference.py` on fresh random inputs (different seed). Any mismatch counts as a **false verification**.
  - **Criterion 3**: re-trace the animation input; check that each frame's state equals the recorded snapshot at its `event` index and that the narration is grounded.
- **Report**: `eval/reports/<timestamp>.{md,json}`, containing:
  - % with all approaches verified, % with ≥1 verified, % with ≥1 verified non-brute approach
  - % unverified, % timeout
  - median/p90 time
  - reasons per failure
  - false verifications
  - A/B disagreements
  - frame-integrity failures
  - tokens per problem (median/p90/max), budget exhaustions

  All numbers come straight from the run.
- The draft problem list is in Appendix A.

## 11. Sandbox and safety

### 11.1 M1 opens with an nsjail spike
nsjail needs to create namespaces. Inside Docker that often requires `privileged`, `CAP_SYS_ADMIN`, or relaxed seccomp/AppArmor, and you're on Windows 11 with Docker Desktop (WSL2 kernel), which adds its own variables.

**Spike pass criteria, all on your machine, via `docker compose up`:**
- runs Python and C++ programs under nsjail
- no `privileged: true` and no `CAP_SYS_ADMIN`; at most a custom seccomp profile, which I'll show you
- network access fails
- host files aren't visible
- CPU, wall time, memory, PID and output limits each trigger and are classified correctly
- a fork bomb doesn't affect other containers

**Spike result (2026-10-13): passed.** All criteria were met with `cap_drop: [ALL]` and a custom seccomp profile; a stricter seccomp filter for the jailed program itself is required on top. Details, evidence and lessons are in `sandbox/spike/RESULTS.md`.

If any of these fail, **I stop and come back to you** with what failed and a recommendation. Fallbacks I'd consider, roughly in order:
1. **Hardened unprivileged container + rlimits**: `network_mode: none`, `read_only`, `cap_drop: ALL`, `no-new-privileges`, compose-level `mem_limit`/`pids_limit`/`cpus`, code run as a non-root user with `setrlimit` and a fresh tmp dir per job. A small pool of these is recycled after each job. It relies only on Docker's own isolation; isolation between jobs is weaker, which recycling mitigates.
2. **gVisor (`runsc`) runtime** for the sandbox container. Stronger, but installing it on Docker Desktop/WSL2 may be awkward.
3. **bubblewrap**: lighter than nsjail, but needs the same user namespaces, so it probably hits the same wall.

### 11.2 Design (once the mechanism is settled)

**As built in M1** (`sandbox/`, details in `sandbox/spike/RESULTS.md`):
- `POST /v1/batch` runs one solution against up to 2,000 tests. C++ is compiled in its own jail; then a driver running as PID 1 of a second jail forks a fresh child per test, with per-test CPU (`ITIMER_PROF`), wall-time, memory and output limits.
- Batch statuses: `ok`, `compile_error`, `batch_timeout` (finished tests keep their results), `sandbox_error`. Per-test outcomes: `ok`, `runtime_error`, `timeout`, `memory`, `output_limit`, `not_run`. **`sandbox_error` is never a verdict on the code** and must not count toward or against verification (M5).
- Python results come back as JSON from the entry function; C++ programs read JSON on stdin and emit JSON on fd 3 (`algolens.h`, `nlohmann/json` available). The glue that maps the input DSL to C++ types arrives with M3/M5.
- The sandbox has no network and is reached only through a Unix socket on a shared volume. A startup self-test gates its health.
- Generated code, AI-written validators and AI-written checkers all run in the sandbox only.
- API/worker reach it over an internal-only network.
- Outcomes: `ok`, `wrong`, `runtime_error`, `timeout`, `memory`, `output_limit`, `compile_error`.
- Hostile-code suite: fork bomb, infinite loop, memory balloon, network call, reading host files, huge output, C++ UB. Plus the hostile-template suite (§7.5).

## 12. Non-functional notes
- **Speed (≤60 s median)**: AI calls run in parallel where independent; tests are batched; C++ compiles run concurrently. Roughly 6–8 AI calls per problem now that Brute B is included.
- **Offline**: the library and cached problems need no AI. If the AI service is down, new problems get a clear error.
- **Privacy**: problem text goes only to the configured AI providers (note: free tiers such as Gemini's may use prompts to improve their models). AlgoLens stores only its sha256; the text sits in the job payload until the worker claims the job and is removed then, whatever the outcome; it's never logged.
- **Observability**: every stage writes timings, tokens and failure reasons to `runs`.

## 13. Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | **Skeleton**: compose stack, DB + migrations, FastAPI health check, React shell, CI (lint + tests), `.env` config incl. token budget | `docker compose up` shows the app shell |
| M1 | **Sandbox + expression language**: nsjail spike first (**stop point if it fails**), then runner, Py/C++ harness, limits, outcome classification; restricted expression parser/evaluator | hostile-code and hostile-template suites pass |
| M2 | **Tracer + player (no AI)**: settrace recorder with full-stack snapshots, frame semantics from §7.2, frame builder, player, array/vars/hashmap renderers, call-stack panel, Python code view; 3 library entries | golden frame-semantics tests pass; play/step/scrub/keys work |
| M3 | **Schema DSL**: generator, validator, input editor UI | edited input validates, reruns, gives clear errors |
| M4 | **Remaining renderers + 6 library entries**: stack, queue, linked list, tree, graph, grid/2D table; C++ line map; library verification | 9 library entries verified and playable offline |
| M5 | **AI pipeline**: parse/reject, Brute A + independent Brute B, approaches, checker + safeguards, verify, repair, token budget, jobs + SSE progress, hash cache | paste → verified approaches end-to-end on 10 problems from Appendix A; token numbers reported so you can set the limit |
| M6 | **Animating AI approaches**: visual spec, conditional narration templates + lint + grounding, 300-frame fallback | AI approaches play; no narration rendered against a false condition on any test trace |
| M7 | **Compare view**: `sys.monitoring` counter, scaling runs, chart | ≥4 sizes over ≥2 orders of magnitude; counts match settrace op counts |
| M8 | **Rest of the library** (~21 entries) | all spec library entries verified |
| M9 | **Eval command**: reference comparison, frame-integrity check, report | report generated on the full eval set |
| M10 | **Hardening**: accessibility, themes, 375 px, fps test, speed tuning from eval numbers | quality targets met and shown in the eval report |

I'd like your review at the end of M1 (sandbox mechanism), M2 (first thing you can see), and M5 (first real verification numbers).

## 14. Testing strategy
- **Unit**:
  - DSL property tests: generated inputs always validate
  - comparators
  - expression parser (including fuzzing)
  - template selection
  - grounding
  - frame builder
  - serializer
- **Golden traces**: frame-semantics fixtures (§7.2) and every library entry's frame array, snapshot-tested.
- **Pipeline tests with a fake AI**:
  - deliberately wrong approaches
  - Brute A/B that share a bug vs ones that disagree
  - a permissive checker
  - broken C++
  - a repair loop that never converges (must stop at the budget)

  Each must end in the right status.
- **Security**: the sandbox suite and hostile templates (M1).
- **Frontend**: component tests for the player and keyboard; Playwright at 375 px and desktop; axe accessibility checks.

## 15. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Brute A and optimal share a misreading | False "verified" (criterion 2) | Brute B on a different model with different inputs and instructions; eval against your references |
| Brute A/B disagree often | Lower verified rate | Measured in eval; revisit prompts using real disagreement cases |
| nsjail doesn't run unprivileged on Docker Desktop | Blocks M1 | Spike first, stop and pick a fallback with you (§11.1) |
| Permissive checker | False "verified" | Mutation-rejection test |
| Narration sentence false despite real values | Misleading animation | Conditions + branch selection + overlap lint + neutral fallback |
| settrace vs sys.monitoring counts differ | Inconsistent op counts | Consistency test in M7 |
| 60 s median not met | Quality target | Parallel calls, batched harness, per-stage timings |
| Deep recursion traces are large | Slow or huge traces | Shared heap snapshots, size cap, smaller input fallback |

## 16. Resolved decisions (v3)
1. **Computed values in narration** are allowed, but always rendered with their operands by the engine, and grounded by provenance (§7.4).
2. **Brute A/B**: one that fails the examples is regenerated once; the problem is unverified only if both pass the examples and still disagree (§6.2).
3. **Class/"design" problems** are out of scope for v1. The operations-list input type (§5) is designed so it can back them later; nothing extra is built now.

---

## Appendix A: Draft eval set (50 problems)

These are well-known problems. You'll write or paste the statements locally; nothing is shipped. Tags mark which special pipeline paths a problem exercises: `[unordered]`, `[checker]` (multiple valid answers), `[float]`, `[ops]` (list-of-operations input). I'd also suggest **removing the worked examples from 3 statements** (I've marked them `[no-ex]`) to exercise the no-examples path.

**Arrays and strings (10)**
1. Best Time to Buy and Sell Stock
2. Maximum Subarray
3. Product of Array Except Self
4. Rotate Array
5. Merge Intervals
6. Search in Rotated Sorted Array
7. Next Permutation
8. Valid Palindrome `[no-ex]`
9. Longest Common Prefix
10. Valid Parentheses

**Hashing, two pointers, sliding window (8)**
11. Two Sum `[checker]` (if multiple pairs are allowed in your statement)
12. Group Anagrams `[unordered]`
13. Longest Substring Without Repeating Characters
14. Container With Most Water
15. 3Sum `[unordered]`
16. Minimum Window Substring
17. Longest Consecutive Sequence
18. Subarray Sum Equals K

**Trees (8)**
19. Maximum Depth of Binary Tree
20. Invert Binary Tree
21. Validate Binary Search Tree
22. Lowest Common Ancestor of a BST
23. Binary Tree Level Order Traversal
24. Diameter of Binary Tree
25. Path Sum II `[unordered]`
26. Construct Binary Tree from Preorder and Inorder Traversal

**Graphs and grids (8)**
27. Number of Islands
28. Rotting Oranges
29. Course Schedule II `[checker]`
30. Network Delay Time (Dijkstra)
31. Number of Connected Components in an Undirected Graph (union-find) `[no-ex]`
32. Shortest Path in Binary Matrix
33. Word Ladder
34. Cheapest Flights Within K Stops

**Dynamic programming (10)**
35. Climbing Stairs
36. House Robber
37. Coin Change
38. Longest Increasing Subsequence
39. Unique Paths II
40. Edit Distance
41. Partition Equal Subset Sum (0/1 knapsack)
42. Word Break
43. Longest Palindromic Substring `[checker]` (ties)
44. Knight Probability in Chessboard `[float]`

**Others (6)**
45. Daily Temperatures (monotonic stack)
46. Largest Rectangle in Histogram (monotonic stack)
47. Kth Largest Element in an Array (heap) `[no-ex]`
48. Merge k Sorted Lists (linked list + heap)
49. Combination Sum (backtracking) `[unordered]`
50. Range Sum Query with point updates, as a list of operations (segment tree) `[ops]`
