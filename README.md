# AlgoLens

Step-by-step algorithm animations built only from real, verified runs of code. See `spec.md` for what it does and `plan.md` for how it's built.

## Run it

Needs Docker (with Compose v2.24+).

```sh
cp .env.example .env   # optional until M5; add ANTHROPIC_API_KEY there
docker compose up --build
```

Open http://localhost:8080. Migrations run automatically when the API starts.

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

Frontend:

```sh
cd frontend
npm install
npm run dev        # proxies /api to localhost:8000
npm run lint && npm run typecheck && npm test
```
