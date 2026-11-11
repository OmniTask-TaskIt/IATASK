"""Pruebas unitarias para el caso de uso GenerateTaskDescriptionUseCase."""

import pytest

from aita.application.use_cases.generate_task_description import GenerateTaskDescriptionUseCase
from aita.domain.exceptions import AiServiceUnavailableError
from aita.domain.models.commands import GenerateTaskDescriptionCommand
from aita.domain.models.results import GeneratedTaskContent


@pytest.mark.asyncio
async def test_generate_task_description_happy_path(mock_ai):
    # Arrange
    expected = GeneratedTaskContent(
        title="Instalación de repisas de madera",
        description="Se solicita técnico para instalar 3 repisas flotantes en sala principal.",
    )
    mock_ai.generate_task_description.return_value = expected
    use_case = GenerateTaskDescriptionUseCase(ai=mock_ai)
    command = GenerateTaskDescriptionCommand(idea="instalar repisas en la sala")

    # Act
    result = await use_case.execute(command)

    # Assert
    assert result == expected
    assert result.title == "Instalación de repisas de madera"
    mock_ai.generate_task_description.assert_awaited_once_with("instalar repisas en la sala")


@pytest.mark.asyncio
async def test_generate_task_description_ai_unavailable_error(mock_ai):
    # Arrange
    mock_ai.generate_task_description.side_effect = AiServiceUnavailableError("Timeout de conexión")
    use_case = GenerateTaskDescriptionUseCase(ai=mock_ai)
    command = GenerateTaskDescriptionCommand(idea="pintar fachada de casa")

    # Act & Assert
    with pytest.raises(AiServiceUnavailableError) as exc_info:
        await use_case.execute(command)

    assert "Timeout de conexión" in exc_info.value.message


@pytest.mark.asyncio
async def test_generate_task_description_unexpected_error_degradation(mock_ai):
    # Arrange: Error de red o inesperado del cliente HTTP
    mock_ai.generate_task_description.side_effect = RuntimeError("Conexión reseteada por peer")
    use_case = GenerateTaskDescriptionUseCase(ai=mock_ai)
    command = GenerateTaskDescriptionCommand(idea="clase de refuerzo de cálculo")

    # Act & Assert: run_ai debe atrapar la excepción y degradar a AiServiceUnavailableError
    with pytest.raises(AiServiceUnavailableError) as exc_info:
        await use_case.execute(command)

    assert exc_info.value.code == "AI_SERVICE_UNAVAILABLE"

