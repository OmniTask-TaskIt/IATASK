"""Eventos de dominio que AITA consume o publica.

El sobre es el mismo para todos: identificador, tipo y marca de tiempo.
El adaptador de mensajería serializa estos modelos; no añade campos de negocio.
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from aita.domain.models.base import DomainModel
from aita.domain.models.chat import Message
from aita.domain.models.enums import AuditReaction, EventType
from aita.domain.models.results import FraudAnalysis, ProfileOptimization
from aita.domain.models.review import Review
from aita.domain.models.task import Task


class DomainEvent(DomainModel):
    event_id: str = Field(min_length=1)
    event_type: EventType
    occurred_at: datetime


class TaskCreatedEvent(DomainEvent):
    """Publicado por el microservicio de Tareas. AITA lo consume."""

    event_type: Literal[EventType.TASK_CREATED] = EventType.TASK_CREATED
    task: Task


class ReviewCompletedEvent(DomainEvent):
    """Publicado por el flujo de reseñas. AITA lo consume."""

    event_type: Literal[EventType.REVIEW_COMPLETED] = EventType.REVIEW_COMPLETED
    review: Review


class ChatMessageSentEvent(DomainEvent):
    """Publicado por el módulo de chat. AITA lo consume."""

    event_type: Literal[EventType.CHAT_MESSAGE_SENT] = EventType.CHAT_MESSAGE_SENT
    message: Message
    task_id: str = Field(min_length=1)


class FraudAlertDetectedEvent(DomainEvent):
    """Publicado por AITA hacia Auditoría HITL en `taskit.security.events`."""

    event_type: Literal[EventType.FRAUD_ALERT_DETECTED] = EventType.FRAUD_ALERT_DETECTED
    analysis: FraudAnalysis
    recommended_action: AuditReaction = AuditReaction.UNDER_REVIEW


class ProfileOptimizationSuggestedEvent(DomainEvent):
    """Publicado por AITA hacia Perfiles en `taskit.profile.events`."""

    event_type: Literal[EventType.PROFILE_OPTIMIZATION_SUGGESTED] = (
        EventType.PROFILE_OPTIMIZATION_SUGGESTED
    )
    optimization: ProfileOptimization
