FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
COPY algolens ./algolens
RUN pip install . && useradd --create-home --uid 10001 algolens

USER algolens
EXPOSE 8000
CMD ["algolens", "serve"]
