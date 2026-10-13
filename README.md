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

Frontend:

```sh
cd frontend
npm install
npm run dev        # proxies /api to localhost:8000
npm run lint && npm run typecheck && npm test
```
