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

### The tutor

Every algorithm page and solved problem has a tutor ("Ask the tutor", bottom right):

- **Explain**: questions about the page, answered from what we've stored and checked (the write-up, the verified code with line numbers, the test results and the thought process). Never the raw problem text, and never unverified code presented as correct.
- **Ask about this step**: a button in the player that sends the step on screen (line, sentence, values) with the question.
- **Just a hint**: one nudge at a time, no solution code.
- **Check my code**: the learner's Python runs in the sandbox on the examples and 25 small random inputs and is compared with the verified solution (no AI involved). The tutor can then explain the real failure.

The conversation stays in the browser tab; the server keeps none of it. Limits: 20 messages per conversation, and 10 questions a minute / 150 a day per visitor. Set the model with `ALGOLENS_MODEL_TUTOR` (default: the narration model); a model of its own keeps chatting from using up the solver's free-tier quota.

### Optional sign-in with Google

Nobody has to sign in: the library, learning path, pasting problems and the tutor all work without an account. Signing in keeps learning-path progress across devices (this browser's progress is merged in the first time), lists the problems you've opened under **Your account**, and raises the tutor's limits (20 questions a minute / 400 a day per account).

To turn it on, create an OAuth client of type "Web application" in Google Cloud Console (APIs & Services → Credentials; set up the consent screen first, "External", and while it's in Testing mode add the Google accounts that may sign in). Use the redirect URI `http://localhost:8080/api/auth/google/callback`, put `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`, and restart. For a real domain, set `ALGOLENS_PUBLIC_URL=https://your-domain` and add that callback URL too.

**Email sign-in** works alongside Google: you type your address, get a 6-digit code (valid once, for 10 minutes; 5 wrong guesses lock it), and you're in. No passwords. The same address reaches the same account whichever way you sign in. It needs an SMTP service: set `ALGOLENS_SMTP_HOST`, `ALGOLENS_SMTP_PORT`, `ALGOLENS_SMTP_USER`, `ALGOLENS_MAIL_FROM` and `SMTP_PASSWORD` (with Gmail: `smtp.gmail.com`, port 587, and an App Password from your Google account's security page). For trying it locally, `ALGOLENS_EMAIL_DEV_LOG=true` writes codes to the API log instead (`docker compose logs api | grep "sign-in code"`); never use that on a public server.

What's kept: Google's user id (if you use Google), your email, name and picture; a hash of each session token (30 days); the ids of topics marked as done; the ids of problems you've opened. Only the `openid email profile` scopes are requested. **Delete my account** removes all of it.

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
