import json
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from shared import StartStream, StopStream, StreamCommand, WorkflowConfig

STREAM_COMMAND = TypeAdapter(StreamCommand)


@pytest.fixture
def start_fields():
    return {
        "camera_id": uuid4(),
        "workflow_id": uuid4(),
        "revision": 3,
        "run_id": uuid4(),
        "config": WorkflowConfig(model_id="dfine-m-ppe"),
    }


def test_start_stream_tags_its_type(start_fields):
    command = StartStream(**start_fields)

    assert command.type == "start_stream"


def test_stop_stream_tags_its_type_and_targets_the_active_run():
    command = StopStream(camera_id=uuid4(), revision=0)

    assert command.type == "stop_stream"
    assert command.run_id is None


@pytest.mark.parametrize("field", ["camera_id", "workflow_id", "revision", "run_id", "config"])
def test_start_stream_requires_each_field(start_fields, field):
    del start_fields[field]

    with pytest.raises(ValidationError, match=rf"{field}\s+Field required"):
        StartStream(**start_fields)


@pytest.mark.parametrize("field", ["camera_id", "revision"])
def test_stop_stream_requires_camera_and_revision(field):
    fields = {"camera_id": uuid4(), "revision": 1}
    del fields[field]

    with pytest.raises(ValidationError, match=rf"{field}\s+Field required"):
        StopStream(**fields)


def test_start_stream_rejects_unknown_fields(start_fields):
    with pytest.raises(ValidationError, match="extra_forbidden"):
        StartStream(**start_fields, priority=1)


def test_stop_stream_rejects_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        StopStream(camera_id=uuid4(), revision=0, force=True)


def test_start_stream_is_immutable(start_fields):
    command = StartStream(**start_fields)

    with pytest.raises(ValidationError, match="frozen_instance"):
        command.revision = 4


def test_stop_stream_is_immutable():
    command = StopStream(camera_id=uuid4(), revision=0)

    with pytest.raises(ValidationError, match="frozen_instance"):
        command.run_id = uuid4()


def test_start_stream_accepts_the_initial_revision(start_fields):
    start_fields["revision"] = 0

    command = StartStream(**start_fields)

    assert command.revision == 0


def test_start_stream_rejects_negative_revision(start_fields):
    start_fields["revision"] = -1

    with pytest.raises(ValidationError, match="greater_than_equal"):
        StartStream(**start_fields)


def test_stop_stream_rejects_negative_revision():
    with pytest.raises(ValidationError, match="greater_than_equal"):
        StopStream(camera_id=uuid4(), revision=-1)


def test_start_stream_requires_a_uuid_run_id(start_fields):
    start_fields["run_id"] = "run-1"

    with pytest.raises(ValidationError, match="uuid_parsing"):
        StartStream(**start_fields)


def test_start_stream_rejects_foreign_type_tag(start_fields):
    with pytest.raises(ValidationError, match="literal_error"):
        StartStream(**start_fields, type="stop_stream")


def test_start_stream_round_trips_through_json(start_fields):
    command = StartStream(**start_fields)

    restored = StartStream.model_validate_json(command.model_dump_json())

    assert restored == command


def test_start_stream_serializes_nested_config(start_fields):
    command = StartStream(**start_fields)

    payload = json.loads(command.model_dump_json())

    assert payload["type"] == "start_stream"
    assert payload["config"] == {
        "model_id": "dfine-m-ppe",
        "confidence_threshold": 0.5,
        "inference_fps": 1,
    }


def test_stop_stream_serializes_ids_as_strings():
    command = StopStream(camera_id=uuid4(), revision=2, run_id=uuid4())

    payload = json.loads(command.model_dump_json())

    assert payload == {
        "type": "stop_stream",
        "camera_id": str(command.camera_id),
        "revision": 2,
        "run_id": str(command.run_id),
    }


def test_stream_command_dispatches_on_type_tag(start_fields):
    start = StartStream(**start_fields)
    stop = StopStream(camera_id=start.camera_id, revision=4)

    parsed = [STREAM_COMMAND.validate_json(command.model_dump_json()) for command in (start, stop)]

    assert parsed == [start, stop]


def test_stream_command_rejects_unknown_type_tag():
    payload = {"type": "pause_stream", "camera_id": str(uuid4()), "revision": 0}

    with pytest.raises(ValidationError, match="union_tag_invalid"):
        STREAM_COMMAND.validate_python(payload)


def test_stream_command_requires_type_tag():
    payload = {"camera_id": str(uuid4()), "revision": 0}

    with pytest.raises(ValidationError, match="union_tag_not_found"):
        STREAM_COMMAND.validate_python(payload)
