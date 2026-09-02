"""FilterRuntime value object and RuntimeState protocol shape."""

from dataclasses import FrozenInstanceError
from zoneinfo import ZoneInfo

import pytest

from api.domain.workflow.runtime import FilterRuntime, RuntimeState


def test_runtime_carries_the_evaluation_context(make_runtime, make_state):
    state = make_state()

    runtime = make_runtime(state=state, node_id="zone-1", timezone="Europe/Berlin")

    assert runtime.node_id == "zone-1"
    assert runtime.timezone == ZoneInfo("Europe/Berlin")
    assert runtime.state is state


def test_runtime_is_frozen(make_runtime):
    runtime = make_runtime()

    with pytest.raises(FrozenInstanceError):
        runtime.node_id = "other"


def test_runtime_has_no_instance_dict(make_runtime):
    assert not hasattr(make_runtime(), "__dict__")


def test_runtime_requires_every_field():
    with pytest.raises(TypeError):
        FilterRuntime(node_id="zone-1")


def test_state_protocol_names_three_operations():
    members = {name for name in dir(RuntimeState) if not name.startswith("_")}

    assert members == {"swap_track_point", "dwell_seconds", "debounce_allows"}


def test_state_double_answers_every_operation(make_state, make_runtime, make_event):
    state = make_state(debounce=False, dwell=12.5)
    runtime = make_runtime(state=state)
    event = make_event()
    args = (runtime.workflow_id, runtime.run_id, runtime.node_id, event.camera_id)

    swapped = state.swap_track_point(*args, 7, (0.5, 0.5), event.ts)
    dwell = state.dwell_seconds(*args, 7, True, event.ts)
    allowed = state.debounce_allows(*args, 30)

    assert swapped is None
    assert dwell == 12.5
    assert allowed is False
    assert [call[0] for call in state.calls] == [
        "swap_track_point",
        "dwell_seconds",
        "debounce_allows",
    ]
