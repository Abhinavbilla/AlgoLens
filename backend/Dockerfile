# Built from the repository root (see docker-compose.yml) so the library ships with the API.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=60 PIP_RETRIES=10 \
    ALGOLENS_LIBRARY_DIR=/app/library
WORKDIR /app

# Dependencies first, in their own layer, with a persistent pip cache: code changes never
# re-download anything, and a flaky connection only has to succeed once.
COPY backend/pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt "setuptools>=69"

COPY backend/algolens ./algolens
# Offline from here on: the build backend was installed above, so this never downloads.
# /run/sandbox is the shared socket volume; whichever container creates it sets its owner,
# so it must be owned by uid 10001 here too.
RUN pip install --no-deps --no-build-isolation --no-cache-dir --no-index . \
    && useradd --create-home --uid 10001 algolens \
    && mkdir -p /run/sandbox && chown algolens:algolens /run/sandbox
COPY library ./library

USER algolens
EXPOSE 8000
CMD ["algolens", "serve"]

# Test image: runtime plus test tools, the tests, and the tracer they record with.
#   docker compose --profile test run --rm backend-test
FROM runtime AS test
USER root
RUN --mount=type=cache,target=/root/.cache/pip pip install "pytest>=8" "ruff>=0.6"
COPY backend/tests ./tests
COPY sandbox/driver /opt/algolens/driver
ENV ALGOLENS_TRACER_DIR=/opt/algolens/driver
USER algolens
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
