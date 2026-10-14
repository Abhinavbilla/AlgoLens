# AlgoLens

Step-by-step algorithm animations built only from real, verified runs of code. See `spec.md` for what it does and `plan.md` for how it's built.

## Run it

Needs Docker (with Compose v2.24+).

```sh
cp .env.example .env   # then paste your API keys into .env (it's git-ignored)
docker compose up --build
```

Open http://localhost:8080. Migrations run automatically when the API starts. The library works without any keys; **Paste a problem** needs them.

### AI keys

Pasted problems are solved by AI models. By default these are free tiers: Gemini for most roles (key from https://aistudio.google.com) and Groq for the independent second brute force (key from https://console.groq.com). Put them in `.env` as `GEMINI_API_KEY` and `GROQ_API_KEY`, then `docker compose up -d` to pick them up. Each role's model is a `provider:model` setting in `.env` (providers: `gemini`, `groq`, `anthropic`, `openai`), so you can switch to paid models without code changes. Brute A and Brute B must be different models.

Privacy: the statement is sent to those providers (free tiers may use prompts to improve their models). AlgoLens stores only a hash of it, never the text.

### What happens to a pasted problem

1. The statement is read into a precise signature, input rules and the worked examples; out-of-scope problems are turned down with a reason.
2. Two brute forces are written independently (different models; the second sees only the statement), plus one or two better approaches.
3. Every approach is run on the examples and 300 random valid inputs against the brute force, and its C++ against its Python. Failures get up to two repair rounds. Only approaches that pass everything are marked verified.
4. Verified approaches get an animation (checked against real recordings), and a chart of how their work grows with input size.

A per-problem token budget (`ALGOLENS_MAX_TOKENS_PER_PROBLEM`) caps the AI spend.

## Develop

Backend (Python 3.12):

```sh
cd backend
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # .venv/bin on Linux/macOS
ruff check . && ruff format --check .
pytest -q
```

Database tests run when `ALGOLENS_TEST_DATABASE_URL` points at an empty Postgres database you don't mind being reset. They're skipped otherwise. With the compose stack up you can use:

```sh
docker compose exec db createdb -U algolens algolens_test
ALGOLENS_TEST_DATABASE_URL=postgresql+psycopg://algolens:algolens@localhost:5432/algolens_test pytest -q
```

Sandbox (runs untrusted code; see `sandbox/spike/RESULTS.md`). Its hostile-code suite runs inside the real sandbox image under the production restrictions:

```sh
docker compose --profile test run --rm sandbox-test
```

Backend tests against the real database and sandbox, on Python 3.12 (creates its own test database):

```sh
docker compose --profile test run --rm backend-test
```

Algorithm library (`library/`, one folder per entry). It's loaded into Postgres when the API starts. To check every entry in the sandbox and record the result shown on its badge:

```sh
docker compose exec api algolens library verify            # all entries
docker compose exec api algolens library verify bubble-sort
```

Evaluation (plan §10): put problems in `eval/<name>/` with `statement.txt`, `reference.py` (defines `reference(...)`, and optionally `check(..., output)`) and an optional `meta.json`. The folder is git-ignored. Then:

```sh
docker compose run --rm -v ./eval:/app/eval api algolens eval --set /app/eval   # all problems
docker compose run --rm -v ./eval:/app/eval api algolens eval --set /app/eval two-sum
```

The report lands in `eval/reports/<time>.md` and `.json`. The exit code is 1 if any verified approach disagrees with your reference (a false verification).

Frontend:

```sh
cd frontend
npm install
npm run dev        # proxies /api to localhost:8000
npm run lint && npm run typecheck && npm test
```

UI check (stack running): screenshots of every library entry at 375 px and 1280 px in light and dark themes, and at every step a check for sideways scrolling, overlapping or clipped pointer labels, and anything moving between steps. It uses the installed Microsoft Edge, so there's no browser download:

```sh
cd frontend && node scripts/ui-check.mjs ../ui-check-out
```
