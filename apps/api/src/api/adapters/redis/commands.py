"""Publish inference desired-state commands."""

from api.adapters.redis.broker import broker
from shared import Channel, StreamCommand

_publisher = broker.publisher(Channel.STREAM_COMMANDS)


async def publish_stream_command(command: StreamCommand) -> None:
    await _publisher.publish(command.model_dump(mode="json"))
