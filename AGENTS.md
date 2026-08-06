# LookSee

Self-hosted video analytics monorepo: `api` (FastAPI control plane),
`inference` (ONNX detection service), `studio` (Next.js workflow editor),
`shared` (api ↔ inference wire contracts). Root is a non-package uv workspace;
its members are the `looksee-api`, `looksee-inference`, `looksee-shared`, and
`looksee-ee` distributions (import names stay `api`, `inference`, `shared`,
`ee`).

## Commands

Run from the repository root.

```bash
uv sync --all-packages --extra cpu
docker compose up -d postgres redis mediamtx

uv run --package looksee-api alembic -c apps/api/alembic.ini upgrade head
uv run --package looksee-api fastapi dev apps/api/src/api/main.py
uv run --package looksee-inference faststream run inference.main:app
pnpm -C apps/studio dev
pnpm -C apps/docs dev
```

Checks — run before finishing any change:

```bash
uv run ruff check .
uv run ruff format --check .
uv run --package looksee-api alembic -c apps/api/alembic.ini check  # after ORM changes
pnpm -C apps/studio lint
pnpm -C apps/studio typecheck
pnpm -C apps/studio build
pnpm -C apps/docs lint
pnpm -C apps/docs build
docker compose --env-file .env.example config --quiet
```

## Layout

```text
apps/api/         domain / application / adapters / entrypoints
apps/inference/   application / adapters (onnx, video, redis, tracking)
apps/studio/      FSD: src/_app, _pages, widgets, features, entities, shared
apps/docs/        Fumadocs documentation site (standalone pnpm root)
packages/shared/  leaf package, depends on pydantic only
packages/brand/   @looksee/brand — canonical brand assets
ee/               commercial edition code — ee/LICENSE, not Apache-2.0
docker/           MediaMTX configuration
compose.yaml      postgres · valkey · mediamtx · api · inference · studio
models/           runtime model bundles — never committed
```

## Architecture rules

- Dependencies point inward: entrypoints → application → adapters → domain.
  Domain knows nothing about FastAPI, SQLAlchemy, or ONNX. Routers stay thin.
- Node field validation lives in Pydantic models: permissive draft payloads plus
  strict `Runnable*` counterparts checked on enable
  (`api/domain/workflow/runnable.py`). Graph-level checks live in
  `api/application/workflow_validation.py` and never inspect node internals.
- A new model architecture is one registered adapter matched by ONNX signature
  (`inference/adapters/onnx/registry.py`); never branch on model ids.
- `looksee-ee` is optional: the open code imports it only in
  `api/domain/workflow/extensions.py` and `api/application/entitlements.py`
  (try/except ImportError), and everything must keep working with `ee/`
  deleted. ee imports core submodules freely, never the reverse elsewhere.
  Paid node kinds are gated on enable via entitlements, never at draft time.
- Inference passes detections as supervision `sv.Detections` end to end.
- Studio slices are imported through public `index.ts` APIs, downward through
  FSD layers only; relative imports inside one slice.

## Style

- Guard clauses and named predicates over boolean chains. No `value or default`
  for optionals — check `is None` explicitly. Dropped data or swallowed errors
  must be logged or raised, never silent.
- Add a Python dependency to the member that imports it and refresh `uv.lock`.
  No `requirements.txt`.
- Import shared contracts from the package root: `from shared import DetectionFrame`.

## Database

- Constraint names come from the naming convention in
  `api/adapters/persistence/db/base.py`; primary keys default to Postgres
  `uuidv7()`.
- The schema is one squashed migration (`0001`) targeting a fresh volume; keep
  `alembic check` clean after any ORM change.

## Configuration

- The root `.env` (+ `.env.example`) is the only configuration source. Compose
  loads it into api and inference via `env_file` and pins service-name URLs and
  container paths in `environment`. New tunables go to `.env.example`, never to
  compose or per-service env files.

## Do not

- Commit model weights, bundle manifests, generated data, or caches.
- Write docs, README sections, or ADRs unless explicitly asked.
