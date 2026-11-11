"""Estimación de un rango de precio justo."""

from aita.application.audit import audit
from aita.application.support import run_ai
from aita.domain.models.commands import EstimateFairPriceCommand
from aita.domain.models.results import PriceEstimate
from aita.domain.ports.inbound import IEstimateFairPriceUseCase
from aita.domain.ports.outbound import IAiModelPort


class EstimateFairPriceUseCase(IEstimateFairPriceUseCase):
    def __init__(self, ai: IAiModelPort) -> None:
        self._ai = ai

    async def execute(self, command: EstimateFairPriceCommand) -> PriceEstimate:
        audit(
            "AI-PRICE",
            f"Solicitud de estimación para categoría {command.category.value} en {command.location}",
        )
        result = await run_ai(
            "AI-PRICE",
            "estimación de precio",
            lambda: self._ai.estimate_fair_price(
                command.description,
                command.category,
                command.location,
            ),
        )
        return result  # type: ignore[return-value]
