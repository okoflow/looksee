ARG BASE_IMAGE=python:3.12-slim-trixie
ARG UV_VERSION=0.11

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM ${BASE_IMAGE} AS builder

COPY --from=uv /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/
COPY apps/inference/pyproject.toml apps/inference/
COPY packages/shared/pyproject.toml packages/shared/
COPY ee/api/pyproject.toml ee/api/

# looksee-ee pulls looksee-api in; the image ships ee code locked behind LICENSE_KEY.
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-workspace --no-dev --package looksee-ee

COPY apps/api/ apps/api/
COPY packages/shared/ packages/shared/
COPY ee/api/ ee/api/

RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable --package looksee-ee

FROM ${BASE_IMAGE}

RUN useradd --uid 1000 --user-group --no-create-home api

RUN install -d -o api -g api -m 0755 /data/snapshots && \
    install -d -o api -g api -m 0700 /data/keys

WORKDIR /app

COPY --from=builder --chown=api:api /app/.venv .venv
COPY --chown=api:api apps/api/alembic.ini apps/api/alembic.ini
COPY --chown=api:api apps/api/alembic apps/api/alembic

ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

USER api

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
