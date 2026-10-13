# M1 spike: can nsjail isolate untrusted code inside an unprivileged container on this machine?
FROM python:3.12-slim-bookworm AS nsjail
RUN apt-get update && apt-get install -y --no-install-recommends \
      autoconf bison flex gcc g++ git libprotobuf-dev libnl-route-3-dev libtool make \
      pkg-config protobuf-compiler ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch 3.4 https://github.com/google/nsjail.git /nsjail \
    && make -C /nsjail -j"$(nproc)"

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
      g++ libprotobuf32 libnl-route-3-200 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=nsjail /nsjail/nsjail /usr/local/bin/nsjail
RUN useradd --create-home --uid 10001 runner
COPY cases /spike/cases
COPY run_spike.py /spike/run_spike.py
USER runner
WORKDIR /spike
CMD ["python", "/spike/run_spike.py"]
