# API service

The API is LookSee's FastAPI control plane. It owns workflows, desired camera state,
model discovery, event policy, actions, alerts, and per-camera realtime updates. It does
not decode video or run ONNX models.

## Layout

```text
src/api/
├── domain/       framework-independent workflow, graph, event, and geometry models
├── application/  workflow, camera, reconciliation, validation, and execution use cases
├── adapters/     PostgreSQL, Valkey, MediaMTX, filesystem, delivery, and runtime state
├── entrypoints/  HTTP and WebSocket routers plus Redis subscribers
├── config.py
├── bootstrap.py  runtime adapter composition
└── main.py
alembic/          database migrations
```

The execution, frame processing, authentication, media authorization, validation,
and delivery core depends on domain models and application-owned ports. Adapters
implement those ports; `bootstrap.py` and HTTP dependencies compose them. Existing
workflow CRUD and camera reconciliation still use SQLAlchemy sessions directly.
Keep HTTP routers thin and infrastructure out of the domain and extracted core;
architecture tests enforce these boundaries.

## Run locally

Complete the root [development setup](../../CONTRIBUTING.md#development-setup) first, then:

```bash
uv run --package looksee-api alembic -c apps/api/alembic.ini upgrade head
uv run --package looksee-api fastapi dev apps/api/src/api/main.py
```

The running service exposes OpenAPI at `http://localhost:8000/docs`. Apply migrations
before starting the API. Verify ORM changes with
`uv run --package looksee-api alembic -c apps/api/alembic.ini check`.
