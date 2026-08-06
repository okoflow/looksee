ARG BASE_IMAGE=python:3.12-slim-trixie
ARG UV_VERSION=0.11

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM ${BASE_IMAGE} AS builder

ARG TARGET=cpu

COPY --from=uv /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/
COPY apps/inference/pyproject.toml apps/inference/
COPY packages/shared/pyproject.toml packages/shared/
COPY ee/api/pyproject.toml ee/api/

RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-workspace --no-dev --package looksee-inference --extra "${TARGET}"

COPY apps/inference/ apps/inference/
COPY packages/shared/ packages/shared/

RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable --package looksee-inference --extra "${TARGET}"

FROM ${BASE_IMAGE}

RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0t64 && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1000 --user-group --no-create-home inference

WORKDIR /app

COPY --from=builder --chown=inference:inference /app/.venv .venv

RUN install -d -o inference -g inference -m 0555 /app/models

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    MODELS_DIR=/app/models \
    OMP_NUM_THREADS=4 \
    OMP_WAIT_POLICY=PASSIVE

USER inference

CMD ["faststream", "run", "inference.main:app"]
