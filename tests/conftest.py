"""Configuración y fixtures compartidas para pruebas unitarias de AITA."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from aita.domain.models.enums import TaskCategory
from aita.domain.models.profile import ProviderProfile
from aita.domain.models.review import Review
from aita.domain.models.task import TaskText
from aita.domain.ports.outbound import IAiModelPort, IEventPublisherPort, IVectorSearchPort


@pytest.fixture
def mock_ai() -> AsyncMock:
    """Mock del puerto de IA."""
    return AsyncMock(spec=IAiModelPort)


@pytest.fixture
def mock_vectors() -> AsyncMock:
    """Mock del almacén vectorial."""
    return AsyncMock(spec=IVectorSearchPort)


@pytest.fixture
def mock_publisher() -> AsyncMock:
    """Mock del publicador de eventos."""
    return AsyncMock(spec=IEventPublisherPort)


@pytest.fixture
def sample_review() -> Review:
    return Review(
        review_id="rev-001",
        task_id="task-123",
        reviewer_id="user-buyer",
        reviewee_id="user-seller",
        rating=5,
        comment="Excelente trabajo, llegó a tiempo y resolvió todo de manera impecable.",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_task_text() -> TaskText:
    return TaskText(
        task_id="task-100",
        task_name="Reparación de fuga en baño",
        task_description="Se necesita plomero urgente para cambiar empaques y arreglar tubería.",
        category=TaskCategory.ARREGLOS,
    )


@pytest.fixture
def sample_provider_profile() -> ProviderProfile:
    return ProviderProfile(
        provider_id="prov-500",
        display_name="Carlos Plomero",
        bio="Técnico especialista con 8 años reparando tuberías.",
        skills=["plomería", "grifería", "filtraciones"],
        location="Bogotá",
        categories=[TaskCategory.ARREGLOS],
    )

