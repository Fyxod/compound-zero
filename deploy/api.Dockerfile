# syntax=docker/dockerfile:1.7

FROM python:3.11.15-slim-bookworm AS dependencies

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /build
COPY requirements.lock ./requirements.lock
RUN python -m pip install --require-hashes --only-binary=:all: -r requirements.lock


FROM python:3.11.15-slim-bookworm AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/opt/venv/bin:$PATH \
    COMPOUND_ZERO_ARTIFACT_DIR=/app/artifacts \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1

RUN groupadd --gid "$APP_GID" app \
    && useradd --uid "$APP_UID" --gid "$APP_GID" --create-home --shell /usr/sbin/nologin app

COPY --from=dependencies /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app ml ./ml
COPY --chown=app:app services ./services
COPY --chown=app:app artifacts ./artifacts
COPY --chown=app:app data/knowledge ./data/knowledge

USER app
EXPOSE 8000

HEALTHCHECK CMD python -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)); assert d['ready'] is True" || exit 1

# One worker is intentional: response-approval state is explicitly ephemeral
# and process-local in this prototype. Production requires a durable store.
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
