"""Workflow HTTP entrypoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from api.adapters.persistence.models import Workflow
from api.application import workflows
from api.application.workflows import WorkflowPatch
from api.entrypoints.http.dependencies import (
    EntitlementsDep,
    ModelCatalogDep,
    SessionDep,
    get_current_user,
)
from api.entrypoints.http.schemas.workflows import WorkflowCreate, WorkflowRead

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[WorkflowRead])
async def list_workflows(session: SessionDep) -> list[Workflow]:
    return await workflows.list_workflows(session)


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    session: SessionDep,
) -> Workflow:
    return await workflows.create_workflow(
        session,
        name=payload.name,
        description=payload.description,
        graph=payload.graph,
    )


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: UUID,
    session: SessionDep,
) -> Workflow:
    return await workflows.get_workflow(session, workflow_id)


@router.patch("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: UUID,
    payload: WorkflowPatch,
    session: SessionDep,
    catalog: ModelCatalogDep,
    entitlements: EntitlementsDep,
) -> Workflow:
    return await workflows.update_workflow(session, workflow_id, payload, catalog, entitlements)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    session: SessionDep,
) -> None:
    await workflows.delete_workflow(session, workflow_id)
