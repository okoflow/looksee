"""Optional commercial node types contributed by the ee distribution.

This module and api.application.entitlements are the only two places the
open codebase may import ee; ee imports core submodules freely, never the
reverse elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.domain.workflow.base import WorkflowModel


@dataclass(frozen=True, slots=True)
class NodeExtension:
    """One commercial node type: draft payload, runnable refinement, licensed feature.

    Action extensions also carry their delivery handler; the dispatcher
    registers it alongside the built-in ones.
    """

    kind: str
    feature: str
    draft: type[WorkflowModel]
    runnable: type[WorkflowModel]
    deliver: str | None = None


def _load_node_extensions() -> tuple[NodeExtension, ...]:
    # ee re-imports this module for NodeExtension, so the class above must be
    # defined before this import runs.
    try:
        from ee.workflow import NODE_EXTENSIONS
    except ImportError:
        return ()

    return NODE_EXTENSIONS


NODE_EXTENSIONS: tuple[NodeExtension, ...] = _load_node_extensions()

LICENSED_FEATURES_BY_KIND: dict[str, str] = {
    extension.kind: extension.feature for extension in NODE_EXTENSIONS
}
