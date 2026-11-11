"""Pruebas unitarias para OptimizeProfileUseCase."""

import pytest

from aita.application.use_cases.optimize_profile import OptimizeProfileUseCase
from aita.domain.exceptions import AiServiceUnavailableError, IntegrationError
from aita.domain.models.events import ProfileOptimizationSuggestedEvent
from aita.domain.models.results import ProfileOptimization


@pytest.mark.asyncio
async def test_optimize_profile_happy_path(mock_ai, mock_publisher, sample_provider_profile):
    # Arrange
    optimization = ProfileOptimization(
        provider_id=sample_provider_profile.provider_id,
        suggestions=[
            "Incluye fotos de antes y después de tus reparaciones.",
            "Menciona que cuentas con herramientas profesionales de termofusión.",
        ],
        optimized_bio="Especialista en plomería residencial con 8 años de trayectoria.",
        keywords=["plomería", "reparaciones", "emergencias"],
    )
    mock_ai.suggest_profile_optimization.return_value = optimization
    use_case = OptimizeProfileUseCase(ai=mock_ai, publisher=mock_publisher)

    # Act
    result = await use_case.execute(sample_provider_profile)

    # Assert
    assert result == optimization
    assert mock_publisher.publish_profile_optimization.await_count == 1
    call_args = mock_publisher.publish_profile_optimization.call_args[0][0]
    assert isinstance(call_args, ProfileOptimizationSuggestedEvent)
    assert call_args.optimization == optimization


@pytest.mark.asyncio
async def test_optimize_profile_ai_failure(mock_ai, mock_publisher, sample_provider_profile):
    # Arrange
    mock_ai.suggest_profile_optimization.side_effect = TimeoutError("Gemini API timeout")
    use_case = OptimizeProfileUseCase(ai=mock_ai, publisher=mock_publisher)

    # Act & Assert
    with pytest.raises(AiServiceUnavailableError):
        await use_case.execute(sample_provider_profile)


@pytest.mark.asyncio
async def test_optimize_profile_publisher_error(mock_ai, mock_publisher, sample_provider_profile):
    # Arrange
    optimization = ProfileOptimization(
        provider_id=sample_provider_profile.provider_id,
        suggestions=["Mejora tu descripción."],
        optimized_bio=None,
        keywords=[],
    )
    mock_ai.suggest_profile_optimization.return_value = optimization
    mock_publisher.publish_profile_optimization.side_effect = IntegrationError("RabbitMQ no disponible")
    use_case = OptimizeProfileUseCase(ai=mock_ai, publisher=mock_publisher)

    # Act & Assert
    with pytest.raises(IntegrationError):
        await use_case.execute(sample_provider_profile)

