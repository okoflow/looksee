"""Enterprise action payloads and their runnable refinements."""

from typing import ClassVar, Literal
from uuid import UUID

from pydantic import Field

from api.domain.credentials import CredentialType
from api.domain.workflow.actions import ActionNodeData


class SlackActionData(ActionNodeData):
    """Slack incoming-webhook message."""

    kind: Literal["slack_action"] = "slack_action"
    credential_type: ClassVar[CredentialType | None] = "slack_webhook"
    credential_id: str = Field(default="", max_length=36)
    message_template: str = Field(default="[{kind}] camera={camera_id} at {ts}", max_length=4096)


class RunnableSlackAction(SlackActionData):
    credential_id: UUID
