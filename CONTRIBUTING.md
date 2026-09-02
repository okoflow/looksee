# Contributing

Thank you for helping build LookSee. This guide covers how to set up a
development environment, the checks a change has to pass, and how commits and
pull requests are shaped. Everyone participating agrees to the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- **Report a bug** with the bug report issue form. Include the commit or
  release, the deployment shape, and the logs of the affected service.
- **Propose a feature** with the feature request form. Describe the problem
  before the solution; small, well-scoped proposals land faster.
- **Report a vulnerability** privately as described in [SECURITY.md](SECURITY.md).
- **Improve documentation** in the
  [looksee-docs](https://github.com/okoflow/looksee-docs) repository; the
  README files in this repository describe the code, not the product.
- **Send a pull request** for an open issue. Comment on the issue first for
  anything larger than a fix, so the approach is agreed before the work.

## Repository layout

| Path | What lives there |
| --- | --- |
| `apps/api` | FastAPI control plane: workflows, cameras, events, actions, alerts |
| `apps/inference` | ONNX detection service: decoding, models, tracking |
| `apps/studio` | Next.js interface: workflow editor and live monitor |
| `packages/shared` | Pydantic wire contracts between the API and inference |
| `ee/api` | Enterprise node types and integrations under `ee/LICENSE` |
| `models` | Model bundles: `manifest.json` plus an ignored `model.onnx` |
| `docker`, `compose.yaml` | MediaMTX configuration and the deployment stack |

Each Python package and Studio has a README that explains its internal layout
and the rules for extending it.

## Development setup

Prerequisites: [uv](https://docs.astral.sh/uv/), Python 3.12, Node.js 24,
[pnpm](https://pnpm.io/) 11, Docker with Compose 2.24 or later.

```bash
git clone https://github.com/okoflow/looksee.git
cd looksee
cp .env.example .env

uv sync --all-packages --extra cpu
pnpm -C apps/studio install --frozen-lockfile
```

Run the infrastructure in containers and the services natively. Uncomment the
"native development" block at the end of `.env` so the services find
`localhost` instead of the compose service names.

```bash
docker compose up -d postgres redis mediamtx

uv run --package looksee-api alembic -c apps/api/alembic.ini upgrade head
uv run --package looksee-api fastapi dev apps/api/src/api/main.py
uv run --package looksee-inference faststream run inference.main:app
pnpm -C apps/studio dev
```

Studio serves `http://localhost:3000`, the API `http://localhost:8000` with
OpenAPI at `/docs`. `docker compose up -d --build` runs the whole stack from
images instead.

Model bundles are not committed. Place a directory under `models/` with a
`manifest.json` and a `model.onnx`; the API discovers it on the next request.

## Checks

Continuous integration runs the same commands on every pull request. Run them
before you push.

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run --package looksee-api alembic -c apps/api/alembic.ini check

pnpm -C apps/studio lint
pnpm -C apps/studio lint:fsd
pnpm -C apps/studio typecheck
pnpm -C apps/studio build

docker compose --env-file .env.example config --quiet
```

`alembic check` needs a database at head: run `upgrade head` first. `ruff
format .` and `pnpm lint:fix` apply the formatting fixes.

## Code guidelines

### Python

- Dependencies point inward: `entrypoints` call `application` use cases, which
  use `domain` models and `adapters` ports. Keep FastAPI, SQLAlchemy, and
  transport details out of `domain`.
- Prefer short functions. Separate the logical phases inside a function
  (guards, preparation, action, return) with one blank line, and name
  intermediate values instead of writing dense expressions.
- No comments that restate the code and no re-export boilerplate. Document
  why, not what.
- Ruff enforces the rule set in `pyproject.toml`, including security (`S`),
  async (`ASYNC`), and timezone (`DTZ`) checks. Do not add `noqa` without a
  reason next to it.
- The API ships one squashed migration, `0001_initial`. After an ORM change,
  update it in place and confirm with `alembic check`; do not add incremental
  revisions before the first stable release.
- `shared` contracts reject unknown fields and have no legacy aliases. When a
  payload changes, change the API and the inference service in the same pull
  request.

### Studio

- Studio follows Feature-Sliced Design: `app`, `_pages`, `widgets`,
  `features`, `entities`, `shared`. Import across slices only through a
  slice's `index.ts`; `pnpm lint:fsd` checks the boundaries.
- Biome, configured through Ultracite, formats and lints the code. Add
  components from shadcn into `src/shared/ui`.
- Runtime configuration comes from `RUNTIME_*` variables validated on the
  server; never read `process.env` in client code.

### Tests

- Tests live next to each package: `packages/shared/tests`, `apps/api/tests`,
  `apps/inference/tests`, `ee/api/tests`, and run with `uv run pytest`.
- Unit tests do not need PostgreSQL, Valkey, MediaMTX, or the network. Use the
  in-memory adapters and small fakes for ports.
- Name tests after the behaviour they prove, one module per source module.

## Commits

Commits follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):
`type(scope): description`.

- Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`,
  `chore`. Only `feat` and `fix` move the version.
- The scope is an area such as `api`, `inference`, `studio`, `shared`, `ee`,
  never a file name.
- The description is imperative and lowercase, under 72 characters, without
  a trailing period. It says what the change does, not what task it closes.
- A breaking change carries `!` before the colon and a `BREAKING CHANGE:`
  footer that states what an operator must do.
- One commit is one logical change that builds and passes on its own. Add a
  body only for what the diff cannot show: the problem, the reason for the
  approach, a constraint. Footers such as `Fixes #12` go last.
- Commits credit people. Do not add generator or tooling trailers.

## Pull requests

- One pull request is one standalone change. Split anything above roughly
  400 changed lines unless the parts only make sense together; stack
  dependent branches on each other rather than on `main`.
- The title is the merge commit subject and follows the commit format. The
  body says what changed and why in a few sentences and names the risky
  spot. Add `Verified:` with the checks you ran and `Fixes #N` when it closes
  an issue.
- Attach a screenshot or recording for visible Studio changes.
- CI has to pass. Reviews focus on correctness, layering, and whether the
  change is the smallest one that solves the problem.

## Licensing of contributions

Code outside `ee/` is licensed under Apache-2.0 and code inside `ee/` under
the [LookSee Enterprise license](ee/LICENSE). By submitting a contribution you
agree that it is licensed under the license of the directory it lands in.
