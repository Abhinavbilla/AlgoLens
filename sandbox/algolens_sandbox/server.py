"""Sandbox HTTP API, served on a Unix socket only (the container has no network at all)."""

import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from algolens_sandbox import selftest
from algolens_sandbox.batch import (
    BatchRequest,
    BatchResponse,
    TraceRequest,
    TraceResponse,
    run_batch,
    run_trace,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("algolens.sandbox")

MAX_CONCURRENT = int(os.environ.get("SANDBOX_MAX_CONCURRENT", "4"))
_slots = threading.BoundedSemaphore(MAX_CONCURRENT)
_state = {"healthy": False, "problems": ["self-test has not run yet"]}


@asynccontextmanager
async def lifespan(_: FastAPI):
    problems = selftest.run()
    _state.update(healthy=not problems, problems=problems)
    if problems:
        log.error("SELF-TEST FAILED, refusing all batches: %s", problems)
    else:
        log.info("self-test passed")
    yield


app = FastAPI(title="AlgoLens sandbox", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    if not _state["healthy"]:
        raise HTTPException(503, detail={"status": "unhealthy", "problems": _state["problems"]})
    return {"status": "ok", "max_concurrent": MAX_CONCURRENT}


@app.post("/v1/batch")
def batch(req: BatchRequest) -> BatchResponse:
    if not _state["healthy"]:
        raise HTTPException(503, detail={"status": "unhealthy", "problems": _state["problems"]})
    # Each jail may use up to 16 processes; this keeps the container under its pid limit.
    with _slots:
        return run_batch(req)


@app.post("/v1/trace")
def trace(req: TraceRequest) -> TraceResponse:
    if not _state["healthy"]:
        raise HTTPException(503, detail={"status": "unhealthy", "problems": _state["problems"]})
    with _slots:
        return run_trace(req)
