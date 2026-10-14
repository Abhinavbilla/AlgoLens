from fastapi import FastAPI, Response

from algolens import __version__
from algolens.api import library, problems
from algolens.db.session import database_is_up
from algolens.sandbox.client import SandboxClient


def sandbox_is_up() -> bool:
    client = SandboxClient()
    try:
        return client.is_healthy()
    finally:
        client.close()


def create_app() -> FastAPI:
    app = FastAPI(title="AlgoLens", version=__version__)
    app.include_router(library.router)
    app.include_router(problems.router)

    @app.get("/api/health")
    def health(response: Response) -> dict[str, str]:
        # Only the database decides liveness. A sandbox outage is reported but doesn't make
        # the API unhealthy: stored results and the library pages still work without it.
        db_ok = database_is_up()
        if not db_ok:
            response.status_code = 503
        return {
            "status": "ok" if db_ok else "degraded",
            "version": __version__,
            "database": "ok" if db_ok else "down",
            "sandbox": "ok" if sandbox_is_up() else "down",
        }

    return app


app = create_app()
