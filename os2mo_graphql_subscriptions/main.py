# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""Event handling."""
import asyncio
from datetime import datetime
from typing import AsyncGenerator
from uuid import UUID
from uuid import uuid4

import strawberry
import structlog
from fastapi import FastAPI
from prometheus_client import Info
from prometheus_fastapi_instrumentator import Instrumentator
from ramqp.mo_models import MOCallbackType
from ramqp.mo_models import MORoutingKey
from ramqp.mo_models import ObjectType
from ramqp.mo_models import PayloadType
from ramqp.mo_models import RequestType
from ramqp.mo_models import ServiceType
from ramqp.moqp import MOAMQPSystem
from starlette.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig

from .config import get_settings
from .config import Settings


logger = structlog.get_logger()


# Listener metrics, number of subscriptions, events served etc


build_information = Info("build_information", "Build inforomation")


def update_build_information(version: str, build_hash: str) -> None:
    """Update build information.

    Args:
        version: The version to set.
        build_hash: The build hash to set.

    Returns:
        None.
    """
    build_information.info(
        {
            "version": version,
            "hash": build_hash,
        }
    )


@strawberry.experimental.pydantic.type(
    model=PayloadType,
    all_fields=True,
    description="Checks whether a specific subsystem is working",
)
class EventOutput:
    pass


# TODO: Remove this - It's just used as a test
@strawberry.type
class User:
    name: str
    age: int


@strawberry.type
class Query:
    @strawberry.field
    # TODO: Remove this - It's just used as a test
    def user(self) -> User:
        return User(name="Patrick", age=100)


ServiceType = strawberry.enum(ServiceType)
ObjectType = strawberry.enum(ObjectType)
RequestType = strawberry.enum(RequestType)


def topic_matches(
    message_routing_key: MORoutingKey, listen_routing_key: MORoutingKey
) -> bool:
    if listen_routing_key.service_type != ServiceType.WILDCARD:
        if listen_routing_key.service_type != message_routing_key.service_type:
            return False
    if listen_routing_key.object_type != ObjectType.WILDCARD:
        if listen_routing_key.object_type != message_routing_key.object_type:
            return False
    if listen_routing_key.request_type != RequestType.WILDCARD:
        if listen_routing_key.request_type != message_routing_key.request_type:
            return False
    return True


class EventBus:
    def __init__(self):
        self.queues: dict[UUID, asyncio.Queue] = {}

    async def listen(
        self,
        listen_routing_key: MORoutingKey,
        uuid: UUID | None = None,
        object_uuid: UUID | None = None,
    ) -> AsyncGenerator[PayloadType, None]:
        async for message_routing_key, payload in self.listen_to_all():
            if not topic_matches(message_routing_key, listen_routing_key):
                continue
            if uuid is not None and payload.uuid != uuid:
                continue
            if object_uuid is not None and payload.object_uuid != object_uuid:
                continue
            yield payload

    async def listen_to_all(
        self,
    ) -> AsyncGenerator[tuple[MORoutingKey, PayloadType], None]:
        queue_uuid = uuid4()
        queue = asyncio.Queue()

        try:
            self.queues[queue_uuid] = queue
            while True:
                item = await queue.get()
                yield item
        finally:
            del self.queues[queue_uuid]

    async def publish_event(
        self, routing_key: MORoutingKey, payload: PayloadType
    ) -> None:
        item = (routing_key, payload)
        await asyncio.gather(*[queue.put(item) for queue in self.queues.values()])


event_bus = EventBus()


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def event_listener(
        self,
        service_type: ServiceType,
        object_type: ObjectType,
        request_type: RequestType,
        uuid: UUID | None = None,
        object_uuid: UUID | None = None,
    ) -> AsyncGenerator[EventOutput, None]:
        routing_key = MORoutingKey(service_type, object_type, request_type)
        async for payload in event_bus.listen(routing_key, uuid, object_uuid):
            yield payload

    @strawberry.subscription
    async def heartbeat(self) -> AsyncGenerator[str, None]:
        while True:
            await asyncio.sleep(1)
            yield datetime.now().isoformat()


schema = strawberry.Schema(
    query=Query,
    subscription=Subscription,
    config=StrawberryConfig(auto_camel_case=False),
)


async def callback(
    mo_routing_key: MORoutingKey,
    payload: PayloadType,
) -> None:
    """Updates event-listeners.

    Args:
        mo_routing_key: The message routing key.
        payload: The message payload.

    Returns:
        None
    """
    logger.debug(
        "Message received",
        service_type=mo_routing_key.service_type,
        object_type=mo_routing_key.object_type,
        request_type=mo_routing_key.request_type,
        payload=payload,
    )
    # TODO: Metrics
    # TODO: AsyncGenerator source here


def configure_logging(settings: Settings) -> None:
    """Setup our logging.

    Args:
        settings: Integration settings module.

    Returns:
        None
    """
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(settings.log_level.value)
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Program entrypoint.

    Starts the metrics server, then listens to AMQP messages forever.

    Returns:
        None
    """
    if settings is None:
        settings = get_settings()

    configure_logging(settings)

    graphql_app = GraphQLRouter(schema, graphiql=True)

    app = FastAPI()
    app.include_router(graphql_app, prefix="/graphql")

    if settings.enable_cors:
        print("Pog")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/")
    async def fire_event():
        await event_bus.publish_event(
            MORoutingKey(
                ServiceType.ORG_UNIT,
                ObjectType.ORG_UNIT,
                RequestType.CREATE,
            ),
            PayloadType(
                uuid=UUID("1afb982a-7b77-4f1d-ba0d-6da8316d533b"),
                object_uuid=uuid4(),
                time=datetime.now(),
            ),
        )

    update_build_information(
        version=settings.commit_tag, build_hash=settings.commit_sha
    )
    Instrumentator().instrument(app).expose(app)

    amqp_system = MOAMQPSystem()
    amqp_system.register(
        ServiceType.WILDCARD, ObjectType.WILDCARD, RequestType.WILDCARD
    )(callback)

    @app.on_event("startup")
    async def startup_amqp_consumer():
        await amqp_system.start(queue_prefix=settings.queue_prefix)

    @app.on_event("shutdown")
    async def stop_amqp_consumer():
        await amqp_system.stop()

    return app
