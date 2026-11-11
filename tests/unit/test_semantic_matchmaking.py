"""Pruebas unitarias para SemanticMatchmakingUseCase."""

import pytest

from aita.application.use_cases.semantic_matchmaking import SemanticMatchmakingUseCase
from aita.domain.exceptions import AiServiceUnavailableError
from aita.domain.models.commands import SemanticMatchCommand
from aita.domain.models.enums import TaskCategory
from aita.domain.models.results import VectorHit


@pytest.mark.asyncio
async def test_index_task_happy_path(mock_ai, mock_vectors, sample_task_text):
    # Arrange
    fake_embedding = [0.1, 0.2, 0.3, 0.4]
    mock_ai.embed.return_value = fake_embedding
    use_case = SemanticMatchmakingUseCase(ai=mock_ai, vectors=mock_vectors)

    # Act
    await use_case.index_task(sample_task_text)

    # Assert
    mock_ai.embed.assert_awaited_once()
    mock_vectors.upsert_task.assert_awaited_once_with(sample_task_text, fake_embedding)


@pytest.mark.asyncio
async def test_index_provider_happy_path(mock_ai, mock_vectors, sample_provider_profile):
    # Arrange
    fake_embedding = [0.5, 0.6, 0.7, 0.8]
    mock_ai.embed.return_value = fake_embedding
    use_case = SemanticMatchmakingUseCase(ai=mock_ai, vectors=mock_vectors)

    # Act
    await use_case.index_provider(sample_provider_profile)

    # Assert
    mock_ai.embed.assert_awaited_once()
    mock_vectors.upsert_provider.assert_awaited_once_with(sample_provider_profile, fake_embedding)


@pytest.mark.asyncio
async def test_match_happy_path(mock_ai, mock_vectors):
    # Arrange
    query_embedding = [0.1, 0.2, 0.3, 0.4]
    mock_ai.embed.return_value = query_embedding
    mock_vectors.search_providers.return_value = [
        VectorHit(provider_id="prov-1", score=0.92, display_name="Juan Fontanero"),
        VectorHit(provider_id="prov-2", score=0.81, display_name="Pedro Plomería"),
    ]

    use_case = SemanticMatchmakingUseCase(ai=mock_ai, vectors=mock_vectors)
    command = SemanticMatchCommand(
        task_id="task-999",
        task_name="Reparar tubería rota",
        task_description="Tubería goteando bajo el fregadero",
        category=TaskCategory.ARREGLOS,
        limit=5,
    )

    # Act
    matches = await use_case.match(command)

    # Assert
    assert len(matches) == 2
    assert matches[0].task_id == "task-999"
    assert matches[0].provider_id == "prov-1"
    assert matches[0].score == 0.92
    assert "0.92" in matches[0].rationale
    mock_vectors.search_providers.assert_awaited_once_with(query_embedding, 5)


@pytest.mark.asyncio
async def test_match_ai_embedding_failure(mock_ai, mock_vectors):
    # Arrange
    mock_ai.embed.side_effect = AiServiceUnavailableError("Servicio de embeddings no disponible")
    use_case = SemanticMatchmakingUseCase(ai=mock_ai, vectors=mock_vectors)
    command = SemanticMatchCommand(
        task_id="task-999",
        task_name="Tutoría matemáticas",
        task_description="Derivadas e integrales",
        category=TaskCategory.EDUCACION,
        limit=3,
    )

    # Act & Assert
    with pytest.raises(AiServiceUnavailableError):
        await use_case.match(command)

