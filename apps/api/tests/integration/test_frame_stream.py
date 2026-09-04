import asyncio
import os
from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from faststream.redis import RedisBroker

from api.application.frame_processing import CameraFrameContext
from api.config import settings
from api.entrypoints.redis.subscribers import create_router
from shared import Channel, StartStream, WorkflowConfig

pytestmark = pytest.mark.filterwarnings(
    "ignore:.*deprecated usage of input argument/s 'lib_(name|version)'.*:DeprecationWarning"
)


@pytest.mark.parametrize("abandoned", [False, True], ids=["new-frame", "recovered-frame"])
async def test_stream_delivers_frames_to_realtime_and_workflow(
    valkey, effects, basic_graph, make_frame, make_detection, abandoned
):
    prefix = f"integration:{uuid4().hex}:"
    stream = f"{prefix}{Channel.DETECTION_FRAMES}"
    frame = make_frame(detections=(make_detection(tracker_id=17),))
    command = StartStream(
        camera_id=frame.camera_id,
        workflow_id=frame.workflow_id,
        revision=frame.revision,
        run_id=frame.run_id,
        config=WorkflowConfig(model_id=frame.model_id),
    )
    contexts = AsyncMock()
    contexts.load.return_value = CameraFrameContext(
        workflow_id=frame.workflow_id,
        node_id="cam",
        name="Front door",
        start_command=command.model_dump(mode="json"),
        enabled=True,
        graph=basic_graph.model_dump(mode="json"),
    )
    processed = asyncio.Event()

    async def run_action(*args):
        await effects.frames.run_action(*args)
        processed.set()

    dependencies = replace(effects.frames, contexts=contexts, run_action=run_action)
    broker = RedisBroker(os.environ["TEST_REDIS_URL"])
    broker.include_router(create_router(dependencies), prefix=prefix)

    try:
        if abandoned:
            await valkey.xgroup_create(stream, settings.consumer_group, id="0-0", mkstream=True)
            message_id = await valkey.xadd(stream, {"__data__": frame.model_dump_json()})
            await valkey.xreadgroup(settings.consumer_group, "abandoned", {stream: ">"}, count=1)
            await valkey.xclaim(
                stream, settings.consumer_group, "abandoned", 0, [message_id], idle=60_001
            )

        await broker.start()

        if not abandoned:
            await broker.publish(frame, stream=stream)

        async with asyncio.timeout(5):
            await processed.wait()
            for _ in range(100):
                if not (await valkey.xpending(stream, settings.consumer_group))["pending"]:
                    break
                await asyncio.sleep(0.01)
            else:
                pytest.fail("processed frame was not acknowledged")

        assert effects.realtime_types() == ["detections", "event"]
        assert effects.realtime[0][1]["detections"][0]["tracker_id"] == 17
        assert len(effects.actions) == 1
        assert effects.actions[0][1].kind == "PERSON_DETECTED"
    finally:
        await broker.stop()
        await valkey.delete(stream)
