"""Shared fakes for the API application, adapter, and HTTP suites.

No PostgreSQL, Redis, MediaMTX, or network: persistence is an in-memory
session that interprets the small set of statement shapes the use cases
build, and every external effect is recorded on an EffectRecorder.
"""

from __future__ import annotations

import operator
import warnings
from collections import defaultdict, namedtuple
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from starlette.exceptions import StarletteDeprecationWarning

with warnings.catch_warnings():
    # Starlette 1.3 warns once at import that TestClient prefers httpx2; the
    # repository pins httpx, and the warning would otherwise fail collection.
    warnings.simplefilter("ignore", StarletteDeprecationWarning)
    import fastapi.testclient  # noqa: F401

from sqlalchemy import Column, Delete, Select, inspect
from sqlalchemy.exc import IntegrityError, MultipleResultsFound
from sqlalchemy.sql import functions, operators
from sqlalchemy.sql.elements import (
    BinaryExpression,
    BindParameter,
    BooleanClauseList,
    Grouping,
    Null,
    UnaryExpression,
)

from api.adapters.actions import alerts as alerts_action
from api.adapters.persistence import credentials as persisted_credentials
from api.adapters.persistence.db.base import Base
from api.adapters.persistence.models import Camera, Credential, Workflow
from api.adapters.realtime.broadcaster import broadcaster
from api.adapters.security import keys
from api.adapters.state.memory import InMemoryRuntimeState
from api.application import camera_runtime, frame_processing, reconcile, worker_status
from api.application.execution import ExecutionIdentity
from api.application.frame_processing import FrameProcessingDependencies
from api.config import settings
from api.domain.events import DetectionEvent
from api.domain.models import ModelClassDescriptor, ModelDescriptor
from api.domain.workflow import WorkflowGraph
from api.entrypoints.http.routers import ws
from shared import Detection, DetectionFrame

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

TEST_SECRET = "unit-test-secret-key"
FIXED_TS = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)

_TABLE_BY_CLASS = {mapper.class_: mapper.local_table.name for mapper in Base.registry.mappers}
_CLASS_BY_TABLE = {name: cls for cls, name in _TABLE_BY_CLASS.items()}
_UNIQUE_NAME_CONSTRAINTS = {Workflow: "uq_workflows_name", Credential: "uq_credentials_name"}

_COMPARISONS: dict[Any, Callable[[Any, Any], bool]] = {
    operators.eq: operator.eq,
    operators.ne: operator.ne,
    operators.is_: operator.is_,
    operators.is_not: operator.is_not,
    operators.in_op: lambda left, right: left in right,
    operators.not_in_op: lambda left, right: left not in right,
}


class UniqueViolationError(Exception):
    """Stand-in for the driver error that carries the violated constraint name."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__(constraint_name)
        self.constraint_name = constraint_name


def unique_violation(constraint_name: str) -> IntegrityError:
    driver_error = Exception("duplicate key value violates unique constraint")
    driver_error.__cause__ = UniqueViolationError(constraint_name)

    return IntegrityError("INSERT", {}, driver_error)


def _resolve(node: Any, scope: dict[str, Any]) -> Any:
    if isinstance(node, Grouping):
        return _resolve(node.element, scope)
    if isinstance(node, Column):
        return getattr(scope[node.table.name], node.key)
    if isinstance(node, BindParameter):
        return node.value
    if isinstance(node, Null):
        return None

    raise NotImplementedError(type(node).__name__)


def _matches(clause: Any, scope: dict[str, Any]) -> bool:
    if clause is None:
        return True
    if isinstance(clause, Grouping):
        return _matches(clause.element, scope)
    if isinstance(clause, BooleanClauseList):
        combine = all if clause.operator is operators.and_ else any

        return combine(_matches(part, scope) for part in clause.clauses)
    if isinstance(clause, BinaryExpression):
        compare = _COMPARISONS[clause.operator]

        return compare(_resolve(clause.left, scope), _resolve(clause.right, scope))

    raise NotImplementedError(type(clause).__name__)


def _sorted(scopes: list[dict[str, Any]], order_by: Iterable[Any]) -> list[dict[str, Any]]:
    for clause in reversed(tuple(order_by)):
        descending = isinstance(clause, UnaryExpression) and clause.modifier is operators.desc_op
        column = clause.element if isinstance(clause, UnaryExpression) else clause
        scopes.sort(key=partial(_resolve, column), reverse=descending)

    return scopes


def _apply_column_defaults(row: Any) -> None:
    for column in inspect(type(row)).columns:
        if getattr(row, column.key) is not None or column.default is None:
            continue

        default = column.default
        value = default.arg(None) if default.is_callable else default.arg
        setattr(row, column.key, value)

    now = datetime.now(UTC)
    if row.id is None:
        row.id = uuid4()
    if row.created_at is None:
        row.created_at = now
    if row.updated_at is None:
        row.updated_at = now


class FakeScalars:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return list(self._values)

    def first(self) -> Any:
        return self._values[0] if self._values else None


class FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> FakeScalars:
        return FakeScalars([row[0] for row in self._rows])

    def all(self) -> list[Any]:
        return list(self._rows)

    def one_or_none(self) -> Any:
        if len(self._rows) > 1:
            raise MultipleResultsFound

        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self) -> Any:
        row = self.one_or_none()

        return row[0] if row is not None else None

    def scalar(self) -> Any:
        return self._rows[0][0] if self._rows else None


class FakeSession:
    """In-memory AsyncSession double for the ORM models and statements the use cases build."""

    def __init__(self) -> None:
        self.rows: dict[type, list[Any]] = defaultdict(list)
        self.commits = 0
        self.rollbacks = 0
        self.fail_on_execute: Exception | None = None
        self._added: list[Any] = []
        self._deleted: list[Any] = []

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    def seed(self, *rows: Any) -> None:
        for row in rows:
            _apply_column_defaults(row)
            self.rows[type(row)].append(row)

    def add(self, row: Any) -> None:
        self.rows[type(row)].append(row)
        self._added.append(row)

    async def flush(self) -> None:
        for rows in self.rows.values():
            for row in rows:
                if row.id is None:
                    _apply_column_defaults(row)

        for model, constraint in _UNIQUE_NAME_CONSTRAINTS.items():
            names = [row.name for row in self.rows[model]]
            if len(set(names)) != len(names):
                raise unique_violation(constraint)

    async def commit(self) -> None:
        await self.flush()
        self._added.clear()
        self._deleted.clear()
        self.commits += 1

    async def rollback(self) -> None:
        for row in self._added:
            self.rows[type(row)].remove(row)
        for row in self._deleted:
            self.rows[type(row)].append(row)
        self._added.clear()
        self._deleted.clear()
        self.rollbacks += 1

    async def refresh(self, row: Any) -> None:
        return None

    async def delete(self, row: Any) -> None:
        self._remove(row)
        if isinstance(row, Workflow):
            for camera in [c for c in self.rows[Camera] if c.workflow_id == row.id]:
                self._remove(camera)

    async def get(self, model: type, ident: Any) -> Any:
        await self.flush()

        return next((row for row in self.rows[model] if row.id == ident), None)

    async def scalar(self, statement: Any) -> Any:
        result = await self.execute(statement)

        return result.scalar()

    async def execute(self, statement: Any) -> FakeResult:
        if self.fail_on_execute is not None:
            raise self.fail_on_execute

        await self.flush()
        if isinstance(statement, Select):
            return self._select(statement)
        if isinstance(statement, Delete):
            return self._delete(statement)

        raise NotImplementedError(type(statement).__name__)

    def _remove(self, row: Any) -> None:
        self.rows[type(row)].remove(row)
        self._deleted.append(row)

    def _scopes(self, entities: list[type], statement: Select) -> list[dict[str, Any]]:
        for workflow in self.rows[Workflow]:
            cameras = [c for c in self.rows[Camera] if c.workflow_id == workflow.id]
            workflow.cameras = sorted(cameras, key=lambda camera: camera.created_at)

        if len(entities) == 1:
            table = _TABLE_BY_CLASS[entities[0]]

            return [{table: row} for row in self.rows[entities[0]]]

        left, right = entities
        left_table, right_table = _TABLE_BY_CLASS[left], _TABLE_BY_CLASS[right]
        onclause = statement.get_final_froms()[0].onclause
        pairs = [
            {left_table: left_row, right_table: right_row}
            for left_row in self.rows[left]
            for right_row in self.rows[right]
        ]

        return [scope for scope in pairs if _matches(onclause, scope)]

    def _select(self, statement: Select) -> FakeResult:
        descriptions = statement.column_descriptions
        entities = list(dict.fromkeys(d["entity"] for d in descriptions if d["entity"] is not None))
        scopes = [
            s for s in self._scopes(entities, statement) if _matches(statement.whereclause, s)
        ]

        first = descriptions[0]["expr"]
        if isinstance(first, functions.count):
            return FakeResult([(len(scopes),)])

        scopes = _sorted(scopes, statement._order_by_clauses)
        if statement._limit is not None:
            scopes = scopes[: statement._limit]

        if isinstance(first, type):
            table = _TABLE_BY_CLASS[first]

            return FakeResult([(scope[table],) for scope in scopes])

        row_type = namedtuple("Row", [d["name"] for d in descriptions], rename=True)
        rows = [
            row_type(
                *(getattr(scope[_TABLE_BY_CLASS[d["entity"]]], d["name"]) for d in descriptions)
            )
            for scope in scopes
        ]

        return FakeResult(rows)

    def _delete(self, statement: Delete) -> FakeResult:
        table = statement.table.name
        model = _CLASS_BY_TABLE[table]

        for row in [r for r in self.rows[model] if _matches(statement.whereclause, {table: r})]:
            self._remove(row)

        return FakeResult([])


class FakeCatalog:
    def __init__(self, *models: ModelDescriptor) -> None:
        self._models = {model.id: model for model in models}

    def get(self, model_id: str) -> ModelDescriptor | None:
        return self._models.get(model_id)

    def list(self) -> tuple[ModelDescriptor, ...]:
        return tuple(self._models[model_id] for model_id in sorted(self._models))


@dataclass
class EffectRecorder:
    """Everything the use cases would have pushed at MediaMTX, Redis, or browsers."""

    runtime_state: InMemoryRuntimeState
    commands: list[Any] = field(default_factory=list)
    upserted_paths: list[tuple[UUID, Any, str | None]] = field(default_factory=list)
    deleted_paths: list[UUID] = field(default_factory=list)
    realtime: list[tuple[UUID, dict[str, Any]]] = field(default_factory=list)
    actions: list[tuple[ExecutionIdentity, DetectionEvent, Any, dict[str, Any]]] = field(
        default_factory=list
    )
    path_names: set[str] = field(default_factory=set)
    cached_names: dict[str, str] = field(default_factory=dict)
    publish_error: Exception | None = None
    upsert_error: Exception | None = None

    def realtime_types(self) -> list[str]:
        return [payload["type"] for _camera_id, payload in self.realtime]


@pytest.fixture(autouse=True)
def fixed_secret(monkeypatch: pytest.MonkeyPatch) -> Iterable[None]:
    monkeypatch.setattr(settings, "secret_key", TEST_SECRET)
    _clear_key_caches()

    yield

    _clear_key_caches()


def _clear_key_caches() -> None:
    keys._process_secret.cache_clear()
    keys.session_signing_key.cache_clear()
    keys.credentials_fernet.cache_clear()


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def people_model() -> ModelDescriptor:
    return ModelDescriptor(
        id="people",
        name="People",
        classes=(
            ModelClassDescriptor(class_id=0, label="person", event_kind="PERSON_DETECTED"),
            ModelClassDescriptor(class_id=1, label="car", event_kind="CAR_DETECTED"),
            ModelClassDescriptor(class_id=2, label="background", event_kind=None),
        ),
        recommended_confidence_threshold=0.4,
    )


@pytest.fixture
def catalog(people_model: ModelDescriptor) -> FakeCatalog:
    return FakeCatalog(people_model)


@pytest.fixture
def effects(
    monkeypatch: pytest.MonkeyPatch,
    fake_session: FakeSession,
    catalog: FakeCatalog,
) -> EffectRecorder:
    recorder = EffectRecorder(runtime_state=InMemoryRuntimeState())

    async def publish(command: Any) -> None:
        if recorder.publish_error is not None:
            raise recorder.publish_error
        recorder.commands.append(command)

    async def upsert(camera_id: UUID, source_type: Any, source_url: str | None) -> None:
        if recorder.upsert_error is not None:
            raise recorder.upsert_error
        recorder.upserted_paths.append((camera_id, source_type, source_url))

    async def delete_path(camera_id: UUID) -> None:
        recorder.deleted_paths.append(camera_id)

    async def list_names() -> set[str]:
        return set(recorder.path_names)

    async def realtime(camera_id: UUID, payload: dict[str, Any]) -> None:
        recorder.realtime.append((camera_id, payload))

    async def ensure_cached(key: str) -> str:
        return recorder.cached_names.get(key, f"cached-{key}")

    async def run_action(
        identity: ExecutionIdentity,
        event: DetectionEvent,
        action: Any,
        context: dict[str, Any],
    ) -> None:
        recorder.actions.append((identity, event, action, context))

    for module in (camera_runtime, reconcile, worker_status):
        monkeypatch.setattr(module, "publish_stream_command", publish)
    for module in (
        camera_runtime,
        reconcile,
        frame_processing,
        alerts_action,
        ws,
        persisted_credentials,
    ):
        monkeypatch.setattr(module, "session_factory", lambda: fake_session)
    for module in (reconcile, worker_status, alerts_action):
        monkeypatch.setattr(module, "runtime_state", recorder.runtime_state)

    monkeypatch.setattr(camera_runtime, "upsert_camera_path", upsert)
    monkeypatch.setattr(camera_runtime, "delete_camera_path", delete_path)
    monkeypatch.setattr(camera_runtime, "ensure_cached", ensure_cached)
    monkeypatch.setattr(reconcile, "delete_camera_path", delete_path)
    monkeypatch.setattr(reconcile, "list_path_names", list_names)
    monkeypatch.setattr(broadcaster, "publish", realtime)
    monkeypatch.setattr(
        frame_processing,
        "_dependencies",
        FrameProcessingDependencies(
            catalog=catalog,
            publish_command=publish,
            runtime_state=recorder.runtime_state,
            event_cooldown_seconds=0.0,
            event_timezone=ZoneInfo("UTC"),
            publish_realtime=realtime,
            run_action=run_action,
        ),
    )

    return recorder


@pytest.fixture
def build_graph() -> Callable[..., WorkflowGraph]:
    def build(
        nodes: dict[str, dict[str, Any]],
        edges: Iterable[tuple[str, ...]] = (),
    ) -> WorkflowGraph:
        edge_documents = []
        for edge in edges:
            source, target = edge[0], edge[1]
            branch = edge[2] if len(edge) > 2 else None
            edge_documents.append(
                {
                    "id": f"{source}->{target}:{branch}",
                    "source": source,
                    "target": target,
                    "branch": branch,
                }
            )

        return WorkflowGraph.model_validate(
            {
                "nodes": [
                    {"id": node_id, "position": {"x": 0, "y": 0}, "data": data}
                    for node_id, data in nodes.items()
                ],
                "edges": edge_documents,
            }
        )

    return build


@pytest.fixture
def basic_nodes() -> dict[str, dict[str, Any]]:
    return {
        "cam": {
            "kind": "camera_source",
            "name": "Front door",
            "source_type": "rtsp",
            "url": "rtsp://cam.local/stream",
        },
        "det": {"kind": "detect", "model_id": "people"},
        "alert": {"kind": "log_alert_action"},
    }


@pytest.fixture
def basic_graph(
    build_graph: Callable[..., WorkflowGraph], basic_nodes: dict[str, dict[str, Any]]
) -> WorkflowGraph:
    return build_graph(basic_nodes, [("cam", "det"), ("det", "alert")])


@pytest.fixture
def make_detection() -> Callable[..., Detection]:
    def make(
        label: str = "person",
        bounding_box: tuple[float, float, float, float] = (100.0, 100.0, 300.0, 400.0),
        confidence: float = 0.9,
        class_id: int = 0,
        tracker_id: int | None = None,
    ) -> Detection:
        return Detection(
            label=label,
            bounding_box=bounding_box,
            confidence=confidence,
            class_id=class_id,
            tracker_id=tracker_id,
        )

    return make


@pytest.fixture
def make_event(make_detection: Callable[..., Detection]) -> Callable[..., DetectionEvent]:
    def make(**overrides: Any) -> DetectionEvent:
        fields: dict[str, Any] = {
            "camera_id": uuid4(),
            "workflow_id": uuid4(),
            "model_id": "people",
            "kind": "PERSON_DETECTED",
            "ts": FIXED_TS,
            "frame_width": 1280,
            "frame_height": 720,
            "detections": [make_detection()],
            "metadata": {"count": 1, "model_id": "people"},
        }
        fields.update(overrides)

        return DetectionEvent(**fields)

    return make


@pytest.fixture
def make_frame(make_detection: Callable[..., Detection]) -> Callable[..., DetectionFrame]:
    def make(**overrides: Any) -> DetectionFrame:
        fields: dict[str, Any] = {
            "camera_id": uuid4(),
            "workflow_id": uuid4(),
            "revision": 1,
            "run_id": uuid4(),
            "model_id": "people",
            "timestamp": FIXED_TS,
            "frame_width": 1280,
            "frame_height": 720,
            "detections": (make_detection(),),
        }
        fields.update(overrides)

        return DetectionFrame(**fields)

    return make


@pytest.fixture
def identity() -> ExecutionIdentity:
    return ExecutionIdentity(workflow_id=uuid4(), run_id=uuid4(), camera_name="Front door")
