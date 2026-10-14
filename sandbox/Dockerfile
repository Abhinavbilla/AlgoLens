# AlgoLens sandbox: runs untrusted Python/C++ under nsjail. See sandbox/spike/RESULTS.md.
FROM python:3.12-slim-bookworm AS nsjail
RUN apt-get update && apt-get install -y --no-install-recommends \
      autoconf bison flex gcc g++ git libprotobuf-dev libnl-route-3-dev libtool make \
      pkg-config protobuf-compiler ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch 3.4 https://github.com/google/nsjail.git /nsjail \
    && make -C /nsjail -j"$(nproc)"

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=60 PIP_RETRIES=10
RUN apt-get update && apt-get install -y --no-install-recommends \
      g++ libprotobuf32 libnl-route-3-200 nlohmann-json3-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --from=nsjail /nsjail/nsjail /usr/local/bin/nsjail
COPY requirements.txt /tmp/requirements.txt
# Persistent pip cache: a flaky connection only has to succeed once.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY include/algolens.h /usr/local/include/algolens/algolens.h
# Precompile the header with exactly the sandbox's compile flags (CPP_FLAGS in batch.py);
# a mismatch would make g++ silently ignore it.
RUN g++ -std=c++17 -O2 -x c++-header /usr/local/include/algolens/algolens.h \
      -o /usr/local/include/algolens/algolens.h.gch
COPY driver /opt/algolens/driver
COPY algolens_sandbox /opt/algolens/app/algolens_sandbox
ENV PYTHONPATH=/opt/algolens/app

# The socket directory is a shared volume; it takes this ownership when first created.
# uvicorn makes the socket itself world-writable, so access is limited by the directory:
# the CMD below makes it owner-only (uid 10001: this service, api and worker) on every start.
RUN useradd --create-home --uid 10001 sandbox && mkdir -p /run/sandbox /jobs \
    && chown sandbox:sandbox /run/sandbox /jobs
USER sandbox
WORKDIR /opt/algolens/app
HEALTHCHECK --interval=3s --timeout=6s --retries=40 \
    CMD ["python", "-m", "algolens_sandbox.healthcheck"]
CMD ["sh", "-c", "chmod 700 /run/sandbox && rm -f /run/sandbox/sandbox.sock && exec uvicorn algolens_sandbox.server:app --uds /run/sandbox/sandbox.sock --log-level info"]

# Test image: same runtime plus pytest and the sandbox's own tests.
FROM runtime AS test
USER root
RUN --mount=type=cache,target=/root/.cache/pip pip install "pytest>=8"
COPY tests /opt/algolens/app/tests
USER sandbox
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"]
