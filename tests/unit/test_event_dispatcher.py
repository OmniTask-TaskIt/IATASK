"""Pruebas unitarias para AitaEventDispatcher (despacho de eventos RabbitMQ)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from aita.application.container import UseCases
from aita.application.event_dispatcher import AitaEventDispatcher
from aita.domain.exceptions import DomainValidationError
from aita.domain.models.enums import TaskCategory, TaskStatus
from aita.domain.models.results import FraudAnalysis, SentimentAnalysis
from aita.domain.models.enums import FraudRiskLevel, SentimentLabel, TextAnalysisSource


@pytest.fixture
def mock_use_cases() -> UseCases:
    return UseCases(
        generate_task_description=AsyncMock(),
        estimate_fair_price=AsyncMock(),
        semantic_matchmaking=AsyncMock(),
        analyze_review_sentiment=AsyncMock(),
        fraud_detection_shield=AsyncMock(),
        optimize_profile=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_dispatch_task_created_event(mock_use_cases):
    # Arrange
    dispatcher = AitaEventDispatcher(use_cases=mock_use_cases)
    payload = {
        "event_id": "evt-001",
        "event_type": "TaskCreatedEvent",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "task": {
            "task_id": "task-777",
            "task_name": "Arreglo de cortocircuito",
            "task_description": "Falla eléctrica general en departamento",
            "task_status": TaskStatus.ACTIVE.value,
            "task_owner": "owner-1",
            "task_assignee": None,
            "creation_date": datetime.now(timezone.utc).isoformat(),
            "category": TaskCategory.ARREGLOS.value,
            "price": 80000,
            "report_reason": None,
            "dispute_reason": None,
            "owner_approval": False,
            "assignee_approval": False,
        },
    }

    # Act
    await dispatcher.dispatch(payload)

    # Assert: Debe invocar fraud_detection_shield e index_task
    assert mock_use_cases.fraud_detection_shield.execute.await_count == 1
    assert mock_use_cases.semantic_matchmaking.index_task.await_count == 1


@pytest.mark.asyncio
async def test_dispatch_chat_message_sent_event(mock_use_cases):
    # Arrange
    dispatcher = AitaEventDispatcher(use_cases=mock_use_cases)
    payload = {
        "event_id": "evt-002",
        "event_type": "ChatMessageSentEvent",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "task_id": "task-777",
        "message": {
            "message_id": "msg-123",
            "chat_id": "chat-001",
            "sender_id": "user-a",
            "content": "Hola, ¿a qué hora puedes venir?",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

    # Act
    await dispatcher.dispatch(payload)

    # Assert: Debe invocar fraud_detection_shield para el mensaje
    assert mock_use_cases.fraud_detection_shield.execute.await_count == 1


@pytest.mark.asyncio
async def test_dispatch_review_completed_event(mock_use_cases):
    # Arrange
    dispatcher = AitaEventDispatcher(use_cases=mock_use_cases)
    payload = {
        "event_id": "evt-003",
        "event_type": "ReviewCompletedEvent",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "review": {
            "review_id": "rev-555",
            "task_id": "task-777",
            "reviewer_id": "user-a",
            "reviewee_id": "user-b",
            "rating": 5,
            "comment": "Gran servicio y muy amable.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # Act
    await dispatcher.dispatch(payload)

    # Assert: Debe invocar analyze_review_sentiment
    assert mock_use_cases.analyze_review_sentiment.execute.await_count == 1


@pytest.mark.asyncio
async def test_dispatch_invalid_payload_raises_error(mock_use_cases):
    # Arrange
    dispatcher = AitaEventDispatcher(use_cases=mock_use_cases)

    # Act & Assert
    with pytest.raises(DomainValidationError):
        await dispatcher.dispatch("no es un dict")

