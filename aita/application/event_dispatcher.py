"""Traduce eventos de entrada a casos de uso.

Un fallo del modelo degrada ese paso y el consumidor sigue. Un fallo al publicar
una alerta no se oculta: la excepción sale para que el mensaje vaya a la DLQ.
"""

from collections.abc import Awaitable

from aita.application.audit import audit
from aita.application.container import UseCases
from aita.domain.exceptions import AiServiceUnavailableError, DomainValidationError
from aita.domain.models.commands import FraudCheckCommand
from aita.domain.models.enums import EventType, TextAnalysisSource
from aita.domain.models.events import (
    ChatMessageSentEvent,
    ReviewCompletedEvent,
    TaskCreatedEvent,
)
from aita.domain.models.task import TaskText


class AitaEventDispatcher:
    def __init__(self, use_cases: UseCases) -> None:
        self._use_cases = use_cases

    async def dispatch(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            raise DomainValidationError("El evento debe ser un objeto JSON.")
        event_type = payload.get("event_type")
        audit("EVENTS", f"Evento recibido: {event_type}")
        if event_type == EventType.TASK_CREATED.value:
            event = TaskCreatedEvent.model_validate(payload)
            await self._on_task_created(event)
            return
        if event_type == EventType.REVIEW_COMPLETED.value:
            event = ReviewCompletedEvent.model_validate(payload)
            await self._degrade(
                f"sentimiento de reseña {event.review.review_id}",
                self._use_cases.analyze_review_sentiment.execute(event.review),
            )
            return
        if event_type == EventType.CHAT_MESSAGE_SENT.value:
            event = ChatMessageSentEvent.model_validate(payload)
            await self._on_chat_message(event)
            return
        audit("EVENTS", f"Evento ignorado: {event_type}")

    async def _on_task_created(self, event: TaskCreatedEvent) -> None:
        task = event.task
        await self._degrade(
            f"AI Shield de tarea {task.task_id}",
            self._use_cases.fraud_detection_shield.execute(
                FraudCheckCommand(
                    source=TextAnalysisSource.TASK_DESCRIPTION,
                    source_id=task.task_id,
                    text=f"{task.task_name}\n{task.task_description}",
                    task_id=task.task_id,
                    sender_id=task.task_owner,
                )
            ),
        )
        await self._degrade(
            f"indexado de tarea {task.task_id}",
            self._use_cases.semantic_matchmaking.index_task(
                TaskText(
                    task_id=task.task_id,
                    task_name=task.task_name,
                    task_description=task.task_description,
                    category=task.category,
                )
            ),
        )

    async def _on_chat_message(self, event: ChatMessageSentEvent) -> None:
        message = event.message
        await self._degrade(
            f"AI Shield de mensaje {message.message_id}",
            self._use_cases.fraud_detection_shield.execute(
                FraudCheckCommand(
                    source=TextAnalysisSource.CHAT_MESSAGE,
                    source_id=message.message_id,
                    text=message.content,
                    task_id=event.task_id,
                    chat_id=message.chat_id,
                    sender_id=message.sender_id,
                )
            ),
        )

    async def _degrade(self, label: str, action: Awaitable[object]) -> None:
        try:
            await action
        except AiServiceUnavailableError as exc:
            audit("EVENTS", f"{label} degradado: {exc.message}")
