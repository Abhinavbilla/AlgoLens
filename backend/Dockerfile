FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=60 PIP_RETRIES=10
WORKDIR /app

COPY pyproject.toml ./
COPY algolens ./algolens
# /run/sandbox is the shared socket volume; whichever container creates it sets its owner,
# so it must be owned by uid 10001 here too.
RUN pip install . && useradd --create-home --uid 10001 algolens \
    && mkdir -p /run/sandbox && chown algolens:algolens /run/sandbox

USER algolens
EXPOSE 8000
CMD ["algolens", "serve"]
