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
├── composition.py
├── config.py
└── main.py
alembic/          the fresh-install database migration
```

Dependencies point inward: entrypoints call application use cases, which use domain
models and adapter ports. Keep HTTP routers thin and keep FastAPI, SQLAlchemy, and
transport details out of the domain layer.

## Run locally

Complete the root [development setup](../../README.md#develop-locally) first, then:

```bash
uv run --package looksee-api alembic -c apps/api/alembic.ini upgrade head
uv run --package looksee-api fastapi dev apps/api/src/api/main.py
```

The running service exposes OpenAPI at `http://localhost:8000/docs`. After an ORM change,
keep the squashed `0001` migration in sync and verify with
`uv run --package looksee-api alembic -c apps/api/alembic.ini check`.
