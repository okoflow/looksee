"""Transactional workflow use cases."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, NoReturn

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from api.adapters.persistence.models import Workflow
from api.application.assets import validate_assets_available
from api.application.camera_runtime import (
    CameraRuntimePlan,
    apply_camera_runtime_plan,
    start_workflow_cameras,
    stop_workflow_cameras,
    sync_workflow_cameras,
    teardown_workflow_cameras,
)
from api.application.credentials import validate_credentials_available
from api.application.errors import ResourceConflictError, ResourceNotFoundError
from api.application.workflow_validation import ModelCatalogReader, validate_runnable_graph
from api.domain.graph import WorkflowGraphIndex
from api.domain.workflow import WorkflowGraph

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from api.application.entitlements import Entitlements

_WORKFLOW_NAME_CONSTRAINT = "uq_workflows_name"

WorkflowName = Annotated[str, Field(min_length=1, max_length=128)]
WorkflowDescription = Annotated[str, Field(max_length=2000)]


class WorkflowPatch(BaseModel):
    """Partial update; a field only applies when the client sent it."""

    model_config = ConfigDict(extra="forbid")

    name: WorkflowName | None = None
    description: WorkflowDescription | None = None
    enabled: bool | None = None
    graph: WorkflowGraph | None = None


async def list_workflows(session: AsyncSession) -> list[Workflow]:
    result = await session.execute(
        select(Workflow)
        .options(selectinload(Workflow.cameras))
        .order_by(Workflow.created_at.desc())
    )

    return list(result.scalars().all())


async def create_workflow(
    session: AsyncSession,
    *,
    name: str,
    description: str | None,
    graph: WorkflowGraph,
) -> Workflow:
    index = WorkflowGraphIndex.build(graph)
    workflow = Workflow(
        name=name,
        description=description,
        graph=graph.model_dump(mode="json"),
    )
    session.add(workflow)

    plan = CameraRuntimePlan()
    try:
        await session.flush()
        await sync_workflow_cameras(session, workflow, index, plan)
        await session.commit()
    except IntegrityError as exc:
        await _translate_integrity_error(session, exc, name)

    await apply_camera_runtime_plan(plan)

    return await get_workflow(session, workflow.id)


async def get_workflow(
    session: AsyncSession,
    workflow_id: UUID,
    *,
    for_update: bool = False,
    load_cameras: bool = True,
) -> Workflow:
    statement = select(Workflow).where(Workflow.id == workflow_id)
    if for_update:
        statement = statement.with_for_update()
    if load_cameras:
        statement = statement.options(selectinload(Workflow.cameras)).execution_options(
            populate_existing=True
        )

    result = await session.execute(statement)
    workflow = result.scalar_one_or_none()

    if workflow is None:
        raise ResourceNotFoundError("workflow not found")

    return workflow


async def update_workflow(
    session: AsyncSession,
    workflow_id: UUID,
    patch: WorkflowPatch,
    catalog: ModelCatalogReader,
    entitlements: Entitlements,
) -> Workflow:
    workflow = await get_workflow(
        session,
        workflow_id,
        for_update=True,
        load_cameras=False,
    )

    graph_changed = patch.graph is not None
    graph = patch.graph if patch.graph is not None else WorkflowGraph.model_validate(workflow.graph)
    index = WorkflowGraphIndex.build(graph)

    enabled_changed = patch.enabled is not None
    will_be_enabled = patch.enabled if patch.enabled is not None else workflow.enabled
    if will_be_enabled and (graph_changed or enabled_changed):
        validate_runnable_graph(index, catalog, entitlements)
        await validate_assets_available(index)
        await validate_credentials_available(session, index)

    if patch.name is not None:
        workflow.name = patch.name
    if "description" in patch.model_fields_set:
        workflow.description = patch.description
    if patch.enabled is not None:
        workflow.enabled = patch.enabled
    if graph_changed:
        workflow.graph = graph.model_dump(mode="json")

    workflow_name = workflow.name

    plan = CameraRuntimePlan()
    try:
        if graph_changed:
            await sync_workflow_cameras(session, workflow, index, plan)

        if workflow.enabled and (enabled_changed or graph_changed):
            await start_workflow_cameras(session, workflow, index, plan)
        elif not workflow.enabled and enabled_changed:
            await stop_workflow_cameras(session, workflow, plan)

        await session.commit()
    except IntegrityError as exc:
        await _translate_integrity_error(session, exc, workflow_name)

    await apply_camera_runtime_plan(plan)

    return await get_workflow(session, workflow.id)


async def delete_workflow(
    session: AsyncSession,
    workflow_id: UUID,
) -> None:
    workflow = await get_workflow(
        session,
        workflow_id,
        for_update=True,
        load_cameras=False,
    )

    plan = await teardown_workflow_cameras(session, workflow)
    await session.delete(workflow)
    await session.commit()

    await apply_camera_runtime_plan(plan)


async def _translate_integrity_error(
    session: AsyncSession,
    exc: IntegrityError,
    workflow_name: str,
) -> NoReturn:
    await session.rollback()
    if not _is_workflow_name_conflict(exc):
        raise exc
    raise ResourceConflictError(f"Workflow named '{workflow_name}' already exists") from None


def _is_workflow_name_conflict(exc: IntegrityError) -> bool:
    cause: BaseException | None = exc.orig
    while cause is not None:
        if getattr(cause, "constraint_name", None) == _WORKFLOW_NAME_CONSTRAINT:
            return True
        cause = cause.__cause__

    return False
