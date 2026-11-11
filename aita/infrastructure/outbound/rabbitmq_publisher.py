"""Adaptador de salida para publicación de eventos en RabbitMQ con aio-pika."""

import json
import logging
from typing import Optional

import aio_pika
from aio_pika import ExchangeType, Message

from aita.application.audit import audit
from aita.domain.exceptions import IntegrationError
from aita.domain.models.events import FraudAlertDetectedEvent, ProfileOptimizationSuggestedEvent
from aita.domain.ports.outbound import IEventPublisherPort

logger = logging.getLogger(__name__)


class RabbitMqEventPublisher(IEventPublisherPort):
    """Publica eventos de AITA en el broker de RabbitMQ."""

    def __init__(
        self,
        rabbitmq_url: str,
        exchange_name: str = "taskit.events",
        security_routing_key: str = "taskit.security.events",
        profile_routing_key: str = "taskit.profile.events",
    ) -> None:
        self._url = rabbitmq_url
        self._exchange_name = exchange_name
        self._security_routing_key = security_routing_key
        self._profile_routing_key = profile_routing_key
        self._connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractRobustChannel] = None
        self._exchange: Optional[aio_pika.abc.AbstractRobustExchange] = None

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return
        try:
            self._connection = await aio_pika.connect_robust(self._url)
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                name=self._exchange_name,
                type=ExchangeType.TOPIC,
                durable=True,
            )
            audit("RABBITMQ-PUB", f"Conectado a exchange '{self._exchange_name}'")
        except Exception as exc:
            logger.error("No se pudo conectar el publicador RabbitMQ: %s", exc)
            raise IntegrationError(f"Error conectando a RabbitMQ: {exc}") from exc

    async def close(self) -> None:
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        audit("RABBITMQ-PUB", "Conexión de publicación cerrada")

    async def _publish(self, routing_key: str, payload: dict) -> None:
        if not self._exchange:
            await self.connect()

        try:
            body = json.dumps(payload, default=str).encode("utf-8")
            message = Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await self._exchange.publish(message, routing_key=routing_key)
            audit("RABBITMQ-PUB", f"Evento publicado en routing key '{routing_key}'")
        except Exception as exc:
            logger.error("Fallo publicando evento en '%s': %s", routing_key, exc)
            raise IntegrationError(f"No se pudo entregar el evento a '{routing_key}': {exc}") from exc

    async def publish_fraud_alert(self, event: FraudAlertDetectedEvent) -> None:
        payload = event.model_dump(mode="json")
        await self._publish(self._security_routing_key, payload)

    async def publish_profile_optimization(
        self,
        event: ProfileOptimizationSuggestedEvent,
    ) -> None:
        payload = event.model_dump(mode="json")
        await self._publish(self._profile_routing_key, payload)


class NullEventPublisher(IEventPublisherPort):
    """Publicador nulo cuando RabbitMQ está deshabilitado en configuración."""

    async def publish_fraud_alert(self, event: FraudAlertDetectedEvent) -> None:
        audit("NULL-PUB", f"RabbitMQ deshabilitado. Alerta no enviada: {event.event_id}")

    async def publish_profile_optimization(
        self,
        event: ProfileOptimizationSuggestedEvent,
    ) -> None:
        audit("NULL-PUB", f"RabbitMQ deshabilitado. Sugerencia no enviada: {event.event_id}")

