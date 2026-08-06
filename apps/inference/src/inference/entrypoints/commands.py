from typing import Annotated

from faststream import Context
from faststream.redis import RedisRouter

from inference.application import WorkerPool
from shared import Channel, StartStream, StopStream, StreamCommand

command_router = RedisRouter()


@command_router.subscriber(Channel.STREAM_COMMANDS)
async def handle_stream_command(
    command: StreamCommand,
    pool: Annotated[WorkerPool, Context("pool")],
) -> None:
    match command:
        case StartStream():
            await pool.start_camera(command)
        case StopStream():
            await pool.stop_camera(command)
