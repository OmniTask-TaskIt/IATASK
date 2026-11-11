"""Pruebas unitarias para EstimateFairPriceUseCase."""

import pytest

from aita.application.use_cases.estimate_fair_price import EstimateFairPriceUseCase
from aita.domain.exceptions import AiServiceUnavailableError
from aita.domain.models.commands import EstimateFairPriceCommand
from aita.domain.models.enums import TaskCategory
from aita.domain.models.results import PriceEstimate


@pytest.mark.asyncio
async def test_estimate_fair_price_happy_path(mock_ai):
    # Arrange
    expected = PriceEstimate(
        min_price=45000,
        max_price=80000,
        currency="COP",
        confidence=0.9,
        rationale="Precio promedio para cambio de grifería en zona urbana.",
    )
    mock_ai.estimate_fair_price.return_value = expected
    use_case = EstimateFairPriceUseCase(ai=mock_ai)
    command = EstimateFairPriceCommand(
        description="Cambio de grifería en lavaplatos",
        category=TaskCategory.ARREGLOS,
        location="Medellín",
    )

    # Act
    result = await use_case.execute(command)

    # Assert
    assert result == expected
    assert result.min_price == 45000
    assert result.max_price == 80000
    mock_ai.estimate_fair_price.assert_awaited_once_with(
        "Cambio de grifería en lavaplatos",
        TaskCategory.ARREGLOS,
        "Medellín",
    )


@pytest.mark.asyncio
async def test_estimate_fair_price_ai_failure_degradation(mock_ai):
    # Arrange
    mock_ai.estimate_fair_price.side_effect = TimeoutError("HTTP request timed out")
    use_case = EstimateFairPriceUseCase(ai=mock_ai)
    command = EstimateFairPriceCommand(
        description="Clases particulares de álgebra lineal",
        category=TaskCategory.EDUCACION,
        location="Cali",
    )

    # Act & Assert
    with pytest.raises(AiServiceUnavailableError):
        await use_case.execute(command)

