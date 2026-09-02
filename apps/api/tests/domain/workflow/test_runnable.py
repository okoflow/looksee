"""ensure_node_runnable: strict refinement of draft node payloads."""

import types
import typing

import pytest
from pydantic import ValidationError

from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.workflow.actions import (
    DiscordActionData,
    EmailActionData,
    LogAlertActionData,
    MqttActionData,
    SnapshotActionData,
    TelegramActionData,
    WebhookActionData,
)
from api.domain.workflow.detect import DetectData
from api.domain.workflow.filters import (
    ClassFilterData,
    DebounceFilterData,
    IfElseFilterData,
    SizeFilterData,
    TimeWindowFilterData,
    ZoneFilterData,
)
from api.domain.workflow.nodes import NodeDataUnion
from api.domain.workflow.runnable import RunnableNodeDataUnion, ensure_node_runnable
from api.domain.workflow.sources import CameraSourceData

CREDENTIAL_ID = "8d1c9d4e-4b3e-4a5f-9c2d-1e2f3a4b5c6d"
TRIANGLE = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]

RUNNABLE_NODES = [
    CameraSourceData(source_type="rtsp", url="rtsp://cam.local/live"),
    CameraSourceData(source_type="rtmp", url="rtmp://live.local/app/key"),
    CameraSourceData(source_type="srt", url="srt://relay.local:9000"),
    CameraSourceData(source_type="webrtc"),
    CameraSourceData(source_type="whep", url="https://sfu.local/whep/cam"),
    CameraSourceData(source_type="file", url="clips/demo.mp4"),
    DetectData(model_id="yolo"),
    IfElseFilterData(condition={"field": "event_kind", "value": "PERSON_DETECTED"}),
    IfElseFilterData(condition={"field": "object_class", "value": "person"}),
    IfElseFilterData(condition={"field": "detection_count"}),
    IfElseFilterData(condition={"field": "max_confidence"}),
    ZoneFilterData(polygon=TRIANGLE),
    ClassFilterData(),
    DebounceFilterData(),
    TimeWindowFilterData(),
    SizeFilterData(),
    TelegramActionData(credential_id=CREDENTIAL_ID, chat_id="42"),
    WebhookActionData(url="https://hooks.example.com/x"),
    LogAlertActionData(),
    SnapshotActionData(),
    EmailActionData(credential_id=CREDENTIAL_ID, to="ops@example.com"),
    MqttActionData(credential_id=CREDENTIAL_ID),
    DiscordActionData(credential_id=CREDENTIAL_ID),
]

NOT_RUNNABLE = [
    (CameraSourceData(), "camera_source.rtsp.url"),
    (CameraSourceData(source_type="rtsp", url="http://cam.local/live"), "camera_source.rtsp.url"),
    (CameraSourceData(source_type="rtmp"), "camera_source.rtmp.url"),
    (CameraSourceData(source_type="srt"), "camera_source.srt.url"),
    (CameraSourceData(source_type="whep"), "camera_source.whep.url"),
    (CameraSourceData(source_type="file", url="../escape"), "camera_source.file.url"),
    (DetectData(), "detect.model_id"),
    (IfElseFilterData(), "if_else_filter.condition.event_kind.value"),
    (
        IfElseFilterData(condition={"field": "object_class", "value": "  "}),
        "if_else_filter.condition.object_class.value",
    ),
    (ZoneFilterData(), "zone_filter.polygon"),
    (ZoneFilterData(polygon=TRIANGLE[:2]), "zone_filter.polygon"),
    (TimeWindowFilterData(weekdays=[]), "time_window_filter.weekdays"),
    (TelegramActionData(chat_id="42"), "telegram_action.credential_id"),
    (TelegramActionData(credential_id=CREDENTIAL_ID), "telegram_action.chat_id"),
    (WebhookActionData(), "webhook_action.url"),
    (WebhookActionData(url="ftp://hooks.example.com/x"), "webhook_action.url"),
    (EmailActionData(to="ops@example.com"), "email_action.credential_id"),
    (EmailActionData(credential_id=CREDENTIAL_ID), "email_action.to"),
    (MqttActionData(), "mqtt_action.credential_id"),
    (MqttActionData(credential_id=CREDENTIAL_ID, topic="  "), "mqtt_action.topic"),
    (DiscordActionData(), "discord_action.credential_id"),
]


def kind_of(data):
    return data.kind


def flatten(annotation):
    origin = typing.get_origin(annotation)

    if origin is typing.Annotated:
        return flatten(typing.get_args(annotation)[0])

    if origin in (types.UnionType, typing.Union):
        return [member for arg in typing.get_args(annotation) for member in flatten(arg)]

    return [annotation]


@pytest.mark.parametrize("data", RUNNABLE_NODES, ids=kind_of)
def test_accepts_fully_configured_nodes(data):
    ensure_node_runnable("n1", data)


@pytest.mark.parametrize(
    ("data", "location"), NOT_RUNNABLE, ids=[location for _, location in NOT_RUNNABLE]
)
def test_rejects_incomplete_nodes_naming_the_field(data, location):
    with pytest.raises(WorkflowGraphError) as excinfo:
        ensure_node_runnable("node-7", data)

    error = excinfo.value

    assert error.code is GraphErrorCode.NODE_NOT_RUNNABLE
    assert error.node_id == "node-7"
    assert str(error).startswith(f"node 'node-7' is not runnable: {location}: ")


def test_chains_the_validation_error():
    with pytest.raises(WorkflowGraphError) as excinfo:
        ensure_node_runnable("n1", DetectData())

    assert isinstance(excinfo.value.__cause__, ValidationError)


def test_reports_only_the_first_failure():
    data = TelegramActionData()

    with pytest.raises(WorkflowGraphError) as excinfo:
        ensure_node_runnable("n1", data)

    message = str(excinfo.value)

    assert "credential_id" in message
    assert "chat_id" not in message


def test_does_not_mutate_the_draft():
    draft = TelegramActionData(credential_id=CREDENTIAL_ID, chat_id=" 42 ")

    ensure_node_runnable("n1", draft)

    assert draft.chat_id == " 42 "
    assert draft.credential_id == CREDENTIAL_ID


def test_runnable_union_covers_every_draft_kind():
    draft_kinds = {member.model_fields["kind"].default for member in flatten(NodeDataUnion)}
    runnable_kinds = {
        member.model_fields["kind"].default for member in flatten(RunnableNodeDataUnion)
    }

    assert runnable_kinds == draft_kinds


def test_every_runnable_refines_a_draft():
    drafts = flatten(NodeDataUnion)

    for runnable_type in flatten(RunnableNodeDataUnion):
        assert any(issubclass(runnable_type, draft) for draft in drafts)


def test_extension_nodes_are_checked_against_their_runnable():
    ee_filters = pytest.importorskip("ee.workflow.filters")
    draft = ee_filters.LineCrossingFilterData()

    with pytest.raises(WorkflowGraphError) as excinfo:
        ensure_node_runnable("n1", draft)

    assert str(excinfo.value).startswith("node 'n1' is not runnable: line_crossing_filter.line")
