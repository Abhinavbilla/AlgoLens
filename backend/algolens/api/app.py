from fastapi import FastAPI, Response

from algolens import __version__
from algolens.db.session import database_is_up


def create_app() -> FastAPI:
    app = FastAPI(title="AlgoLens", version=__version__)

    @app.get("/api/health")
    def health(response: Response) -> dict[str, str]:
        db_ok = database_is_up()
        if not db_ok:
            response.status_code = 503
        return {
            "status": "ok" if db_ok else "degraded",
            "version": __version__,
            "database": "ok" if db_ok else "down",
        }

    return app


app = create_app()
