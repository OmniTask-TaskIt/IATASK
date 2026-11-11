"""Consumidor asíncrono de RabbitMQ para eventos entrantes a AITA."""

import asyncio
import json
import logging
from typing import Optional

import aio_pika
from aio_pika import ExchangeType

from aita.application.audit import audit
from aita.application.event_dispatcher import AitaEventDispatcher

logger = logging.getLogger(__name__)


class RabbitMqConsumer:
    """Escucha eventos de la plataforma Task It y los enruta al despachador de casos de uso."""

    def __init__(
        self,
        rabbitmq_url: str,
        dispatcher: AitaEventDispatcher,
        exchange_name: str = "taskit.events",
        dead_letter_exchange: str = "taskit.dlx",
        queue_name: str = "aita.events",
        routing_key: str = "taskit.aita.events",
    ) -> None:
        self._url = rabbitmq_url
        self._dispatcher = dispatcher
        self._exchange_name = exchange_name
        self._dlx_name = dead_letter_exchange
        self._queue_name = queue_name
        self._routing_key = routing_key
        self._connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractRobustChannel] = None
        self._consumer_tag: Optional[str] = None
        self._is_running = False

    async def start(self) -> None:
        if self._is_running:
            return

        try:
            self._connection = await aio_pika.connect_robust(self._url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)

            await self._channel.declare_exchange(
                name=self._dlx_name,
                type=ExchangeType.TOPIC,
                durable=True,
            )

            exchange = await self._channel.declare_exchange(
                name=self._exchange_name,
                type=ExchangeType.TOPIC,
                durable=True,
            )

            queue = await self._channel.declare_queue(
                name=self._queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": self._dlx_name,
                },
            )

            await queue.bind(exchange, routing_key=self._routing_key)
            await queue.bind(exchange, routing_key="taskit.*.created")
            await queue.bind(exchange, routing_key="taskit.*.sent")

            self._consumer_tag = await queue.consume(self._on_message)
            self._is_running = True
            audit("RABBITMQ-CONS", f"Consumidor iniciado en cola '{self._queue_name}'")
        except Exception as exc:
            logger.error("No se pudo iniciar el consumidor RabbitMQ: %s", exc)
            raise

    async def stop(self) -> None:
        self._is_running = False
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        audit("RABBITMQ-CONS", "Consumidor RabbitMQ detenido")

    async def _on_message(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process(requeue=False, ignore_processed=True):
            try:
                raw_body = message.body.decode("utf-8")
                print("🔥 [DEBUG RABBITMQ] ¡MENSAJE RECIBIDO EN CRUDO! ->", raw_body) 
                
                payload = json.loads(raw_body)
                
                if "eventType" in payload:
                    payload["event_type"] = payload.pop("eventType")
                if "eventId" in payload:
                    payload["event_id"] = payload.pop("eventId")
                if "occurredAt" in payload:
                    payload["occurred_at"] = payload.pop("occurredAt")
                
                payload.pop("version", None)
                payload.pop("producer", None)
                    
                if "payload" in payload and payload.get("event_type") == "ReviewCompletedEvent":
                    java_data = payload.pop("payload")
                    payload["review"] = {
                        "review_id": java_data.get("reviewId"),
                        "task_id": java_data.get("taskId"),
                        "reviewer_id": java_data.get("reviewerId"),
                        "reviewee_id": java_data.get("revieweeId"),
                        "rating": java_data.get("rating"),
                        "comment": java_data.get("comment"),
                        "created_at": java_data.get("createdAt")
                    }

                await self._dispatcher.dispatch(payload)
                await message.ack()
            except Exception as exc:
                print("❌ [DEBUG RABBITMQ] ERROR ATRAPADO EN CONSUMIDOR:", exc) 
                logger.exception("Error procesando evento en consumidor: %s", exc)
                await message.reject(requeue=False)