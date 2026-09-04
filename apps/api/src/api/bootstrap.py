"""Production adapter composition."""

from dataclasses import dataclass
from uuid import UUID

from api.adapters.actions.dispatcher import dispatch_action
from api.adapters.actions.queued import QueuedDeliverySender
from api.adapters.filesystem.model_catalog import model_catalog
from api.adapters.persistence.accounts import SqlAlchemyAccounts
from api.adapters.persistence.db import session_factory
from api.adapters.persistence.deliveries import PostgresDeliveryQueue
from api.adapters.persistence.frame_contexts import SqlAlchemyFrameContexts
from api.adapters.realtime.broadcaster import broadcaster
from api.adapters.redis.commands import publish_stream_command
from api.adapters.state.memory import runtime_state
from api.application.deliveries import DeliveryWorker, QueueingActions
from api.application.frame_processing import FrameProcessingDependencies
from api.config import Settings


@dataclass(frozen=True, slots=True)
class RuntimeServices:
    frames: FrameProcessingDependencies
    deliveries: DeliveryWorker


async def session_user_exists(user_id: UUID) -> bool:
    async with session_factory() as session:
        return await SqlAlchemyAccounts(session).by_id(user_id) is not None


def build_runtime(settings: Settings) -> RuntimeServices:
    deliveries = PostgresDeliveryQueue(session_factory)

    return RuntimeServices(
        frames=FrameProcessingDependencies(
            contexts=SqlAlchemyFrameContexts(session_factory),
            catalog=model_catalog,
            publish_command=publish_stream_command,
            runtime_state=runtime_state,
            event_cooldown_seconds=settings.event_cooldown_seconds,
            event_timezone=settings.event_timezone,
            publish_realtime=broadcaster.publish,
            run_action=QueueingActions(deliveries, dispatch_action),
        ),
        deliveries=DeliveryWorker(deliveries, QueuedDeliverySender(settings.snapshots_dir)),
    )
