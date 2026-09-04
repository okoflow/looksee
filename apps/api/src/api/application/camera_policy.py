from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

from shared import StartStream, WorkflowConfig

if TYPE_CHECKING:
    from uuid import UUID

    from api.domain.graph import WorkflowGraphIndex

logger = logging.getLogger(__name__)


class DesiredRunReport(Protocol):
    """Identity fields every detection frame and worker event carries for run fencing."""

    workflow_id: UUID
    revision: int
    run_id: UUID
    model_id: str


def matches_desired_run(report: DesiredRunReport, desired: StartStream) -> bool:
    if report.workflow_id != desired.workflow_id:
        return False
    if report.revision != desired.revision:
        return False
    if report.run_id != desired.run_id:
        return False

    return report.model_id == desired.config.model_id


def inference_config(index: WorkflowGraphIndex, source_node_id: str) -> WorkflowConfig:
    selected = index.selected_detect_for_source(source_node_id)

    return WorkflowConfig(
        model_id=selected.model_id,
        confidence_threshold=selected.data.confidence_threshold,
        inference_fps=selected.data.inference_fps,
    )


def start_is_current(
    current: StartStream | None,
    *,
    workflow_id: UUID,
    runtime_revision: int,
    config: WorkflowConfig,
    force_restart: bool,
) -> bool:
    if current is None:
        return False
    if force_restart:
        return False
    if current.revision != runtime_revision:
        return False
    if current.workflow_id != workflow_id:
        return False

    return current.config == config


def parse_start_command(camera_id: UUID, raw: dict[str, Any] | None) -> StartStream | None:
    """Parse a camera's persisted desired-run command; None when absent or invalid."""
    if raw is None:
        return None

    try:
        return StartStream.model_validate(raw)
    except ValueError as exc:
        logger.warning("invalid persisted start command camera=%s reason=%s", camera_id, exc)

        return None
