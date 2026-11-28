"""Action node payloads and their runnable refinements.

Each refined node splits into a private fields base plus two siblings: the
lenient draft that Studio edits and the strict Runnable* check. The siblings
declare only the fields whose type or constraints differ.
"""

from typing import Annotated, ClassVar, Literal
from uuid import UUID

from pydantic import Field, HttpUrl, StringConstraints

from api.domain.credentials import CredentialType
from api.domain.enums import AlertSeverity
from api.domain.workflow.base import WorkflowModel

RequiredChatId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]


class ActionNodeData(WorkflowModel):
    """Base contract for action payloads: delivered by one registered handler.

    Commercial actions registered through api.domain.workflow.extensions
    subclass this too, so runtime dispatch must check this base, not the
    ActionData union. Actions that talk to an external service declare the
    credential type they need; the enable-time check resolves credential_id
    against it.
    """

    credential_type: ClassVar[CredentialType | None] = None


class _TelegramActionFields(ActionNodeData):
    kind: Literal["telegram_action"] = "telegram_action"
    credential_type: ClassVar[CredentialType | None] = "telegram_bot"
    message_template: str = Field(default="[{kind}] camera={camera_id} at {ts}", max_length=4096)


class TelegramActionData(_TelegramActionFields):
    credential_id: str = Field(default="", max_length=36)
    chat_id: str = Field(default="", max_length=64)


class _WebhookActionFields(ActionNodeData):
    kind: Literal["webhook_action"] = "webhook_action"
    method: Literal["POST", "GET", "PUT"] = "POST"


class WebhookActionData(_WebhookActionFields):
    url: str = Field(default="", max_length=2048)


class LogAlertActionData(ActionNodeData):
    kind: Literal["log_alert_action"] = "log_alert_action"
    severity: AlertSeverity = AlertSeverity.WARNING
    # 0 records every event; otherwise repeats within the window are dropped per camera.
    cooldown_seconds: int = Field(default=30, ge=0, le=3600)


class SnapshotActionData(ActionNodeData):
    """Save the camera's latest frame as evidence; downstream actions get its URL."""

    kind: Literal["snapshot_action"] = "snapshot_action"
    annotate: bool = True


class _EmailActionFields(ActionNodeData):
    kind: Literal["email_action"] = "email_action"
    credential_type: ClassVar[CredentialType | None] = "smtp"
    subject_template: str = Field(default="[{kind}] on camera {camera_id}", max_length=998)
    body_template: str = Field(
        default="{kind} at {ts}\ncamera: {camera_id}\nsnapshot: {snapshot_url}",
        max_length=8192,
    )


class EmailActionData(_EmailActionFields):
    credential_id: str = Field(default="", max_length=36)
    to: str = Field(default="", max_length=320)


class _MqttActionFields(ActionNodeData):
    kind: Literal["mqtt_action"] = "mqtt_action"
    credential_type: ClassVar[CredentialType | None] = "mqtt"
    payload_template: str = Field(default="", max_length=8192)


class MqttActionData(_MqttActionFields):
    credential_id: str = Field(default="", max_length=36)
    topic: str = Field(default="looksee/events", max_length=512)


class _DiscordActionFields(ActionNodeData):
    kind: Literal["discord_action"] = "discord_action"
    credential_type: ClassVar[CredentialType | None] = "discord_webhook"
    message_template: str = Field(default="[{kind}] camera={camera_id} at {ts}", max_length=2000)


class DiscordActionData(_DiscordActionFields):
    """Discord webhook message; content is capped by Discord at 2000 characters."""

    credential_id: str = Field(default="", max_length=36)


ActionData = (
    TelegramActionData
    | WebhookActionData
    | LogAlertActionData
    | SnapshotActionData
    | EmailActionData
    | MqttActionData
    | DiscordActionData
)


class RunnableTelegramAction(_TelegramActionFields):
    credential_id: UUID
    chat_id: RequiredChatId


class RunnableWebhookAction(_WebhookActionFields):
    url: HttpUrl


class RunnableEmailAction(_EmailActionFields):
    credential_id: UUID
    to: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=320)]


class RunnableMqttAction(_MqttActionFields):
    credential_id: UUID
    topic: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]


class RunnableDiscordAction(_DiscordActionFields):
    credential_id: UUID
